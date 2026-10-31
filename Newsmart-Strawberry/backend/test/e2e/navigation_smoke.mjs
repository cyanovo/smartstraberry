import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH, headless: true })
const errors = []
const failedResponses = []
try {
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
  await page.addInitScript(token => localStorage.setItem('user_token', token), process.env.TEST_TOKEN)
  page.on('pageerror', e => { errors.push(e.stack); console.log('PAGEERROR', e.stack) })
  page.on('response', r => { if (r.status() >= 400) failedResponses.push(`${r.status()} ${r.url()}`) })
  await page.goto('http://127.0.0.1:5179/tomato-dashboard')
  await page.locator('.nav a').first().waitFor()
  const paths = await page.locator('.nav a').evaluateAll(es => es.map(e => e.getAttribute('href')))
  for (const path of paths) {
    console.log('CHECK', path)
    await page.locator(`.nav a[href="${path}"]`).click()
    await page.waitForURL(url => url.pathname === path)
    await page.waitForTimeout(1500)
    console.log('AT', page.url(), (await page.locator('#app-router-view').innerText({ timeout: 5000 })).slice(0,100))
    assert.equal(new URL(page.url()).pathname, path)
  }
  const output = resolve(import.meta.dirname, '../../../.runtime/qa')
  await mkdir(output, { recursive: true })
  await page.screenshot({ path: resolve(output, 'navigation-desktop.png') })
  await page.setViewportSize({ width: 390, height: 844 })
  await page.locator('.nav a[href="/agent"]').click()
  await page.waitForURL('**/agent')
  await page.waitForTimeout(1000)
  await page.screenshot({ path: resolve(output, 'navigation-mobile.png') })
  assert.deepEqual(errors, [])
  assert.deepEqual(failedResponses, [])
} finally { await browser.close() }
