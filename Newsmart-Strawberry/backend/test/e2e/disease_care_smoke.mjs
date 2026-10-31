import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
const base = process.env.TEST_WEB_URL || 'http://127.0.0.1:5179'
const entry = await (await fetch(`${base}/src/main.js`)).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
try {
  for (const width of [1440, 390]) for (const dark of [false, true]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    const errors = [], confirmations = []
    let rows = []
    const actions = [{ key: 'irrigation', value: false, label: '停止滴灌' },
      { key: 'ventilation', value: true, label: '打开通风' },
      { key: 'rotation', value: true, label: '打开旋转' }, { key: 'light', value: true, label: '打开光照' }]
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/api/**', route => {
      const req = route.request(), path = new URL(req.url()).pathname
      if (path === '/api/disease-care/stream' && req.method() === 'POST') {
        assert.deepEqual(req.postDataJSON().record_ids, ['d1'])
        assert.equal(req.postDataJSON().question, '看看这片叶子怎么处理？')
        rows = [{ id: 'care1', status: 'pending', data: { question: req.postDataJSON().question, record_ids: ['d1'],
          tools: [{ name: '读取病虫害识别记录', status: 'ready', result: { counts: { 白粉病: 1 } } },
            { name: '读取实时传感器与设备状态', status: 'ready', result: { air: { temp: 24 } } }],
          answer: '草莓白粉病防治建议\n\n发病原因\n真菌侵染，注意通风与种苗健康。\n\n解决方案\n清除病叶，规范防治。\n\n注意事项\n避免缺水，按标签用药。\n\n是否确认发送四项控制指令？',
          actions, expires_at: new Date(Date.now() + 180000).toISOString(), message: '等待确认，尚未发送指令' } }]
        const events = [{ type: 'stage', text: '正在检索知识资料' }, { type: 'tools', tools: rows[0].data.tools }, { type: 'delta', text: rows[0].data.answer }, { type: 'done', row: rows[0] }]
        return route.fulfill({ contentType: 'text/event-stream; charset=utf-8', body: events.map(event => `data: ${JSON.stringify(event)}\n\n`).join('') })
      }
      if (path.endsWith('/confirm')) {
        confirmations.push(req.postDataJSON())
        rows[0].status = 'sent_unconfirmed'
        rows[0].data.message = '控制请求已发送，实际动作请核验设备'
        rows[0].data.results = actions.map(a => ({ ...a, status: 'sent_unconfirmed' }))
        return route.fulfill({ json: rows[0] })
      }
      if (path === '/api/disease-care/thread') return route.fulfill({ json: rows })
      return route.fulfill({ json: {} })
    })
    await page.route('**/__care_test', route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h,ref} from '${dependency('vue')}'; import {createPinia} from '${dependency('pinia')}';
      import Antd,{ConfigProvider} from '${dependency('ant-design-vue')}';
      import {useThemeStore} from '/src/stores/theme.js';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import View from '/src/components/DiseaseCareConversation.vue';
      localStorage.setItem('theme','${dark ? 'dark' : 'light'}'); localStorage.setItem('user_token','test');
      createApp({setup(){const theme=useThemeStore(), view=ref();window.runCare=()=>view.value.analyze('thread',['d1'],null,'看看这片叶子怎么处理？');return()=>h(ConfigProvider,{theme:theme.currentTheme},{default:()=>h('main',{style:'max-width:850px;margin:auto;padding:16px'},[h(View,{ref:view,threadId:'thread'})])})}}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${base}/__care_test`)
    await page.waitForFunction(() => !!window.runCare)
    await page.evaluate(() => window.runCare())
    await page.getByRole('button', { name: '确认并发送四项指令' }).waitFor()
    await page.getByText('看看这片叶子怎么处理？', { exact: true }).waitFor()
    assert.equal(confirmations.length, 0)
    const summary = page.getByRole('button', { name: /已调用 2 个工具/ })
    await summary.waitFor()
    assert.equal(await summary.getAttribute('aria-expanded'), 'false')
    await summary.click()
    assert.equal(await summary.getAttribute('aria-expanded'), 'true')
    assert.equal(await page.locator('.tool-call-container').count(), 2)
    await summary.click()
    await page.screenshot({ path: resolve(output, `care-${width}-${dark}.png`), fullPage: true })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    assert.equal(await page.getByText('演示', { exact: false }).count(), 0)
    await page.getByRole('button', { name: '确认并发送四项指令' }).click()
    await page.getByText('打开光照：已发送', { exact: true }).waitFor()
    rows[0].data.kb_id = 'kb-test'
    rows[0].data.tools.push({ name: '检索草莓白粉病知识', status: 'unavailable', result: '知识检索失败' })
    await page.reload()
    await page.getByText('暂未获取知识库资料', { exact: true }).waitFor()
    await page.getByText('看看这片叶子怎么处理？', { exact: true }).waitFor()
    assert.equal(await page.getByText('知识库检索失败', { exact: true }).count(), 0)
    await page.getByRole('button', { name: /已调用 3 个工具.*1 失败/ }).waitFor()
    await page.screenshot({ path: resolve(output, `care-tools-failed-${width}-${dark}.png`), fullPage: true })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    assert.deepEqual(confirmations, [{ thread_id: 'thread', accept: true }])
    assert.equal(await page.getByRole('button', { name: '确认并发送四项指令' }).count(), 0)
    await page.reload()
    await page.getByText('打开光照：已发送', { exact: true }).waitFor()
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, dark, confirmations: confirmations.length, errors }))
    await page.close()
  }
} finally { await browser.close() }
