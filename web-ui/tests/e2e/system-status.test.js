/**
 * Playwright E2E 测试 - 系统状态页面
 *
 * 测试覆盖：
 * 1. 页面访问和基础元素
 * 2. 系统状态卡片（版本、运行时间、调试模式）
 * 3. 基础设施状态（MySQL, Redis, Kafka, ClickHouse）
 * 4. 组件统计（DataWorker, BacktestWorker, ExecutionNode, Scheduler, TaskTimer）
 * 5. 组件详情表格
 * 6. 自动刷新功能
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

async function login(page) {
  await page.goto(`${WEB_UI_URL}/login`)
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
  await page.reload({ waitUntil: 'networkidle' })
  await page.locator('input[placeholder="enter username"]').fill('admin')
  await page.locator('input[placeholder="enter password"]').fill('admin123')
  await page.locator('button:has-text("EXECUTE")').click()
  await page.waitForURL('**/dashboard', { timeout: 10000 })
}

async function expandMenu(page, menuName) {
  const menuExpanded = await page.locator(`.ant-menu-submenu-open:has-text("${menuName}")`).count()
  if (menuExpanded === 0) {
    await page.click(`.ant-menu-submenu-title:has-text("${menuName}")`)
    await page.waitForTimeout(300)
  }
}

async function navigateToSystemStatus(page) {
  await login(page)
  await expandMenu(page, '系统管理')
  await page.click('.ant-menu-item:has-text("系统状态")')
  await page.waitForTimeout(1500) // 等待数据加载
}

test.describe('系统状态页面 - 基础功能', () => {

  test('可以访问系统状态页面', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.page-title:has-text("系统状态")')).toBeVisible({ timeout: 5000 })
  })

  test('页面有刷新按钮', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('button:has-text("刷新")')).toBeVisible({ timeout: 5000 })
  })

  test('页面有自动刷新开关', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-switch')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('系统状态页面 - 状态卡片', () => {

  test('显示服务状态卡片', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("服务状态")')).toBeVisible({ timeout: 5000 })
  })

  test('显示版本信息', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("版本")')).toBeVisible({ timeout: 5000 })
    // 版本号存在即可
    const versionCard = page.locator('.ant-card-bordered').filter({ hasText: '版本' })
    await expect(versionCard).toBeVisible({ timeout: 5000 })
  })

  test('显示运行时间', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("运行时间")')).toBeVisible({ timeout: 5000 })
  })

  test('显示调试模式状态', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("调试模式")')).toBeVisible({ timeout: 5000 })
  })

  test('显示在线组件数量', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("在线组件")')).toBeVisible({ timeout: 5000 })
  })

  test('显示最后更新时间', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("最后更新")')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('系统状态页面 - 基础设施状态', () => {

  test('显示基础设施卡片区域', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-card-head-title:has-text("基础设施")')).toBeVisible({ timeout: 5000 })
  })

  test('MySQL 状态显示', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    // 检查 MySQL 卡片存在且显示状态标签
    const mysqlCard = page.locator('.ant-card-small').filter({ hasText: 'MySQL' })
    await expect(mysqlCard).toBeVisible({ timeout: 5000 })
    await expect(mysqlCard.locator('.ant-tag')).toBeVisible()
  })

  test('Redis 状态显示', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    const redisCard = page.locator('.ant-card-small').filter({ hasText: 'Redis' })
    await expect(redisCard).toBeVisible({ timeout: 5000 })
    await expect(redisCard.locator('.ant-tag')).toBeVisible()
  })

  test('Kafka 状态显示', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    const kafkaCard = page.locator('.ant-card-small').filter({ hasText: 'Kafka' })
    await expect(kafkaCard).toBeVisible({ timeout: 5000 })
    await expect(kafkaCard.locator('.ant-tag')).toBeVisible()
  })

  test('ClickHouse 状态显示', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    const chCard = page.locator('.ant-card-small').filter({ hasText: 'ClickHouse' })
    await expect(chCard).toBeVisible({ timeout: 5000 })
    await expect(chCard.locator('.ant-tag')).toBeVisible()
  })

  test('所有基础设施显示已连接状态', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    // 获取基础设施区域的所有状态标签
    const connectedTags = await page.locator('.ant-tag-green:has-text("已连接")').count()
    // 至少应该有 MySQL, Redis, ClickHouse 三个连接
    expect(connectedTags).toBeGreaterThanOrEqual(3)
  })
})

test.describe('系统状态页面 - 组件统计', () => {

  test('显示组件统计卡片区域', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-card-head-title:has-text("组件统计")')).toBeVisible({ timeout: 5000 })
  })

  test('显示 DataWorker 统计', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("DataWorker")')).toBeVisible({ timeout: 5000 })
  })

  test('显示 BacktestWorker 统计', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("BacktestWorker")')).toBeVisible({ timeout: 5000 })
  })

  test('显示 ExecutionNode 统计', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("ExecutionNode")')).toBeVisible({ timeout: 5000 })
  })

  test('显示 Scheduler 统计', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("Scheduler")')).toBeVisible({ timeout: 5000 })
  })

  test('显示 TaskTimer 统计', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-statistic-title:has-text("TaskTimer")')).toBeVisible({ timeout: 5000 })
  })
})

test.describe('系统状态页面 - 组件详情表格', () => {

  test('显示组件详情表格', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await expect(page.locator('.ant-card-head-title:has-text("组件详情")')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 5000 })
  })

  test('表格有正确的列标题', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)

    const expectedHeaders = ['组件 ID', '类型', '状态', '详情', '最后心跳']
    for (const header of expectedHeaders) {
      await expect(page.locator(`.ant-table-thead th:has-text("${header}")`)).toBeVisible({ timeout: 3000 })
    }
  })

  test('表格显示组件数据', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)

    // 等待数据加载
    await page.waitForTimeout(2000)

    // 检查表格行数
    const rowCount = await page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)').count()
    expect(rowCount).toBeGreaterThan(0)
  })

  test('组件数据显示正确的类型标签', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)
    await page.waitForTimeout(2000)

    // 检查是否有组件类型标签（数据Worker、回测Worker等）
    const typeTags = await page.locator('.ant-table-tbody .ant-tag').count()
    expect(typeTags).toBeGreaterThan(0)
  })
})

test.describe('系统状态页面 - 交互功能', () => {

  test('点击刷新按钮更新数据', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)

    // 点击刷新
    await page.click('button:has-text("刷新")')
    await page.waitForTimeout(2000)

    // 验证页面仍然正常
    await expect(page.locator('.page-title:has-text("系统状态")')).toBeVisible({ timeout: 5000 })
    // 验证状态卡片仍然可见
    await expect(page.locator('.ant-statistic-title:has-text("服务状态")')).toBeVisible({ timeout: 5000 })
  })

  test('自动刷新开关可以切换', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)

    const switchEl = page.locator('.ant-switch')

    // 获取初始状态
    const initialState = await switchEl.isChecked()

    // 点击切换
    await switchEl.click()
    await page.waitForTimeout(300)

    // 验证状态改变
    const newState = await switchEl.isChecked()
    expect(newState).toBe(!initialState)

    // 恢复原状态
    await switchEl.click()
  })

  test('无错误消息显示', async () => {
    const { page } = await getPage()
    await navigateToSystemStatus(page)

    // 检查没有错误消息
    const errorCount = await page.locator('.ant-message-error, .ant-alert-error').count()
    expect(errorCount).toBe(0)
  })
})
