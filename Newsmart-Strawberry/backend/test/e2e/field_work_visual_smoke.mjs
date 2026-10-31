import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH, args: ['--disable-features=LocalNetworkAccessChecks'] })
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
const entry = await (await fetch('http://127.0.0.1:5179/src/main.js')).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
try {
  for (const width of [1440, 390]) for (const dark of [false, true]) {
    const page = await browser.newPage({ viewport: { width, height: 950 } })
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/api/**', route => {
      const path = new URL(route.request().url()).pathname
      if (path === '/api/albums') return route.fulfill({ json: { total: 1, items: [{ id: 'a1', name: '草莓一号簇', cluster_code: 'ST-001' }] } })
      if (path.includes('/photos')) return route.fulfill({ json: { total: 0, items: [] } })
      if (path.endsWith('/knowledge')) return route.fulfill({ json: [] })
      if (path.endsWith('/records/detection')) return route.fulfill({ json: [{ id: 'disease-fixture', parent_id: 'a1', name: '技能展示测试记录', status: 'ready', created_at: '2026-10-22T10:00:00Z', data: { task: 'disease', counts: { '灰霉病': 2 } } }] })
      if (path.includes('/records/')) return route.fulfill({ json: [{ id: 'fixture-version', kind: path.split('/').at(-1), name: '技能展示测试记录', status: 'paused', created_at: '2026-10-22T10:00:00Z', data: { sha256: '0123456789abcdef'.repeat(4) } }] })
      return route.fulfill({ json: {} })
    })
    await page.route('**/__field_test', route => route.fulfill({ contentType: 'text/html', body: `<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import { createApp, h } from '${dependency('vue')}';
      import { createPinia } from '${dependency('pinia')}';
      import Antd, { ConfigProvider } from '${dependency('ant-design-vue')}';
      import { useThemeStore } from '/src/stores/theme.js';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import View from '/src/views/FieldWorkView.vue';
      import Panel from '/src/components/AlbumAnalysisPanel.vue';
      localStorage.setItem('user_token','isolated-test'); localStorage.setItem('theme','${dark ? 'dark' : 'light'}');
      createApp({setup(){const theme=useThemeStore();return()=>h(ConfigProvider,{theme:theme.currentTheme},{default:()=>[h(Panel),h(View)]})}}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto('http://127.0.0.1:5179/__field_test')
    await page.getByRole('heading', { name: '采集与模型工作台' }).waitFor()
    await page.locator('.album-analysis-entry > .ant-select').nth(1).click()
    await page.locator('.ant-select-item-option').filter({ hasText: '灰霉病: 2' }).click()
    await page.keyboard.press('Escape')
    assert.match(await page.locator('.album-analysis-entry').innerText(), /灰霉病: 2/)
    for (const tab of ['自动采集', '数据备份', '团队共享', '模型版本', '识别追溯']) {
      await page.getByRole('tab', { name: tab, exact: true }).click()
      await page.waitForFunction(() => !document.querySelector('.ant-spin-spinning'))
      await page.getByText('技能展示测试记录', { exact: true }).waitFor()
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    }
    await page.waitForTimeout(400)
    assert.ok(await page.locator('.ant-table-thead').evaluate(el => el.getBoundingClientRect().height < 90))
    await page.screenshot({ path: resolve(output, `field-work-${width}-${dark ? 'dark' : 'light'}.png`), fullPage: true })
    await page.getByTitle('照片集分析与设备建议').click()
    await page.getByRole('tab', { name: '关联分析', exact: true }).waitFor()
    await page.screenshot({ path: resolve(output, `analysis-panel-${width}-${dark ? 'dark' : 'light'}.png`) })
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, dark, tabs: 5, errors }))
    await page.close()
  }
} finally { await browser.close() }
