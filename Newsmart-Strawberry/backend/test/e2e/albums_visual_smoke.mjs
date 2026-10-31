import assert from 'node:assert/strict'
import { mkdir, mkdtemp, writeFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROMIUM_PATH,
  args: ['--disable-features=LocalNetworkAccessChecks'] })
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
const entry = await (await fetch('http://127.0.0.1:5179/src/main.js')).text()
const dependency = name => entry.match(new RegExp(`"([^"\\n]*${name}\\.js[^"\\n]*)"`))[1]
try {
  for (const width of [1440, 390]) for (const dark of [false, true]) {
    const page = await browser.newPage({ viewport: { width, height: 950 } })
    const errors = []
    page.on('pageerror', e => errors.push(e.message))
    page.on('console', msg => { if (msg.type() === 'error') console.error(msg.text()) })
    const png = await page.evaluate(() => {
      const canvas = document.createElement('canvas')
      canvas.width = 320; canvas.height = 240
      const ctx = canvas.getContext('2d')
      ctx.fillStyle = '#287e4b'; ctx.fillRect(0, 0, 320, 240)
      ctx.fillStyle = '#ed4c53'; ctx.beginPath(); ctx.ellipse(160, 120, 55, 70, 0, 0, 7); ctx.fill()
      return canvas.toDataURL('image/png').split(',')[1]
    })
    const bytes = Buffer.from(png, 'base64')
    let album = null
    let uploaded = false
    let uploadCount = 0
    let archived = false
    await page.route('**/api/**', async route => {
      const url = new URL(route.request().url())
      if (url.pathname === '/api/albums' && route.request().method() === 'POST') {
        album = { ...route.request().postDataJSON(), id: 'album-1', photo_count: 0 }
        return route.fulfill({ status: 201, json: album })
      }
      if (url.pathname === '/api/albums') return route.fulfill({ json: { total: album ? 1 : 0, items: album ? [album] : [] } })
      if (url.pathname.endsWith('/file')) return route.fulfill({ contentType: 'image/png', body: bytes })
      if (url.pathname.endsWith('/archive')) { archived = true; return route.fulfill({ contentType: 'application/zip', body: Buffer.from('PK-test') }) }
      if (route.request().method() === 'POST') { uploaded = true; uploadCount++; return route.fulfill({ status: 201, json: { id: 'photo-1' } }) }
      return route.fulfill({ json: { total: uploaded ? 1 : 0, items: uploaded ? [{ id: 'photo-1', filename: 'strawberry-test.png', width: 320, height: 240, size: bytes.length, captured_at: '2026-10-22T10:00:00Z', source: 'upload' }] : [] } })
    })
    await page.route('**/__albums_test', route => route.fulfill({ contentType: 'text/html', body: `
      <html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import { createApp, h } from '${dependency('vue')}';
      import { createPinia } from '${dependency('pinia')}';
      import Antd, { ConfigProvider } from '${dependency('ant-design-vue')}';
      import { useThemeStore } from '/src/stores/theme.js';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import View from '/src/views/AlbumsView.vue';
      localStorage.setItem('user_token','isolated-test'); localStorage.setItem('theme','${dark ? 'dark' : 'light'}');
      createApp({setup(){const theme = useThemeStore(); return () => h(ConfigProvider,{theme:theme.currentTheme},{default:()=>h(View)})}}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto('http://127.0.0.1:5179/__albums_test')
    await page.getByRole('button', { name: '新建照片集' }).click()
    const fields = page.locator('.ant-modal input')
    await fields.nth(0).fill('ST-001')
    await fields.nth(1).fill('草莓一号簇')
    await fields.nth(2).fill('A 区')
    await fields.nth(3).fill('strawberry-local')
    await page.getByRole('button', { name: '创建照片集' }).click()
    await page.getByRole('heading', { name: '草莓一号簇' }).waitFor()
    await page.locator('input[type=file]:not([webkitdirectory])').setInputFiles({ name: 'strawberry-test.png', mimeType: 'image/png', buffer: bytes })
    await page.waitForFunction(() => document.querySelector('.photo-preview img')?.naturalWidth > 0)
    await page.waitForFunction(() => [...document.querySelectorAll('.ant-modal-wrap')].every(el => getComputedStyle(el).display === 'none'))
    await page.waitForFunction(() => !document.querySelector('.ant-spin-spinning'))
    await page.screenshot({ path: resolve(output, `albums-${width}-${dark ? 'dark' : 'light'}.png`), fullPage: true })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.getByRole('button', { name: '预览原图', exact: true }).click()
    await page.waitForFunction(() => document.querySelector('.full-image')?.naturalWidth === 320)
    await page.getByRole('button', { name: 'Close', exact: true }).click()
    const download = page.waitForEvent('download')
    await page.getByRole('button', { name: '下载原图', exact: true }).click()
    assert.equal((await download).suggestedFilename(), 'strawberry-test.png')
    const folder = await mkdtemp(resolve(tmpdir(), 'album-upload-'))
    try {
      await mkdir(resolve(folder, 'nested'))
      for (let i = 0; i < 32; i++) await writeFile(resolve(folder, 'nested', `${i}.png`), bytes)
      await writeFile(resolve(folder, 'notes.txt'), 'skip')
      await page.locator('input[webkitdirectory]').setInputFiles(folder)
      await page.getByText('已导入 32 张，失败 0 张，跳过 1 个非支持文件').waitFor()
      assert.equal(uploadCount, 33)
      const zip = page.waitForEvent('download')
      await page.getByRole('button', { name: '下载全部图片', exact: true }).click()
      assert.equal((await zip).suggestedFilename(), '草莓一号簇-原图.zip')
      assert.equal(archived, true)
      await page.screenshot({ path: resolve(output, `albums-folder-${width}-${dark ? 'dark' : 'light'}.png`), fullPage: true })
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    } finally { await rm(folder, { recursive: true, force: true }) }
    await page.getByRole('button', { name: '返回照片集', exact: true }).click()
    await page.getByRole('button', { name: '草莓一号簇', exact: true }).waitFor()
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, dark, created: !!album, uploaded, errors }))
    await page.close()
  }
} finally { await browser.close() }
