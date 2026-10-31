import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
const origin = 'http://127.0.0.1:5179'
const entry = await (await fetch(`${origin}/src/main.js`)).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
try {
  for (const width of [1280, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/api/**', route => route.abort())
    await page.route('**/__retrieval_test', route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: `
      <html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div>
      <script type="module">
        import { createApp, h, reactive } from '${dependency('vue')}';
        import { createPinia } from '${dependency('pinia')}';
        import Antd from '${dependency('ant-design-vue')}';
        import '/src/assets/css/main.css';
        import Group from '/src/components/ToolCallsGroupComponent.vue';
        const state = reactive({ call: { id: 'kb-test', name: 'query_kb', args: { kb_id: 'kb-test', kb_name: '草莓种植知识库', query_text: '草莓白粉病如何防治' } }, answer: '' });
        window.complete = () => { state.call.tool_call_result = { content: JSON.stringify({ kb_name: '草莓种植知识库', results: [
          { content: '测试片段', metadata: { source: '草莓病虫害防治手册.pdf' } },
          { content: '测试片段二', metadata: { source: '草莓病虫害防治手册.pdf' } },
          { content: '管理方法', metadata: { source: '设施草莓栽培管理规范.docx' } }
        ] }) }; state.answer = '这是用于验证显示顺序的模拟回答。'; };
        createApp({ setup() { return () => h('main', { style: 'max-width:800px;margin:auto;padding:20px' }, [
          h(Group, { toolCalls: [state.call], isActive: !state.answer }), h('p', { id: 'answer' }, state.answer)
        ]); } }).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${origin}/__retrieval_test`)
    await page.getByText('正在检索知识库', { exact: true }).waitFor()
    assert.equal(await page.locator('#answer').textContent(), '')
    await page.evaluate(() => window.complete())
    await page.getByText('知识库检索完成', { exact: true }).waitFor()
    assert.equal(await page.locator('.retrieval-files li').count(), 2)
    await page.screenshot({ path: resolve(output, `retrieval-${width}.png`), fullPage: true })
    assert.ok(await page.getByText('草莓病虫害防治手册.pdf', { exact: true }).isVisible())
    assert.ok(await page.evaluate(() => document.querySelector('.retrieval-status').getBoundingClientRect().bottom < document.querySelector('#answer').getBoundingClientRect().top))
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.screenshot({ path: resolve(output, `retrieval-${width}.png`), fullPage: true })
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, files: 2, errors }))
    await page.close()
  }
} finally { await browser.close() }
