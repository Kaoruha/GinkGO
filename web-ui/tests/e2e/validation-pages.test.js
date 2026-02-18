/**
 * Playwright E2E 测试 - 验证和优化页面
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()
  return { browser, page }
}

async function login(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => { localStorage.clear(); sessionStorage.clear() })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('input[placeholder="enter username"]').fill('admin')
  await page.locator('input[placeholder="enter password"]').fill('admin123')
  await page.locator('button:has-text("EXECUTE")').click()
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}

async function expandMenu(page, menuName) {
  const menuExpanded = await page.locator(`.ant-menu-submenu-open:has-text("${menuName}")`).count()
  if (menuExpanded === 0) {
    await page.click(`.ant-menu-submenu-title:has-text("${menuName}")`)
    await page.waitForTimeout(300)
  }
}

test.describe('验证页面', () => {

  test('可以访问走步验证页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '样本验证')
    await page.click('.ant-menu-item:has-text("走步验证")')
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-card').first()).toBeVisible({ timeout: 5000 })
  })

  test('可以访问蒙特卡洛页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '样本验证')
    await page.click('.ant-menu-item:has-text("蒙特卡洛")')
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-card').first()).toBeVisible({ timeout: 5000 })
  })

  test('可以访问敏感性分析页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '样本验证')
    await page.click('.ant-menu-item:has-text("敏感性分析")')
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-card').first()).toBeVisible({ timeout: 5000 })
  })
})

test.describe('数据管理页面', () => {

  test('可以访问数据同步页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '数据管理')
    await page.click('.ant-menu-item:has-text("数据同步")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("数据同步")')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('回测对比页面', () => {

  test('可以访问回测对比页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '策略回测')
    await page.click('.ant-menu-item:has-text("回测对比")')
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-card')).toBeVisible({ timeout: 5000 })
  })
})
