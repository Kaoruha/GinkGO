/**
 * Playwright E2E 测试 - Portfolio CRUD 流程
 * 测试创建投资组合、搜索、筛选、详情验证、删除
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
const portfolioName = `E2E_Test_${Date.now()}`

// 测试配置：参数名和值
const TEST_CONFIG = {
  selector: {
    name: 'fixed_selector',
    params: {
      name: 'FixedSelector_E2E',
      codes: '000001.SZ,000002.SZ'
    }
  },
  sizer: {
    name: 'fixed_sizer',
    params: {
      name: 'FixedSizer_E2E',
      volume: '1000'
    }
  },
  strategy: {
    name: 'random_signal_strategy',
    params: {
      name: 'RandomStrategy_E2E',
      buy_probability: '0.9',
      sell_probability: '0.05',
      max_signals: '4'
    }
  }
}

// 辅助函数：根据label填写参数
async function fillParamByLabel(page, sectionSelector, label, value) {
  const paramRows = await page.$$(sectionSelector + ' .param-row')
  for (const row of paramRows) {
    const labelEl = await row.$('.param-label')
    if (labelEl) {
      const labelText = await labelEl.textContent()
      if (labelText && labelText.includes(label)) {
        const numInput = await row.$('.ant-input-number-input')
        if (numInput) {
          await numInput.fill(String(value))
          console.log(`  ✓ ${label} = ${value}`)
          return true
        }
        const input = await row.$('.ant-input')
        if (input) {
          await input.fill(String(value))
          console.log(`  ✓ ${label} = ${value}`)
          return true
        }
      }
    }
  }
  console.log(`  ⚠ 未找到参数: ${label}`)
  return false
}

test.describe.serial('Portfolio CRUD Flow', () => {

  test('1. Create portfolio with component params via modal', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    const modal = await page.$('.ant-modal')
    expect(modal).not.toBeNull()

    await page.fill('.ant-modal input[placeholder="组合名称"]', portfolioName)
    await page.fill('.ant-modal .ant-input-number-input', '100000')
    await page.waitForTimeout(300)

    // 添加选股器
    console.log('添加选股器:', TEST_CONFIG.selector.name)
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.selector.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    console.log('配置选股器参数:')
    for (const [key, value] of Object.entries(TEST_CONFIG.selector.params)) {
      await fillParamByLabel(page, '.ant-modal .config-section', key, value)
    }
    await page.waitForTimeout(500)

    // 添加仓位管理器
    console.log('添加仓位管理器:', TEST_CONFIG.sizer.name)
    await page.click('.ant-modal .type-btn:nth-child(2)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.sizer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    console.log('配置仓位管理器参数:')
    for (const [key, value] of Object.entries(TEST_CONFIG.sizer.params)) {
      await fillParamByLabel(page, '.ant-modal .config-section', key, value)
    }
    await page.waitForTimeout(500)

    // 添加策略
    console.log('添加策略:', TEST_CONFIG.strategy.name)
    await page.click('.ant-modal .type-btn:nth-child(3)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.strategy.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    console.log('配置策略参数:')
    for (const [key, value] of Object.entries(TEST_CONFIG.strategy.params)) {
      await fillParamByLabel(page, '.ant-modal .config-section', key, value)
    }
    await page.waitForTimeout(500)

    await page.click('.ant-modal button.ant-btn-primary')
    await page.waitForTimeout(3000)

    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('✅ 投资组合创建成功')
  })

  test('2. Search functionality', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('=== 测试搜索功能 ===')

    // 获取搜索前的卡片数
    const beforeCards = await page.$$('.portfolio-card')
    console.log('搜索前卡片数:', beforeCards.length)

    // 搜索
    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1000)

    // 验证搜索结果
    const afterCards = await page.$$('.portfolio-card')
    console.log('搜索后卡片数:', afterCards.length)
    expect(afterCards.length).toBeGreaterThanOrEqual(1)

    // 验证搜索结果包含目标组合
    if (afterCards.length > 0) {
      const firstName = await afterCards[0].evaluate(el => {
        return el.querySelector('.card-title .name')?.textContent
      })
      expect(firstName).toBe(portfolioName)
      console.log('✅ 搜索验证成功，找到组合:', firstName)
    }
  })

  test('3. Filter by mode', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('=== 测试模式筛选 ===')

    // 获取筛选前的卡片数
    const beforeCards = await page.$$('.portfolio-card')
    const beforeCount = beforeCards.length
    console.log('筛选前卡片数:', beforeCount)

    // 点击"回测"筛选
    await page.click('.ant-radio-button-wrapper:has-text("回测")')
    await page.waitForTimeout(1000)

    const afterCards = await page.$$('.portfolio-card')
    console.log('筛选后卡片数:', afterCards.length)

    // 验证筛选后的卡片都有正确的模式标签
    for (const card of afterCards) {
      const modeTag = await card.$('.card-title .ant-tag')
      if (modeTag) {
        const tagText = await modeTag.textContent()
        expect(tagText).toBe('回测')
      }
    }

    // 点击"全部"恢复
    await page.click('.ant-radio-button-wrapper:has-text("全部")')
    await page.waitForTimeout(1000)

    console.log('✅ 模式筛选功能正常')
  })

  test('4. View detail and verify component params', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const card = await page.$('.portfolio-card')
    expect(card).not.toBeNull()
    await card.click()
    await page.waitForTimeout(3000)

    const currentUrl = page.url()
    expect(currentUrl).toContain('/portfolio/')
    expect(currentUrl).not.toContain('/portfolio/create')
    console.log('详情页URL:', currentUrl)

    const pageTitle = await page.$('.page-title')
    if (pageTitle) {
      const title = await pageTitle.evaluate(el => el.textContent)
      expect(title).toBe(portfolioName)
      console.log('页面标题:', title)
    }

    const componentsCard = await page.$('.components-card')
    expect(componentsCard).not.toBeNull()
    console.log('✅ 组件配置卡片存在')

    const componentNames = await page.$$('.component-name')
    expect(componentNames.length).toBeGreaterThanOrEqual(3)
    console.log('组件数量:', componentNames.length)

    const configTags = await page.$$('.config-tag')
    console.log('参数标签数量:', configTags.length)
    expect(configTags.length).toBeGreaterThan(0)

    const bodyText = await page.$eval('body', el => el.innerText)
    expect(bodyText).toContain(TEST_CONFIG.selector.params.codes)
    expect(bodyText).toContain(TEST_CONFIG.strategy.params.buy_probability)
    expect(bodyText).toContain(TEST_CONFIG.strategy.params.sell_probability)
    expect(bodyText).toContain(TEST_CONFIG.strategy.params.max_signals)

    console.log('✅ 参数配置验证成功')
  })

  test('5. Statistics cards', async () => {
    const { page } = await getPage()

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    console.log('=== 测试统计卡片 ===')

    // 检查统计卡片是否存在
    const statCards = await page.$$('.stat-card')
    expect(statCards.length).toBe(4)
    console.log('统计卡片数量:', statCards.length)

    // 验证统计值
    const statValues = await page.$$eval('.ant-statistic-title', elements =>
      elements.map(el => el.textContent)
    )
    expect(statValues).toContain('总投资组合')
    expect(statValues).toContain('运行中')
    expect(statValues).toContain('平均净值')
    expect(statValues).toContain('总资产')

    console.log('✅ 统计卡片验证成功')
  })

  test('6. Delete portfolio', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const cards = await page.$$('.portfolio-card')
    expect(cards.length).toBeGreaterThanOrEqual(1)

    const moreBtn = await cards[0].$('.ant-dropdown-trigger')
    await moreBtn.click()
    await page.waitForTimeout(800)

    const menuItems = await page.$$('.ant-dropdown-menu-item')
    await menuItems[1].click()
    await page.waitForTimeout(800)

    await page.click('.ant-modal .ant-btn-dangerous')
    await page.waitForTimeout(3000)

    await page.fill('.ant-input-search input', '')
    await page.waitForTimeout(500)

    await page.fill('.ant-input-search input', portfolioName)
    await page.waitForTimeout(1500)

    const remainingCards = await page.$$('.portfolio-card')
    const hasEmpty = await page.$('.ant-empty') !== null

    expect(remainingCards.length === 0 || hasEmpty).toBeTruthy()
    console.log('✅ 删除验证成功')
  })
})
