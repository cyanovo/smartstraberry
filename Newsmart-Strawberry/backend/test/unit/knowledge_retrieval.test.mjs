import { test } from 'node:test'
import assert from 'node:assert/strict'
import { summarizeKnowledgeRetrieval as summarize } from '../../../web/src/utils/knowledgeRetrieval.js'

test('running uses actual arguments without inventing files', () => {
  const result = summarize({ args: '{"kb_id":"kb1","query_text":"草莓病害"}' })
  assert.equal(result.state, 'running')
  assert.equal(result.kbId, 'kb1')
  assert.deepEqual(result.files, [])
})
test('completed results expose names, deduplicate chunks and hide directory paths', () => {
  const result = summarize({ tool_call_result: { content: JSON.stringify({ kb_name: '草莓资料', results: [
    { metadata: { source: 'D:\\private\\种植.pdf' } },
    { metadata: { source: 'D:\\private\\种植.pdf' } },
    { metadata: { file_name: '管理.docx' } },
  ] }) } })
  assert.equal(result.state, 'completed')
  assert.equal(result.kbName, '草莓资料')
  assert.equal(result.count, 3)
  assert.deepEqual(result.files, ['种植.pdf', '管理.docx'])
})
test('empty, failed and unnamed sources are distinct', () => {
  assert.equal(summarize({ tool_call_result: { content: 'Milvus context' } }).label, '知识库检索完成')
  assert.equal(summarize({ tool_call_result: { content: '{"results":[]}' } }).label, '未找到相关资料')
  assert.equal(summarize({ tool_call_result: { content: '检索失败: timeout' } }).state, 'error')
  assert.equal(summarize({ tool_call_result: { status: 'error', content: '{}' } }).state, 'error')
  assert.deepEqual(summarize({ tool_call_result: { content: { results: [{ file_id: 'opaque-id' }] } } }).files, [])
})
