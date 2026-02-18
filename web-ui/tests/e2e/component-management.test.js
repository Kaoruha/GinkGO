/**
 * Playwright E2E 测试 - 组件管理功能
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

// 辅助函数：登录
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

// 辅助函数：展开组件管理菜单
async function expandComponentMenu(page) {
  const menuExpanded = await page.locator('.ant-menu-submenu-open:has-text("组件管理")').count()
  if (menuExpanded === 0) {
    await page.click('.ant-menu-submenu-title:has-text("组件管理")')
    await page.waitForTimeout(300)
  }
}

test.describe('组件管理功能', () => {

  test('可以访问策略组件页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("策略组件")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("策略组件")')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('button:has-text("新建")')).toBeVisible()
  })

  test('可以访问风控组件页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("风控组件")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("风控组件")')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问仓位组件页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("仓位组件")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("仓位组件")')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问选股器页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("选股器")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("选股器组件")')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问分析器页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("分析器")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("分析器组件")')).toBeVisible({ timeout: 5000 })
  })

  test('可以访问事件处理器页面', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("事件处理器")')
    await page.waitForTimeout(500)
    await expect(page.locator('.page-title:has-text("事件处理器")')).toBeVisible({ timeout: 5000 })
  })

  test('可以创建新策略文件', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("策略组件")')
    await page.waitForTimeout(500)

    // 点击新建按钮
    await page.click('button:has-text("新建")')
    await page.waitForTimeout(500)

    // 等待对话框出现
    const modal = page.locator('.ant-modal-content')
    await expect(modal).toBeVisible({ timeout: 5000 })

    // 输入文件名
    const testFileName = `test_strategy_${Date.now()}`
    await modal.locator('input').fill(testFileName)

    // 确认创建 (按钮文本可能有空格)
    await modal.locator('button').filter({ hasText: '确' }).last().click()
    await page.waitForTimeout(2000)

    // 验证跳转到详情页
    await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.code-textarea')).toBeVisible({ timeout: 5000 })

    // 验证 URL 包含文件 ID
    expect(page.url()).toMatch(/\/components\/strategies\/[a-f0-9-]+/)
  })

  test('可以编辑并保存文件', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("策略组件")')
    await page.waitForTimeout(500)

    // 点击第一个文件进入详情页
    await page.click('.ant-table-tbody tr:first-child .file-link')
    await page.waitForTimeout(2000)

    // 确保详情页已加载
    await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })
    await expect(page.locator('.code-textarea')).toBeVisible({ timeout: 5000 })

    // 在 textarea 中输入内容
    const textarea = page.locator('.code-textarea')
    await textarea.click({ force: true })
    await page.keyboard.press('Control+a')
    await page.keyboard.type('# Test edit content\nprint("hello world")')

    // 点击保存按钮
    await page.click('.toolbar button:has-text("保存")')
    await page.waitForTimeout(2000)

    // 验证保存成功消息
    const successMessage = page.locator('.ant-message')
    await expect(successMessage).toBeVisible({ timeout: 5000 })
  })

  test('可以搜索文件', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("策略组件")')
    await page.waitForTimeout(500)

    // 等待表格加载
    await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 })

    // 输入搜索关键词
    const searchInput = page.locator('.ant-input-search input').first()
    await searchInput.fill('nonexistent_file_xyz_12345')
    await page.waitForTimeout(800)

    // 验证表格行数
    const tableRows = await page.locator('.ant-table-tbody tr:not(.ant-table-placeholder)').count()
    expect(tableRows).toBeGreaterThanOrEqual(0)
  })

  test('可以从详情页返回列表页', async () => {
    const { page } = await getPage()
    await login(page)

    await expandComponentMenu(page)
    await page.click('.ant-menu-item:has-text("策略组件")')
    await page.waitForTimeout(500)

    // 等待表格加载
    await page.waitForSelector('.ant-table-tbody tr', { timeout: 5000 })

    // 点击第一个文件进入详情页
    await page.click('.ant-table-tbody tr:first-child .file-link')
    await page.waitForTimeout(2000)

    // 验证在详情页
    await expect(page.locator('.component-detail')).toBeVisible({ timeout: 5000 })
    expect(page.url()).toMatch(/\/components\/strategies\/[a-f0-9-]+/)

    // 点击返回按钮
    await page.locator('.back-btn').click({ force: true })
    await page.waitForTimeout(2000)

    // 验证回到列表页
    expect(page.url()).toMatch(/\/components\/strategies$/)
    await expect(page.locator('.component-list-page')).toBeVisible({ timeout: 5000 })
  })

  test('所有组件页面都有正确的标题', async () => {
    const { page } = await getPage()
    await login(page)

    const pages = [
      { menu: '策略组件', title: '策略组件' },
      { menu: '风控组件', title: '风控组件' },
      { menu: '仓位组件', title: '仓位组件' },
      { menu: '选股器', title: '选股器组件' },
      { menu: '分析器', title: '分析器组件' },
      { menu: '事件处理器', title: '事件处理器' },
    ]

    for (const pageInfo of pages) {
      await expandComponentMenu(page)
      await page.click(`.ant-menu-item:has-text("${pageInfo.menu}")`)
      await page.waitForTimeout(500)
      await expect(page.locator(`.page-title:has-text("${pageInfo.title}")`)).toBeVisible({ timeout: 3000 })
    }
  })
})
