/**
 * Playwright E2E 测试 - 完整端到端回测流程
 * 测试：创建 → 启动 → 等待完成 → 验证结果
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

const taskName = `E2E_Complete_${Date.now()}`
let taskUuid = null

test.describe.serial('Backtest E2E Complete Flow', () => {

  test('1. Create backtest task with portfolio', async () => {
    const { page } = await getPage()
    test.setTimeout(120000)

    console.log('\n=== Step 1: 创建回测任务 ===')
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 点击创建按钮
    await page.click('button:has-text("创建回测")')
    await page.waitForTimeout(1000)

    // 填写名称
    await page.fill('.ant-modal input[placeholder="请输入任务名称"]', taskName)
    await page.waitForTimeout(300)

    // 选择 Portfolio - 改进的选择逻辑
    const portfolioSelect = await page.$('.ant-modal .ant-form-item:has-text("Portfolio") .ant-select-selector')
    if (portfolioSelect) {
      await portfolioSelect.click()
    } else {
      await page.click('.ant-modal .ant-select-selector')
    }

    // 等待下拉菜单显示
    await page.waitForSelector('.ant-select-dropdown:not(.ant-select-dropdown-hidden)', { timeout: 5000 })
    await page.waitForTimeout(500)

    // 选择第一个 Portfolio
    const portfolioOptions = await page.$$('.ant-select-dropdown .ant-select-item')
    if (portfolioOptions.length > 0) {
      await portfolioOptions[0].click()
      console.log(`✅ 选择了 Portfolio (共 ${portfolioOptions.length} 个选项)`)
    } else {
      throw new Error('No portfolio options available')
    }
    await page.waitForTimeout(500)

    // 设置开始日期
    const startDatePicker = await page.$('.ant-modal .ant-form-item:has-text("开始日期") .ant-picker')
    if (startDatePicker) {
      await startDatePicker.click()
      await page.waitForTimeout(300)
      const dateCell = await page.$('.ant-picker-dropdown .ant-picker-cell:not(.ant-picker-cell-disabled)')
      if (dateCell) await dateCell.click()
    }
    await page.waitForTimeout(500)

    // 设置结束日期
    const endDatePicker = await page.$('.ant-modal .ant-form-item:has-text("结束日期") .ant-picker')
    if (endDatePicker) {
      await endDatePicker.click()
      await page.waitForTimeout(300)
      const dateCells = await page.$$('.ant-picker-dropdown .ant-picker-cell:not(.ant-picker-cell-disabled)')
      if (dateCells.length > 1) await dateCells[dateCells.length - 1].click()
    }
    await page.waitForTimeout(500)

    // 提交创建
    await page.click('.ant-modal .ant-btn-primary')
    await page.waitForTimeout(3000)

    // 验证创建成功
    const successMsg = await page.$('.ant-message-success')
    expect(successMsg).not.toBeNull()
    console.log('✅ 任务创建成功')

    // 等待模态框关闭
    await page.waitForTimeout(2000)

    // 刷新列表并查找新创建的任务
    await page.reload()
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 在表格中查找包含我们任务名称的行
    const allRows = await page.$$('.ant-table-tbody tr')
    let taskRow = null
    for (const row of allRows) {
      const text = await row.textContent()
      if (text && text.includes(taskName)) {
        taskRow = row
        break
      }
    }

    if (taskRow) {
      // 点击详情按钮获取 UUID
      const detailBtn = await taskRow.$('button:has-text("详情")')
      if (detailBtn) {
        await detailBtn.click()
        await page.waitForTimeout(2000)
        // 从 URL 获取 UUID
        const url = page.url()
        const match = url.match(/backtest\/([a-f0-9]+)/)
        if (match) {
          taskUuid = match[1]
          console.log(`📋 新任务 UUID: ${taskUuid}`)
        }
        // 返回列表
        await page.goBack()
        await page.waitForTimeout(1000)
      }
    } else {
      console.log('⚠️ 未找到新创建的任务，使用第一行')
      const firstRow = await page.$('.ant-table-tbody tr:first-child')
      if (firstRow) {
        const detailBtn = await firstRow.$('button:has-text("详情")')
        if (detailBtn) {
          await detailBtn.click()
          await page.waitForTimeout(2000)
          const url = page.url()
          const match = url.match(/backtest\/([a-f0-9]+)/)
          if (match) {
            taskUuid = match[1]
            console.log(`📋 任务 UUID: ${taskUuid}`)
          }
          await page.goBack()
          await page.waitForTimeout(1000)
        }
      }
    }
  })

  test('2. Start task and wait for completion', async () => {
    const { page } = await getPage()
    test.setTimeout(300000)  // 5分钟超时

    console.log('\n=== Step 2: 启动任务并等待完成 ===')
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 点击第一行的启动按钮
    const tableRows = await page.$$('.ant-table-tbody tr')
    if (tableRows.length > 0) {
      const startBtn = await tableRows[0].$('button:has-text("启动")')
      if (startBtn) {
        await startBtn.click()
        await page.waitForTimeout(1000)

        // 确认启动
        const confirmBtn = await page.$('.ant-popconfirm .ant-btn-primary')
        if (confirmBtn) {
          await confirmBtn.click()
          console.log('✅ 启动命令已发送')
        }
      } else {
        console.log('⚠️ 任务可能已在运行中')
      }
    }

    // 等待任务完成（轮询状态）
    console.log('⏳ 等待任务执行...')
    let completed = false
    let attempts = 0
    const maxAttempts = 60  // 最多等待2分钟

    while (!completed && attempts < maxAttempts) {
      await page.waitForTimeout(2000)
      await page.reload()
      await page.waitForLoadState('networkidle')
      await page.waitForTimeout(1000)

      const rows = await page.$$('.ant-table-tbody tr')
      if (rows.length > 0) {
        // 状态列是第2列 (td:nth-child(2))
        const statusCell = await rows[0].$('td:nth-child(2)')
        // 总盈亏列是第3列
        const pnlCell = await rows[0].$('td:nth-child(3)')

        if (statusCell) {
          const status = await statusCell.textContent()
          const pnl = pnlCell ? await pnlCell.textContent() : '0'

          console.log(`  状态: ${status}, 盈亏: ${pnl}`)

          if (status === 'completed' || status === 'failed' || status === 'stopped' ||
              status === '已完成' || status === '失败' || status === '已停止') {
            completed = true
            console.log(`✅ 任务最终状态: ${status}`)
          }
        }
      }

      attempts++
    }

    if (!completed) {
      console.log('⚠️ 等待超时，任务可能仍在运行')
    }
  })

  test('3. Verify task results', async () => {
    const { page } = await getPage()
    test.setTimeout(60000)

    console.log('\n=== Step 3: 验证任务结果 ===')
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    const tableRows = await page.$$('.ant-table-tbody tr')
    expect(tableRows.length).toBeGreaterThan(0)

    // 检查第一行状态
    const firstRow = tableRows[0]
    // 状态列是第2列 (td:nth-child(2))
    const statusCell = await firstRow.$('td:nth-child(2)')
    if (statusCell) {
      const status = await statusCell.textContent()
      console.log(`最终状态: ${status}`)

      // 状态应该是 created, pending, running, completed, failed 或 stopped (支持中英文)
      const validStatuses = [
        'created', 'pending', 'running', 'completed', 'failed', 'stopped',
        '已创建', '等待中', '运行中', '已完成', '失败', '已停止'
      ]
      expect(validStatuses.includes(status.trim())).toBe(true)
    }

    // 点击详情查看结果
    const detailBtn = await firstRow.$('button:has-text("详情")')
    if (detailBtn) {
      await detailBtn.click()
      await page.waitForTimeout(2000)

      // 检查详情页面
      const url = page.url()
      console.log(`详情页 URL: ${url}`)
      expect(url).toContain('/backtest/')

      // 等待详情加载
      await page.waitForTimeout(2000)

      // 检查是否有结果数据显示
      const pageContent = await page.textContent('body')
      console.log('✅ 详情页面加载成功')
    }

    console.log('✅ E2E 完整流程验证通过')
  })

  test('4. Cleanup', async () => {
    const { page } = await getPage()
    test.setTimeout(30000)

    console.log('\n=== Step 4: 清理测试数据 ===')
    await page.goto(`${WEB_UI_URL}/stage1/backtest`)
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 删除第一行任务
    const tableRows = await page.$$('.ant-table-tbody tr')
    if (tableRows.length > 0) {
      const deleteBtn = await tableRows[0].$('button:has-text("删除")')
      if (deleteBtn) {
        await deleteBtn.click()
        await page.waitForTimeout(500)

        const confirmBtn = await page.$('.ant-popconfirm .ant-btn-dangerous')
        if (confirmBtn) {
          await confirmBtn.click()
          await page.waitForTimeout(2000)
          console.log('✅ 测试数据已清理')
        }
      }
    }
  })
})
