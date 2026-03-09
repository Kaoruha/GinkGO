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

test('回测列表页健康检查', async () => {
  // ✅ 使用 getHealthyPage：页面有错误会立即抛出异常
  const { browser, page } = await getHealthyPage(`${WEB_UI_URL}/stage1/backtest`)

  try {
    // 到这里说明页面是健康的，验证关键元素
    await expect(page.locator('.page-container')).toBeVisible()
    await expect(page.locator('.ant-table')).toBeVisible()

    const bodyText = await page.locator('body').textContent()
    expect(bodyText).toContain('回测任务')
    expect(bodyText).toContain('全部')

    console.log('✅ 回测列表页健康检查通过')
  } finally {
    await browser.close()
  }
})

test('回测详情页健康检查', async () => {
  const { browser, page } = await getHealthyPage(`${WEB_UI_URL}/stage1/backtest`)

  try {
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

// 导入 assertPageHealthy 函数
import { assertPageHealthy } from './helpers/page-health'
