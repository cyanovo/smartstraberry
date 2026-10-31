import { apiGet, apiPost } from './base'

export const analyzeDisease = (data) => apiPost('/api/disease-care', data)
export const diseaseCareSuggestions = () => apiGet('/api/disease-care')
export async function streamDisease(data, onEvent, signal) {
  const response = await apiPost('/api/disease-care/stream', data, { signal }, true, 'raw')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = '', completed = false
  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        if (!frame.startsWith('data: ')) continue
        const event = JSON.parse(frame.slice(6))
        if (event.type === 'error') throw new Error(event.text)
        onEvent(event)
        if (event.type === 'done') completed = true
      }
    }
    if (!completed) throw new Error('输出连接中断，请刷新查看已保存的分析记录')
  } finally { await reader.cancel(); reader.releaseLock() }
}
export const diseaseCareHistory = (thread) => apiGet(`/api/disease-care/${encodeURIComponent(thread)}`)
export const confirmDisease = (id, thread, accept) => apiPost(`/api/disease-care/${id}/confirm`, { thread_id: thread, accept })
