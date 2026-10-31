import assert from 'node:assert/strict'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined })
const base = process.env.FRONTEND_URL || 'http://127.0.0.1:5178'
const errors = []
const unsupportedRequests = []
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => {
    if (new URL(request.url()).pathname.startsWith('/api/')) unsupportedRequests.push(request.url())
  })
  let loginFails = true
  let captchaRequests = 0
  // UI contract tests use fixtures, never submit real account passwords.
  await page.route('**/legacy/**', async route => {
    const path = new URL(route.request().url()).pathname
    let data = { code: 200 }
    if (path.endsWith('/captchaImage')) {
      captchaRequests++
      data = { code: 200, captchaEnabled: true, uuid: 'fixture-captcha', img: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a/1sAAAAASUVORK5CYII=' }
    } else if (path.endsWith('/login')) {
      const body = route.request().postDataJSON()
      assert.equal(body.uuid, 'fixture-captcha')
      assert.equal(body.code, '2')
      data = loginFails ? { code: 500, msg: 'fixture login rejected' } : { code: 200, token: 'fixture-only' }
    } else if (path.endsWith('/getInfo')) data.user = { userName: 'fixture-user' }
    else if (path.endsWith('/list') || path.endsWith('/plantId') || path.endsWith('/areaName')) {
      assert.equal(route.request().headers().authorization, 'Bearer fixture-only')
      data = { code: 200, rows: [], total: 0 }
    }
    await route.fulfill({ json: data })
  })
  await page.goto(base)
  await page.locator('.hero-actions button').waitFor()
  await page.waitForTimeout(1200)
  await page.screenshot({ path: join(tmpdir(), 'strawberry-home-source.png') })
  await page.locator('.hero-actions button').click()
  await page.waitForURL('**/login')
  await page.locator('button[type=submit]:enabled').waitFor()
  await page.locator('input[autocomplete="current-password"]').fill('fixture-password')
  await page.getByPlaceholder('计算结果').fill('2')
  await page.locator('button[type=submit]').click()
  await page.getByRole('alert').filter({ hasText: 'fixture login rejected' }).waitFor()
  await page.locator('button[type=submit]:enabled').waitFor()
  assert.equal(captchaRequests, 2)
  loginFails = false
  await page.getByPlaceholder('计算结果').fill('2')
  await page.locator('button[type=submit]').click()
  await page.waitForURL('**/dashboard')
  await page.locator('.hero-metric strong').first().filter({ hasText: '0' }).waitFor()
  await page.screenshot({ path: join(tmpdir(), 'strawberry-dashboard-source.png') })
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 })
    for (const path of ['dashboard', 'areas', 'plants', 'devices', 'hardware', 'records', 'diseases', 'clusters']) {
      await page.goto(`${base}/${path}`)
      await page.locator('.page-header-title').waitFor()
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path} overflow at ${width}`)
    }
  }
  await page.locator('.foo button').click()
  await page.waitForURL('**/login')
  assert.equal(await page.evaluate(() => sessionStorage.getItem('strawberry-admin-token')), null)
  await page.goto(`${base}/dashboard`)
  await page.waitForURL('**/login')
  assert.deepEqual(errors, [])
  assert.deepEqual(unsupportedRequests, [])
  console.log('PASS: source entry, captcha refresh, login error/success, all routes, responsive widths, logout, auth guard, no new-backend requests')
} finally {
  await browser.close()
}
