<template>
  <section v-if="rows.length || busy || error" class="disease-conversation" aria-live="polite">
    <a-alert v-if="error" type="error" :message="error" closable @close="error = ''" />
    <a-spin v-if="busy" :tip="stage" />
    <article v-for="row in visibleRows" :key="row.id">
      <AgentMessageComponent v-if="row.data.question" :message="{ id: `${row.id}-question`, type: 'human', content: row.data.question }" />
      <ToolCallsGroupComponent :tool-calls="toolCalls(row)" />
      <AgentMessageComponent :message="answerMessage(row)" :hide-tool-calls="true" />
      <a-space wrap><a-tag v-for="action in row.data.actions" :key="action.key">{{ action.label }}</a-tag></a-space>
      <p v-if="row.status !== 'streaming'">{{ labels[row.status] || row.status }} · {{ row.data.message }}</p>
      <p v-if="row.status === 'pending'">有效期至 {{ new Date(row.data.expires_at).toLocaleTimeString() }}</p>
      <a-space v-if="row.status === 'pending'">
        <a-button type="primary" :loading="confirming === row.id" :disabled="!!confirming" @click="confirm(row, true)">确认并发送四项指令</a-button>
        <a-button :disabled="!!confirming" @click="confirm(row, false)">取消</a-button>
      </a-space>
      <p v-for="result in row.data.results || []" :key="result.key">{{ result.label }}：{{ labels[result.status] || result.status }}</p>
    </article>
  </section>
</template>

<script setup>
import { computed, onUnmounted, ref, watch } from 'vue'
import { streamDisease, confirmDisease, diseaseCareHistory } from '@/apis/disease_care_api'
import ToolCallsGroupComponent from '@/components/ToolCallsGroupComponent.vue'
import AgentMessageComponent from '@/components/AgentMessageComponent.vue'

function answerMessage(row) {
  const content = row.data.answer.replace(/^(草莓白粉病防治建议|发病原因|解决方案|注意事项)\s*$/gm, '### $1')
  return {
    id: `${row.id}-answer`, type: 'ai', role: 'assistant', status: 'finished',
    content: row.data.kb_id || row.status === 'streaming' ? content : `${content}\n\n> 未选择知识库，以上为白粉病通用防治建议。`
  }
}

function toolCalls(row) {
  return (row.data.tools || []).map((tool, index) => {
    const knowledge = tool.name === '检索草莓白粉病知识'
    const status = tool.status === 'ready' ? 'success' : 'error'
    return {
      id: `${row.id}-tool-${index}`,
      name: knowledge ? 'query_kb' : tool.name,
      display_label: knowledge ? '知识库检索' : tool.name,
      retrieval_error_label: knowledge ? '暂未获取知识库资料' : undefined,
      args: knowledge
        ? { kb_id: row.data.kb_id, query_text: '草莓白粉病的发病原因、防治措施与用药注意事项' }
        : tool.name === '读取病虫害识别记录' ? { record_ids: row.data.record_ids } : {},
      status,
      tool_call_result: { status, content: typeof tool.result === 'string' ? tool.result : JSON.stringify(tool.result) }
    }
  })
}

const props = defineProps({ threadId: { type: String, default: '' } })
const emit = defineEmits(['visible'])
const rows = ref([]), busy = ref(false), confirming = ref(''), error = ref('')
const draft = ref(null), stage = ref('正在读取识别记录')
const visibleRows = computed(() => draft.value ? [...rows.value, draft.value] : rows.value)
let controller
onUnmounted(() => controller?.abort())
watch(() => !!(rows.value.length || busy.value || error.value), value => emit('visible', value), { immediate: true })
const labels = { pending: '等待确认', rejected: '已取消', expired: '已过期', unavailable: '控制不可用', sending: '发送中', sent_unconfirmed: '已发送', failed: '发送失败', partial_failure: '部分指令失败或未知', unknown: '状态未知，请核验设备' }
let generation = 0
watch(() => props.threadId, async thread => {
  controller?.abort()
  draft.value = null
  const version = ++generation
  rows.value = []; error.value = ''
  if (!thread) return
  try { const result = await diseaseCareHistory(thread); if (version === generation) rows.value = result.reverse() }
  catch (e) { if (version === generation) error.value = e.message }
}, { immediate: true })
async function analyze(thread, recordIds, kbId, question = '分析所选病虫害记录') {
  if (busy.value) return
  busy.value = true; error.value = ''
  controller = new AbortController()
  draft.value = { id: 'streaming-care', status: 'streaming', data: { question, record_ids: recordIds, kb_id: kbId, tools: [], answer: '', actions: [] } }
  try {
    await streamDisease({ thread_id: thread, record_ids: recordIds, kb_id: kbId || null, question }, event => {
      if (thread !== props.threadId) return
      if (event.type === 'stage') stage.value = event.text
      if (event.type === 'tools') draft.value.data.tools = event.tools
      if (event.type === 'delta') { stage.value = '正在输出防治方案'; draft.value.data.answer += event.text }
      if (event.type === 'done') {
        ++generation
        rows.value = [...rows.value.filter(r => r.id !== event.row.id), event.row]
        draft.value = null
      }
    }, controller.signal)
  } catch (e) { if (thread === props.threadId && e.name !== 'AbortError') error.value = e.message }
  finally { busy.value = false; draft.value = null }
}
async function confirm(row, accept) {
  const thread = props.threadId
  confirming.value = row.id; error.value = ''
  try {
    const result = await confirmDisease(row.id, thread, accept)
    if (thread === props.threadId) rows.value = rows.value.map(r => r.id === row.id ? result : r)
  } catch (e) {
    if (thread === props.threadId) error.value = e.message
    try {
      const result = await diseaseCareHistory(thread)
      if (thread === props.threadId) rows.value = result.reverse()
    } catch { /* Preserve the original confirmation failure. */ }
  } finally { confirming.value = '' }
}
defineExpose({ analyze })
</script>

<style scoped lang="less">
.disease-conversation { padding: 16px 0; min-width: 0; color: var(--color-text); }
article { display: flex; flex-direction: column; align-items: stretch; gap: 12px; padding: 16px 0; }
p { overflow-wrap: anywhere; }
p { margin: 12px 0; }
</style>
