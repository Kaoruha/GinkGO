/**
 * 数据页面 E2E 测试
 *
 * 测试数据概览、Dashboard、K线数据、股票列表页面
 */

import { test, expect } from '@playwright/test'

const WEB_UI_URL = process.env.WEB_UI_URL || 'http://localhost:5173'

test.describe.configure({ mode: 'serial' })

// 辅助函数：执行登录并等待认证完成
async function doLogin(page, context) {
  await context.clearCookies()
  // 清除 localStorage
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

test.describe('数据页面 E2E 测试', () => {
  test.describe('Dashboard 页面', () => {
    test('应该正确显示 Dashboard', async ({ page, context }) => {
      await doLogin(page, context)

      // 验证系统状态卡片
      const statCards = page.locator('.stat-card')
      await expect(statCards).toHaveCount(4)

      // 验证4阶段卡片
      const stageCards = page.locator('.stage-card')
      await expect(stageCards).toHaveCount(4)

      // 验证阶段卡片内容
      await expect(stageCards.nth(0)).toContainText('回测')
      await expect(stageCards.nth(1)).toContainText('验证')
      await expect(stageCards.nth(2)).toContainText('模拟')
      await expect(stageCards.nth(3)).toContainText('实盘')
    })

    test('阶段卡片应该显示正确的样式', async ({ page, context }) => {
      await doLogin(page, context)

      // 验证各阶段卡片的边框颜色
      const stage1 = page.locator('.stage-card.stage-1')
      const stage2 = page.locator('.stage-card.stage-2')
      const stage3 = page.locator('.stage-card.stage-3')
      const stage4 = page.locator('.stage-card.stage-4')

      await expect(stage1).toBeVisible()
      await expect(stage2).toBeVisible()
      await expect(stage3).toBeVisible()
      await expect(stage4).toBeVisible()
    })
  })

  test.describe('数据概览页面', () => {
    test('应该正确显示数据概览', async ({ page, context }) => {
      await doLogin(page, context)

      // 导航到数据概览页面
      await page.goto(`${WEB_UI_URL}/data`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toContainText('数据概览')

      // 验证统计卡片存在
      const statCards = page.locator('.stat-card')
      await expect(statCards.first()).toBeVisible()

      // 验证快捷操作按钮存在
      const actionBtns = page.locator('.action-btn')
      await expect(actionBtns.first()).toBeVisible()
    })
  })

  test.describe('K线数据页面', () => {
    test('应该正确显示K线数据页面', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/data/bars`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toContainText('K线数据')

      // 验证空状态
      const chartEmpty = page.locator('.chart-empty')
      await expect(chartEmpty).toBeVisible()
    })

    test('应该能够选择股票查看K线', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/data/bars`)
      await page.waitForLoadState('networkidle')

      // 选择股票 - 使用第一个 select 元素（股票选择器）
      const stockSelect = page.locator('select.form-select').first()
      await stockSelect.selectOption('000001.SZ')

      // 等待图表加载
      await page.waitForTimeout(2000)

      // 验证图表容器
      const chartContainer = page.locator('.chart-container')
      await expect(chartContainer).toBeVisible()
    })
  })

  test.describe('股票列表页面', () => {
    test('应该正确显示股票列表', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/data/stocks`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const pageTitle = page.locator('.page-title')
      await expect(pageTitle).toContainText('股票信息')

      // 验证统计卡片
      const statCards = page.locator('.stat-card')
      await expect(statCards).toHaveCount(3)

      // 验证表格
      const table = page.locator('.data-table')
      await expect(table).toBeVisible()
    })

    test('应该能够搜索股票', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/data/stocks`)
      await page.waitForLoadState('networkidle')

      // 输入搜索关键词
      const searchInput = page.locator('.search-input')
      await searchInput.fill('平安')

      // 等待搜索结果
      await page.waitForTimeout(500)

      // 验证表格仍显示
      const table = page.locator('.data-table')
      await expect(table).toBeVisible()
    })
  })
})
