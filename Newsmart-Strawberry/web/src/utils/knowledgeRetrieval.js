export function summarizeKnowledgeRetrieval(call) {
  const decode = value => {
    if (typeof value !== 'string') return value || {}
    try { return JSON.parse(value) || {} } catch { return value }
  }
  const args = decode(call.args ?? call.function?.arguments)
  const result = call.tool_call_result
  const payload = decode(result?.content)
  const failed = call.status === 'error' || result?.status === 'error' ||
    (typeof payload === 'string' && /失败|不存在|无法|未启用|请提供/.test(payload))
  const completed = result != null || call.status === 'success'
  const hasTextResult = typeof payload === 'string' && payload.trim().length > 0
  const chunks = Array.isArray(payload.results) ? payload.results : Array.isArray(payload.chunks) ? payload.chunks : []
  const files = [...new Set(chunks.filter(item => item && typeof item === 'object').map(item => {
    const meta = item.metadata || {}
    const name = meta.source || meta.file_name || meta.filename || item.file_name || item.filename
    return typeof name === 'string' ? name.split(/[\\/]/).pop() : ''
  }).filter(Boolean))]
  return {
    kbId: args.kb_id || payload.kb_id || '',
    kbName: payload.kb_name || args.kb_name || '',
    query: args.query_text || '',
    files,
    count: chunks.length,
    state: failed ? 'error' : completed ? 'completed' : 'running',
    label: failed ? (call.retrieval_error_label || '知识库检索失败') : !completed ? '正在检索知识库' : chunks.length || hasTextResult ? '知识库检索完成' : '未找到相关资料',
  }
}
