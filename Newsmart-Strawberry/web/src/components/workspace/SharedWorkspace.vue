<template>
  <section class="shared-workspace">
    <header>
      <h2>团队工作区</h2>
      <a-space wrap>
        <a-button title="刷新" :loading="loading" @click="load"><RefreshCw :size="16" /></a-button>
        <a-button :disabled="busy" @click="folderModal = true"><FolderPlus :size="16" />新建文件夹</a-button>
        <a-button type="primary" :disabled="busy" @click="uploadModal = true"><Upload :size="16" />上传文件</a-button>
      </a-space>
    </header>
    <a-alert v-if="error" :message="error" type="error" closable @close="error = ''" />
    <nav aria-label="共享目录">
      <a-button type="link" @click="folder = ''">共享根目录</a-button>
      <template v-for="(part, index) in folder.split('/').filter(Boolean)" :key="index">
        <span>/</span><a-button type="link" @click="folder = folder.split('/').slice(0, index + 1).join('/')">{{ part }}</a-button>
      </template>
    </nav>
    <a-input-search v-model:value="search" placeholder="搜索当前目录" allow-clear />
    <a-table :data-source="entries" :columns="columns" row-key="id" :loading="loading" :scroll="{ x: 850 }" :pagination="{ pageSize: 20, hideOnSinglePage: true }">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <a-button type="link" class="filename" @click="record.isDir ? folder = record.path : detail = record"><Folder v-if="record.isDir" :size="16" /><File v-else :size="16" />{{ record.name }}</a-button>
        </template>
        <template v-else-if="column.key === 'size'">{{ record.isDir ? '—' : `${(record.data.size / 1024).toFixed(1)} KB` }}</template>
        <template v-else-if="column.key === 'time'">{{ record.created_at ? new Date(record.created_at).toLocaleString() : '—' }}</template>
        <template v-else-if="column.key === 'note'">{{ record.data?.version_note || '—' }}</template>
        <template v-else-if="column.key === 'actions' && !record.isDir">
          <a-space>
            <a-button title="文件详情" @click="detail = record"><Info :size="16" /></a-button>
            <a-button title="下载" :disabled="busy" @click="download(record)"><Download :size="16" /></a-button>
            <a-popconfirm v-if="user.isAdmin || String(user.uid) === record.owner_uid" title="删除此版本文件？" @confirm="remove(record)"><a-button title="删除" danger :disabled="busy"><Trash2 :size="16" /></a-button></a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>
    <a-modal v-model:open="folderModal" title="新建共享文件夹" ok-text="创建" cancel-text="取消" :confirm-loading="busy" @ok="createFolder">
      <a-input v-model:value="folderName" placeholder="文件夹名称" :maxlength="100" @press-enter="createFolder" />
    </a-modal>
    <a-modal v-model:open="uploadModal" title="上传共享文件" ok-text="上传" cancel-text="取消" :confirm-loading="busy" :mask-closable="!busy" :closable="!busy" :cancel-button-props="{ disabled: busy }" @ok="upload">
      <a-form layout="vertical">
        <a-form-item label="目标目录">{{ folder || '共享根目录' }}</a-form-item>
        <a-form-item label="文件（每个不超过 100 MB）"><input :key="inputKey" type="file" multiple :disabled="busy" @change="files = Array.from($event.target.files || [])" /></a-form-item>
        <a-form-item label="版本说明"><a-textarea v-model:value="note" :maxlength="500" :disabled="busy" /></a-form-item>
      </a-form>
    </a-modal>
    <a-modal :open="!!detail" title="共享文件详情" :footer="null" @cancel="detail = null">
      <a-descriptions v-if="detail" :column="1" bordered>
        <a-descriptions-item label="文件名">{{ detail.name }}</a-descriptions-item>
        <a-descriptions-item label="上传者">{{ detail.owner_uid }}</a-descriptions-item>
        <a-descriptions-item label="版本 ID">{{ detail.id }}</a-descriptions-item>
        <a-descriptions-item label="版本说明">{{ detail.data.version_note || '未填写' }}</a-descriptions-item>
        <a-descriptions-item label="SHA-256"><span class="hash">{{ detail.data.sha256 }}</span></a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import { Download, File, Folder, FolderPlus, Info, RefreshCw, Trash2, Upload } from 'lucide-vue-next'
import { useUserStore } from '@/stores/user'
import { fieldRecords, createSharedFolder, uploadFieldFile, downloadFieldFile, removeShared } from '@/apis/field_work_api'

const user = useUserStore()
const folder = ref(''), search = ref(''), rows = ref([]), folders = ref([])
const loading = ref(false), busy = ref(false), error = ref(''), detail = ref(null)
const folderModal = ref(false), uploadModal = ref(false), folderName = ref(''), note = ref(''), files = ref([]), inputKey = ref(0)
const columns = [{ title: '名称 / 版本', key: 'name', width: 260 }, { title: '大小', key: 'size', width: 100 }, { title: '上传时间', key: 'time', width: 180 }, { title: '版本说明', key: 'note', width: 160 }, { title: '操作', key: 'actions', width: 150 }]
const entries = computed(() => {
  const prefix = folder.value ? `${folder.value}/` : ''
  const dirs = new Map()
  for (const path of [...folders.value.map(row => row.name), ...rows.value.map(row => row.parent_id)]) {
    if (!path.startsWith(prefix) || path === folder.value) continue
    const name = path.slice(prefix.length).split('/')[0]
    if (name) dirs.set(name, { id: `dir:${prefix}${name}`, name, path: prefix + name, isDir: true })
  }
  return [...dirs.values(), ...rows.value.filter(row => row.parent_id === folder.value && row.status === 'ready')]
    .filter(row => row.name.toLowerCase().includes(search.value.toLowerCase()))
})
async function allRecords(kind) {
  const result = []
  let page
  do { page = await fieldRecords(kind, undefined, result.length); result.push(...page) } while (page.length === 100)
  return result
}
async function load() {
  loading.value = true; error.value = ''
  try { [rows.value, folders.value] = await Promise.all([allRecords('shared'), allRecords('folder')]) }
  catch (e) { error.value = e.message }
  finally { loading.value = false }
}
async function createFolder() {
  if (busy.value) return
  const name = folderName.value.trim()
  if (!name || /[/\\]/.test(name) || name === '.' || name === '..') return message.warning('请输入有效的单层文件夹名称')
  const path = [folder.value, name].filter(Boolean).join('/')
  if (entries.value.some(row => row.isDir && row.path === path)) return message.warning('文件夹已存在')
  busy.value = true
  try { await createSharedFolder(path); folderModal.value = false; folderName.value = ''; await load() }
  catch (e) { message.error(e.message) } finally { busy.value = false }
}
async function upload() {
  if (busy.value) return
  if (!files.value.length || files.value.length > 50) return message.warning('请选择 1–50 个文件')
  if (files.value.some(file => !file.size || file.size > 100 * 1024 * 1024)) return message.warning('文件不能为空且不得超过 100 MB')
  busy.value = true
  try {
    while (files.value.length) {
      await uploadFieldFile('shared', files.value[0], { folder: folder.value, version_note: note.value })
      files.value.shift()
    }
    uploadModal.value = false; note.value = ''; inputKey.value++; message.success('共享文件上传完成')
  } catch (e) { message.error(`上传中断，剩余 ${files.value.length} 个文件可重试：${e.message}`) }
  finally { await load(); busy.value = false }
}
async function download(row) {
  try { await downloadFieldFile(row) } catch (e) { message.error(e.message) }
}
async function remove(row) {
  busy.value = true
  try { await removeShared(row.id); await load() } catch (e) { message.error(e.message) }
  finally { busy.value = false }
}
onMounted(load)
</script>

<style scoped lang="less">
.shared-workspace { padding: 20px; min-width: 0; overflow: auto; color: var(--color-text); }
header { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
h2 { font-size: 18px; margin: 0; }
nav { display: flex; flex-wrap: wrap; align-items: center; margin: 12px 0; }
.ant-input-search { margin-bottom: 16px; max-width: 360px; }
.ant-btn { display: inline-flex; align-items: center; gap: 6px; }
.filename { white-space: normal; text-align: left; height: auto; overflow-wrap: anywhere; max-width: 100%; }
.filename svg { flex-shrink: 0; }
.hash { overflow-wrap: anywhere; }
input[type='file'] { max-width: 100%; }
</style>
