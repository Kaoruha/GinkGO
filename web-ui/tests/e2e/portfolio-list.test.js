/**
 * Portfolio List E2E 测试
 *
 * 测试投资组合列表页面的核心功能
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

test.describe('Portfolio List E2E 测试', () => {
  test.describe('列表页面基础功能', () => {
    test('应该正确显示投资组合列表', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 验证页面标题
      const h1 = page.locator('.page-header h1')
      await expect(h1).toContainText('投资组合')

      // 验证搜索框
      const searchInput = page.locator('.search-input')
      await expect(searchInput).toBeVisible()

      // 验证创建按钮（使用更精确的选择器避免多元素冲突）
      const createBtn = page.locator('.page-header .btn-primary').or(page.locator('.btn-primary:has-text("创建组合")'))
      await expect(createBtn.first()).toBeVisible()
    })

    test('应该正确显示统计卡片', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 验证4个统计卡片
      const statCards = page.locator('.stat-card')
      await expect(statCards).toHaveCount(4)

      // 验证统计标签
      const statLabels = page.locator('.stat-label')
      await expect(statLabels.nth(0)).toContainText('总投资组合')
      await expect(statLabels.nth(1)).toContainText('运行中')
      await expect(statLabels.nth(2)).toContainText('平均净值')
      await expect(statLabels.nth(3)).toContainText('总资产')
    })

    test('应该正确显示筛选按钮组', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 验证筛选按钮组
      const radioGroup = page.locator('.radio-group')
      await expect(radioGroup).toBeVisible()

      // 验证4个筛选按钮
      const radioButtons = page.locator('.radio-button')
      await expect(radioButtons).toHaveCount(4)

      // 验证按钮文本
      await expect(radioButtons.nth(0)).toContainText('全部')
      await expect(radioButtons.nth(1)).toContainText('回测')
      await expect(radioButtons.nth(2)).toContainText('模拟')
      await expect(radioButtons.nth(3)).toContainText('实盘')
    })

    test('应该能够点击筛选按钮', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 点击"回测"筛选按钮
      const backtestBtn = page.locator('.radio-button').filter({ hasText: '回测' })
      await backtestBtn.click()
      await page.waitForTimeout(500)

      // 验证按钮变为激活状态
      await expect(backtestBtn).toHaveClass(/active/)
    })
  })

  test.describe('组合卡片功能', () => {
    test('应该正确显示组合卡片', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 检查是否有组合卡片
      const cards = page.locator('.portfolio-card')
      const count = await cards.count()

      if (count > 0) {
        // 验证卡片结构
        const firstCard = cards.first()

        // 验证卡片标题
        const cardTitle = firstCard.locator('.card-title .name')
        await expect(cardTitle).toBeVisible()

        // 验证卡片内容
        const cardContent = firstCard.locator('.card-content')
        await expect(cardContent).toBeVisible()

        // 验证卡片底部
        const cardFooter = firstCard.locator('.card-footer')
        await expect(cardFooter).toBeVisible()
      }
    })

    test('应该能够打开卡片菜单', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      const cards = page.locator('.portfolio-card')
      const count = await cards.count()

      if (count > 0) {
        const firstCard = cards.first()
        const menuBtn = firstCard.locator('.btn-icon')
        await menuBtn.click()
        await page.waitForTimeout(300)

        // 验证下拉菜单显示
        const dropdown = firstCard.locator('.dropdown-menu')
        await expect(dropdown).toBeVisible()

        // 验证菜单项
        const dropdownItems = dropdown.locator('.dropdown-item')
        await expect(dropdownItems).toHaveCount(2)
        await expect(dropdownItems.nth(0)).toContainText('详情')
        await expect(dropdownItems.nth(1)).toContainText('删除')
      }
    })

    test('标签应该有正确的颜色类', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      const cards = page.locator('.portfolio-card')
      const count = await cards.count()

      if (count > 0) {
        const firstCard = cards.first()

        // 验证模式标签有颜色类
        const modeTag = firstCard.locator('.card-title .tag')
        const hasColorClass = await modeTag.evaluate(el => {
          return el.classList.contains('tag-purple') ||
                 el.classList.contains('tag-blue') ||
                 el.classList.contains('tag-green') ||
                 el.classList.contains('tag-orange')
        })
        expect(hasColorClass).toBe(true)
      }
    })
  })

  test.describe('搜索功能', () => {
    test('应该能够搜索组合', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      const searchInput = page.locator('.search-input')
      await searchInput.fill('test')
      await page.waitForTimeout(1000)

      // 验证搜索框有内容
      const value = await searchInput.inputValue()
      expect(value).toBe('test')
    })
  })

  test.describe('创建按钮', () => {
    test('点击创建按钮应该显示模态框', async ({ page, context }) => {
      await doLogin(page, context)

      await page.goto(`${WEB_UI_URL}/portfolio`)
      await page.waitForLoadState('networkidle')

      // 点击创建按钮
      const createBtn = page.locator('.btn-primary').filter({ hasText: '创建组合' })
      await createBtn.click()
      await page.waitForTimeout(500)

      // 验证模态框显示
      const modal = page.locator('.modal-overlay')
      await expect(modal).toBeVisible()

      // 验证模态框标题
      const modalTitle = modal.locator('.modal-header h3')
      await expect(modalTitle).toContainText('创建投资组合')

      // 关闭模态框
      const closeBtn = modal.locator('.btn-close')
      await closeBtn.click()
      await page.waitForTimeout(300)

      // 验证模态框关闭
      await expect(modal).not.toBeVisible()
    })
  })
})
