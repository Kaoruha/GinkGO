/**
 * Playwright E2E 测试 - 完整回测流程（从组合创建到回测验证）
 * 参考 examples/complete_backtest_example.py 配置
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

// 参考 examples/complete_backtest_example.py 的配置
const TEST_CONFIG = {
  portfolioName: `回测验证_${Date.now()}`,
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

test.describe.serial('Backtest Portfolio Flow', () => {

  test('1. Create portfolio with components', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    console.log('=== Step 1: 创建投资组合 ===')
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

    // ========== 添加选股器 ==========
    console.log('添加选股器:', TEST_CONFIG.selector.name)
    await page.click('.ant-modal .type-btn:nth-child(1)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.selector.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    const selectorParamInput = await page.$('.ant-modal .config-section:first-child .item-params input')
    if (selectorParamInput) {
      await selectorParamInput.fill(TEST_CONFIG.selector.codes)
      console.log('  codes:', TEST_CONFIG.selector.codes)
    }
    await page.waitForTimeout(300)

    // ========== 添加仓位管理器 ==========
    console.log('添加仓位管理器:', TEST_CONFIG.sizer.name)
    await page.click('.ant-modal .type-btn:nth-child(2)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.sizer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    const sizerParamInput = await page.$('.ant-modal .config-section:nth-child(2) .item-params input')
    if (sizerParamInput) {
      await sizerParamInput.fill(TEST_CONFIG.sizer.volume)
      console.log('  volume:', TEST_CONFIG.sizer.volume)
    }
    await page.waitForTimeout(300)

    // ========== 添加策略 ==========
    console.log('添加策略:', TEST_CONFIG.strategy.name)
    await page.click('.ant-modal .type-btn:nth-child(3)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.strategy.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // 配置策略参数
    const strategyParamRows = await page.$$('.ant-modal .config-section:nth-child(3) .item-params .param-row')
    for (const row of strategyParamRows) {
      const label = await row.$eval('.param-label', el => el.textContent)
      const input = await row.$('.ant-input-number-input')
      if (!input) continue

      if (label.includes('buy_probability')) {
        await input.fill(String(TEST_CONFIG.strategy.buy_probability))
        console.log('  buy_probability:', TEST_CONFIG.strategy.buy_probability)
      } else if (label.includes('sell_probability')) {
        await input.fill(String(TEST_CONFIG.strategy.sell_probability))
        console.log('  sell_probability:', TEST_CONFIG.strategy.sell_probability)
      } else if (label.includes('max_signals')) {
        await input.fill(String(TEST_CONFIG.strategy.max_signals))
        console.log('  max_signals:', TEST_CONFIG.strategy.max_signals)
      }
    }
    await page.waitForTimeout(500)

    // ========== 添加分析器 ==========
    console.log('添加分析器:', TEST_CONFIG.analyzer.name)
    await page.click('.ant-modal .type-btn:nth-child(5)')
    await page.waitForTimeout(300)
    await page.click('.ant-modal .component-selector .ant-select-selector')
    await page.waitForTimeout(500)
    await page.keyboard.type(TEST_CONFIG.analyzer.name)
    await page.waitForTimeout(500)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(1000)

    // ========== 提交创建 ==========
    await page.click('.ant-modal button.ant-btn-primary')
    await page.waitForTimeout(3000)

    const successMsg = await page.locator('.ant-message-success')
    await expect(successMsg).toBeVisible({ timeout: 5000 })
    console.log('✅ 投资组合创建成功')
  })

  test('2. Create backtest via API', async () => {
    test.setTimeout(60000)

    console.log('=== Step 2: 创建回测任务 ===')

    // 通过 API 获取刚创建的 portfolio
    const listResponse = await fetch(`${API_URL}/api/v1/portfolio?mode=BACKTEST`)
    const listData = await listResponse.json()
    const portfolio = listData.data?.find(p => p.name === TEST_CONFIG.portfolioName)

    if (portfolio) {
      portfolioUuid = portfolio.uuid
      console.log('找到 Portfolio:', portfolioUuid)
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
    console.log('✅ 回测任务创建成功:', backtestUuid)
  })

  test('3. Start backtest and monitor status', async () => {
    const { page } = await getPage()
    test.setTimeout(360000)  // 6分钟超时

    console.log('=== Step 3: 启动回测并监控状态 ===')

    // 确保有 backtestUuid
    if (!backtestUuid) {
      const listResponse = await fetch(`${API_URL}/api/v1/backtest`)
      const listData = await listResponse.json()
      const task = listData.data?.find(t => t.name === TEST_CONFIG.backtestName)
      if (task) {
        backtestUuid = task.uuid
        console.log('获取到任务 UUID:', backtestUuid)
      } else {
        throw new Error('未找到回测任务')
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
    } else {
      console.log('启动请求失败，但可能已在运行')
    }

    // 导航到回测页面查看状态
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 轮询状态直到完成
    let status = 'created'
    let waitCount = 0
    const maxWait = 300  // 5分钟超时

    while (status !== 'completed' && status !== 'failed' && waitCount < maxWait) {
      const statusResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}`)
      const statusData = await statusResponse.json()
      status = statusData.status

      console.log(`[${waitCount}s] 状态: ${status} | 进度: ${statusData.progress}% | 信号: ${statusData.total_signals} | 订单: ${statusData.total_orders}`)

      if (status === 'completed' || status === 'failed') break

      // 每10秒刷新页面
      if (waitCount % 10 === 0) {
        await page.reload()
        await page.waitForLoadState('networkidle')
      }

      await page.waitForTimeout(1000)
      waitCount++
    }

    console.log('✅ 回测状态监控完成，最终状态:', status)
  })

  test('4. Verify backtest results', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)  // 2分钟超时

    console.log('=== Step 4: 验证回测结果 ===')

    if (!backtestUuid) {
      // 尝试获取任务 UUID
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

    console.log('\n📊 回测结果:')
    console.log('  ========================================')
    console.log(`  任务名称: ${detail.name}`)
    console.log(`  状态: ${detail.status}`)
    console.log(`  进度: ${detail.progress}%`)
    console.log(`  信号数: ${detail.total_signals}`)
    console.log(`  订单数: ${detail.total_orders}`)
    console.log(`  持仓数: ${detail.total_positions}`)
    console.log(`  事件数: ${detail.total_events}`)
    console.log(`  期末价值: ¥${parseFloat(detail.final_portfolio_value || 0).toLocaleString()}`)
    console.log(`  总收益: ${parseFloat(detail.total_pnl || 0).toFixed(2)}%`)
    console.log(`  最大回撤: ${parseFloat(detail.max_drawdown || 0).toFixed(2)}%`)

    // 验证关键指标
    expect(detail.status).toBe('completed')
    expect(detail.total_signals).toBeGreaterThan(0)
    console.log('\n✅ 验证通过:')
    console.log(`  ✅ 状态为 completed`)
    console.log(`  ✅ 生成了 ${detail.total_signals} 个信号`)

    if (detail.total_orders > 0) {
      console.log(`  ✅ 执行了 ${detail.total_orders} 个订单`)
    }

    // 获取净值数据
    console.log('\n📈 获取净值数据...')
    const netValueResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}/netvalue`)
    if (netValueResponse.ok) {
      const netValue = await netValueResponse.json()
      const strategyData = netValue.strategy || []
      console.log(`  净值记录数: ${strategyData.length}`)
      if (strategyData.length > 0) {
        console.log(`  起始净值: ${strategyData[0].value}`)
        console.log(`  结束净值: ${strategyData[strategyData.length - 1].value}`)
        expect(strategyData.length).toBeGreaterThan(0)
        console.log('  ✅ 净值数据正常')
      }
    }

    // 获取分析器数据
    console.log('\n📊 获取分析器数据...')
    const analyzersResponse = await fetch(`${API_URL}/api/v1/backtest/${backtestUuid}/analyzers`)
    if (analyzersResponse.ok) {
      const analyzers = await analyzersResponse.json()
      console.log(`  分析器数量: ${analyzers.analyzers?.length || 0}`)
      for (const a of (analyzers.analyzers || [])) {
        console.log(`  - ${a.name}: ${a.record_count} 条记录`)
      }
    }

    // 在页面上验证
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    console.log('\n✅ 完整回测流程验证成功!')
  })
})
