<template>
  <div class="page-agent-selector" v-if="allSubAgentOptions.length > 0">
    <span class="agent-label">AI</span>
    <a-select
      :value="selectedAgent"
      class="agent-select"
      size="small"
      :bordered="false"
      :options="allSubAgentOptions"
      @change="handleChange"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { useAgentStore } from '@/stores/agent'
import { usePageAgent } from '@/stores/pageAgent'

const props = defineProps({
  defaultAgent: { type: String, required: true },
})

const emit = defineEmits(['change'])

const agentStore = useAgentStore()
const { setPageAgent } = usePageAgent()
const selectedAgent = ref(props.defaultAgent)

// 从 store 动态获取全部子智能体，删除智能体时不会断裂
const allSubAgentOptions = computed(() => {
  const agents = agentStore.agents || []
  const subs = agents.filter(a => a.is_subagent)
  if (!subs.length) return []
  return subs.map(a => ({
    value: a.id || a.slug,
    label: a.name || a.slug,
    description: a.description || '',
  }))
})

// 确保选中值始终有效：如果 defaultAgent 不在列表中，选第一个
watch(allSubAgentOptions, (opts) => {
  if (!opts.length) return
  const exists = opts.find(o => o.value === selectedAgent.value)
  if (!exists) {
    selectedAgent.value = opts[0].value
  }
}, { immediate: true })

// 首次挂载时确保 store 已加载（含子智能体）
onMounted(async () => {
  if (!agentStore.isInitialized) {
    await agentStore.initialize()
  }
  // 强制拉取含子智能体的完整列表
  await agentStore.fetchAgents({ includeSubagents: true })
  // 确保选中值有效
  const opts = allSubAgentOptions.value
  if (opts.length && !opts.find(o => o.value === selectedAgent.value)) {
    selectedAgent.value = opts[0].value
  }
})

function handleChange(value) {
  selectedAgent.value = value
  const opt = allSubAgentOptions.value.find(o => o.value === value)
  if (opt) setPageAgent(value, opt.label)
  emit('change', value)
}

// 初始化写入共享状态 + watch 变化
watch(selectedAgent, (val) => {
  const opt = allSubAgentOptions.value.find(o => o.value === val)
  if (opt) setPageAgent(val, opt.label)
}, { immediate: true })
</script>

<style scoped lang="less">
.page-agent-selector {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 2px 0 8px;
  border: 1px solid var(--gray-150);
  border-radius: 6px;
  background: var(--gray-0);
}

.agent-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--main-color);
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.agent-select {
  min-width: 120px;

  :deep(.ant-select-selector) {
    border: none !important;
    padding: 0 !important;
    font-size: 12px;
    height: 26px;
    line-height: 26px;
    background: transparent !important;
  }

  :deep(.ant-select-selection-item) {
    color: var(--gray-700);
    font-weight: 500;
  }
}

.agent-option {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 2px 0;
}

.agent-option-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-900);
  line-height: 1.3;
}

.agent-option-desc {
  font-size: 10px;
  color: var(--gray-500);
  line-height: 1.3;
}
</style>
