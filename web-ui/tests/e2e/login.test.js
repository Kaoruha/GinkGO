/**
 * Playwright E2E 测试 - 登录功能
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

// 辅助函数：获取远程浏览器页面
async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()
  return { browser, page }
}

// 辅助函数：清除登录状态
async function clearAuthState(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
}

test.describe('登录功能', () => {

  test('可以访问登录页面', async () => {
    const { page } = await getPage()
    await clearAuthState(page)
    await page.reload({ waitUntil: 'networkidle' })

    await expect(page.locator('h1')).toContainText('GINKGO')
    await expect(page.locator('input[placeholder="enter username"]')).toBeVisible()
    await expect(page.locator('input[placeholder="enter password"]')).toBeVisible()
    await expect(page.locator('button:has-text("EXECUTE")')).toBeVisible()
  })

  test('登录成功', async () => {
    const { page } = await getPage()
    await clearAuthState(page)
    await page.reload({ waitUntil: 'networkidle' })

    await page.locator('input[placeholder="enter username"]').fill('admin')
    await page.locator('input[placeholder="enter password"]').fill('admin123')
    await page.locator('button:has-text("EXECUTE")').click()

    await page.waitForURL('**/dashboard', { timeout: 10000 })
    expect(page.url()).toContain('/dashboard')
  })

  test('登录失败', async () => {
    const { page } = await getPage()
    await clearAuthState(page)
    await page.reload({ waitUntil: 'networkidle' })

    await page.locator('input[placeholder="enter username"]').fill('admin')
    await page.locator('input[placeholder="enter password"]').fill('wrongpassword')
    await page.locator('button:has-text("EXECUTE")').click()

    await page.waitForTimeout(1500)
    expect(page.url()).toContain('/login')
  })
})
