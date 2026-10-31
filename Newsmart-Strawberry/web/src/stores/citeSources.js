import { reactive } from 'vue'

/** 当前对话的引用来源列表，由流式响应 cite_sources 事件更新 */
export const citeSourceStore = reactive({
  sources: []
})

export function setCiteSources(sources) {
  citeSourceStore.sources = sources || []
}

export function getCiteSource(index) {
  const idx = parseInt(index)
  return citeSourceStore.sources.find(s => s.index === idx) || null
}
