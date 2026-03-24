/**
 * 页面健康检查测试
 *
 * ⚠️ 核心原则：页面有错误 = 测试立即失败
 *
 * 这是第一层测试，用于快速验证页面是否正常加载
 * 如果此测试失败，所有其他功能测试都会跳过
 *
 * 运行频率：每次代码变更后
 */

import { test, expect } from '@playwright/test'
import { getHealthyPage, WEB_UI_URL } from './helpers/page-health'
import { assertPageHealthy } from './helpers/page-health'

// 辅助函数：执行登录
async function doLogin(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.fill('#username', 'admin')
  await page.fill('#password', 'admin123')
  await page.click('.login-btn')
  await page.waitForURL(/\/dashboard/, { timeout: 5000 })
}

test('回测列表页健康检查', async () => {
  const { chromium } = await import('@playwright/test')

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })

  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // 先登录
    await doLogin(page)

    // 然后访问回测页面
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')

    // 验证关键元素存在（但不强制要求表格，可能没有数据）
    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toContain('回测')

    // 检查是否有表格或空状态
    const hasTable = await page.locator('.data-table').count() > 0
    const hasEmptyState = await page.locator('.empty-state').count() > 0

    expect(hasTable || hasEmptyState).toBeTruthy()

    console.log('✅ 回测列表页健康检查通过')
  } finally {
    await browser.close()
  }
})

test('回测详情页健康检查', async () => {
  const { chromium } = await import('@playwright/test')

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })

  const context = await browser.newContext()
  const page = await context.newPage()

  try {
    // 先登录
    await doLogin(page)

    // 访问回测列表
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')

    // 查找第一个详情链接
    const detailLink = page.locator('a:has-text("查看详情")').first()
    const count = await detailLink.count()

    if (count > 0) {
      await detailLink.click()
      await page.waitForTimeout(2000)

      // 再次检查详情页健康状态
      await assertPageHealthy(page)

      // 验证详情页元素
      await expect(page.locator('.page-title, h1, h2')).toBeVisible()
      console.log('✅ 回测详情页健康检查通过')
    } else {
      console.log('⚠️  没有找到详情链接，跳过详情页检查')
    }
  } finally {
    await browser.close()
  }
})
