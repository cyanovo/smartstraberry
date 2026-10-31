import assert from 'node:assert/strict'
import { resolve } from 'node:path'
import { mkdir } from 'node:fs/promises'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.TEST_WEB_URL || 'http://127.0.0.1:5179'
const entry = await (await fetch(`${base}/src/main.js`)).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 800 } })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    await page.route('**/__record_select', route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h,ref} from '${dependency('vue')}';
      import Antd from '${dependency('ant-design-vue')}';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import Select from '/src/components/DiseaseRecordSelect.vue';
      const options=[{value:'record-1',label:'2026/10/26 10:30:15 白粉病 一号棚',time:'2026/10/26 10:30:15',result:'白粉病: 2',album:'一号棚草莓簇照片集'}, {value:'record-2',label:'2026/10/25 09:15:00 叶斑病 二号棚',time:'2026/10/25 09:15:00',result:'叶斑病: 1',album:'二号棚'}];
      createApp({setup(){const value=ref(['record-1']);return()=>h('main',{style:'width:340px;max-width:calc(100% - 32px);margin:24px auto'},[h(Select,{value:value.value,options,'onUpdate:value':v=>value.value=v})])}}).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${base}/__record_select`)
    await page.locator('.selected-record').waitFor()
    assert.match(await page.locator('.selected-record').innerText(), /2026\/10\/26 10:30:15/)
    await page.locator('input').click()
    await page.getByText('2026/10/25 09:15:00', { exact: true }).click()
    assert.equal(await page.locator('.selected-record').count(), 2)
    await page.screenshot({ path: resolve(output, `record-select-${width}.png`), fullPage: true })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.getByRole('button', { name: '移除此记录' }).first().click()
    assert.equal(await page.locator('.selected-record').count(), 1)
    await page.locator('input').fill('不存在的病害')
    await page.getByText('暂无匹配的病虫害记录').waitFor()
    assert.deepEqual(errors, [])
    console.log(`PASS record selector ${width}: timestamps, multi-select, remove, search, overflow`)
    await page.close()
  }
} finally { await browser.close() }
