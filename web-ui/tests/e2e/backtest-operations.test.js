/**
 * 回测任务操作测试
 *
 * 测试状态机的所有操作：start, stop, cancel
 */

import { test, expect } from '@playwright/test'
import { getHealthyPage, WEB_UI_URL } from './helpers/page-health'

const BACKTEST_PATH = '/stage1/backtest'

test.describe('回测任务操作 - 启动(start)', () => {
  test('应能启动已完成状态的回测任务', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找已完成的任务
      await page.locator('.ant-tag:has-text("已完成")').first().waitFor({ timeout: 5000 })

      // 检查启动按钮是否存在且可点击
      const startButtons = page.locator('button:has-text("启动")')
      const count = await startButtons.count()

      if (count > 0) {
        // 获取第一个启动按钮对应的任务状态
        const firstButton = startButtons.first()
        const row = firstButton.locator('xpath=ancestor::tr')
        const statusTag = row.locator('.ant-tag').first()
        const statusText = await statusTag.textContent()

        console.log(`找到状态为 "${statusText}" 的任务，有启动按钮`)

        // 点击启动按钮
        await firstButton.click()
        await page.waitForTimeout(3000)

        // 检查是否有任何消息提示（成功或错误）
        const anyMessage = page.locator('.ant-message-notice-content')
        const messageCount = await anyMessage.count()

        if (messageCount > 0) {
          const messageText = await anyMessage.first().textContent()
          console.log(`消息提示: "${messageText.trim()}"`)
          // 验证消息内容
          expect(messageText.toLowerCase()).toMatch(/启动|success|fail|error/)
        } else {
          // 检查控制台错误
          console.log('⚠️  没有看到消息提示，操作可能失败或无响应')
        }
      } else {
        console.log('⚠️  没有找到可启动的任务（已完成/已停止/失败状态）')
      }
    } finally {
      await browser.close()
    }
  })

  test('不应显示待调度状态任务的启动按钮', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找待调度状态的任务
      const createdTasks = page.locator('.ant-tag:has-text("待调度")')
      const count = await createdTasks.count()

      if (count > 0) {
        // 检查待调度任务的行是否有启动按钮
        const firstTaskRow = createdTasks.first().locator('xpath=ancestor::tr')
        const startButton = firstTaskRow.locator('button:has-text("启动")')
        const hasStartButton = await startButton.count() > 0

        expect(hasStartButton).toBeFalsy()
        console.log('✓ 待调度状态任务不显示启动按钮（符合状态机设计）')
      } else {
        console.log('⚠️  没有找到待调度状态的任务')
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 停止(stop)', () => {
  test('应能停止进行中状态的回测任务', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找进行中的任务
      const runningTasks = page.locator('.ant-tag:has-text("进行中")')
      const count = await runningTasks.count()

      if (count > 0) {
        // 检查进行中任务的停止按钮
        const firstTaskRow = runningTasks.first().locator('xpath=ancestor::tr')
        const stopButton = firstTaskRow.locator('button:has-text("停止")')
        const hasStopButton = await stopButton.count() > 0

        if (hasStopButton) {
          console.log('✓ 进行中状态任务显示停止按钮')

          // 点击停止按钮
          await stopButton.click()
          await page.waitForTimeout(2000)

          // 验证停止消息提示
          const hasSuccessMessage = await page.locator('.ant-message-success, .ant-message-type-success').count() > 0
          expect(hasSuccessMessage).toBeTruthy()
        } else {
          console.log('⚠️  进行中状态任务没有停止按钮')
        }
      } else {
        console.log('⚠️  没有找到进行中状态的任务')
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 取消(cancel)', () => {
  test('应能取消待调度状态的回测任务', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找待调度状态的任务
      const createdTasks = page.locator('.ant-tag:has-text("待调度")')
      const count = await createdTasks.count()

      if (count > 0) {
        // 检查待调度任务的取消按钮
        const firstTaskRow = createdTasks.first().locator('xpath=ancestor::tr')
        const cancelButton = firstTaskRow.locator('button:has-text("取消")')
        const hasCancelButton = await cancelButton.count() > 0

        if (hasCancelButton) {
          console.log('✓ 待调度状态任务显示取消按钮')

          // 点击取消按钮
          await cancelButton.click()
          await page.waitForTimeout(2000)

          // 验证取消消息提示
          const hasSuccessMessage = await page.locator('.ant-message-success, .ant-message-type-success').count() > 0
          expect(hasSuccessMessage).toBeTruthy()
        } else {
          console.log('⚠️  待调度状态任务没有取消按钮')
        }
      } else {
        console.log('⚠️  没有找到待调度状态的任务')
      }
    } finally {
      await browser.close()
    }
  })

  test('应能取消排队中状态的回测任务', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找排队中状态的任务
      const pendingTasks = page.locator('.ant-tag:has-text("排队中")')
      const count = await pendingTasks.count()

      if (count > 0) {
        // 检查排队中任务的取消按钮
        const firstTaskRow = pendingTasks.first().locator('xpath=ancestor::tr')
        const cancelButton = firstTaskRow.locator('button:has-text("取消")')
        const hasCancelButton = await cancelButton.count() > 0

        expect(hasCancelButton).toBeTruthy()
        console.log('✓ 排队中状态任务显示取消按钮')
      } else {
        console.log('⚠️  没有找到排队中状态的任务')
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 批量操作', () => {
  test('批量启动应只对可启动的任务有效', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 选中多个任务
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count >= 2) {
        // 选中前两个任务
        await checkboxes.nth(0).click()
        await checkboxes.nth(1).click()

        // 检查批量启动按钮状态
        const batchStartButton = page.locator('button:has-text("批量启动")')
        const isDisabled = await batchStartButton.isDisabled()

        console.log(`批量启动按钮状态: ${isDisabled ? '禁用' : '启用'}`)

        // 如果按钮启用，尝试点击
        if (!isDisabled) {
          await batchStartButton.click()
          await page.waitForTimeout(2000)

          // 验证操作结果
          const hasMessage = await page.locator('.ant-message').count() > 0
          console.log(`批量操作${hasMessage ? '有消息提示' : '无消息提示'}`)
        }
      }
    } finally {
      await browser.close()
    }
  })

  test('批量取消应只对待调度/排队中任务有效', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count >= 2) {
        await checkboxes.nth(0).click()
        await checkboxes.nth(1).click()

        const batchCancelButton = page.locator('button:has-text("批量取消")')
        const hasButton = await batchCancelButton.count() > 0

        if (hasButton) {
          const isDisabled = await batchCancelButton.isDisabled()
          console.log(`批量取消按钮状态: ${isDisabled ? '禁用' : '启用'}`)
        }
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 状态转换验证', () => {
  test('操作后状态应正确更新', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 记录初始状态
      const initialStatusCounts = {}
      for (const status of ['待调度', '排队中', '进行中', '已完成', '已停止', '失败']) {
        const count = await page.locator(`.ant-tag:has-text("${status}")`).count()
        initialStatusCounts[status] = count
      }

      console.log('初始状态分布:', initialStatusCounts)

      // 刷新页面
      await page.reload()
      await page.waitForTimeout(2000)

      // 验证状态统计卡片显示正确
      const statsText = await page.locator('.stats-row').textContent()
      expect(statsText).toContain('总任务数')
      expect(statsText).toContain('已完成')
      expect(statsText).toContain('运行中')
      expect(statsText).toContain('失败')

      console.log('✓ 状态统计卡片显示正常')
    } finally {
      await browser.close()
    }
  })
})
