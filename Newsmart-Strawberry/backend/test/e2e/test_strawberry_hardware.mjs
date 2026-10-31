import assert from 'node:assert/strict'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined })
const base = process.env.FRONTEND_URL || 'http://127.0.0.1:5178'
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
  const errors = [], commands = [], writes = [], queries = []
  let denied = false, controlFails = false
  let devices = [{ deviceId: 1, deviceName: '测试传感器', deviceNumber: 'TEST-01', deviceState: 1, plantId: 1, areaId: 1, plantName: '草莓', areaName: '一号棚' }]
  page.on('pageerror', e => errors.push(e.message))
  await page.route('**/legacy/**', async route => {
    const req = route.request(), url = new URL(req.url()), path = url.pathname
    let data = { code: 200 }
    if (path.endsWith('/getInfo')) data = { code: 200, user: { userName: 'fixture' }, permissions: denied ? ['system:device:list'] : ['*:*:*'] }
    else if (path.endsWith('/device/list')) {
      queries.push(Object.fromEntries(url.searchParams))
      const result = devices.filter(d => !url.searchParams.has('deviceName') || d.deviceName.includes(url.searchParams.get('deviceName')))
      data = { code: 200, rows: result, total: result.length }
    } else if (path.endsWith('/plantId')) data = { code: 200, rows: [{ plantId: 1, plantName: '草莓' }], total: 1 }
    else if (path.endsWith('/areaName')) data = { code: 200, rows: [{ areaId: 1, areaName: '一号棚' }], total: 1 }
    else if (path.endsWith('/record/list')) data = { code: 200, rows: [{ airTemperature: 24, airHumidity: 0, soilPh: 6.5, createDate: '2026-10-22 10:00:00', areaName: '一号棚' }], total: 1 }
    else if (/\/record\/(fan|irrigation)$/.test(path)) {
      assert.equal(req.method(), 'POST')
      commands.push({ path, ...req.postDataJSON() })
      data = controlFails ? { code: 500, msg: 'MQTT unavailable' } : { code: 200 }
    } else if (path.endsWith('/device/export')) {
      assert.equal(req.method(), 'POST')
      await route.fulfill({ contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', body: 'fixture-export' })
      return
    } else if (path.endsWith('/device') && ['POST', 'PUT'].includes(req.method())) {
      const body = req.postDataJSON()
      writes.push({ method: req.method(), body })
      assert.equal(typeof body.deviceState, 'number')
      assert.equal(body.userId, undefined)
      if (req.method() === 'POST') devices.push({ ...body, deviceId: 2 })
      else devices = devices.map(d => d.deviceId === body.deviceId ? { ...d, ...body } : d)
    } else if (/\/device\/\d+$/.test(path)) {
      const id = Number(path.split('/').at(-1))
      if (req.method() === 'DELETE') devices = devices.filter(d => d.deviceId !== id)
      else data.data = devices.find(d => d.deviceId === id)
    } else throw new Error(`Unexpected API ${req.method()} ${path}`)
    await route.fulfill({ json: data })
  })
  await page.goto(base)
  await page.evaluate(() => sessionStorage.setItem('strawberry-admin-token', 'fixture-only'))
  await page.goto(`${base}/hardware`)
  await page.getByText('24', { exact: true }).waitFor()
  assert.equal(commands.length, 0)
  assert.equal(await page.getByText('补光灯控制', { exact: true }).count(), 0)
  const fan = page.locator('.actuator-row').filter({ hasText: '风扇' })
  await fan.getByRole('button', { name: '启动' }).click()
  assert.equal(commands.length, 0)
  await page.getByRole('button', { name: '确认发送' }).click()
  await fan.getByText(/启动指令已发送/).waitFor()
  assert.deepEqual(commands[0], { path: '/legacy/system/record/fan', action: 'start', speed: 3 })
  controlFails = true
  await fan.getByRole('button', { name: '停止' }).click()
  await page.getByText('MQTT unavailable').waitFor()
  assert.equal(await fan.getByText(/停止指令已发送/).count(), 0)
  controlFails = false
  const irrigation = page.locator('.actuator-row').filter({ hasText: '滴灌' })
  await irrigation.getByRole('button', { name: '启动' }).click()
  await page.getByRole('button', { name: '确认发送' }).click()
  await irrigation.getByText(/启动指令已发送/).waitFor()
  assert.deepEqual(commands.at(-1), { path: '/legacy/system/record/irrigation', action: 'start', duration: 300, intensity: 80 })
  await page.screenshot({ path: join(tmpdir(), 'strawberry-hardware-desktop.png'), fullPage: true })
  await page.goto(`${base}/devices`)
  await page.getByText('测试传感器', { exact: true }).waitFor()
  await page.getByTitle('修改设备', { exact: true }).click()
  const modal = page.getByRole('dialog')
  await modal.locator('input').first().fill('已修改传感器')
  await modal.getByRole('button', { name: /保\s*存/ }).click()
  await page.getByText('已修改传感器', { exact: true }).waitFor()
  assert.equal(writes[0].method, 'PUT')
  await page.getByRole('button', { name: '新增设备' }).click()
  await modal.getByRole('button', { name: /保\s*存/ }).click()
  await modal.getByText('此项不能为空').first().waitFor()
  assert.equal(writes.length, 1)
  await modal.locator('input').nth(0).fill('新增测试设备')
  await modal.locator('input').nth(1).fill('TEST-02')
  const selects = modal.locator('.ant-select-selector')
  await selects.nth(1).click()
  await page.locator('.ant-select-dropdown:visible').getByText('草莓', { exact: true }).click()
  await selects.nth(2).click()
  await page.locator('.ant-select-dropdown:visible').getByText('一号棚', { exact: true }).click()
  await modal.getByRole('button', { name: /保\s*存/ }).click()
  await page.getByText('新增测试设备', { exact: true }).waitFor()
  assert.equal(writes.at(-1).method, 'POST')
  const downloadPromise = page.waitForEvent('download')
  await page.getByTitle('导出设备列表').click()
  assert.match((await downloadPromise).suggestedFilename(), /\.xlsx$/)
  await page.locator('tr').filter({ hasText: '新增测试设备' }).getByTitle('删除设备', { exact: true }).click()
  await page.getByRole('button', { name: /^删\s*除$/ }).click()
  await page.getByText('新增测试设备', { exact: true }).waitFor({ state: 'hidden' })
  await page.locator('.device-filters input').first().fill('不存在')
  await page.getByRole('button', { name: '查询', exact: true }).click()
  await page.locator('.ant-empty').waitFor()
  assert.equal(queries.at(-1).deviceName, '不存在')
  await page.getByTitle('重置查询').click()
  await page.getByText('已修改传感器', { exact: true }).waitFor()
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 })
    for (const path of ['devices', 'hardware']) {
      await page.goto(`${base}/${path}`)
      await page.locator('.page-header-title').waitFor()
      await page.waitForTimeout(250)
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path} overflow ${width}`)
      await page.screenshot({ path: join(tmpdir(), `strawberry-${path}-${width}.png`), fullPage: true })
    }
  }
  denied = true
  await page.goto(`${base}/devices`)
  await page.getByText('已修改传感器', { exact: true }).waitFor()
  assert.equal(await page.getByRole('button', { name: '新增设备' }).count(), 0)
  assert.equal(await page.getByTitle('删除设备', { exact: true }).count(), 0)
  assert.deepEqual(errors, [])
  console.log('PASS: hardware contracts, confirmation, error handling, CRUD, validation, export, filters, permissions, responsive rendering')
} finally { await browser.close() }
