/**
 * Playwright E2E 测试 - 回测详情页面 Tab 功能
 * 验证新增的分析器和交易记录标签页
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

async function getPage() {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || context.pages()[0]
  return { browser, page }
}

test.describe.serial('Backtest Detail Tabs', () => {

  test('1. 验证回测详情页 Tab 结构', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    console.log('\n=== 测试回测详情页 Tab 结构 ===')

    // 访问回测列表
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 找到已完成的回测任务
    const rows = await page.$$('.ant-table-tbody tr')
    let targetRow = null

    for (const row of rows) {
      const statusCell = await row.$('td:nth-child(2)')
      if (statusCell) {
        const status = await statusCell.textContent()
        if (status && status.includes('已完成')) {
          targetRow = row
          break
        }
      }
    }

    if (!targetRow && rows.length > 0) {
      targetRow = rows[0]
      console.log('⚠️ 未找到已完成任务，使用第一行')
    }

    if (!targetRow) {
      throw new Error('没有找到任何回测任务')
    }

    // 点击详情按钮
    const detailBtn = await targetRow.$('button:has-text("详情")')
    if (detailBtn) {
      await detailBtn.click()
      await page.waitForTimeout(3000)
    } else {
      throw new Error('未找到详情按钮')
    }

    // 验证 URL 包含 /backtest/
    const url = page.url()
    expect(url).toContain('/backtest/')
    console.log('✅ 进入详情页:', url)

    // 验证 Tab 标签存在
    const tabs = await page.$$('.ant-tabs-tab')
    expect(tabs.length).toBeGreaterThanOrEqual(3)
    console.log(`✅ 发现 ${tabs.length} 个 Tab 标签`)

    // 验证标签文本
    const tabTexts = await Promise.all(tabs.map(tab => tab.textContent()))
    console.log('  Tab 标签:', tabTexts)

    expect(tabTexts.some(t => t?.includes('概览'))).toBeTruthy()
    expect(tabTexts.some(t => t?.includes('分析器'))).toBeTruthy()
    expect(tabTexts.some(t => t?.includes('交易记录'))).toBeTruthy()
    console.log('✅ 标签页结构正确')
  })

  test('2. 验证分析器标签页', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    console.log('\n=== 测试分析器标签页 ===')

    // 确保在详情页
    if (!page.url().includes('/backtest/')) {
      await page.goto(`${WEB_UI_URL}/stage1/backtest`)
      await page.waitForTimeout(2000)
      const rows = await page.$$('.ant-table-tbody tr')
      if (rows.length > 0) {
        const detailBtn = await rows[0].$('button:has-text("详情")')
        if (detailBtn) {
          await detailBtn.click()
          await page.waitForTimeout(3000)
        }
      }
    }

    // 点击分析器 Tab
    const analyzerTab = await page.$('.ant-tabs-tab:has-text("分析器")')
    if (analyzerTab) {
      await analyzerTab.click()
      await page.waitForTimeout(2000)
      console.log('✅ 切换到分析器标签页')
    } else {
      throw new Error('未找到分析器标签')
    }

    // 验证分析器选择器存在
    const selector = await page.$('.ant-select-selector')
    expect(selector).not.toBeNull()
    console.log('✅ 分析器选择器存在')

    // 验证是否有图表区域
    const chartContainer = await page.$('.tv-chart-container')
    if (chartContainer) {
      console.log('✅ 图表容器存在')
    } else {
      console.log('⚠️ 图表容器未找到（可能数据未加载）')
    }

    // 验证统计信息卡片
    const statsCards = await page.$$('.ant-statistic')
    if (statsCards.length > 0) {
      console.log(`✅ 发现 ${statsCards.length} 个统计项`)

      // 读取统计值
      for (const card of statsCards.slice(0, 3)) {
        const title = await card.$('.ant-statistic-title')
        const value = await card.$('.ant-statistic-content-value')
        if (title && value) {
          const titleText = await title.textContent()
          const valueText = await value.textContent()
          console.log(`  📊 ${titleText}: ${valueText}`)
        }
      }
    }
  })

  test('3. 验证交易记录标签页', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    console.log('\n=== 测试交易记录标签页 ===')

    // 点击交易记录 Tab
    const tradesTab = await page.$('.ant-tabs-tab:has-text("交易记录")')
    if (tradesTab) {
      await tradesTab.click()
      await page.waitForTimeout(2000)
      console.log('✅ 切换到交易记录标签页')
    } else {
      throw new Error('未找到交易记录标签')
    }

    // 验证子标签存在（信号、订单、持仓）
    const subTabs = await page.$$('.trade-records-panel .ant-tabs-tab')
    if (subTabs.length > 0) {
      console.log(`✅ 发现 ${subTabs.length} 个子标签`)
      const subTabTexts = await Promise.all(subTabs.map(t => t.textContent()))
      console.log('  子标签:', subTabTexts)
    }

    // 检查信号记录表格
    await page.waitForTimeout(1000)
    const tables = await page.$$('.ant-table')
    if (tables.length > 0) {
      console.log('✅ 数据表格存在')

      // 读取表格行数
      const tableRows = await page.$$('.ant-table-tbody tr')
      console.log(`  📊 信号记录: ${tableRows.length} 条`)

      // 读取前几行数据
      for (const row of tableRows.slice(0, 3)) {
        const cells = await row.$$('td')
        if (cells.length > 0) {
          const codeCell = cells[0]
          const dirCell = cells[1]
          if (codeCell && dirCell) {
            const code = await codeCell.textContent()
            const dir = await dirCell.textContent()
            console.log(`    ${code?.trim()} | ${dir?.trim()}`)
          }
        }
      }
    } else {
      console.log('⚠️ 未找到数据表格')
    }

    console.log('\n✅ 回测详情页 Tab 功能验证完成!')
  })
})
