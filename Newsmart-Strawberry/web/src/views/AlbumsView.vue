<script setup>
import { onMounted, onBeforeUnmount, reactive, ref } from 'vue'
import { ArrowLeft, Download, Eye, FolderUp, ImagePlus, Plus, RefreshCw, Trash2 } from 'lucide-vue-next'
import { message } from 'ant-design-vue'
import { createAlbum, downloadAlbumArchive, getAlbumPhotoFile, listAlbumPhotos, listAlbums, uploadAlbumPhoto } from '@/apis/album_api'
import { removeAlbumPhoto } from '@/apis/field_work_api'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
async function deletePhoto(photo) {
  try { await removeAlbumPhoto(photo.id); await loadPhotos(photoPage.value) }
  catch (e) { message.error(e.message) }
}

const albums = ref([])
const total = ref(0)
const page = ref(1)
const selected = ref(null)
const photos = ref([])
const photoTotal = ref(0)
const photoPage = ref(1)
const loading = ref(false)
const uploading = ref(false)
const saving = ref(false)
const error = ref('')
const dialog = ref(false)
const preview = ref('')
const previewName = ref('')
const input = ref(null)
const folderInput = ref(null)
const downloading = ref(false)
const progress = reactive({ done: 0, total: 0 })
const uploadSummary = ref('')
const uploadFailures = ref([])
let disposed = false
const capturedAt = ref(null)
const form = reactive({ cluster_code: '', name: '', plot: '', device_id: '' })
let generation = 0
const columns = [
  { title: '草莓簇编号', dataIndex: 'cluster_code', width: 170 },
  { title: '照片集', key: 'name', width: 220 },
  { title: '地块', dataIndex: 'plot', width: 160 },
  { title: '设备编号', dataIndex: 'device_id', width: 180 },
  { title: '图片数', dataIndex: 'photo_count', width: 90 },
]
function releasePhotos() {
  photos.value.forEach(photo => { if (photo.url) URL.revokeObjectURL(photo.url) })
  photos.value = []
}
async function loadAlbums(next = page.value) {
  loading.value = true
  error.value = ''
  try {
    const result = await listAlbums(next)
    albums.value = result.items
    total.value = result.total
    page.value = next
  } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
async function loadPhotos(next = 1) {
  const token = ++generation
  const id = selected.value.id
  loading.value = true
  error.value = ''
  releasePhotos()
  try {
    const result = await listAlbumPhotos(id, next)
    if (token !== generation) return
    photoTotal.value = result.total
    photoPage.value = next
    photos.value = result.items.map(photo => ({ ...photo, url: '', failed: false }))
    await Promise.all(photos.value.map(async photo => {
      try {
        const blob = await getAlbumPhotoFile(photo.id, true)
        if (token === generation) photo.url = URL.createObjectURL(blob)
      } catch { if (token === generation) photo.failed = true }
    }))
  } catch (e) { if (token === generation) error.value = e.message }
  finally { if (token === generation) loading.value = false }
}
function openAlbum(album) { selected.value = album; photoTotal.value = 0; uploadSummary.value = ''; uploadFailures.value = []; loadPhotos() }
function back() {
  generation++
  releasePhotos()
  selected.value = null
  loadAlbums()
}
function newAlbum() {
  Object.assign(form, { cluster_code: '', name: '', plot: '', device_id: '' })
  dialog.value = true
}
async function save() {
  saving.value = true
  try {
    const album = await createAlbum(form)
    dialog.value = false
    openAlbum(album)
  } catch (e) { message.error(e.message) }
  finally { saving.value = false }
}
async function upload(event) {
  const chosen = [...event.target.files]
  event.target.value = ''
  if (!chosen.length || uploading.value || !selected.value) return
  const files = chosen.filter(file => /\.(jpe?g|png|webp)$/i.test(file.name))
  const skipped = chosen.length - files.length
  uploadSummary.value = ''
  uploadFailures.value = []
  if (!files.length) { message.warning('文件夹中没有 JPEG、PNG 或 WebP 图片'); return }
  uploading.value = true
  Object.assign(progress, { done: 0, total: files.length })
  const id = selected.value.id
  const time = capturedAt.value?.toISOString()
  let success = 0
  for (const file of files) {
    if (disposed) break
    try {
      await uploadAlbumPhoto(id, file, time)
      success++
    } catch (e) { uploadFailures.value.push(`${file.webkitRelativePath || file.name}：${e.message}`) }
    progress.done++
  }
  uploading.value = false
  uploadSummary.value = `已导入 ${success} 张，失败 ${uploadFailures.value.length} 张，跳过 ${skipped} 个非支持文件`
  if (!disposed && selected.value?.id === id) await loadPhotos(1)
}
async function downloadAll() {
  if (downloading.value || !selected.value) return
  const album = selected.value
  downloading.value = true
  try {
    const blob = await downloadAlbumArchive(album.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const name = [...album.name].map(char => char.charCodeAt(0) < 32 || '<>:"/\\|?*'.includes(char) ? '_' : char).join('')
    link.download = `${name}-原图.zip`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch (e) { message.error(e.message) }
  finally { downloading.value = false }
}
async function openPhoto(photo, download = false) {
  try {
    const blob = await getAlbumPhotoFile(photo.id)
    const url = URL.createObjectURL(blob)
    if (download) {
      const link = document.createElement('a')
      link.href = url
      link.download = photo.filename
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } else {
      closePreview()
      preview.value = url
      previewName.value = photo.filename
    }
  } catch (e) { message.error(e.message) }
}
function closePreview() { if (preview.value) URL.revokeObjectURL(preview.value); preview.value = '' }
onMounted(() => loadAlbums())
onBeforeUnmount(() => { disposed = true; generation++; releasePhotos(); closePreview() })
</script>

<template>
  <main class="albums-page">
    <header class="album-heading">
      <div class="title-group">
        <a-tooltip v-if="selected" title="返回照片集"><a-button aria-label="返回照片集" :disabled="uploading" @click="back"><ArrowLeft :size="18" /></a-button></a-tooltip>
        <h2>{{ selected ? selected.name : '草莓照片集' }}</h2>
      </div>
      <div class="actions">
        <a-tooltip title="刷新"><a-button aria-label="刷新" :disabled="loading || uploading" @click="selected ? loadPhotos(photoPage) : loadAlbums()"><RefreshCw :size="16" /></a-button></a-tooltip>
        <a-button v-if="!selected" type="primary" @click="newAlbum"><Plus :size="16" />新建照片集</a-button>
      </div>
    </header>
    <a-alert v-if="error" type="error" :message="error" show-icon />
    <template v-if="!selected">
      <a-table :columns="columns" :data-source="albums" :loading="loading" row-key="id" :scroll="{x:820}" :pagination="false">
        <template #bodyCell="{column,record}"><a-button v-if="column.key === 'name'" type="link" class="album-name" @click="openAlbum(record)">{{ record.name }}</a-button></template>
        <template #emptyText>暂无照片集</template>
      </a-table>
      <a-pagination v-model:current="page" :total="total" :page-size="50" :show-size-changer="false" :disabled="loading" @change="loadAlbums" />
    </template>
    <template v-else>
      <dl class="album-meta">
        <div><dt>草莓簇编号</dt><dd>{{ selected.cluster_code }}</dd></div>
        <div><dt>地块</dt><dd>{{ selected.plot || '未设置' }}</dd></div>
        <div><dt>设备编号</dt><dd>{{ selected.device_id || '未关联' }}</dd></div>
        <div><dt>图片数</dt><dd>{{ photoTotal }}</dd></div>
      </dl>
      <div class="upload-toolbar">
        <label for="capture-time">采集时间</label>
        <a-date-picker id="capture-time" v-model:value="capturedAt" show-time placeholder="默认上传时间" :disabled="uploading" />
        <a-button type="primary" :loading="uploading" :disabled="loading" @click="input.click()"><ImagePlus :size="16" />上传原图</a-button>
        <a-button :disabled="loading || uploading" @click="folderInput.click()"><FolderUp :size="16" />导入文件夹</a-button>
        <a-button :loading="downloading" :disabled="loading || uploading || !photoTotal" @click="downloadAll"><Download :size="16" />下载全部图片</a-button>
        <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" multiple hidden @change="upload" />
        <input ref="folderInput" type="file" webkitdirectory directory multiple hidden @change="upload" />
      </div>
      <div v-if="uploading" role="status">正在导入 {{ progress.done }} / {{ progress.total }}<a-progress :percent="Math.floor(progress.done / progress.total * 100)" /></div>
      <a-alert v-if="uploadSummary" :type="uploadFailures.length ? 'warning' : 'success'" :message="uploadSummary" show-icon />
      <details v-if="uploadFailures.length" class="upload-errors"><summary>查看导入失败详情（{{ uploadFailures.length }}）</summary><ul><li v-for="(failure, index) in uploadFailures" :key="index">{{ failure }}</li></ul></details>
      <a-spin :spinning="loading">
        <a-empty v-if="!photos.length && !loading" description="暂无图片" />
        <div class="photo-grid">
          <article v-for="photo in photos" :key="photo.id" class="photo-item">
            <button class="photo-preview" :aria-label="`预览 ${photo.filename}`" @click="openPhoto(photo)">
              <img v-if="photo.url" :src="photo.url" :alt="photo.filename" />
              <span v-else>{{ photo.failed ? '预览加载失败' : '加载中' }}</span>
            </button>
            <div class="photo-caption">
              <strong :title="photo.filename">{{ photo.filename }}</strong>
              <time>{{ new Date(photo.captured_at).toLocaleString() }}</time>
              <span>{{ photo.width }} × {{ photo.height }} · {{ (photo.size / 1024 / 1024).toFixed(2) }} MB</span>
              <div class="actions">
                <a-tooltip title="预览原图"><a-button aria-label="预览原图" @click="openPhoto(photo)"><Eye :size="16" /></a-button></a-tooltip>
                <a-tooltip title="下载原图"><a-button aria-label="下载原图" @click="openPhoto(photo, true)"><Download :size="16" /></a-button></a-tooltip>
                <a-popconfirm v-if="userStore.isAdmin || photo.owner_uid === String(userStore.uid)" title="删除原图及关联病虫害记录？此操作不可恢复；有关联成熟度记录时不删除。" @confirm="deletePhoto(photo)"><a-button danger title="删除原图"><Trash2 :size="16" /></a-button></a-popconfirm>
                <a-tag>{{ photo.source === 'upload' ? '手动上传' : '自动采集' }}</a-tag>
              </div>
            </div>
          </article>
        </div>
      </a-spin>
      <a-pagination :current="photoPage" :total="photoTotal" :page-size="24" :show-size-changer="false" :disabled="loading || uploading" @change="loadPhotos" />
    </template>
    <a-modal v-model:open="dialog" title="新建照片集" :footer="null" :closable="!saving" :mask-closable="!saving">
      <a-form :model="form" layout="vertical" @finish="save">
        <a-form-item name="cluster_code" label="草莓簇编号" :rules="[{required:true,message:'请输入草莓簇编号'},{pattern:/^[A-Za-z0-9_-]+$/,message:'编号仅允许字母、数字、下划线和短横线'}]"><a-input v-model:value="form.cluster_code" :maxlength="64" placeholder="ST-001" /></a-form-item>
        <a-form-item name="name" label="照片集名称" :rules="[{required:true,whitespace:true,message:'请输入照片集名称'}]"><a-input v-model:value="form.name" :maxlength="128" /></a-form-item>
        <a-form-item label="地块"><a-input v-model:value="form.plot" :maxlength="128" /></a-form-item>
        <a-form-item label="设备编号"><a-input v-model:value="form.device_id" :maxlength="128" /></a-form-item>
        <a-button html-type="submit" type="primary" :loading="saving">创建照片集</a-button>
      </a-form>
    </a-modal>
    <a-modal :open="!!preview" :title="previewName" :footer="null" width="960px" @cancel="closePreview"><img class="full-image" :src="preview" :alt="previewName" /></a-modal>
  </main>
</template>

<style scoped lang="less">
.albums-page { padding: 24px; height: 100%; overflow: auto; min-width: 0; color: var(--color-text); background: var(--gray-0); }
.album-heading, .title-group, .actions, .upload-toolbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.album-heading { justify-content: space-between; margin-bottom: 24px; }
.title-group { min-width: 0; flex: 1; }
h2 { font-size: 22px; margin: 0; overflow-wrap: anywhere; }
.album-meta { display: flex; flex-wrap: wrap; gap: 16px 40px; padding: 16px 0; border-block: 1px solid var(--gray-150); }
.album-meta div { min-width: 120px; max-width: 100%; }
dt, time, .photo-caption > span { color: var(--color-text-secondary); font-size: 12px; }
dd { margin: 4px 0 0; overflow-wrap: anywhere; }
.upload-toolbar { margin: 20px 0; }
.upload-errors { margin: 12px 0; overflow-wrap: anywhere; }
.upload-errors ul { max-height: 200px; overflow: auto; }
.photo-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(min(240px,100%),1fr)); gap: 16px; }
.photo-item { border: 1px solid var(--gray-150); border-radius: 8px; overflow: hidden; min-width: 0; }
.photo-preview { width: 100%; aspect-ratio: 4/3; border: 0; background: var(--gray-50); display: flex; align-items: center; justify-content: center; padding: 0; cursor: pointer; color: var(--color-text-secondary); }
.photo-preview img { width: 100%; height: 100%; object-fit: contain; }
.photo-caption { display: flex; flex-direction: column; gap: 8px; padding: 12px; }
.photo-caption strong { overflow: hidden; white-space: nowrap; text-overflow: ellipsis; }
.full-image { display: block; width: 100%; max-height: 75vh; object-fit: contain; }
.album-name { white-space: normal; height: auto; text-align: left; overflow-wrap: anywhere; padding: 0; }
:deep(.ant-btn) { display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
:deep(.ant-pagination) { margin-top: 24px; }
@media (max-width: 600px) { .albums-page { padding: 16px; } h2 { font-size: 20px; } }
</style>
