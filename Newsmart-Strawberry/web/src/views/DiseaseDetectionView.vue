<template>
  <div class="disease-center layout-container">
    <PageHeader title="病虫害识别" :show-border="true">
      <template #info>
        <a-tag :color="activeModel ? 'success' : 'warning'">{{ activeModel ? activeModel.name : '未启用模型' }}</a-tag>
        <a-button @click="modelOpen = true"><Upload :size="16" />模型导入</a-button>
      </template>
    </PageHeader>
    <main class="disease-content">
      <a-alert v-if="error" :message="error" type="error" closable @close="error = ''" />
      <section class="detect-action-bar">
        <div class="action-left">
          <label>照片集<a-select v-model:value="albumId" :disabled="busy" :options="albums.map(a => ({ value: a.id, label: `${a.name} · ${a.cluster_code}` }))" @change="changeAlbum" /></label>
          <a-button title="新建照片集" :disabled="busy" @click="albumOpen = true"><Plus :size="16" /></a-button>
          <label>原图<a-select v-model:value="photoId" :disabled="busy || !albumId" :options="photos.map(p => ({ value: p.id, label: p.filename }))" @change="selectPhoto" /></label>
          <div class="photo-pagination">
            <a-button title="上一页原图" :disabled="busy || photoPage === 1" @click="loadPhotos(-1)"><ChevronLeft :size="16" /></a-button>
            <a-button title="下一页原图" :disabled="busy || photoPage * 24 >= photoTotal" @click="loadPhotos(1)"><ChevronRight :size="16" /></a-button>
          </div>
          <label>置信度<a-input-number v-model:value="threshold" :disabled="busy" :min="0.05" :max="0.99" :step="0.05" /></label>
        </div>
        <div class="action-right">
          <a-button :disabled="busy || !albumId" @click="imageInput.click()"><Upload :size="16" />上传图片</a-button>
          <a-button :disabled="busy" @click="toggleCamera"><Video :size="16" />{{ stream ? '关闭摄像头' : '开启摄像头' }}</a-button>
          <a-button v-if="stream" :disabled="busy || !cameraReady" @click="capture"><Camera :size="16" />拍照保存</a-button>
          <a-button type="primary" :loading="busy" :disabled="(stream ? !cameraReady : !photoId) || !activeModel || threshold == null" @click="detect"><ScanLine :size="16" />开始识别</a-button>
          <input ref="imageInput" hidden type="file" accept="image/jpeg,image/png,image/webp" @change="uploadImage" />
        </div>
      </section>
      <section class="preview-result-section">
        <div class="camera-panel">
          <div class="panel-header"><div class="section-title"><Camera :size="18" /><h3>原图与识别标注</h3></div></div>
          <video v-show="stream" ref="video" autoplay muted playsinline @loadeddata="cameraReady = !!stream" @emptied="cameraReady = false" />
          <DetectionEvidence v-if="result && !stream" :record="result" />
          <img v-else-if="preview && !stream" :src="preview" alt="待识别原图" class="preview-image" />
          <a-empty v-else-if="!stream" description="暂无原图" />
        </div>
        <div class="result-panel">
          <div class="panel-header"><div class="section-title"><ScanLine :size="18" /><h3>检测结果</h3></div><a-tag v-if="result">{{ result.status === 'ready' ? '已完成' : '失败' }}</a-tag></div>
          <a-spin v-if="busy" class="result-loading" />
          <template v-else-if="result?.status === 'ready'">
            <div class="result-summary"><strong>{{ result.data.detections.length }}</strong><span>检测目标</span><span>{{ new Date(result.created_at).toLocaleString() }}</span></div>
            <div class="class-counts"><a-tag v-for="(count, name) in result.data.counts" :key="name">{{ name }}：{{ count }}</a-tag></div>
            <a-button type="primary" @click="router.push({ path: '/agent', query: { disease_record: result.id } })">引用结果到 AI 问答</a-button>
            <a-table size="small" :data-source="result.data.detections.map((d, i) => ({ ...d, key: i }))" :columns="resultColumns" :pagination="false" :scroll="{ y: 320 }" />
            <a-empty v-if="!result.data.detections.length" description="当前阈值下未检出目标" />
          </template>
          <a-alert v-else-if="result?.status === 'failed'" :message="result.data.error || '识别失败'" type="error" />
          <a-empty v-else description="暂无检测结果" />
        </div>
      </section>
      <section class="history-section">
        <div class="panel-header"><div class="section-title"><History :size="18" /><h3>识别记录</h3></div><a-button title="刷新记录" :disabled="busy" @click="refresh"><RefreshCw :size="16" /></a-button></div>
        <a-table :data-source="history" :columns="historyColumns" row-key="id" :pagination="false" :scroll="{ x: 650 }">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'time'">{{ new Date(record.created_at).toLocaleString() }}</template>
            <template v-if="column.key === 'counts'">{{ Object.entries(record.data.counts || {}).map(([k, v]) => `${k}: ${v}`).join('，') || '—' }}</template>
            <template v-if="column.key === 'status'">{{ record.status === 'ready' ? '已完成' : record.status === 'failed' ? '失败' : '处理中' }}</template>
            <template v-if="column.key === 'actions'"><a-button title="查看识别记录" :disabled="busy" @click="viewRecord(record)"><Eye :size="16" /></a-button></template>
          </template>
        </a-table>
        <footer><a-button :disabled="busy || historyPage === 1" @click="changeHistory(-1)">上一页</a-button><span>第 {{ historyPage }} 页</span><a-button :disabled="busy || !historyMore" @click="changeHistory(1)">下一页</a-button></footer>
      </section>
    </main>
    <a-modal v-model:open="albumOpen" title="新建照片集" :confirm-loading="busy" :closable="!busy" :mask-closable="!busy" @ok="saveAlbum">
      <a-alert v-if="error" :message="error" type="error" />
      <a-form layout="vertical">
        <a-form-item label="照片集名称" required><a-input v-model:value="albumName" :maxlength="128" /></a-form-item>
        <a-form-item label="草莓簇编号" required><a-input v-model:value="clusterCode" :maxlength="64" /></a-form-item>
      </a-form>
    </a-modal>
    <a-modal v-model:open="modelOpen" title="病虫害模型" :footer="null" :width="800" :closable="!busy" :mask-closable="!busy">
      <a-alert v-if="error" :message="error" type="error" />
      <div class="model-toolbar">
        <a-checkbox v-model:checked="trusted" :disabled="busy || !user.isAdmin">确认模型来源可信（PT 可执行代码）</a-checkbox>
        <a-button :disabled="!trusted || !user.isAdmin" :loading="busy" @click="modelInput.click()"><Upload :size="16" />导入并校验</a-button>
        <input ref="modelInput" hidden type="file" accept=".pt,.onnx" @change="importModel" />
      </div>
      <a-list :data-source="models">
        <template #renderItem="{ item }"><a-list-item>
          <a-list-item-meta :title="item.name" :description="item.data.error || (item.data.classes || []).join('、')" />
          <a-tag>{{ modelStatuses[item.status] || item.status }}</a-tag>
          <a-popconfirm v-if="user.isAdmin && ['validated', 'inactive'].includes(item.status)" title="启用此病虫害模型？" @confirm="enableModel(item.id)"><a-button :disabled="busy">启用</a-button></a-popconfirm>
        </a-list-item></template>
      </a-list>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { message } from 'ant-design-vue'
import { useRouter } from 'vue-router'
import { Camera, ChevronLeft, ChevronRight, Eye, History, Plus, RefreshCw, ScanLine, Upload, Video } from 'lucide-vue-next'
import PageHeader from '@/components/shared/PageHeader.vue'
import DetectionEvidence from '@/components/DetectionEvidence.vue'
import { useUserStore } from '@/stores/user'
import { createAlbum, getAlbumPhotoFile, listAlbums, listAlbumPhotos, uploadAlbumPhoto } from '@/apis/album_api'
import { activateModel, fieldRecords, runDetection, uploadFieldFile } from '@/apis/field_work_api'

const user = useUserStore()
const router = useRouter()
const albums = ref([]), photos = ref([]), models = ref([]), history = ref([])
const albumId = ref(), photoId = ref(), result = ref(null), threshold = ref(0.5)
const busy = ref(false), error = ref(''), preview = ref(''), modelOpen = ref(false), trusted = ref(false)
const photoPage = ref(1), photoTotal = ref(0), historyPage = ref(1), historyMore = ref(false)
const imageInput = ref(), modelInput = ref(), video = ref(), stream = shallowRef(null)
const cameraReady = ref(false), albumOpen = ref(false), albumName = ref(''), clusterCode = ref('')
let disposed = false
const activeModel = computed(() => models.value.find(m => m.status === 'active'))
const modelStatuses = { active: '已启用', inactive: '历史版本', validated: '校验通过', failed: '校验失败', validating: '校验中' }
const resultColumns = [{ title: '类别', dataIndex: 'label' }, { title: '置信度', dataIndex: 'confidence', customRender: ({ text }) => `${(text * 100).toFixed(1)}%` }]
const historyColumns = [{ title: '检测时间', key: 'time', width: 190 }, { title: '识别结果', key: 'counts' }, { title: '状态', key: 'status', width: 90 }, { title: '操作', key: 'actions', width: 80 }]
async function act(fn) {
  if (busy.value) return
  busy.value = true; error.value = ''
  try { await fn() } catch (e) { error.value = e.message || '操作失败' } finally { busy.value = false }
}
function clearPreview() { if (preview.value) URL.revokeObjectURL(preview.value); preview.value = '' }
async function showPhoto() {
  clearPreview(); result.value = null
  if (photoId.value) {
    const blob = await getAlbumPhotoFile(photoId.value)
    if (!disposed) preview.value = URL.createObjectURL(blob)
  }
}
async function fetchPhotos() {
  if (!albumId.value) return
  const data = await listAlbumPhotos(albumId.value, photoPage.value)
  photos.value = data.items; photoTotal.value = data.total
}
async function fetchHistory() {
  if (!albumId.value) return
  const rows = await fieldRecords('detection', albumId.value, (historyPage.value - 1) * 100)
  historyMore.value = rows.length === 100
  history.value = rows.filter(r => r.data.task === 'disease')
}
async function fetchModels() {
  const all = []; let rows
  do { rows = await fieldRecords('model', 'disease', all.length); all.push(...rows) } while (rows.length === 100)
  models.value = all
}
function changeAlbum() { return act(async () => { photoPage.value = 1; historyPage.value = 1; photoId.value = undefined; result.value = null; clearPreview(); await fetchPhotos(); await fetchHistory() }) }
function selectPhoto() { return act(async () => { stopCamera(); await showPhoto() }) }
function loadPhotos(delta) { return act(async () => { photoPage.value += delta; await fetchPhotos() }) }
function changeHistory(delta) { return act(async () => { historyPage.value += delta; await fetchHistory() }) }
function refresh() { return act(async () => { await fetchModels(); await fetchHistory() }) }
function saveAlbum() { return act(async () => {
  if (!albumName.value.trim()) throw new Error('请输入照片集名称')
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(clusterCode.value.trim())) throw new Error('草莓簇编号只能包含字母、数字、下划线和短横线')
  const album = await createAlbum({ name: albumName.value.trim(), cluster_code: clusterCode.value.trim() })
  albums.value.push(album); albumId.value = album.id
  photoId.value = undefined; result.value = null; clearPreview()
  photoPage.value = 1; historyPage.value = 1
  await fetchPhotos(); await fetchHistory()
  albumOpen.value = false; albumName.value = ''; clusterCode.value = ''
}) }
async function storeImage(file) {
  if (!albumId.value) throw new Error('请先选择照片集')
  if (file.size > 20 * 1024 ** 2) throw new Error('图片不得超过 20 MB')
  const photo = await uploadAlbumPhoto(albumId.value, file)
  photoPage.value = 1; await fetchPhotos()
  if (!photos.value.some(p => p.id === photo.id)) photos.value.unshift(photo)
  photoId.value = photo.id; stopCamera(); await showPhoto()
  message.success('原图已保存')
}
function uploadImage(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (file) return act(() => storeImage(file))
}
function detect() { return act(async () => {
  if (stream.value) await captureFrame()
  if (!photoId.value) throw new Error('请先选择原图或拍照')
  result.value = null
  try { result.value = await runDetection({ photo_id: photoId.value, task: 'disease', threshold: threshold.value }) }
  finally { await fetchHistory() }
}) }
function viewRecord(row) { stopCamera(); photoId.value = undefined; result.value = row }
function importModel(event) {
  const file = event.target.files?.[0]; event.target.value = ''
  if (!file) return
  return act(async () => {
    if (file.size > 200 * 1024 ** 2) throw new Error('模型不得超过 200 MB')
    try { await uploadFieldFile('models', file, { task: 'disease', trusted: trusted.value }); message.success('模型校验通过，请选择启用') }
    finally { await fetchModels() }
  })
}
function enableModel(id) { return act(async () => { await activateModel(id); await fetchModels(); message.success('病虫害模型已启用') }) }
function stopCamera() {
  cameraReady.value = false
  stream.value?.getTracks().forEach(t => t.stop()); stream.value = null
  if (video.value) video.value.srcObject = null
}
function toggleCamera() { return act(async () => {
  if (stream.value) { stopCamera(); return }
  if (!navigator.mediaDevices?.getUserMedia) throw new Error('浏览器不支持摄像头，请通过 localhost 或 HTTPS 访问')
  const media = await navigator.mediaDevices.getUserMedia({ video: true, audio: false })
  if (disposed) { media.getTracks().forEach(t => t.stop()); return }
  stream.value = media; cameraReady.value = false
  media.getVideoTracks().forEach(track => track.addEventListener('ended', () => { if (stream.value === media) stopCamera() }, { once: true }))
  try {
    await nextTick()
    if (disposed) { stopCamera(); return }
    video.value.srcObject = media
    await video.value.play()
    cameraReady.value = !!stream.value && video.value.readyState >= 2
  } catch (e) { stopCamera(); throw e }
}) }
async function captureFrame() {
  if (!albumId.value) { albumOpen.value = true; throw new Error('请先新建或选择照片集，保存本次拍摄的原图') }
  if (!stream.value || !cameraReady.value || !video.value?.videoWidth) throw new Error('摄像头尚未就绪')
  const canvas = document.createElement('canvas')
  canvas.width = video.value.videoWidth; canvas.height = video.value.videoHeight
  canvas.getContext('2d').drawImage(video.value, 0, 0)
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.95))
  if (!blob) throw new Error('拍照失败')
  await storeImage(new File([blob], `disease-${Date.now()}.jpg`, { type: 'image/jpeg' }))
}
function capture() { return act(captureFrame) }
onMounted(() => act(async () => {
  await fetchModels()
  let page = 1, data
  do { data = await listAlbums(page++); albums.value.push(...data.items) } while (albums.value.length < data.total)
  if (albums.value.length) { albumId.value = albums.value[0].id; await fetchPhotos(); await fetchHistory() }
}))
onUnmounted(() => { disposed = true; stopCamera(); clearPreview() })
</script>

<style scoped lang="less">
/* Layout and tokens follow TomatoMaturityCenterView's detection panels. */
.disease-center { min-height: 100%; background: var(--gray-25); }
.disease-content { display: flex; flex-direction: column; gap: 16px; padding: var(--page-padding); }
.detect-action-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 18px; border: 1px solid var(--gray-150); border-radius: 8px; background: var(--gray-0); }
.action-left, .action-right { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.photo-pagination { display: flex; gap: 6px; }
label { display: flex; flex-direction: column; gap: 6px; color: var(--gray-600); font-size: 13px; }
label .ant-select { width: 220px; max-width: 100%; }
.preview-result-section { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; min-height: 400px; }
.camera-panel, .result-panel { border: 1px solid var(--gray-150); border-radius: 8px; background: var(--gray-0); overflow: hidden; display: flex; flex-direction: column; min-width: 0; }
.panel-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--gray-150); }
.section-title { display: flex; align-items: center; gap: 8px; color: var(--main-color); h3 { margin: 0; color: var(--gray-1000); font-size: 15px; font-weight: 650; } }
.preview-image, video { width: 100%; height: 360px; object-fit: contain; background: var(--gray-100); }
.ant-empty, .result-loading { margin: 60px 12px; }
.result-summary { display: flex; align-items: baseline; flex-wrap: wrap; gap: 12px; padding: 18px; strong { font-size: 28px; color: var(--main-color); } }
.class-counts { padding: 0 18px 16px; display: flex; gap: 6px; flex-wrap: wrap; }
.history-section { min-width: 0; }
.ant-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
footer, .model-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; margin: 16px 0; }
footer { justify-content: end; }
:deep(.ant-list-item-meta-description) { overflow-wrap: anywhere; }
@media (max-width: 800px) { .preview-result-section { grid-template-columns: minmax(0, 1fr); } .disease-content { padding: 12px; } .action-left, .action-right { width: 100%; } label { max-width: 100%; } }
</style>
