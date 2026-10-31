import { ref } from 'vue'

// 页面选中的子智能体（跨组件共享）
const currentPageAgent = ref(null) // { slug, name }

export function usePageAgent() {
  function setPageAgent(slug, name) {
    currentPageAgent.value = { slug, name }
  }

  function getPageAgentContext() {
    // 不注入强制上下文，让 Agent 根据用户问题自由选择子智能体
    return ''
  }

  return { currentPageAgent, setPageAgent, getPageAgentContext }
}
