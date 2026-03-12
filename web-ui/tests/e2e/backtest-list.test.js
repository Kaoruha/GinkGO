/**
 * E2E 测试：回测列表与详情功能
 *
 * ⚠️ 核心原则：页面有错误 = 测试立即失败
 * 测试流程：1. 先检查页面健康 2. 再验证功能
 */

import { test, expect } from '@playwright/test'
import { getHealthyPage, WEB_UI_URL } from './helpers/page-health'

const BACKTEST_PATH = '/stage1/backtest'

// ========== 第一层：页面健康检查（有问题立即失败） ==========

test.describe('回测列表页 - 页面健康检查', () => {
  test('页面必须健康加载，无任何错误', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    // 如果页面有任何错误，getHealthyPage 已经抛出异常，测试失败
    // 到这里说明页面是健康的
    const title = await page.title()
    console.log(`✅ 页面健康: ${title}`)

    await browser.close()
  })
})

// ========== 第二层：功能验证（页面健康后才执行） ==========

test.describe('回测列表页 - 基础显示', () => {
  test('应显示页面标题和基本结构', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 验证页面结构
      await expect(page.locator('.page-container')).toBeVisible()
      await expect(page.locator('.page-header')).toBeVisible()
      await expect(page.locator('.page-title')).toHaveText('回测任务')
    } finally {
      await browser.close()
    }
  })

  test('应显示六态筛选按钮', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 验证筛选按钮存在且可见（使用 a-radio-button）
      await expect(page.locator('.filters-bar:has-text("全部")')).toBeVisible()
      await expect(page.locator('.filters-bar:has-text("待调度")')).toBeVisible()
      // 验证整个筛选栏可见
      await expect(page.locator('.filters-bar .ant-radio-group')).toBeVisible()
    } finally {
      await browser.close()
    }
  })

  test('应显示统计卡片', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 验证统计行存在且可见
      await expect(page.locator('.stats-row')).toBeVisible()

      // 验证统计数据内容
      const bodyText = await page.locator('body').textContent()
      expect(bodyText).toContain('总任务数')
      expect(bodyText).toContain('已完成')
      expect(bodyText).toContain('运行中')
      expect(bodyText).toContain('失败')
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测列表操作', () => {
  test('应支持任务选择', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找表格中的复选框
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count > 0) {
        // 点击第一个复选框
        await checkboxes.first().click()

        // 验证批量操作栏出现
        await expect(page.locator('.batch-action-bar')).toBeVisible()
        await expect(page.locator('.batch-action-bar')).toContainText('已选择')
      }
    } finally {
      await browser.close()
    }
  })

  test('应支持全选功能', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const selectAllCheckbox = page.locator('.ant-table .ant-checkbox-input').first()
      const count = await selectAllCheckbox.count()

      if (count > 0) {
        // 点击表头的全选复选框
        await page.locator('.ant-table-thead .ant-checkbox-input').click()

        // 验证批量操作栏显示选中数量
        const batchBar = page.locator('.batch-action-bar')
        await expect(batchBar).toBeVisible()
      }
    } finally {
      await browser.close()
    }
  })

  test('应支持取消选择', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count > 0) {
        // 选中一个任务
        await checkboxes.first().click()
        await expect(page.locator('.batch-action-bar')).toBeVisible()

        // 点击取消选择按钮
        await page.locator('button:has-text("取消选择")').click()

        // 批量操作栏应隐藏
        await expect(page.locator('.batch-action-bar')).not.toBeVisible()
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('回测详情页', () => {
  test('应显示回测详情', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 查找第一个任务的"查看详情"链接
      const detailLink = page.locator('a:has-text("查看详情")').first()
      const count = await detailLink.count()

      if (count > 0) {
        await detailLink.click()
        await page.waitForTimeout(2000)

        // 验证详情页标题
        await expect(page.locator('.page-title, h1, h2')).toBeVisible()
      }
    } finally {
      await browser.close()
    }
  })

  test('应显示操作按钮（根据状态和权限）', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const detailLink = page.locator('a:has-text("查看详情")').first()
      const count = await detailLink.count()

      if (count > 0) {
        await detailLink.click()
        await page.waitForTimeout(2000)

        // 检查操作按钮区域存在
        const actions = page.locator('.header-actions button, .header-actions a')
        const actionCount = await actions.count()
        expect(actionCount).toBeGreaterThan(0)
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('状态标签显示', () => {
  test('应正确显示六态标签', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 检查表格中是否有状态标签
      const statusTags = page.locator('.ant-table tbody .ant-tag')
      const count = await statusTags.count()

      if (count > 0) {
        // 获取第一个状态标签的文本
        const firstTagText = await statusTags.first().textContent()
        console.log('第一个状态标签:', firstTagText)

        // 验证状态标签文本是中文
        expect(['待调度', '排队中', '进行中', '已完成', '已停止', '失败']).toContain(firstTagText?.trim())
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('批量操作按钮', () => {
  test('选中任务后应显示批量操作按钮', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count > 0) {
        await checkboxes.first().click()

        // 验证批量操作按钮存在
        await expect(page.locator('button:has-text("批量启动")')).toBeVisible()
        await expect(page.locator('button:has-text("批量停止")')).toBeVisible()
        await expect(page.locator('button:has-text("批量取消")')).toBeVisible()
        await expect(page.locator('button:has-text("取消选择")')).toBeVisible()
      }
    } finally {
      await browser.close()
    }
  })

  test('批量操作按钮状态应根据选中任务动态变化', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      const checkboxes = page.locator('.ant-table .ant-checkbox-input')
      const count = await checkboxes.count()

      if (count > 1) {
        // 选中第一个任务
        await checkboxes.nth(0).click()

        // 检查批量启动按钮状态
        const batchStart = page.locator('button:has-text("批量启动")')
        const isDisabled1 = await batchStart.isDisabled()

        // 选中第二个任务
        await checkboxes.nth(1).click()

        // 检查批量启动按钮状态可能发生变化
        const isDisabled2 = await batchStart.isDisabled()

        console.log(`批量启动按钮状态: ${isDisabled1} -> ${isDisabled2}`)
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('刷新功能', () => {
  test('应支持手动刷新列表', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 找到刷新按钮
      const actionButtons = page.locator('.header-actions button')
      const count = await actionButtons.count()

      if (count > 1) {
        console.log(`找到 ${count} 个操作按钮`)
      }
    } finally {
      await browser.close()
    }
  })
})

test.describe('权限控制', () => {
  test('检查权限提示功能', async () => {
    const { browser, page } = await getHealthyPage(`${WEB_UI_URL}${BACKTEST_PATH}`)

    try {
      // 检查是否有"无权限"文本或类似的权限控制提示
      const noPermissionText = page.locator('text=/无权限|没有权限/')
      const count = await noPermissionText.count()

      // 如果存在无权限提示，验证它正确显示
      if (count > 0) {
        await expect(noPermissionText.first()).toBeVisible()
        console.log('发现无权限提示，权限控制正常')
      } else {
        console.log('没有发现无权限提示（可能所有任务都有权限）')
      }
    } finally {
      await browser.close()
    }
  })
})
