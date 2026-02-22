/**
 * Playwright E2E 测试 - Portfolio 创建后页面跳转验证
 * 通过模态框创建投资组合
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

// 辅助函数：获取远程浏览器页面
async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || context.pages()[0]
  return { browser, page }
}

// 生成唯一的组合名称
const portfolioName = `CreateNav_${Date.now()}`

test.describe('Portfolio Create Navigation', () => {

  test('Create portfolio via modal and verify navigation to detail page', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    // 1. 访问列表页面
    console.log('=== Step 1: 访问列表页面 ===')
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    console.log('列表页URL:', page.url())

    // 点击创建组合按钮打开模态框
    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    // 验证模态框打开
    const modal = await page.$('.ant-modal')
    expect(modal).not.toBeNull()
    console.log('✅ 模态框已打开')

    // 填写组合名称
    await page.fill('.ant-modal input[placeholder="组合名称"]', portfolioName)
    await page.fill('.ant-modal .ant-input-number-input', '100000')

    // 2. 添加必要组件
    console.log('\n=== Step 2: 添加组件 ===')

    // 添加选股器
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type('fixed_selector')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 配置选股器参数
    const selectorInput = await page.$('.ant-modal .config-section:first-child .item-params input')
    if (selectorInput) {
      await selectorInput.fill('000001.SZ')
    }

    // 添加仓位管理器
    await page.click('.ant-modal .type-btn:nth-child(2)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type('fixed_sizer')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 添加策略
    await page.click('.ant-modal .type-btn:nth-child(3)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type('random_signal')
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    console.log('组件添加完成')

    // 3. 点击创建按钮
    console.log('\n=== Step 3: 点击创建按钮 ===')
    await page.click('.ant-modal button.ant-btn-primary')

    // 4. 验证页面跳转
    console.log('\n=== Step 4: 验证页面跳转 ===')
    await page.waitForTimeout(3000)

    const newUrl = page.url()
    console.log('创建后URL:', newUrl)

    // 验证成功消息
    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('✅ 成功消息显示')

    // 验证URL变化 - 应该跳转到详情页
    // URL格式应该是 /portfolio/{uuid}
    expect(newUrl).toContain('/portfolio/')
    expect(newUrl).not.toContain('/portfolio?')
    console.log('✅ URL已跳转到详情页')

    // 提取UUID
    const uuid = newUrl.split('/portfolio/')[1]
    expect(uuid).toHaveLength(32)
    console.log('UUID:', uuid)

    // 5. 验证详情页内容
    console.log('\n=== Step 5: 验证详情页内容 ===')
    await page.waitForTimeout(2000)

    // 验证页面标题
    const pageTitle = await page.$('.page-title')
    expect(pageTitle).not.toBeNull()
    const title = await pageTitle.evaluate(el => el.textContent)
    expect(title).toBe(portfolioName)
    console.log('页面标题:', title)

    // 验证组件配置区域
    const componentsCard = await page.$('.components-card')
    expect(componentsCard).not.toBeNull()
    console.log('✅ 组件配置卡片存在')

    // 验证统计卡片
    const statCards = await page.$$('.stat-card')
    expect(statCards.length).toBe(4)
    console.log('统计卡片数量:', statCards.length)

    // 6. 验证返回按钮
    console.log('\n=== Step 6: 验证返回按钮 ===')
    const backBtn = await page.$('.back-btn')
    expect(backBtn).not.toBeNull()
    console.log('✅ 返回按钮存在')

    // 点击返回按钮
    await backBtn.click()
    await page.waitForTimeout(2000)

    const afterBackUrl = page.url()
    console.log('返回后URL:', afterBackUrl)
    expect(afterBackUrl).toContain('/portfolio')
    expect(afterBackUrl).not.toContain(uuid)
    console.log('✅ 返回列表页成功')

    // 7. 清理 - 删除创建的组合
    console.log('\n=== Step 7: 清理测试数据 ===')
    await page.waitForTimeout(1000)
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const cards = await page.$$('.portfolio-card')
    if (cards.length > 0) {
      const moreBtn = await cards[0].$('.ant-dropdown-trigger')
      await moreBtn.click()
      await page.waitForTimeout(800)

      const menuItems = await page.$$('.ant-dropdown-menu-item')
      await menuItems[1].click()  // 删除是第二个选项（详情、删除）
      await page.waitForTimeout(800)

      await page.click('.ant-modal .ant-btn-dangerous')
      await page.waitForTimeout(2000)
      console.log('✅ 测试数据已清理')
    }
  })
})
