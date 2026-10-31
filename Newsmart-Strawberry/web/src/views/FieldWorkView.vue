<template>
  <main class="field-work">
    <header><h2>采集与模型工作台</h2><a-button :loading="busy" title="刷新" @click="load"><RefreshCw :size="16" /></a-button></header>
    <a-alert v-if="error" :message="error" type="error" closable @close="error = ''" />
    <a-tabs v-model:active-key="tab" @change="load">
      <a-tab-pane key="capture" tab="自动采集" />
      <a-tab-pane key="backup" tab="数据备份" />
      <a-tab-pane key="shared" tab="团队共享" />
      <a-tab-pane key="model" tab="模型版本" />
      <a-tab-pane key="detection" tab="识别追溯" />
    </a-tabs>
    <section class="toolbar">
      <label v-if="['capture', 'backup', 'detection'].includes(tab)">照片集
        <a-select v-model:value="albumId" :options="albums.map(a => ({ value: a.id, label: `${a.name} (${a.cluster_code})` }))" @change="albumChanged" />
      </label>
      <template v-if="tab === 'capture'">
        <label>摄像头编号<a-input-number v-model:value="cameraId" :min="0" :max="32" /></label>
        <label>间隔（秒）<a-input-number v-model:value="interval" :min="10" :max="86400" /></label>
        <a-button type="primary" :disabled="!albumId" :loading="busy" @click="act(() => createCapture({ album_id: albumId, camera_id: cameraId, interval_seconds: interval }))"><Plus :size="16" />创建任务</a-button>
      </template>
      <template v-if="tab === 'backup'">
        <label>开始时间<input v-model="start" type="datetime-local" /></label>
        <label>结束时间<input v-model="end" type="datetime-local" /></label>
        <a-button type="primary" :disabled="!albumId || !start || !end" :loading="busy" @click="backup"><Archive :size="16" />创建备份</a-button>
      </template>
      <template v-if="tab === 'shared'">
        <label>共享目录<a-auto-complete v-model:value="folder" :options="folders.map(f => ({ value: f.name }))" @select="load" /></label>
        <label>版本说明<a-input v-model:value="versionNote" :maxlength="500" /></label>
        <a-button :loading="busy" @click="act(() => createSharedFolder(folder))"><FolderPlus :size="16" />创建目录</a-button>
        <a-button type="primary" :loading="busy" @click="fileInput.click()"><Upload :size="16" />上传文件</a-button>
      </template>
      <template v-if="['model', 'detection'].includes(tab)">
        <label>识别任务<a-segmented v-model:value="task" :options="[{ value: 'maturity', label: '成熟度' }, { value: 'disease', label: '病虫害' }]" /></label>
      </template>
      <template v-if="tab === 'model'">
        <a-checkbox v-model:checked="trusted">模型来自可信训练环境</a-checkbox>
        <a-button type="primary" :disabled="!trusted || !isAdmin" :loading="busy" @click="fileInput.click()"><Upload :size="16" />上传并校验</a-button>
      </template>
      <template v-if="tab === 'detection'">
        <label>原图<a-select v-model:value="photoId" :options="photos.map(p => ({ value: p.id, label: `${p.filename} · ${new Date(p.captured_at).toLocaleString()}` }))" /></label>
        <a-button :disabled="photoPage <= 1" @click="changePhotos(-1)">上一页</a-button>
        <a-button :disabled="photoPage * 24 >= photoTotal" @click="changePhotos(1)">下一页</a-button>
        <label>置信度<a-input-number v-model:value="threshold" :min="0.05" :max="0.99" :step="0.05" /></label>
        <a-button type="primary" :disabled="!photoId" :loading="busy" @click="act(() => runDetection({ photo_id: photoId, task, threshold }))"><ScanLine :size="16" />识别原图</a-button>
      </template>
      <input ref="fileInput" hidden type="file" :accept="tab === 'model' ? '.pt,.onnx' : undefined" @change="upload" />
    </section>
    <a-table :data-source="rows" :columns="columns" row-key="id" :loading="busy" :pagination="false" :scroll="{ x: 1000 }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'"><span>{{ record.name }}</span><small>{{ record.id }}</small></template>
        <template v-if="column.key === 'status'"><a-tag :color="statusColor(record.status)">{{ statusLabels[record.status] || record.status }}</a-tag></template>
        <template v-if="column.key === 'time'">{{ new Date(record.created_at).toLocaleString() }}</template>
        <template v-if="column.key === 'detail'"><span class="detail">{{ record.data.error || record.data.sha256 || record.data.last_capture || record.data.model_id || record.parent_id }}</span></template>
        <template v-if="column.key === 'actions'">
          <a-space wrap>
            <a-button size="small" title="详情" @click="detail = record"><Eye :size="15" /></a-button>
            <template v-if="tab === 'capture'">
              <a-popconfirm :title="record.status === 'running' ? '停止自动采集？' : '访问绑定摄像头并开始定时采集？'" @confirm="act(() => captureAction(record.id, record.status === 'running' ? 'stop' : 'start'))"><a-button size="small">{{ record.status === 'running' ? '停止' : '启动' }}</a-button></a-popconfirm>
            </template>
            <a-button v-if="['backup', 'shared'].includes(tab) && record.status === 'ready'" size="small" title="下载" @click="act(() => downloadFieldFile(record))"><Download :size="15" /></a-button>
            <a-popconfirm v-if="tab === 'shared' && (isAdmin || record.owner_uid === String(userStore.uid))" title="删除此版本文件？" @confirm="act(() => removeShared(record.id))"><a-button size="small" danger title="删除"><Trash2 :size="15" /></a-button></a-popconfirm>
            <a-popconfirm v-if="tab === 'model' && isAdmin && ['validated', 'inactive'].includes(record.status)" title="切换到此模型版本？" @confirm="act(() => activateModel(record.id))"><a-button size="small">{{ record.status === 'inactive' ? '回退至此版本' : '启用' }}</a-button></a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>
    <footer><a-button :disabled="page <= 1 || busy" @click="page--; load()">上一页</a-button><span>第 {{ page }} 页</span><a-button :disabled="rows.length < 100 || busy" @click="page++; load()">下一页</a-button></footer>
    <a-modal :open="!!detail" title="记录详情" :footer="null" :width="760" @cancel="detail = null"><DetectionEvidence v-if="detail?.kind === 'detection'" :record="detail" /><pre>{{ JSON.stringify(detail, null, 2) }}</pre></a-modal>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { Archive, Download, Eye, FolderPlus, Plus, RefreshCw, ScanLine, Trash2, Upload } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import DetectionEvidence from '@/components/DetectionEvidence.vue'
import { listAlbums, listAlbumPhotos } from '@/apis/album_api'
import { fieldRecords, createCapture, captureAction, createBackup, createSharedFolder, uploadFieldFile, downloadFieldFile, activateModel, runDetection, removeShared } from '@/apis/field_work_api'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)
const tab = ref('capture'), rows = ref([]), albums = ref([]), folders = ref([]), photos = ref([])
const albumId = ref(), photoId = ref(), cameraId = ref(0), interval = ref(60), threshold = ref(0.5)
const task = ref('maturity'), trusted = ref(false), folder = ref(''), fileInput = ref(null)
const versionNote = ref('')
const busy = ref(false), error = ref(''), detail = ref(null), page = ref(1), photoPage = ref(1), photoTotal = ref(0)
const localDate = (value) => new Date(value.getTime() - value.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
const start = ref(localDate(new Date(Date.now() - 86400000))), end = ref(localDate(new Date()))
const columns = [{ title: '名称 / 版本', key: 'name', width: 230 }, { title: '状态', key: 'status', width: 120 }, { title: '创建时间', key: 'time', width: 180 }, { title: '校验 / 关联信息', key: 'detail', width: 260 }, { title: '操作', key: 'actions', width: 210 }]
const statusLabels = { ready: '已完成', paused: '已暂停', running: '运行中', failed: '失败', interrupted: '已中断', active: '已启用', inactive: '历史版本', validated: '校验通过', validating: '校验中' }
const statusColor = (status) => ['failed', 'interrupted'].includes(status) ? 'error' : ['ready', 'active', 'validated'].includes(status) ? 'success' : 'default'
async function load() {
  const generation = ++loadGeneration
  busy.value = true
  error.value = ''
  try {
    const parent = ['capture', 'backup', 'detection'].includes(tab.value) ? albumId.value : tab.value === 'shared' ? folder.value : undefined
    const result = await fieldRecords(tab.value, parent, (page.value - 1) * 100)
    if (generation !== loadGeneration) return
    rows.value = result
    if (tab.value === 'shared') folders.value = await fieldRecords('folder')
  } catch (e) { if (generation === loadGeneration) error.value = e.message || '加载失败' } finally { if (generation === loadGeneration) busy.value = false }
}
let loadGeneration = 0
async function act(fn) {
  busy.value = true
  try { await fn(); message.success('操作完成'); await load() } catch (e) { error.value = e.message || '操作失败' } finally { busy.value = false }
}
async function albumChanged() {
  photoPage.value = 1
  photoId.value = undefined
  await changePhotos(0)
  await load()
}
async function changePhotos(delta) {
  if (!albumId.value) return
  photoPage.value += delta
  try { const result = await listAlbumPhotos(albumId.value, photoPage.value); photos.value = result.items; photoTotal.value = result.total } catch (e) { error.value = e.message }
}
async function upload(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  await act(() => uploadFieldFile(tab.value === 'model' ? 'models' : 'shared', file, tab.value === 'model' ? { task: task.value, trusted: trusted.value } : { folder: folder.value, version_note: versionNote.value }))
}
async function backup() {
  await act(() => createBackup({ album_id: albumId.value, start: new Date(start.value).toISOString(), end: new Date(end.value).toISOString() }))
}
watch(tab, () => { page.value = 1 })
onMounted(async () => {
  try {
    let index = 1, result
    do { result = await listAlbums(index++); albums.value.push(...result.items) } while (albums.value.length < result.total)
    await load()
  } catch (e) { error.value = e.message }
})
</script>

<style scoped lang="less">
.field-work { padding: 24px; height: 100%; overflow: auto; background: var(--gray-0); color: var(--color-text); }
header, footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
h2 { font-size: 22px; margin: 0 0 12px; }
.toolbar { display: flex; flex-wrap: wrap; gap: 16px; align-items: end; margin: 16px 0 24px; }
label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; max-width: 100%; }
label > .ant-select { width: 240px; max-width: 100%; }
input[type='datetime-local'] { padding: 5px 8px; border: 1px solid var(--gray-200); border-radius: 6px; background: var(--gray-0); color: var(--color-text); }
.ant-btn { display: inline-flex; align-items: center; gap: 6px; }
small, .detail { display: block; overflow-wrap: anywhere; font-size: 12px; color: var(--color-text-secondary); }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 65vh; overflow: auto; }
footer { justify-content: end; margin-top: 16px; }
@media (max-width: 600px) { .field-work { padding: 14px; } .toolbar label { width: 100%; } }
</style>
