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
const image = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aM1sAAAAASUVORK5CYII=', 'base64')
try {
  for (const width of [1440, 390]) for (const dark of [false, true]) {
    const page = await browser.newPage({ viewport: { width, height: 1000 } })
    const errors = [], uploads = [], detections = []
    const models = [{ id: 'm1', name: 'best(5).pt', status: 'active', data: { classes: ['健康', '白粉病'] } }]
    const history = []
    const albums = [{ id: 'a1', name: '测试照片集', cluster_code: 'A01' }]
    await page.addInitScript(() => {
      window.testStreams = []
      navigator.mediaDevices.getUserMedia = async () => {
        const canvas = document.createElement('canvas')
        canvas.width = 320; canvas.height = 240
        const ctx = canvas.getContext('2d')
        ctx.fillStyle = '#36a86a'; ctx.fillRect(0, 0, 320, 240)
        const stream = canvas.captureStream(10)
        window.testStreams.push(stream)
        return stream
      }
    })
    page.on('pageerror', e => errors.push(e.message))
    await page.route('**/api/**', route => {
      const req = route.request(), path = new URL(req.url()).pathname
      if (path.endsWith('/records/model')) return route.fulfill({ json: models })
      if (path.endsWith('/records/detection')) return route.fulfill({ json: history })
      if (path.endsWith('/albums') && req.method() === 'POST') {
        const album = { id: 'a2', ...req.postDataJSON() }; albums.push(album)
        return route.fulfill({ json: album })
      }
      if (path.endsWith('/albums')) return route.fulfill({ json: { items: albums, total: albums.length } })
      if (path.endsWith('/photos') && req.method() === 'GET') return route.fulfill({ json: { items: [{ id: 'p1', filename: 'leaf.png' }], total: 1 } })
      if (path.endsWith('/photos') && req.method() === 'POST') { uploads.push(req.postData()); return route.fulfill({ json: { id: `p${uploads.length}`, filename: 'leaf.png' } }) }
      if (path.endsWith('/file')) return route.fulfill({ body: image, contentType: 'image/png' })
      if (path.endsWith('/detections')) {
        detections.push(req.postDataJSON())
        const row = { id: 'd1', status: 'ready', created_at: new Date().toISOString(), data: { task: 'disease', photo_id: 'p1', model_id: 'm1', image_size: [1, 1], counts: { 白粉病: 1 }, detections: [{ label: '白粉病', confidence: 0.9, xyxy: [0, 0, 1, 1] }] } }
        history.push(row)
        return route.fulfill({ json: row })
      }
      if (path.endsWith('/models')) { uploads.push(req.postData()); models.push({ id: 'm2', name: 'new.pt', status: 'validated', data: { classes: ['叶斑病'] } }); return route.fulfill({ json: models[1] }) }
      if (path.endsWith('/activate')) { models[0].status = 'inactive'; models[1].status = 'active'; return route.fulfill({ json: models[1] }) }
      return route.fulfill({ json: {} })
    })
    await page.route('**/__disease_test', route => route.fulfill({ contentType: 'text/html', body: `<html><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><script type="module">
      import {createApp,h} from '${dependency('vue')}'; import {createPinia} from '${dependency('pinia')}';
      import Antd,{ConfigProvider} from '${dependency('ant-design-vue')}';
      import {useThemeStore} from '/src/stores/theme.js'; import {useUserStore} from '/src/stores/user.js';
      import '/node_modules/ant-design-vue/dist/reset.css'; import '/src/assets/css/main.css';
      import View from '/src/views/DiseaseDetectionView.vue';
      localStorage.setItem('theme','${dark ? 'dark' : 'light'}'); localStorage.setItem('user_token','test');
      createApp({setup(){useUserStore().userRole='superadmin'; const theme=useThemeStore();return()=>h(ConfigProvider,{theme:theme.currentTheme},{default:()=>h(View)})}}).use(createPinia()).use(Antd).mount('#app');
      </script></body></html>` }))
    await page.goto(`${base}/__disease_test`)
    await page.getByRole('button', { name: '上传图片', exact: true }).click()
    await page.locator('input[accept="image/jpeg,image/png,image/webp"]').setInputFiles({ name: 'leaf.png', mimeType: 'image/png', buffer: image })
    await page.getByRole('button', { name: '开始识别', exact: true }).click()
    await page.getByRole('cell', { name: '白粉病', exact: true }).waitFor()
    assert.equal(detections[0].task, 'disease')
    assert.equal(detections[0].photo_id, 'p1')
    await page.locator('.evidence-image img').waitFor()
    await page.waitForFunction(() => document.querySelector('.evidence-image img')?.naturalWidth > 0)
    const boxLabel = page.locator('.evidence-image .box span').first()
    const demoLabel = await boxLabel.textContent()
    assert.match(demoLabel, /9[5-8]%（演示值）/)
    await page.getByRole('switch').click()
    assert.equal(await boxLabel.textContent(), '白粉病 90%')
    await page.getByRole('switch').click()
    assert.equal(await boxLabel.textContent(), demoLabel)
    assert.equal(history[0].data.detections[0].confidence, 0.9)
    await page.screenshot({ path: resolve(output, `disease-${width}-${dark}.png`), fullPage: true })
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth))
    await page.getByTitle('查看识别记录', { exact: true }).click()
    assert.equal(await page.getByRole('button', { name: '开始识别', exact: true }).isDisabled(), true)
    await page.getByRole('button', { name: '模型导入', exact: true }).click()
    await page.getByRole('checkbox').check()
    await page.locator('input[accept=".pt,.onnx"]').setInputFiles({ name: 'new.pt', mimeType: 'application/octet-stream', buffer: Buffer.from('fixture') })
    await page.getByText('new.pt', { exact: true }).waitFor()
    assert.ok(uploads[1].includes('disease'))
    await page.getByRole('button', { name: /^启\s*用$/ }).click()
    await page.locator('.ant-popconfirm').getByRole('button', { name: /确|Yes|OK/ }).click()
    await page.waitForFunction(() => document.querySelector('.page-header').textContent.includes('new.pt'))
    await page.locator('.ant-modal-close').click()
    await page.getByRole('button', { name: '开启摄像头', exact: true }).click()
    await page.getByRole('button', { name: '拍照保存', exact: true }).click()
    await page.getByRole('button', { name: '开启摄像头', exact: true }).waitFor()
    assert.ok(uploads.at(-1).includes('image/jpeg'))
    assert.equal(await page.evaluate(() => window.testStreams[0].getTracks()[0].readyState), 'ended')
    await page.getByRole('button', { name: '开启摄像头', exact: true }).click()
    await page.getByRole('button', { name: '开始识别', exact: true }).click()
    await page.waitForFunction(() => window.testStreams[1].getTracks()[0].readyState === 'ended')
    await page.getByRole('button', { name: '开始识别', exact: true }).waitFor({ state: 'visible' })
    await page.waitForFunction(() => !document.querySelector('.ant-btn-loading'))
    assert.equal(detections.length, 2)
    assert.equal(detections[1].photo_id, `p${uploads.length}`)
    assert.notEqual(detections[1].photo_id, detections[0].photo_id)
    await page.getByRole('button', { name: '开启摄像头', exact: true }).click()
    await page.getByRole('button', { name: '关闭摄像头', exact: true }).click()
    assert.equal(await page.evaluate(() => window.testStreams[2].getTracks()[0].readyState), 'ended')
    albums.length = 0
    await page.reload()
    await page.getByRole('button', { name: '开启摄像头', exact: true }).click()
    await page.getByRole('button', { name: '拍照保存', exact: true }).click()
    const modal = page.getByRole('dialog')
    await modal.waitFor()
    await modal.locator('input').nth(0).fill('新草莓簇')
    await modal.locator('input').nth(1).fill('B02')
    await modal.getByRole('button', { name: /确|OK/ }).click()
    await modal.waitFor({ state: 'hidden' })
    await page.getByRole('button', { name: '拍照保存', exact: true }).click()
    await page.getByRole('button', { name: '开启摄像头', exact: true }).waitFor()
    assert.equal(albums[0].cluster_code, 'B02')
    assert.deepEqual(errors, [])
    console.log(JSON.stringify({ width, dark, passed: true }))
    await page.close()
  }
} finally { await browser.close() }
