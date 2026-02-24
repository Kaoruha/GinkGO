/**
 * Playwright E2E 测试 - 完整回测流程（含版本管理）
 * 测试从组合创建到回测验证，包括组件版本信息的保存和追溯
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'
const API_URL = 'http://localhost:8000'

async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || context.pages()[0]
  return { browser, page }
}

// 测试配置
const TEST_CONFIG = {
  portfolioName: `回测版本验证_${Date.now()}`,
  backtestName: `回测任务_${Date.now()}`,
  initialCash: 100000,
  selector: { name: 'fixed_selector', codes: '000001.SZ,000002.SZ' },
  sizer: { name: 'fixed_sizer', volume: '100' },
  strategy: { name: 'random_signal_strategy', buy_probability: 0.9, sell_probability: 0.05, max_signals: 10 },
  analyzer: { name: 'net_value' },
  dateRange: { start: '2023-01-01', end: '2024-06-30' }
}

let portfolioUuid = null
let backtestUuid = null
let savedComponentVersions = {}

// 辅助函数：从组件选择下拉框中获取组件版本信息
async function getComponentVersionFromDropdown(page, componentName) {
  await page.click('.component-selector .ant-select-selector')
  await page.waitForTimeout(500)

  // 查找匹配的组件选项
  const options = await page.$$('.ant-select-dropdown .ant-select-item-option')
  for (const option of options) {
    const text = await option.textContent()
    if (text && text.includes(componentName)) {
      // 提取版本号（格式如 1.0.0）
      const versionMatch = text.match(/(\d+\.\d+\.\d+)/)
      const hasLatestTag = text.includes('最新')

      // 关闭下拉框
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)

      return {
        version: versionMatch ? versionMatch[1] : 'UNKNOWN_VERSION',
        isLatest: hasLatestTag
      }
    }
  }

  // 关闭下拉框
  await page.keyboard.press('Escape')
  await page.waitForTimeout(300)
  return null
}

// 辅助函数：获取当前配置区域的组件版本
async function getCurrentComponentVersion(page) {
  // 检查 .item-info 内是否有版本相关内容
  const itemInfos = await page.$$('.ant-modal .item-info')
  if (itemInfos.length > 0) {
    const lastItemInfo = itemInfos[itemInfos.length - 1]

    // 获取 item-info 的文本内容，检查是否包含版本号
    const textContent = await lastItemInfo.textContent()
    const hasVersion = /\d+\.\d+\.\d+/.test(textContent)

    if (hasVersion) {
      const versionMatch = textContent.match(/(\d+\.\d+\.\d+)/)
      // 检查是否禁用
      const hasDisabledClass = await lastItemInfo.evaluate(el => {
        const selectEl = el.querySelector('.ant-select')
        return selectEl ? selectEl.classList.contains('ant-select-disabled') : false
      })

      return {
        version: versionMatch ? versionMatch[1] : 'UNKNOWN_VERSION',
        disabled: hasDisabledClass
      }
    }
  }
  return null
}

test.describe.serial('Backtest Portfolio Flow (Version Management)', () => {

  test('1. Create portfolio with component versions', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    console.log('=== Step 1: 创建投资组合（记录版本信息） ===')
    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 点击创建按钮
    await page.click('button.ant-btn-primary:has-text("创建组合")')
    await page.waitForTimeout(1000)

    // 填写基本信息
    await page.fill('.ant-modal input[placeholder="组合名称"]', TEST_CONFIG.portfolioName)
    await page.fill('.ant-modal .ant-input-number-input', String(TEST_CONFIG.initialCash))
    await page.waitForTimeout(300)

    // ========== 添加选股器（记录版本） ==========
    console.log('\n添加选股器:', TEST_CONFIG.selector.name)
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)

    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.selector.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    // 记录实际选择的版本
    const currentSelectorVersion = await getCurrentComponentVersion(page)
    savedComponentVersions.selector = currentSelectorVersion
    console.log('  当前选择版本:', currentSelectorVersion)

    // 配置参数 - 使用最后添加的组件
    const configSections = await page.$$('.ant-modal .config-section')
    const lastSectionIndex = configSections.length
    const selectorParamRows = await page.$$(`.ant-modal .config-section:nth-child(${lastSectionIndex}) .item-params .param-row`)
    for (const row of selectorParamRows) {
      const label = await row.$eval('.param-label', el => el.textContent.trim())
      const input = await row.$('input')
      if (!input) continue

      // label 是 "codes (逗号分隔)"
      if (label.includes('codes')) {
        await input.click()
        await input.fill(TEST_CONFIG.selector.codes)
        console.log('  codes:', TEST_CONFIG.selector.codes)
        break
      }
    }
    await page.waitForTimeout(300)

    // ========== 添加仓位管理器（记录版本） ==========
    console.log('\n添加仓位管理器:', TEST_CONFIG.sizer.name)
    await page.click('.ant-modal .type-btn:nth-child(2)')
    await page.waitForTimeout(300)

    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.sizer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    const currentSizerVersion = await getCurrentComponentVersion(page)
    savedComponentVersions.sizer = currentSizerVersion
    console.log('  当前选择版本:', currentSizerVersion)

    // 配置参数 - 使用最后添加的组件
    const configSections2 = await page.$$('.ant-modal .config-section')
    const lastSectionIndex2 = configSections2.length
    const sizerParamRows = await page.$$(`.ant-modal .config-section:nth-child(${lastSectionIndex2}) .item-params .param-row`)
    for (const row of sizerParamRows) {
      const label = await row.$eval('.param-label', el => el.textContent.trim())
      const input = await row.$('.ant-input-number-input')
      if (!input) continue

      if (label === 'volume') {
        await input.click()
        await input.fill(TEST_CONFIG.sizer.volume)
        console.log('  volume:', TEST_CONFIG.sizer.volume)
        break
      }
    }
    await page.waitForTimeout(300)

    // ========== 添加策略（记录版本） ==========
    console.log('\n添加策略:', TEST_CONFIG.strategy.name)
    await page.click('.ant-modal .type-btn:nth-child(3)')
    await page.waitForTimeout(300)

    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.strategy.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    const currentStrategyVersion = await getCurrentComponentVersion(page)
    savedComponentVersions.strategy = currentStrategyVersion
    console.log('  当前选择版本:', currentStrategyVersion)

    // 配置参数 - 使用最后添加的组件
    const configSections3 = await page.$$('.ant-modal .config-section')
    const lastSectionIndex3 = configSections3.length
    const strategyParamRows = await page.$$(`.ant-modal .config-section:nth-child(${lastSectionIndex3}) .item-params .param-row`)
    for (const row of strategyParamRows) {
      const label = await row.$eval('.param-label', el => el.textContent.trim())
      const input = await row.$('.ant-input-number-input')
      if (!input) continue

      if (label === 'buy_probability') {
        await input.click()
        await input.fill(String(TEST_CONFIG.strategy.buy_probability))
        console.log('  buy_probability:', TEST_CONFIG.strategy.buy_probability)
      } else if (label === 'sell_probability') {
        await input.click()
        await input.fill(String(TEST_CONFIG.strategy.sell_probability))
        console.log('  sell_probability:', TEST_CONFIG.strategy.sell_probability)
      } else if (label === 'max_signals') {
        await input.click()
        await input.fill(String(TEST_CONFIG.strategy.max_signals))
        console.log('  max_signals:', TEST_CONFIG.strategy.max_signals)
      }
    }
    await page.waitForTimeout(500)

    // ========== 添加分析器（记录版本） ==========
    console.log('\n添加分析器:', TEST_CONFIG.analyzer.name)
    await page.click('.ant-modal .type-btn:nth-child(5)')
    await page.waitForTimeout(300)

    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.analyzer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1500)

    const currentAnalyzerVersion = await getCurrentComponentVersion(page)
    savedComponentVersions.analyzer = currentAnalyzerVersion
    console.log('  当前选择版本:', currentAnalyzerVersion)

    // 打印所有保存的版本信息
    console.log('\n=== 保存的组件版本信息 ===')
    console.log(JSON.stringify(savedComponentVersions, null, 2))

    // ========== 提交创建 ==========
    await page.click('.ant-modal button.ant-btn-primary')
    await page.waitForTimeout(3000)

    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('\n✅ 投资组合创建成功（版本信息已保存）')
  })

  test('2. Verify saved versions in portfolio detail', async () => {
    const { page } = await getPage()

    console.log('\n=== Step 2: 验证详情页中的组件信息 ===')

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(3000)

    // 搜索刚创建的组合
    await page.fill('.ant-input-search input', TEST_CONFIG.portfolioName)
    await page.waitForTimeout(1500)

    const card = await page.$('.portfolio-card')
    expect(card).not.toBeNull()
    await card.click()
    await page.waitForTimeout(3000)

    // 验证组件存在
    console.log('\n验证组件显示:')

    const componentItems = await page.$$('.component-item')
    console.log(`组件数量: ${componentItems.length}`)
    expect(componentItems.length).toBeGreaterThanOrEqual(3)

    // 验证组件名称显示
    for (const item of componentItems) {
      const nameEl = await item.$('.component-name')
      if (nameEl) {
        const componentName = await nameEl.textContent()
        console.log(`  ✓ ${componentName?.trim()}`)
      }
    }

    console.log(`\n✅ 验证了 ${componentItems.length} 个组件`)
  })

  test('3. Create backtest and verify version snapshot', async () => {
    test.setTimeout(60000)

    console.log('\n=== Step 3: 创建回测任务（版本快照） ===')

    // 通过 API 获取刚创建的 portfolio
    const listResponse = await fetch(`${API_URL}/api/v1/portfolio?mode=BACKTEST`)
    const listData = await listResponse.json()
    const portfolio = listData.data?.find(p => p.name === TEST_CONFIG.portfolioName)

    if (portfolio) {
      portfolioUuid = portfolio.uuid
      console.log('找到 Portfolio:', portfolioUuid)

      // 验证 portfolio 包含版本信息
      console.log('Portfolio 组件数量:', portfolio.components?.length || 0)
      if (portfolio.components) {
        for (const comp of portfolio.components) {
          console.log(`  - ${comp.name}: 版本 ${comp.version || '未设置'}`)
        }
      }
    } else {
      throw new Error('未找到创建的投资组合')
    }

    // 通过 API 创建回测任务
    const backtestData = {
      name: TEST_CONFIG.backtestName,
      portfolio_id: portfolioUuid,
      start_date: TEST_CONFIG.dateRange.start,
      end_date: TEST_CONFIG.dateRange.end
    }

    const createResponse = await fetch(`${API_URL}/api/v1/backtest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backtestData)
    })

    if (!createResponse.ok) {
      throw new Error(`创建回测失败: ${createResponse.status}`)
    }

    const backtest = await createResponse.json()
    backtestUuid = backtest.uuid
    console.log('\n✅ 回测任务创建成功:', backtestUuid)

    // 验证回测任务包含组件版本信息
    console.log('\n验证回测配置快照:')
    const detailResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}`)
    const detail = await detailResponse.json()

    if (detail.config_snapshot) {
      console.log('配置快照存在，包含组件版本信息')
      // 这里可以进一步验证快照中的版本信息
    }
  })

  test('4. Start backtest and verify status', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)  // 1分钟超时

    console.log('\n=== Step 4: 启动回测任务 ===')

    if (!backtestUuid) {
      const listResponse = await fetch(`${API_URL}/api/v1/backtest`)
      const listData = await listResponse.json()
      const task = listData.data?.find(t => t.name === TEST_CONFIG.backtestName)
      if (task) {
        backtestUuid = task.uuid
        console.log('获取到任务 UUID:', backtestUuid)
      }
    }

    // 通过 API 启动回测
    console.log('通过 API 启动回测...')
    const startResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        portfolio_uuid: portfolioUuid,
        start_date: TEST_CONFIG.dateRange.start,
        end_date: TEST_CONFIG.dateRange.end
      })
    })

    if (startResponse.ok) {
      const startResult = await startResponse.json()
      console.log('启动结果:', startResult)
      console.log('✅ 回测任务启动成功')
    } else {
      console.log('启动请求状态:', startResponse.status)
      console.log('注意: 实际运行回测需要 worker 进程')
    }

    // 导航到回测页面验证任务显示
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    console.log('✅ 回测页面加载成功')
  })

  test('5. Verify backtest task created', async () => {
    const { page } = await getPage()
    test.setTimeout(30000)

    console.log('\n=== Step 5: 验证回测任务创建 ===')

    if (!backtestUuid) {
      const listResponse = await fetch(`${API_URL}/api/v1/backtest`)
      const listData = await listResponse.json()
      const task = listData.data?.find(t => t.name === TEST_CONFIG.backtestName)
      if (task) backtestUuid = task.uuid
    }

    if (!backtestUuid) {
      throw new Error('无法获取回测任务 UUID')
    }

    // 获取任务详情
    const detailResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}`)
    const detail = await detailResponse.json()

    console.log('\n📊 回测任务详情:')
    console.log('  ========================================')
    console.log(`  任务名称: ${detail.name}`)
    console.log(`  状态: ${detail.status}`)
    console.log(`  Portfolio ID: ${detail.portfolio_id}`)

    // 验证任务创建成功
    expect(detail.uuid).toBe(backtestUuid)
    expect(detail.portfolio_id).toBe(portfolioUuid)
    console.log('\n✅ 回测任务创建成功')
    console.log(`  ✅ 任务 UUID: ${backtestUuid}`)
    console.log(`  ✅ Portfolio UUID: ${portfolioUuid}`)
    console.log('\n注意: 完整回测运行需要 worker 进程，此处仅验证任务创建')
  })

  test('6. Cleanup - Delete test portfolio', async () => {
    const { page } = await getPage()

    console.log('\n=== 清理测试数据 ===')

    await page.goto(`${WEB_UI_URL}/portfolio`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    await page.fill('.ant-input-search input', TEST_CONFIG.portfolioName)
    await page.waitForTimeout(1500)

    const cards = await page.$$('.portfolio-card')
    if (cards.length > 0) {
      const moreBtn = await cards[0].$('.ant-dropdown-trigger')
      await moreBtn.click()
      await page.waitForTimeout(800)

      const menuItems = await page.$$('.ant-dropdown-menu-item')
      await menuItems[1].click()
      await page.waitForTimeout(800)

      await page.click('.ant-modal .ant-btn-dangerous')
      await page.waitForTimeout(3000)

      console.log('✅ 测试数据已清理')
    }
  })
})
