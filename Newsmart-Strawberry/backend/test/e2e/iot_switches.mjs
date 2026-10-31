import assert from 'node:assert/strict'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const base = process.env.TEST_WEB_URL || 'http://127.0.0.1:5179'
const entry = await (await fetch(`${base}/src/main.js`)).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
try {
  for (const width of [1440, 390]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    const calls = [], errors = []
    let fail = false
    let online = true
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/api/**', route => {
      const url = new URL(route.request().url())
      if (url.pathname.includes('/actuators/')) {
        calls.push(url.searchParams.get('value'))
        return route.fulfill({ status: fail ? 500 : 200, json: fail ? { detail: '测试发送失败' } : { status: 'sent_unconfirmed' } })
      }
      if (url.pathname.endsWith('/dashboard')) return route.fulfill({ json: { device_control: { online, broker_connected: true, protocol: 'strawberry', reported_health: { air: '001', soil: '000', relay: '001' } } } })
      if (url.pathname.endsWith('/history/devices')) return route.fulfill({ json: { devices: [] } })
      if (url.pathname.endsWith('/history')) return route.fulfill({ json: { items: [], total: 0 } })
      return route.fulfill({ json: [] })
    })
    await page.route('**/__switches', route => route.fulfill({ contentType: 'text/html; charset=utf-8', body: `<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h} from '${dependency('vue')}';import {createPinia} from '${dependency('pinia')}';import Antd from '${dependency('ant-design-vue')}';
      import '/node_modules/ant-design-vue/dist/reset.css';import '/src/assets/css/main.css';
      import View from '/src/views/IndustrialIotView.vue';localStorage.setItem('user_token','test');
      createApp({render:()=>h(View)}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${base}/__switches`)
    const toggle = page.getByRole('switch', { name: '滴灌水泵开关' })
    await page.waitForFunction(() => document.querySelector('[aria-label="滴灌水泵开关"]')?.disabled === false)
    assert.equal(await page.getByRole('switch').count(), 5)
    await page.getByText('设备在线', { exact: true }).waitFor()
    assert.equal(await page.locator('.device-health .ant-tag').allTextContents().then(items => items.join(',')), '正常,异常,正常')
    assert.equal(await page.getByText('实际开关状态未知').count(), 0)
    assert.equal(await page.getByText(/继电器\s*\d/).count(), 0)
    await toggle.click()
    await page.getByRole('button', { name: /取\s*消/ }).click()
    assert.equal(calls.length, 0)
    assert.equal(await toggle.getAttribute('aria-checked'), 'false')
    await toggle.click()
    await page.getByRole('button', { name: '确认开启' }).click()
    await page.waitForFunction(() => document.querySelector('[aria-label="滴灌水泵开关"]').getAttribute('aria-checked') === 'true')
    fail = true
    await toggle.click()
    await page.getByText('停止指令发送失败', { exact: true }).waitFor()
    assert.equal(await toggle.getAttribute('aria-checked'), 'true')
    fail = false
    await toggle.click()
    await page.waitForFunction(() => document.querySelector('[aria-label="滴灌水泵开关"]').getAttribute('aria-checked') === 'false')
    assert.deepEqual(calls, ['true', 'false', 'false'])
    await toggle.click()
    online = false
    await page.getByRole('button', { name: '刷新设备状态' }).evaluate(button => button.click())
    await page.getByText('设备离线', { exact: true }).waitFor()
    await page.getByRole('button', { name: '确认开启' }).click()
    assert.deepEqual(calls, ['true', 'false', 'false'], 'Disconnect during confirmation must not send start')
    assert.ok(await toggle.isDisabled())
    assert.equal(await page.locator('.device-health .ant-tag').allTextContents().then(items => items.join(',')), '待上报,待上报,待上报')
    const stopAll = page.getByRole('button', { name: '一键关闭所有设备' })
    assert.ok(await stopAll.isEnabled(), 'Stop all remains available without recent telemetry')
    fail = true
    await stopAll.click()
    await page.getByText('停止指令发送失败', { exact: true }).first().waitFor()
    await page.waitForFunction(() => [...document.querySelectorAll('.command-status')].filter(el => el.textContent === '停止指令发送失败').length === 5)
    assert.deepEqual(calls.slice(3), Array(5).fill('false'))
    fail = false
    await stopAll.click()
    await page.waitForFunction(() => [...document.querySelectorAll('.command-status')].filter(el => el.textContent.includes('停止指令已发送')).length === 5)
    assert.deepEqual(calls.slice(8), Array(5).fill('false'))
    assert.equal(await page.locator('[role="switch"][aria-checked="true"]').count(), 0)
    online = true
    await page.getByRole('button', { name: '刷新设备状态' }).click()
    await page.getByText('设备在线', { exact: true }).waitFor()
    assert.ok(await toggle.isEnabled())
    assert.deepEqual(errors, [])
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    console.log(`PASS switches ${width}: cancel, on, failure, off, layout`)
    await page.close()
  }
} finally { await browser.close() }
