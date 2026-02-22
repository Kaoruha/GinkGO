/**
 * Playwright E2E 测试 - 订单和持仓功能
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || context.pages()[0]
  return { browser, page }
}

async function login(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
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

test.describe('订单和持仓功能', () => {

  test('可以访问模拟订单页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '模拟交易')
    await page.click('.ant-menu-item:has-text("订单记录")')
    await page.waitForTimeout(800)
    // 检查页面表格存在
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问实盘订单页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '实盘交易')
    await page.click('.ant-menu-item:has-text("订单管理")')
    await page.waitForTimeout(800)
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问实盘持仓页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '实盘交易')
    await page.click('.ant-menu-item:has-text("持仓管理")')
    await page.waitForTimeout(800)
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问模拟交易监控页面', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '模拟交易')
    await page.click('.ant-menu-item:has-text("模拟监控")')
    await page.waitForTimeout(800)
    // 检查统计卡片存在（多个卡片，检查第一个）
    await expect(page.locator('.ant-statistic').first()).toBeVisible({ timeout: 5000 })
  })

  test('模拟交易页面有设置抽屉', async () => {
    const { page } = await getPage()
    await login(page)
    await expandMenu(page, '模拟交易')
    await page.click('.ant-menu-item:has-text("模拟监控")')
    await page.waitForTimeout(500)
    await page.click('button:has-text("设置")')
    await page.waitForTimeout(300)
    await expect(page.locator('.ant-drawer')).toBeVisible({ timeout: 5000 })
  })
})
