import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH,
  args: ['--disable-features=LocalNetworkAccessChecks'] })
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
const entry = await (await fetch('http://127.0.0.1:5179/src/main.js')).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
try {
  for (const width of [1440, 390]) {
    for (const dark of [false, true]) {
      const page = await browser.newPage({ viewport: { width, height: 950 } })
      const errors = []
      const commands = []
      let online = true
      page.on('pageerror', e => { errors.push(e.message); console.error(e.message) })
      page.on('console', msg => { if (msg.type() === 'error') console.error(msg.text()) })
      await page.route('**/api/**', route => {
        const url = new URL(route.request().url())
        if (url.pathname === '/api/disease-care') return route.fulfill({ json: [] })
        if (url.pathname === '/api/iot/history/devices') return route.fulfill({ json: { devices: ['test-controller'] } })
        if (url.pathname === '/api/iot/history') return route.fulfill({ json: {
          total: 1, items: [{ id: 'sample-1', device_id: 'test-controller', kind: 'air',
            sampled_at: new Date().toISOString(), values: { temp: 24.5, humidity: 65 } }],
        } })
        if (url.pathname === '/api/iot/history/export') return route.fulfill({ contentType: 'text/csv', body: 'device_id,temp\ntest-controller,24.5\n' })
        if (url.pathname === '/api/iot/dashboard') {
          return route.fulfill({ json: {
            device_control: { protocol: 'strawberry', broker_connected: true, online, last_seen: Date.now() / 1000 },
            air: { timestamp: new Date().toISOString(), temp: 24.5, humidity: 65, co2: 420, illumination: 12000 },
            soil: { timestamp: new Date().toISOString(), soil_temperature: 22, soil_moisture: 45, ph_value: 6.5, soil_conductivity: 1100, nitrogen: 120, phosphorus: 40, potassium: 90 },
          } })
        }
        if (url.pathname.startsWith('/api/iot/actuators/')) {
          commands.push(url.pathname + url.search)
          return route.fulfill({ json: { status: 'sent_unconfirmed' } })
        }
        return route.fulfill({ json: {} })
      })
      await page.route('**/__iot_visual_test', route => route.fulfill({ contentType: 'text/html', body: `
        <html class="${dark ? 'dark' : ''}"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div>
        <script type="module">
          import { createApp, h } from '${dependency('vue')}';
          import { createPinia } from '${dependency('pinia')}';
          import Antd, { ConfigProvider } from '${dependency('ant-design-vue')}';
          import { useThemeStore } from '/src/stores/theme.js';
          import '/node_modules/ant-design-vue/dist/reset.css';
          import '/src/assets/css/main.css';
          import View from '/src/views/IndustrialIotView.vue';
          localStorage.setItem('user_token', 'isolated-test');
          localStorage.setItem('theme', '${dark ? 'dark' : 'light'}');
          createApp({ setup() {
            const themeStore = useThemeStore();
            return () => h(ConfigProvider, { theme: themeStore.currentTheme }, { default: () => h(View) });
          } }).use(createPinia()).use(Antd).mount('#app');
        </script></body></html>` }))
      await page.goto('http://127.0.0.1:5179/__iot_visual_test')
      await page.getByText('24.5 °C', { exact: true }).waitFor()
      await page.waitForFunction(() => [...document.querySelectorAll('[data-device] button')].every(button => !button.disabled))
      await page.evaluate(() => document.fonts.ready)
      assert.equal(await page.locator('[data-device]').count(), 5)
      await page.getByRole('cell', { name: 'test-controller', exact: true }).waitFor()
      const download = page.waitForEvent('download')
      await page.getByRole('button', { name: '导出 CSV' }).click()
      assert.equal((await download).suggestedFilename(), 'sensor-history.csv')
      await page.screenshot({ path: resolve(output, `iot-${width}-${dark ? 'dark' : 'light'}.png`), fullPage: true })
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'No horizontal overflow')
      const relay = page.locator('[data-device="fertigation"]')
      await relay.getByRole('switch').click()
      assert.equal(commands.length, 0, 'Start requires confirmation')
      await page.getByRole('button', { name: '确认开启' }).click()
      await relay.getByRole('status').filter({ hasText: '开启指令已发送' }).waitFor()
      assert.deepEqual(commands, ['/api/iot/actuators/fertigation?value=true'])
      assert.equal(await page.getByText('实际开关状态未知', { exact: true }).count(), 0)
      online = false
      await page.getByRole('button', { name: '刷新设备状态' }).click()
      await page.getByText('设备离线', { exact: true }).waitFor()
      assert.ok(await page.getByRole('switch', { name: '滴灌水泵开关' }).isDisabled())
      assert.ok(await relay.getByRole('switch').isEnabled())
      assert.deepEqual(errors, [])
      console.log(JSON.stringify({ width, dark, commands, errors }))
      await page.close()
    }
  }
} finally { await browser.close() }
