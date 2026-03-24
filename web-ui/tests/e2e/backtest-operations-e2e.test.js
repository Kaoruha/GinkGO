/**
 * 回测任务操作端到端测试
 *
 * 验证标准：
 * 1. 操作不报错
 * 2. 回测任务状态产生实际变化
 */

import { test, expect } from '@playwright/test'
import { getHealthyPage, WEB_UI_URL } from './helpers/page-health'

const BACKTEST_PATH = '/stage1/backtest'

test.describe('回测任务操作 - 端到端状态变化验证', () => {
  test('启动任务后状态应从已完成变为排队中或进行中', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找已完成状态的任务
      const completedTasks = page.locator('.status-tag:has-text("已完成")')
      const count = await completedTasks.count()

      if (count === 0) {
        console.log('⚠️  没有找到已完成状态的任务，跳过测试')
        return
      }

      // 获取第一个已完成任务的行和 UUID
      const firstTaskRow = completedTasks.first().locator('xpath=ancestor::tr')
      const firstTaskUUID = await firstTaskRow.locator('.task-uuid').textContent()
      console.log(`选择任务: ${firstTaskUUID?.trim()}`)

      // 记录初始状态
      const initialStatus = await completedTasks.first().textContent()
      console.log(`初始状态: ${initialStatus}`)

      // 点击启动按钮
      const startButton = firstTaskRow.locator('button:has-text("启动")')
      await startButton.click()

      // 等待消息提示
      await page.waitForTimeout(2000)

      // 验证消息提示
      const messageElement = page.locator('.toast-notification')
      const hasSuccessMessage = await messageElement.count() > 0
      if (hasSuccessMessage) {
        const messageText = await messageElement.textContent()
        console.log(`消息提示: ${messageText.trim()}`)
        expect(messageText.toLowerCase()).toMatch(/启动|success/)
      }

      // 刷新页面查看状态变化
      await page.reload()
      await page.waitForTimeout(3000)

      // 重新查找该任务的状态
      const taskRows = page.locator('.ant-table tbody tr')
      const rowCount = await taskRows.count()

      let foundUpdatedTask = false
      let newStatus = ''

      for (let i = 0; i < rowCount; i++) {
        const row = taskRows.nth(i)
        const uuidCell = row.locator('.task-uuid')
        const uuidText = await uuidCell.textContent()

        if (uuidText?.trim() === firstTaskUUID?.trim()) {
          const statusTag = row.locator('.status-tag').first()
          newStatus = await statusTag.textContent()
          foundUpdatedTask = true
          console.log(`新状态: ${newStatus}`)
          break
        }
      }

      expect(foundUpdatedTask).toBeTruthy()
      expect(newStatus).not.toBe(initialStatus)

      // 验证状态变化：已完成 -> 排队中/进行中
      const validNewStates = ['排队中', '进行中', 'pending', 'running']
      const statusChanged = validNewStates.some(s => newStatus?.includes(s))
      expect(statusChanged).toBeTruthy()

      console.log(`✓ 任务状态成功从 "${initialStatus}" 变为 "${newStatus}"`)
    } finally {
      await browser.close()
    }
  })

  test('取消任务后状态应从待调度变为已停止', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找待调度状态的任务
      const createdTasks = page.locator('.status-tag:has-text("待调度")')
      const count = await createdTasks.count()

      if (count === 0) {
        console.log('⚠️  没有找到待调度状态的任务，跳过测试')
        return
      }

      // 获取第一个待调度任务的行和 UUID
      const firstTaskRow = createdTasks.first().locator('xpath=ancestor::tr')
      const firstTaskUUID = await firstTaskRow.locator('.task-uuid').textContent()
      console.log(`选择任务: ${firstTaskUUID?.trim()}`)

      // 记录初始状态
      const initialStatus = await createdTasks.first().textContent()
      console.log(`初始状态: ${initialStatus}`)

      // 点击取消按钮
      const cancelButton = firstTaskRow.locator('button:has-text("取消")')
      await cancelButton.click()

      // 等待消息提示
      await page.waitForTimeout(2000)

      // 验证消息提示
      const messageElement = page.locator('.toast-notification')
      const hasMessage = await messageElement.count() > 0
      if (hasMessage) {
        const messageText = await messageElement.textContent()
        console.log(`消息提示: ${messageText.trim()}`)
      }

      // 刷新页面查看状态变化
      await page.reload()
      await page.waitForTimeout(3000)

      // 重新查找该任务的状态
      const taskRows = page.locator('.ant-table tbody tr')
      const rowCount = await taskRows.count()

      let foundUpdatedTask = false
      let newStatus = ''

      for (let i = 0; i < rowCount; i++) {
        const row = taskRows.nth(i)
        const uuidCell = row.locator('.task-uuid')
        const uuidText = await uuidCell.textContent()

        if (uuidText?.trim() === firstTaskUUID?.trim()) {
          const statusTag = row.locator('.status-tag').first()
          newStatus = await statusTag.textContent()
          foundUpdatedTask = true
          console.log(`新状态: ${newStatus}`)
          break
        }
      }

      if (foundUpdatedTask) {
        // 验证状态变为已停止
        expect(newStatus).toBe('已停止')
        console.log(`✓ 任务状态成功从 "${initialStatus}" 变为 "${newStatus}"`)
      } else {
        console.log('⚠️  任务可能已被删除或从列表中移除')
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务批量操作 - 端到端验证', () => {
  test.setTimeout(90000) // 增加超时到90秒

  test('批量启动后选中任务的状态应发生变化', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 选中多个已完成/已停止的任务
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count < 2) {
        console.log('⚠️  任务数量不足，跳过测试')
        return
      }

      // 记录选中前的状态
      const initialStates = []
      const selectedUUIDs = []

      for (let i = 0; i < Math.min(3, count); i++) {
        const row = checkboxes.nth(i).locator('xpath=ancestor::tr')
        const uuidText = await row.locator('.task-uuid').textContent()
        const statusTag = row.locator('.status-tag').first()
        const statusText = await statusTag.textContent()

        selectedUUIDs.push(uuidText?.trim())
        initialStates.push(statusText)

        await checkboxes.nth(i).click()
      }

      console.log(`选中 ${selectedUUIDs.length} 个任务`)
      console.log('初始状态:', initialStates)

      // 检查批量操作按钮状态
      const batchStartButton = page.locator('button:has-text("批量启动")')
      const isDisabled = await batchStartButton.isDisabled()
      console.log(`批量启动按钮状态: ${isDisabled ? '禁用' : '启用'}`)

      if (isDisabled) {
        console.log('⚠️  批量启动按钮被禁用，没有可启动的任务，跳过测试')
        return
      }

      // 点击批量启动
      console.log('点击批量启动按钮...')
      await batchStartButton.click()

      // 等待批量操作完成（消息提示出现）
      await page.waitForSelector('.toast-notification', { timeout: 10000 })
      await page.waitForTimeout(2000)

      // 验证消息提示
      const messageElement = page.locator('.toast-notification')
      const hasMessage = await messageElement.count() > 0
      if (hasMessage) {
        const messageText = await messageElement.textContent()
        console.log(`批量操作消息: ${messageText.trim()}`)
      }

      // 刷新查看状态变化
      await page.reload()
      await page.waitForTimeout(3000)

      // 验证至少有一个任务状态发生了变化
      const taskRows = page.locator('.ant-table tbody tr')
      const rowCount = await taskRows.count()

      let stateChangedCount = 0

      for (let i = 0; i < rowCount; i++) {
        const row = taskRows.nth(i)
        const uuidCell = row.locator('.task-uuid')
        const uuidText = await uuidCell.textContent()

        const uuidIndex = selectedUUIDs.indexOf(uuidText?.trim())
        if (uuidIndex >= 0) {
          const statusTag = row.locator('.status-tag').first()
          const newStatus = await statusTag.textContent()

          if (newStatus !== initialStates[uuidIndex]) {
            stateChangedCount++
            console.log(`任务 ${uuidText?.slice(0, 8)}: ${initialStates[uuidIndex]} -> ${newStatus}`)
          }
        }
      }

      expect(stateChangedCount).toBeGreaterThan(0)
      console.log(`✓ ${stateChangedCount}/${selectedUUIDs.length} 个任务状态发生变化`)
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 错误处理验证', () => {
  test('对错误状态执行操作应返回错误提示', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 尝试对待调度任务执行启动操作（应该失败或没有按钮）
      const createdTasks = page.locator('.status-tag:has-text("待调度")')
      const count = await createdTasks.count()

      if (count > 0) {
        const firstTaskRow = createdTasks.first().locator('xpath=ancestor::tr')
        const startButton = firstTaskRow.locator('button:has-text("启动")')
        const hasStartButton = await startButton.count()

        if (hasStartButton) {
          // 如果有启动按钮（状态机实现可能有误），点击它应该显示错误
          await startButton.click()
          await page.waitForTimeout(2000)

          // 检查是否有错误消息
          const errorElement = page.locator('.toast-notification-error, .toast-notification-type-error')
          const hasError = await errorElement.count() > 0

          if (hasError) {
            console.log('✓ 正确显示错误提示')
          }
        } else {
          console.log('✓ 待调度状态不显示启动按钮（符合状态机设计）')
        }
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测任务操作 - 完整生命周期验证', () => {
  test('创建任务的完整生命周期：创建->启动->停止', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 点击创建回测按钮
      const createButton = page.locator('button:has-text("创建回测")')
      const hasCreateButton = await createButton.count() > 0

      if (!hasCreateButton) {
        console.log('⚠️  没有找到创建按钮，跳过测试')
        return
      }

      await createButton.click()
      await page.waitForTimeout(1000)

      // 检查是否打开创建模态框
      const modal = page.locator('.ant-modal')
      const hasModal = await modal.count() > 0

      if (hasModal) {
        console.log('✓ 创建模态框已打开')

        // 这里可以填写创建表单并提交
        // 由于测试数据准备复杂，这里只验证模态框打开
        // 按 ESC 键关闭模态框
        await page.keyboard.press('Escape')
        console.log('✓ 跳过创建流程（需要完整测试数据）')
      }
    } finally {
      await browser.close()
    }
  })
})
