import assert from 'node:assert/strict'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.TEST_WEB_URL || 'http://127.0.0.1:5179'
const entry = await (await fetch(`${base}/src/main.js`)).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    const errors = [], calls = []
    page.on('pageerror', e => errors.push(e.message))
    const row = { id: 'care1', parent_id: 'thread', name: '草莓白粉病防治建议', created_at: '2026-10-26T08:00:00Z', status: 'pending', data: {
      question: '怎么处理？', expires_at: new Date(Date.now() + 180000).toISOString(), actions: [
        { key: 'irrigation', label: '停止滴灌' }, { key: 'ventilation', label: '打开通风' },
        { key: 'rotation', label: '打开旋转' }, { key: 'light', label: '打开光照' }
      ]
    } }
    await page.route('**/api/**', route => {
      if (route.request().method() === 'POST') {
        calls.push(route.request().postDataJSON())
        row.status = 'sent_unconfirmed'
        return route.fulfill({ json: row })
      }
      return route.fulfill({ json: [row, { ...row, id: 'older', name: '旧建议', created_at: '2026-10-25T08:00:00Z' }] })
    })
    await page.route('**/__suggestions', route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h} from '${dependency('vue')}';import {createPinia} from '${dependency('pinia')}';import Antd from '${dependency('ant-design-vue')}';
      import '/node_modules/ant-design-vue/dist/reset.css';import '/src/assets/css/main.css';
      import View from '/src/components/DiseaseCareSuggestions.vue';localStorage.setItem('user_token','test');
      createApp({render:()=>h(View,{control:{online:true,broker_connected:true,protocol:'strawberry'}})}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${base}/__suggestions`)
    await page.getByText(/建议时间：2026/).waitFor()
    assert.equal(await page.locator('article').count(), 1)
    assert.equal(await page.getByText('旧建议', { exact: true }).count(), 0)
    await page.getByRole('button', { name: '一键开始' }).click()
    await page.getByText('已发送', { exact: true }).waitFor()
    assert.deepEqual(calls, [{ thread_id: 'thread', accept: true }])
    assert.equal(await page.getByRole('button', { name: '一键开始' }).isDisabled(), true)
    await page.reload()
    await page.getByText('已发送', { exact: true }).waitFor()
    row.status = 'pending'; row.data.expires_at = '2020-01-01T00:00:00Z'
    await page.reload()
    await page.getByText('已过期，请重新分析', { exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: '一键开始' }).isDisabled(), true)
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    row.status = 'unavailable'
    await page.reload()
    await page.getByText('暂不可执行', { exact: true }).waitFor()
    assert.equal(await page.getByText('生成建议时设备不可用', { exact: true }).count(), 0)
    await page.getByText('设备当前已在线，请在 AI 问答中重新分析，生成新的可执行建议。', { exact: true }).waitFor()
    assert.ok(await page.getByRole('button', { name: '一键开始' }).isDisabled())
    assert.equal(calls.length, 1)
    assert.deepEqual(errors, [])
    console.log(`PASS suggestions ${width}: time, confirmation, reload, expiry, layout`)
    await page.close()
  }
} finally { await browser.close() }
