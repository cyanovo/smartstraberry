import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const root = new URL('../../../web/src/', import.meta.url)
const view = await readFile(new URL('views/AgentView.vue', root), 'utf8')
const chat = await readFile(new URL('components/AgentChatComponent.vue', root), 'utf8')
const panel = await readFile(new URL('components/AlbumAnalysisPanel.vue', root), 'utf8')
const body = view.match(/async function routeDiseaseMessage\(\{ text \}\) \{([\s\S]*?)\n\}/)[1]
const selection = { value: { recordIds: [], kbId: null } }
const calls = []
const route = new Function('diseaseSelection', 'analyzeDisease', `return async function ({ text } = {}) {${body}}`)(
  selection, async payload => calls.push(payload)
)
assert.equal(await route(), false)
assert.equal(calls.length, 0)
selection.value = { recordIds: ['d1', 'd2'], kbId: 'kb1' }
assert.equal(await route({ text: '看看这片叶子怎么处理？' }), true)
assert.deepEqual(calls, [{ recordIds: ['d1', 'd2'], kbId: 'kb1', question: '看看这片叶子怎么处理？' }])
assert.notEqual(calls[0].recordIds, selection.value.recordIds)
selection.value.recordIds = []
assert.equal(await route(), false)
assert.equal(calls.length, 1)
assert.ok(view.includes(':before-send="routeDiseaseMessage"'))
assert.ok(view.includes(':send-disabled="diseaseBusy"'))
assert.ok(view.includes('@disease-selection="selection => diseaseSelection = selection"'))
assert.ok(panel.includes("emit('disease-selection', { recordIds: [...diseaseIds.value], kbId: kbId.value })"))
const hook = chat.indexOf('if (await props.beforeSend({ text, image }))')
const normal = chat.indexOf('if (currentChatId.value && /^(接受|拒绝)$/.test(text))')
assert.ok(hook > 0 && hook < normal)
assert.match(chat.slice(hook, normal), /userInput.value = ''\s+return/)
console.log('PASS: selected records route to fixed care; clearing restores normal chat; send hook exits before agent/control path.')
