<template>
  <div class="album-analysis-entry">
    <a-select v-model:value="albumId" allow-clear placeholder="选择照片集" :options="albums.map(a => ({ label: a.name, value: a.id }))" @change="open = !!albumId" />
    <DiseaseRecordSelect v-model:value="diseaseIds" :options="diseaseOptions" :loading="recordsLoading" @dropdown-visible-change="visible => visible && loadDiseaseRecords()" />
    <a-select v-model:value="kbId" allow-clear placeholder="选择参考知识库" :options="knowledge.map(k => ({ label: k.name, value: k.kb_id }))" aria-label="参考知识库" />
    <a-button :disabled="!diseaseIds.length" @click="askDisease">病害防治分析</a-button>
    <a-button title="照片集分析与设备建议" @click="open = true"><ChartNoAxesCombined :size="17" /><a-badge :count="pending.length" /></a-button>
    <a-drawer v-model:open="open" title="照片集分析与设备建议" :width="drawerWidth">
      <a-alert v-if="error" :message="error" type="error" closable @close="error = ''" />
      <a-tabs>
        <a-tab-pane key="analysis" tab="关联分析">
          <a-form layout="vertical">
            <a-form-item label="照片集"><a-select v-model:value="albumId" :options="albums.map(a => ({ label: a.name, value: a.id }))" /></a-form-item>
            <a-form-item label="病虫害识别记录"><DiseaseRecordSelect v-model:value="diseaseIds" :options="diseaseOptions" :loading="recordsLoading" @dropdown-visible-change="visible => visible && loadDiseaseRecords()" /></a-form-item>
            <a-form-item label="参考知识库"><a-select v-model:value="kbId" allow-clear :options="knowledge.map(k => ({ label: k.name, value: k.kb_id }))" /></a-form-item>
            <a-form-item label="实测平均单果质量（克）"><a-input-number v-model:value="mass" :min="0.01" :max="500" /></a-form-item>
            <a-space wrap><a-button type="primary" :loading="busy" :disabled="!albumId" @click="analyze">生成分析</a-button><a-button :disabled="!albumId" @click="askAgent">交给智能体分析</a-button></a-space>
          </a-form>
          <a-form-item label="历史分析"><a-select allow-clear :value="analysis?.id" :options="history.map(row => ({ value: row.id, label: new Date(row.created_at).toLocaleString() }))" @change="id => analysis = history.find(row => row.id === id) || null" /></a-form-item>
          <template v-if="analysis">
            <h3>最新可见果实</h3>
            <a-descriptions :column="1" bordered size="small">
              <a-descriptions-item label="识别范围">最新单张照片，不累计重复拍摄</a-descriptions-item>
              <a-descriptions-item label="可见果实">{{ analysis.data.estimate.visible_fruits ?? '证据不足' }}</a-descriptions-item>
              <a-descriptions-item label="成熟果实">{{ analysis.data.estimate.visible_ripe ?? '证据不足' }}</a-descriptions-item>
              <a-descriptions-item label="可见成熟果质量">{{ analysis.data.estimate.visible_ripe_mass_g == null ? '未提供实测单果质量' : `${analysis.data.estimate.visible_ripe_mass_g} 克` }}</a-descriptions-item>
              <a-descriptions-item label="病虫害">{{ analysis.data.latest_disease?.data.counts ?? '暂无成功识别记录' }}</a-descriptions-item>
              <a-descriptions-item label="手动选择的病虫害记录"><div v-for="row in analysis.data.selected_disease_records || []" :key="row.id">{{ diseaseLabel(row) }}</div><span v-if="!analysis.data.selected_disease_records?.length">未手动选择</span></a-descriptions-item>
              <a-descriptions-item label="传感器记录">{{ analysis.data.sensor_history.total }}</a-descriptions-item>
              <a-descriptions-item label="知识检索">{{ analysis.data.knowledge.status }}</a-descriptions-item>
            </a-descriptions>
            <a-alert class="notice" type="warning" message="当前结果不是整棚产量预测，未校正遮挡、漏检和后续生长损失。" />
            <a-collapse><a-collapse-panel key="evidence" header="证据与来源"><pre>{{ JSON.stringify(analysis.data, null, 2) }}</pre></a-collapse-panel></a-collapse>
          </template>
        </a-tab-pane>
        <a-tab-pane key="control" tab="设备建议">
          <a-space><a-button :disabled="!threadId" @click="refreshControls"><RefreshCw :size="16" />刷新</a-button><a-button @click="emit('ask', '读取当前所有传感器状态，结合实时数据给出设备控制建议。需要控制时调用 control_actuator 生成待确认建议，不要声称已经执行。')">读取传感器并建议</a-button></a-space>
          <a-empty v-if="!controls.length" description="暂无设备建议" />
          <article v-for="row in controls" :key="row.id" class="proposal">
            <h4>{{ row.name }}</h4><p>{{ row.data.key }} · {{ row.data.value ? '开启' : '关闭' }}</p>
            <a-tag>{{ labels[row.status] || row.status }}</a-tag>
            <p>有效期至 {{ new Date(row.data.expires_at).toLocaleString() }}</p>
            <a-space v-if="row.status === 'pending'">
              <a-popconfirm title="确认向设备发送此控制请求？" @confirm="confirm(row, true)"><a-button type="primary" :loading="busy">接受并发送</a-button></a-popconfirm>
              <a-button :loading="busy" @click="confirm(row, false)">拒绝</a-button>
            </a-space>
            <p v-if="row.data.message">{{ row.data.message }}</p>
          </article>
        </a-tab-pane>
      </a-tabs>
    </a-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChartNoAxesCombined, RefreshCw } from 'lucide-vue-next'
import { listAlbums } from '@/apis/album_api'
import DiseaseRecordSelect from '@/components/DiseaseRecordSelect.vue'
import { runAnalysis, fieldKnowledge, fieldRecords, confirmControl } from '@/apis/field_work_api'
const props = defineProps({ threadId: { type: String, default: '' } })
const emit = defineEmits(['ask', 'disease', 'disease-selection'])
const route = useRoute()
const albums = ref([]), knowledge = ref([]), albumId = ref(), kbId = ref(), mass = ref(null)
const open = ref(false), busy = ref(false), error = ref(''), analysis = ref(null), controls = ref([])
const history = ref([])
const diseaseIds = ref([]), diseaseRecords = ref([])
watch([diseaseIds, kbId], () => {
  emit('disease-selection', { recordIds: [...diseaseIds.value], kbId: kbId.value })
}, { deep: true, immediate: true })
watch(() => route.query.disease_record, id => {
  if (typeof id === 'string' && id) diseaseIds.value = [id]
}, { immediate: true })
function askDisease() {
  emit('disease', { recordIds: [...diseaseIds.value], kbId: kbId.value })
  open.value = false
}
function diseaseLabel(row) {
  const album = albums.value.find(a => a.id === row.parent_id)
  return `${album?.name || row.parent_id} · ${new Date(row.created_at).toLocaleString()} · ${Object.entries(row.data.counts || {}).map(([name, count]) => `${name}: ${count}`).join('，') || '未检出病虫害'} · ${row.id.slice(0, 8)}`
}
const recordsLoading = ref(false)
const diseaseOptions = computed(() => diseaseRecords.value.map(row => ({
  value: row.id, label: diseaseLabel(row),
  time: new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }),
  album: albums.value.find(album => album.id === row.parent_id)?.name || row.parent_id,
  result: Object.entries(row.data.counts || {}).map(([name, count]) => `${name}: ${count}`).join('，') || '未检出病虫害',
  disabled: diseaseIds.value.length >= 20 && !diseaseIds.value.includes(row.id)
})))
async function loadDiseaseRecords() {
  if (recordsLoading.value) return
  recordsLoading.value = true
  try {
    const rows = []
    let page
    do { page = await fieldRecords('detection', undefined, rows.length); rows.push(...page) } while (page.length === 100)
    diseaseRecords.value = rows.filter(row => row.status === 'ready' && row.data.task === 'disease')
  } catch (e) { error.value = e.message; open.value = true }
  finally { recordsLoading.value = false }
}
const drawerWidth = Math.min(window.innerWidth, 560)
const pending = computed(() => controls.value.filter(r => r.status === 'pending'))
const labels = { pending: '等待确认', rejected: '已拒绝', expired: '已过期', sending: '发送中', sent_unconfirmed: '已发送，执行未确认', failed: '发送失败', unknown: '状态未知，勿重复发送' }
let timer
let analysisGeneration = 0
async function analyze() {
  const generation = ++analysisGeneration
  busy.value = true; error.value = ''
  try {
    const result = await runAnalysis({ album_id: albumId.value, kb_id: kbId.value || null, average_mass_g: mass.value, disease_record_ids: diseaseIds.value })
    if (generation === analysisGeneration) { analysis.value = result; history.value.unshift(result) }
  } catch (e) { if (generation === analysisGeneration) error.value = e.message } finally { if (generation === analysisGeneration) busy.value = false }
}
function askAgent() {
  emit('ask', `请调用 analyze_strawberry_album 分析照片集 ${albumId.value}，参数 disease_record_ids=${JSON.stringify(diseaseIds.value)}，知识库 ${kbId.value || '未选择'}，实测平均单果重量${mass.value == null ? '未提供，不要编造' : `${mass.value}克`}。读取所选病虫害记录，保留各自照片集来源，跨照片集证据仅作参考。结合传感器和知识证据给出建议，明确估产范围与局限。`)
  open.value = false
}
async function refreshControls() {
  if (!props.threadId) { controls.value = []; return }
  const thread = props.threadId
  try { const rows = await fieldRecords('control', thread); if (thread === props.threadId) controls.value = rows } catch (e) { if (open.value) error.value = e.message }
}
async function confirm(row, accept) {
  busy.value = true
  try { await confirmControl(row.id, props.threadId, accept); await refreshControls() } catch (e) { error.value = e.message; await refreshControls() } finally { busy.value = false }
}
watch(() => props.threadId, () => { controls.value = []; refreshControls() })
watch(albumId, async (id) => {
  const generation = ++analysisGeneration
  analysis.value = null; busy.value = false; history.value = []
  if (!id) return
  try { const rows = await fieldRecords('analysis', id); if (generation === analysisGeneration) history.value = rows }
  catch (e) { if (generation === analysisGeneration) error.value = e.message }
})
onMounted(async () => {
  timer = setInterval(refreshControls, 5000)
  try {
    let page = 1, result
    do { result = await listAlbums(page++); albums.value.push(...result.items) } while (albums.value.length < result.total)
    knowledge.value = await fieldKnowledge()
    if (!kbId.value) kbId.value = (knowledge.value.find(k => /草莓/.test(k.name)) || knowledge.value[0])?.kb_id
    await loadDiseaseRecords()
    await refreshControls()
  } catch (e) { error.value = e.message }
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped lang="less">
.album-analysis-entry { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; min-width: 0; }
.album-analysis-entry > .ant-select { width: 170px; max-width: 36vw; }
.album-analysis-entry > .disease-record-select { width: 340px; max-width: 100%; }
@media (max-width: 600px) {
  .album-analysis-entry { width: 100%; }
  .album-analysis-entry > .disease-record-select { width: 100%; }
}
.ant-btn { display: inline-flex; align-items: center; gap: 6px; }
.proposal { border-bottom: 1px solid var(--gray-150); padding: 16px 0; }
h3 { font-size: 16px; margin-top: 24px; } h4, p { overflow-wrap: anywhere; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; max-height: 450px; overflow: auto; }
.notice { margin: 16px 0; }
</style>
