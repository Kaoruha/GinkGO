/**
 * Backtest List E2E 测试
 *
 * 测试回测任务列表页面的核心功能
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

  await page.fill('#username', 'admin')
  await page.fill('#password', 'admin123')
  await page.click('.login-btn')

  await page.waitForURL(/\/dashboard/, { timeout: 5000 })

  const hasToken = await page.evaluate(() => {
    return !!localStorage.getItem('access_token')
  })
  expect(hasToken).toBe(true)
}

test.describe('Backtest List E2E 测试', () => {
  test.describe('列表页面基础功能', () => {
    test('应该正确显示回测任务列表', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const h1 = page.locator('.page-title')
      await expect(h1).toContainText('回测任务')

      // 验证刷新按钮
      const refreshBtn = page.locator('.btn-secondary')
      await expect(refreshBtn.first()).toBeVisible()

      // 验证创建回测按钮
      const createBtn = page.locator('.btn-primary')
      await expect(createBtn).toContainText('创建回测')
    })

    test('应该正确显示统计卡片', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 验证4个统计卡片
      const statCards = page.locator('.stat-card')
      await expect(statCards).toHaveCount(4)

      // 验证统计标签
      const statLabels = page.locator('.stat-label')
      await expect(statLabels.nth(0)).toContainText('总任务数')
      await expect(statLabels.nth(1)).toContainText('已完成')
      await expect(statLabels.nth(2)).toContainText('运行中')
      await expect(statLabels.nth(3)).toContainText('失败')
    })

    test('应该正确显示状态筛选按钮组', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 验证筛选按钮组
      const radioGroup = page.locator('.filters-bar .radio-group')
      await expect(radioGroup).toBeVisible()

      // 验证筛选按钮
      const radioButtons = page.locator('.filters-bar .radio-button')
      await expect(radioButtons.first()).toBeVisible()

      // 验证"全部"按钮
      await expect(radioButtons.filter({ hasText: '全部' })).toBeVisible()
    })

    test('应该能够点击状态筛选按钮', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 点击"已完成"筛选按钮
      const completedBtn = page.locator('.filters-bar .radio-button').filter({ hasText: '已完成' })
      await completedBtn.click()
      await page.waitForTimeout(500)

      // 验证按钮变为激活状态
      await expect(completedBtn).toHaveClass(/active/)
    })
  })

  test.describe('搜索功能', () => {
    test('应该能够搜索任务', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const searchInput = page.locator('.search-input')
      await searchInput.fill('test')
      await page.waitForTimeout(1000)

      // 验证搜索框有内容
      const value = await searchInput.inputValue()
      expect(value).toBe('test')
    })

    test('应该能够按回车键搜索', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const searchInput = page.locator('.search-input')
      await searchInput.fill('test')
      await searchInput.press('Enter')
      await page.waitForTimeout(1000)

      // 验证搜索框有内容
      const value = await searchInput.inputValue()
      expect(value).toBe('test')
    })
  })

  test.describe('创建回测模态框', () => {
    test('点击创建按钮应该显示模态框', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 点击创建按钮
      const createBtn = page.locator('.btn-primary').filter({ hasText: '创建回测' })
      await createBtn.click()
      await page.waitForTimeout(500)

      // 验证模态框显示
      const modal = page.locator('.modal-overlay')
      await expect(modal).toBeVisible()

      // 验证模态框标题
      const modalTitle = modal.locator('.modal-header h3')
      await expect(modalTitle).toContainText('创建回测任务')

      // 关闭模态框
      const closeBtn = modal.locator('.btn-close')
      await closeBtn.click()
      await page.waitForTimeout(300)

      // 验证模态框关闭
      await expect(modal).not.toBeVisible()
    })

    test('模态框应该包含所有表单字段', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 点击创建按钮
      const createBtn = page.locator('.btn-primary').filter({ hasText: '创建回测' })
      await createBtn.click()
      await page.waitForTimeout(500)

      // 验证表单字段
      const modal = page.locator('.modal-overlay')

      // 验证任务名称输入框
      const nameInput = modal.locator('.form-input').first()
      await expect(nameInput).toBeVisible()

      // 验证 Portfolio 选择框
      const portfolioSelect = modal.locator('.form-select').first()
      await expect(portfolioSelect).toBeVisible()

      // 验证日期输入框
      const dateInputs = modal.locator('input[type="date"]')
      await expect(dateInputs).toHaveCount(2)

      // 关闭模态框
      const closeBtn = modal.locator('.btn-close')
      await closeBtn.click()
    })
  })

  test.describe('任务表格', () => {
    test('应该正确显示任务列表', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      // 检查是否有任务数据
      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 验证表格列
        const headers = page.locator('.data-table th')
        await expect(headers.nth(1)).toContainText('任务')
        await expect(headers.nth(2)).toContainText('状态')
        await expect(headers.nth(3)).toContainText('总盈亏')
      }
    })

    test('表格应该有复选框列', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 验证表头有全选复选框
        const headerCheckbox = page.locator('.data-table th input[type="checkbox"]')
        await expect(headerCheckbox).toBeVisible()
      } else {
        console.log('⚠️  没有任务数据，跳过复选框列测试')
      }
    })

    test('应该能够选择任务行', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 点击第一个任务的复选框
        const firstCheckbox = page.locator('.data-table tbody td input[type="checkbox"]').first()
        await firstCheckbox.click()
        await page.waitForTimeout(300)

        // 验证批量操作栏显示
        const batchBar = page.locator('.batch-action-bar')
        await expect(batchBar).toBeVisible()
        await expect(batchBar).toContainText('已选择')
      }
    })

    test('应该能够全选任务', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 点击表头的全选复选框
        const headerCheckbox = page.locator('.data-table th input[type="checkbox"]')
        await headerCheckbox.click()
        await page.waitForTimeout(300)

        // 验证批量操作栏显示
        const batchBar = page.locator('.batch-action-bar')
        await expect(batchBar).toBeVisible()
      }
    })

    test('应该能够取消选择', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 选中一个任务
        const firstCheckbox = page.locator('.data-table tbody td input[type="checkbox"]').first()
        await firstCheckbox.click()
        await expect(page.locator('.batch-action-bar')).toBeVisible()

        // 点击取消选择按钮
        const cancelBtn = page.locator('.batch-action-bar .btn-small').filter({ hasText: '取消选择' })
        await cancelBtn.click()
        await page.waitForTimeout(300)

        // 批量操作栏应隐藏
        await expect(page.locator('.batch-action-bar')).not.toBeVisible()
      }
    })
  })

  test.describe('分页功能', () => {
    test('应该显示分页控件', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForLoadState('networkidle')

      const tasks = await page.locator('.data-table tbody tr').count()

      if (tasks > 0) {
        // 验证分页控件存在
        const pagination = page.locator('.pagination')
        await expect(pagination).toBeVisible()

        // 验证分页信息
        const pageInfo = page.locator('.pagination-info')
        await expect(pageInfo).toBeVisible()

        // 验证每页条数选择器
        const pageSizeSelect = page.locator('.page-size-select')
        await expect(pageSizeSelect).toBeVisible()
      }
    })
  })
})
