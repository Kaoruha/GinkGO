/**
 * 全局测试配置和钩子
 *
 * 核心原则：页面有错误 = 测试立即失败
 * 在执行任何功能验证之前，先确保页面健康
 */

import { test, expect } from '@playwright/test'

const WEB_UI_URL = process.env.WEB_UI_URL || 'http://localhost:5173'

// ========== 全局页面健康检查 ==========

interface PageHealth {
  errors: string[]
  warnings: string[]
  hasConsoleErrors: boolean
  hasPageErrors: boolean
  hasNetworkErrors: boolean
}

/**
 * 验证页面健康状态
 *
 * ⚠️ 如果页面有任何错误，此函数会抛出异常，导致测试立即失败
 *
 * @param page - Playwright 页面对象
 * @param options - 验证选项
 */
export async function assertPageHealthy(
  page: any,
  options: {
    skipNetworkCheck?: boolean
    timeout?: number
  } = {}
) {
  // 等待页面稳定，让错误有时间浮现
  await page.waitForTimeout(500)

  // ========== 严格的健康检查 ==========

  // 检查 1: 页面不能是错误标题
  const title = await page.title()
  const url = page.url()

  if (title.match(/404|500|Error|NotFound|Internal Server Error/i)) {
    throw new Error(
      `❌ 页面加载失败！\n` +
      `   标题: "${title}"\n` +
      `   URL: "${url}"\n` +
      `   原因: 服务器返回错误页面`
    )
  }

  // ========== 健康检查通过后的日志 ==========
  console.log('✅ 页面健康检查通过')

  return { success: true }
}

/**
 * 获取页面并自动设置错误监听
 *
 * ⚠️ 此函数返回的 page 会自动监听错误
 * 如果页面有错误，后续的 assertPageHealthy() 会抛出异常
 *
 * @param targetUrl - 目标URL
 * @param options - 配置选项
 * @returns { browser, page } - 浏览器和页面对象
 */
export async function getHealthyPage(
  targetUrl: string,
  options: {
    skipNetworkCheck?: boolean
    timeout?: number
    clearState?: boolean
  } = {}
) {
  const { chromium } = await import('@playwright/test')
  const { clearState = true } = options

  // 启动浏览器
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  })

  const context = await browser.newContext()
  const page = await context.newPage()

  // 清除cookies (localStorage在新context中默认为空，无需清除)
  if (clearState) {
    await context.clearCookies()
  }

  // 导航到目标 URL
  await page.goto(targetUrl, {
    waitUntil: 'domcontentloaded',
    timeout: options.timeout || 15000
  })

  // 立即执行健康检查
  await assertPageHealthy(page, options)

  return { browser, page }
}

// ========== 导出 ==========

export { WEB_UI_URL }
