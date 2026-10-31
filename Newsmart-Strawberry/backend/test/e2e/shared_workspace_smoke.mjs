import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH })
const entry = await (await fetch('http://127.0.0.1:5179/src/main.js')).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
try {
  for (const width of [1440, 390]) for (const dark of [false, true]) {
    const page = await browser.newPage({ viewport: { width, height: 900 } })
    const errors = [], uploads = []
    const folders = [{ id: 'folder1', name: 'training/labels' }]
    const rows = [{ id: 'version1', name: 'labels.zip', parent_id: 'training/labels', owner_uid: 'me', status: 'ready', created_at: new Date().toISOString(), data: { size: 6, version_note: 'v1', sha256: 'abc' } }]
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/api/**', route => {
      const req = route.request(), path = new URL(req.url()).pathname
      if (path.endsWith('/records/shared')) return route.fulfill({ json: rows })
      if (path.endsWith('/records/folder')) return route.fulfill({ json: folders })
      if (path.endsWith('/folders')) { folders.push({ id: 'new', name: 'training/new' }); return route.fulfill({ json: {} }) }
      if (path.endsWith('/shared') && req.method() === 'POST') { uploads.push(req.postData()); return route.fulfill({ json: {} }) }
      if (path.includes('/files/')) return route.fulfill({ body: 'labels', headers: { 'Content-Type': 'application/octet-stream' } })
      if (req.method() === 'DELETE') { rows.splice(0); return route.fulfill({ json: { ok: true } }) }
      return route.fulfill({ json: {} })
    })
    await page.route('**/__shared_test', route => route.fulfill({ contentType: 'text/html', body: `<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h} from '${dependency('vue')}'; import {createPinia} from '${dependency('pinia')}';
      import Antd,{ConfigProvider} from '${dependency('ant-design-vue')}';
      import {useThemeStore} from '/src/stores/theme.js'; import {useUserStore} from '/src/stores/user.js';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import View from '/src/components/workspace/SharedWorkspace.vue';
      localStorage.setItem('theme','${dark ? 'dark' : 'light'}');
      localStorage.setItem('user_token','isolated-fixture');
      createApp({setup(){useUserStore().uid='me'; const theme=useThemeStore();return()=>h(ConfigProvider,{theme:theme.currentTheme},{default:()=>h(View)})}}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto('http://127.0.0.1:5179/__shared_test')
    await page.getByRole('button', { name: 'training', exact: true }).click()
    await page.getByRole('button', { name: '新建文件夹', exact: true }).click()
    await page.getByPlaceholder('文件夹名称').fill('new')
    await page.getByRole('button', { name: /^创\s*建$/ }).click()
    await page.getByRole('button', { name: 'new', exact: true }).waitFor()
    await page.getByRole('button', { name: 'labels', exact: true }).click()
    await page.getByRole('button', { name: 'labels.zip', exact: true }).waitFor()
    const download = page.waitForEvent('download')
    await page.getByTitle('下载', { exact: true }).click()
    assert.equal((await download).suggestedFilename(), 'labels.zip')
    await page.getByRole('button', { name: '上传文件', exact: true }).click()
    await page.locator('input[type=file]').setInputFiles({ name: 'new.txt', mimeType: 'text/plain', buffer: Buffer.from('new') })
    await page.getByRole('button', { name: /^上\s*传$/ }).click()
    await page.waitForFunction(() => !document.querySelector('.ant-modal-wrap:not([style*="display: none"])'))
    assert.equal(uploads.length, 1)
    assert.ok(uploads[0].includes('training/labels'))
    await page.screenshot({ path: resolve(output, `shared-${width}-${dark}.png`) })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.getByTitle('删除', { exact: true }).click()
    await page.locator('.ant-popconfirm').getByRole('button', { name: /确|Yes|OK/ }).click()
    await page.getByRole('button', { name: 'labels.zip', exact: true }).waitFor({ state: 'hidden' })
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, dark, passed: true }))
    await page.close()
  }
} finally { await browser.close() }
