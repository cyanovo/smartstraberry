import assert from 'node:assert/strict'
import { mkdir } from 'node:fs/promises'
import { resolve } from 'node:path'

const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright')
const browser = await chromium.launch({
  headless: true,
  ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {})
})
const output = resolve(import.meta.dirname, '../../../.runtime/qa')
await mkdir(output, { recursive: true })
try {
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport })
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    await page.goto('http://127.0.0.1:5179/', { waitUntil: 'networkidle' })
    const enter = page.getByRole('button', { name: '进入系统', exact: true })
    await enter.waitFor()
    await page.screenshot({ path: resolve(output, `home-${viewport.width}.png`), fullPage: true })
    await enter.click()
    await page.waitForURL('**/login')
    await page.waitForLoadState('networkidle')
    assert.ok(await page.locator('input').count(), 'Login/initialization form must render')
    await page.screenshot({ path: resolve(output, `login-${viewport.width}.png`), fullPage: true })
    assert.deepEqual(errors, [], 'No uncaught browser exceptions')
    console.log(JSON.stringify({ viewport, url: page.url(), errors }))
    await page.close()
  }
} finally {
  await browser.close()
}
