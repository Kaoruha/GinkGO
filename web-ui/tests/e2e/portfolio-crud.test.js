/**
 * Playwright E2E 测试 - Portfolio CRUD 流程
 * 测试创建投资组合，包含组件参数配置和详情页验证
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

// 生成唯一的组合名称
const portfolioName = `E2E_Test_${Date.now()}`

// 参考examples/complete_backtest_example.py的配置
const TEST_CONFIG = {
  // FixedSelector: codes参数
  selector: {
    name: 'fixed_selector',
    codes: '000001.SZ,000002.SZ'
  },
  // FixedSizer: volume参数
  sizer: {
    name: 'fixed_sizer',
    volume: '1000'
  },
  // RandomSignalStrategy: buy_probability, sell_probability, max_signals
  strategy: {
    name: 'random_signal_strategy',
    buy_probability: 0.9,
    sell_probability: 0.05,
    max_signals: 4
  }
}

test.describe.serial('Portfolio CRUD Flow', () => {

  test('1. Create portfolio with component params via modal', async () => {
    const { page } = await getPage()

    // 访问列表页面
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 点击创建组合按钮打开模态框
    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    // 验证模态框打开
    const modal = await page.$('.ant-modal')
    expect(modal).not.toBeNull()

    // 填写基本信息
    await page.fill('.ant-modal input[placeholder="组合名称"]', portfolioName)

    // 设置初始资金
    await page.fill('.ant-modal .ant-input-number-input', '100000')
    await page.waitForTimeout(300)

    // ========== 添加选股器 fixed_selector ==========
    console.log('添加选股器:', TEST_CONFIG.selector.name)
    await page.click('.ant-modal .type-btn:nth-child(1)') // 选股器Tab
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)

    // 搜索并选择 fixed_selector
    await page.keyboard.type(TEST_CONFIG.selector.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 配置选股器参数: codes
    const selectorParamInput = await page.$('.ant-modal .config-section:first-child .item-params input')
    if (selectorParamInput) {
      await selectorParamInput.fill(TEST_CONFIG.selector.codes)
      console.log('配置选股器参数 codes:', TEST_CONFIG.selector.codes)
      await page.waitForTimeout(300)
    }

    // ========== 添加仓位管理器 fixed_sizer ==========
    console.log('添加仓位管理器:', TEST_CONFIG.sizer.name)
    await page.click('.ant-modal .type-btn:nth-child(2)') // 仓位管理Tab
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)

    // 搜索并选择 fixed_sizer
    await page.keyboard.type(TEST_CONFIG.sizer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 配置仓位管理器参数: volume
    const sizerParamInput = await page.$('.ant-modal .config-section:nth-child(2) .item-params input')
    if (sizerParamInput) {
      await sizerParamInput.fill(TEST_CONFIG.sizer.volume)
      console.log('配置仓位管理器参数 volume:', TEST_CONFIG.sizer.volume)
      await page.waitForTimeout(300)
    }

    // ========== 添加策略 random_signal_strategy ==========
    console.log('添加策略:', TEST_CONFIG.strategy.name)
    await page.click('.ant-modal .type-btn:nth-child(3)') // 策略Tab
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)

    // 搜索并选择 random_signal_strategy
    await page.keyboard.type(TEST_CONFIG.strategy.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 配置策略参数: buy_probability, sell_probability, max_signals
    const strategyParamInputs = await page.$$('.ant-modal .config-section:nth-child(3) .item-params .param-row')
    console.log('策略参数数量:', strategyParamInputs.length)

    // 遍历参数行，根据label设置值
    for (const paramRow of strategyParamInputs) {
      const label = await paramRow.$eval('.param-label', el => el.textContent)
      console.log('策略参数:', label)

      if (label.includes('buy_probability')) {
        const input = await paramRow.$('.ant-input-number-input')
        if (input) {
          await input.fill(String(TEST_CONFIG.strategy.buy_probability))
          console.log('  设置为:', TEST_CONFIG.strategy.buy_probability)
        }
      } else if (label.includes('sell_probability')) {
        const input = await paramRow.$('.ant-input-number-input')
        if (input) {
          await input.fill(String(TEST_CONFIG.strategy.sell_probability))
          console.log('  设置为:', TEST_CONFIG.strategy.sell_probability)
        }
      } else if (label.includes('max_signals')) {
        const input = await paramRow.$('.ant-input-number-input')
        if (input) {
          await input.fill(String(TEST_CONFIG.strategy.max_signals))
          console.log('  设置为:', TEST_CONFIG.strategy.max_signals)
        }
      }
    }

    await page.waitForTimeout(500)

    // ========== 点击创建按钮 ==========
    await page.click('.ant-modal button.ant-btn-primary')
    await page.waitForTimeout(3000)

    // 验证创建成功消息
    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('✅ 投资组合创建成功')
  })

  test('2. Search and verify portfolio', async () => {
    const { page } = await getPage()

    // 访问列表页面
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // 使用搜索框搜索
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1000)

    // 验证搜索结果包含创建的组合
    const cards = await page.$$('.portfolio-card')
    expect(cards.length).toBeGreaterThanOrEqual(1)

    // 验证第一个卡片的名称
    const firstName = await cards[0].evaluate(el => {
      return el.querySelector('.card-title .name')?.textContent
    })
    expect(firstName).toBe(portfolioName)
    console.log('✅ 搜索验证成功，找到组合:', firstName)
  })

  test('3. View detail and verify component params', async () => {
    const { page } = await getPage()

    // 访问列表页面
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // 搜索组合
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    // 点击卡片进入详情页
    const card = await page.$('.portfolio-card')
    expect(card).not.toBeNull()
    await card.click()
    await page.waitForTimeout(3000)

    // 验证URL变化到详情页
    const currentUrl = page.url()
    expect(currentUrl).toContain('/portfolio/')
    expect(currentUrl).not.toContain('/portfolio/create')
    console.log('详情页URL:', currentUrl)

    // 验证页面标题是组合名称
    const pageTitle = await page.$('.page-title')
    if (pageTitle) {
      const title = await pageTitle.evaluate(el => el.textContent)
      expect(title).toBe(portfolioName)
      console.log('页面标题:', title)
    }

    // 验证组件配置卡片存在
    const componentsCard = await page.$('.components-card')
    expect(componentsCard).not.toBeNull()
    console.log('✅ 组件配置卡片存在')

    // 验证组件数量 (选股器、仓位管理、策略)
    const componentNames = await page.$$('.component-name')
    expect(componentNames.length).toBeGreaterThanOrEqual(3)
    console.log('组件数量:', componentNames.length)

    // 验证参数标签存在并包含正确的值
    const configTags = await page.$$('.config-tag')
    console.log('参数标签数量:', configTags.length)

    // 验证关键参数值
    const pageContent = await page.content()
    expect(pageContent).toContain('codes')
    expect(pageContent).toContain(TEST_CONFIG.selector.codes)
    expect(pageContent).toContain('buy_probability')
    expect(pageContent).toContain(String(TEST_CONFIG.strategy.buy_probability))
    expect(pageContent).toContain('sell_probability')
    expect(pageContent).toContain(String(TEST_CONFIG.strategy.sell_probability))
    expect(pageContent).toContain('max_signals')
    expect(pageContent).toContain(String(TEST_CONFIG.strategy.max_signals))

    console.log('✅ 参数配置验证成功:')
    console.log('  - codes:', TEST_CONFIG.selector.codes)
    console.log('  - buy_probability:', TEST_CONFIG.strategy.buy_probability)
    console.log('  - sell_probability:', TEST_CONFIG.strategy.sell_probability)
    console.log('  - max_signals:', TEST_CONFIG.strategy.max_signals)
  })

  test('4. Delete portfolio', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    // 访问列表页面
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // 搜索要删除的组合
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    // 找到目标卡片
    const cards = await page.$$('.portfolio-card')
    expect(cards.length).toBeGreaterThanOrEqual(1)

    // 点击卡片的更多按钮
    const moreBtn = await cards[0].$('.ant-dropdown-trigger')
    await moreBtn.click()
    await page.waitForTimeout(800)

    // 点击删除菜单项 (第二个：详情、删除)
    const menuItems = await page.$$('.ant-dropdown-menu-item')
    await menuItems[1].click() // 删除是第二个选项
    await page.waitForTimeout(800)

    // 确认删除
    await page.click('.ant-modal .ant-btn-dangerous')
    await page.waitForTimeout(3000)

    // 清空搜索框
    await page.fill('.ant-input-search input', '')
    await page.waitForTimeout(500)

    // 再次搜索，确认已删除
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    // 验证搜索结果为空
    const remainingCards = await page.$$('.portfolio-card')
    const hasEmpty = await page.$('.ant-empty') !== null

    expect(remainingCards.length === 0 || hasEmpty).toBeTruthy()
    console.log('✅ 删除验证成功')
  })
})
