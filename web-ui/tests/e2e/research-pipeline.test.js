/**
 * Playwright E2E 测试 - 研究链路 MVP 验证
 *
 * 验证 Dashboard 统计数据、模拟盘页面、实盘账号页面的基本可访问性和渲染
 */

import { test, expect } from '@playwright/test'

const WEB_UI_URL = process.env.WEB_UI_URL || 'http://localhost:5173'

test.describe.configure({ mode: 'serial' })

// 辅助函数：执行登录并等待认证完成
async function doLogin(page, context) {
  await context.clearCookies()
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => {
    localStorage.clear()
  })

  // 填写登录表单
  await page.fill('#username', 'admin')
  await page.fill('#password', 'admin123')
  await page.click('.login-btn')

  // 等待导航到 dashboard
  await page.waitForURL(/\/dashboard/, { timeout: 5000 })

  // 验证 localStorage 中有 token
  const hasToken = await page.evaluate(() => {
    return !!localStorage.getItem('access_token')
  })
  expect(hasToken).toBe(true)
}

test.describe('研究链路 MVP 验证', () => {
  test.describe('Dashboard 页面', () => {
    test('Dashboard 显示统计数据', async ({ page, context }) => {
      await doLogin(page, context)

      // 等待页面加载完成
      await page.waitForLoadState('networkidle')

      // 验证统计卡片区域存在（.stat-card）
      const statCards = page.locator('.stats-grid .stat-card')
      await expect(statCards.first()).toBeVisible({ timeout: 5000 })

      // 验证至少有 4 个统计卡片
      const statCardCount = await statCards.count()
      expect(statCardCount).toBeGreaterThanOrEqual(4)

      // 验证统计卡片包含常见标签文本
      const statsContent = await page.locator('.stats-grid').textContent()
      expect(statsContent).toContain('运行中 Portfolio')
    })

    test('Dashboard 显示四阶段卡片', async ({ page, context }) => {
      await doLogin(page, context)

      await page.waitForLoadState('networkidle')

      // 验证 4 阶段卡片
      const stageCards = page.locator('.stage-card')
      await expect(stageCards).toHaveCount(4)

      // 验证阶段卡片内容
      await expect(stageCards.nth(0)).toContainText('回测')
      await expect(stageCards.nth(1)).toContainText('验证')
      await expect(stageCards.nth(2)).toContainText('模拟')
      await expect(stageCards.nth(3)).toContainText('实盘')
    })
  })

  test.describe('模拟盘页面', () => {
    test('模拟盘页面可访问', async ({ page, context }) => {
      await doLogin(page, context)

      // 导航到模拟交易页面
      await page.goto(`${WEB_UI_URL}/paper`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题包含"模拟交易"
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toBeVisible({ timeout: 5000 })
      await expect(pageTitle).toContainText('模拟交易')

      // 验证页面统计卡片区域存在
      const statCards = page.locator('.stats-grid .stat-card')
      await expect(statCards.first()).toBeVisible({ timeout: 5000 })

      // 验证包含关键统计标签
      const statsContent = await page.locator('.stats-grid').textContent()
      expect(statsContent).toContain('今日盈亏')
    })

    test('模拟盘订单记录页面可访问', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/paper/orders`)
      await page.waitForLoadState('networkidle')

      // 验证页面容器存在（页面不报错即可通过）
      const pageContainer = page.locator('.page-container')
      await expect(pageContainer).toBeVisible({ timeout: 5000 })
    })
  })

  test.describe('实盘交易页面', () => {
    test('实盘监控页面可访问', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/live`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题包含"实盘监控"
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toBeVisible({ timeout: 5000 })
      await expect(pageTitle).toContainText('实盘监控')

      // 验证统计卡片存在
      const statCards = page.locator('.stats-grid .stat-card')
      await expect(statCards.first()).toBeVisible({ timeout: 5000 })

      // 验证包含关键统计标签
      const statsContent = await page.locator('.stats-grid').textContent()
      expect(statsContent).toContain('总资产')
    })

    test('实盘账号配置页面可访问', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/live/account-config`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toBeVisible({ timeout: 5000 })
      await expect(pageTitle).toContainText('实盘账号配置')

      // 验证添加账号按钮存在
      const addBtn = page.locator('.btn-primary')
      await expect(addBtn.first()).toBeVisible({ timeout: 5000 })
      await expect(addBtn.first()).toContainText('添加账号')
    })

    test('实盘持仓管理页面可访问', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/live/positions`)
      await page.waitForLoadState('networkidle')

      // 验证页面容器存在
      const pageContainer = page.locator('.page-container')
      await expect(pageContainer).toBeVisible({ timeout: 5000 })
    })
  })
})
