<script setup>
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { RefreshCw, Play, Sparkles } from 'lucide-vue-next'
import { diseaseCareSuggestions, confirmDisease } from '@/apis/disease_care_api'

const props = defineProps({ control: { type: Object, default: () => ({}) } })
const rows = ref([]), loading = ref(false), sending = ref(''), error = ref(''), now = ref(Date.now())
const labels = { pending: '待执行', expired: '已过期，请重新分析', rejected: '已取消', unavailable: '暂不可执行', sending: '发送中', sent_unconfirmed: '已发送', partial_failure: '部分失败或状态未知，请核验设备', failed: '发送失败', unknown: '状态未知，请核验设备' }
let timer, disposed = false
function status(row) {
  return row.status === 'pending' && !(Date.parse(row.data.expires_at) > now.value) ? 'expired' : row.status
}
function canExecute(row) {
  return status(row) === 'pending' && props.control.online && props.control.broker_connected && props.control.protocol === 'strawberry'
}
async function load() {
  if (loading.value || sending.value) return
  loading.value = true
  try {
    const result = await diseaseCareSuggestions()
    if (!disposed) { rows.value = result; error.value = '' }
  } catch (e) { if (!disposed) error.value = e.message }
  finally { loading.value = false }
}
async function execute(row) {
  if (sending.value || loading.value || !canExecute(row)) return
  sending.value = row.id; error.value = ''
  try {
    const result = await confirmDisease(row.id, row.parent_id, true)
    if (!disposed) rows.value = rows.value.map(item => item.id === row.id ? result : item)
  } catch (e) {
    if (!disposed) error.value = e.message
    // Reconcile ambiguous network outcomes without resending physical commands.
    try { const result = await diseaseCareSuggestions(); if (!disposed) rows.value = result }
    catch { /* Keep the original confirmation error visible. */ }
  } finally { sending.value = '' }
}
onMounted(() => {
  load()
  timer = setInterval(() => { now.value = Date.now(); load() }, 5000)
})
onBeforeUnmount(() => { disposed = true; clearInterval(timer) })
</script>

<template>
  <section class="care-suggestions" aria-label="AI 决策建议">
    <header><Sparkles :size="18" /><h3>AI 决策建议</h3><a-tooltip title="刷新建议"><a-button aria-label="刷新建议" :loading="loading" :disabled="!!sending" @click="load"><RefreshCw :size="16" /></a-button></a-tooltip></header>
    <a-alert v-if="error" type="error" :message="error" show-icon />
    <a-empty v-if="!rows.length && !loading && !error" description="暂无决策建议" />
    <article v-for="row in rows.slice(0, 1)" :key="row.id">
      <div class="suggestion-heading"><strong>{{ row.name }}</strong><a-tag>{{ labels[status(row)] || row.status }}</a-tag></div>
      <p class="suggestion-time">建议时间：{{ new Date(row.created_at).toLocaleString('zh-CN', { hour12: false }) }}</p>
      <p v-if="row.data.question">{{ row.data.question }}</p>
      <a-space wrap><a-tag v-for="action in row.data.actions" :key="action.key">{{ action.label }}</a-tag></a-space>
      <p v-if="status(row) === 'unavailable'">{{ control.online && control.broker_connected && control.protocol === 'strawberry' ? '设备当前已在线，请在 AI 问答中重新分析，生成新的可执行建议。' : '设备当前不可用，恢复连接后请重新分析。' }}</p>
      <p v-if="status(row) === 'pending'">有效期至 {{ new Date(row.data.expires_at).toLocaleTimeString('zh-CN', { hour12: false }) }}；执行前请确认现场安全。</p>
      <p v-if="status(row) === 'pending' && !canExecute(row)">设备离线或通信协议不可用，暂不能执行。</p>
      <a-button type="primary" :loading="sending === row.id" :disabled="!!sending || loading || !canExecute(row)" @click="execute(row)"><Play :size="14" />一键开始</a-button>
      <p v-for="result in row.data.results || []" :key="result.key">{{ result.label }}：{{ labels[result.status] || result.status }}</p>
    </article>
  </section>
</template>

<style scoped lang="less">
.care-suggestions { border-top: 1px solid var(--gray-150); padding-top: 20px; color: var(--color-text); min-width: 0; }
header, .suggestion-heading { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
header h3 { flex: 1; margin: 0; font-size: 16px; }
article { padding: 18px 0; border-bottom: 1px solid var(--gray-150); overflow-wrap: anywhere; }
p { margin: 10px 0; }
.suggestion-time { color: var(--gray-600); font-size: 13px; }
button { display: inline-flex; align-items: center; gap: 6px; }
</style>
