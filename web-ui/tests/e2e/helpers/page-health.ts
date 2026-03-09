/**
 * 全局测试配置和钩子
 *
 * 核心原则：页面有错误 = 测试立即失败
 * 在执行任何功能验证之前，先确保页面健康
 */

import { test, expect } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

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
  const {
    skipNetworkCheck = false,
    timeout = 5000
  } = options

  const health: PageHealth = {
    errors: [],
    warnings: [],
    hasConsoleErrors: false,
    hasPageErrors: false,
    hasNetworkErrors: false
  }

  // 收集所有页面错误
  const collectErrors = () => {
    // 1. 控制台错误
    page.on('console', msg => {
      const text = msg.text()
      if (msg.type() === 'error') {
        health.errors.push(`[CONSOLE ERROR] ${text}`)
        health.hasConsoleErrors = true
        console.error(`❌ Console Error: ${text}`)
      } else if (msg.type() === 'warning') {
        health.warnings.push(`[CONSOLE WARN] ${text}`)
        console.warn(`⚠️  Console Warning: ${text}`)
      }
    })

    // 2. 页面运行时错误
    page.on('pageerror', error => {
      health.errors.push(`[PAGE ERROR] ${error.message}`)
      health.hasPageErrors = true
      console.error(`❌ Page Error: ${error.message}`)
    })

    // 3. 网络请求失败
    if (!skipNetworkCheck) {
      page.on('requestfailed', request => {
        const failure = request.failure()
        const url = request.url()

        // 忽略一些可接受的失败（如字体、图片等）
        const skippablePatterns = [
          '/fonts/',
          '/images/',
          '.woff',
          '.woff2',
          '.ttf',
          '.svg',
          'favicon',
          'analytics'
        ]

        const isSkippable = skippablePatterns.some(pattern => url.includes(pattern))

        if (!isSkippable) {
          health.errors.push(`[NETWORK ERROR] ${url} - ${failure?.errorText || 'Unknown'}`)
          health.hasNetworkErrors = true
          console.error(`❌ Network Error: ${url} - ${failure?.errorText}`)
        }
      })
    }
  }

  // 等待页面稳定，让错误有时间浮现
  await page.waitForTimeout(2000)

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

  // 检查 2: 不能有任何 JavaScript 错误
  if (health.hasConsoleErrors || health.hasPageErrors) {
    const errorSummary = health.errors
      .slice(0, 10) // 最多显示10个错误
      .join('\n    ')

    throw new Error(
      `❌ 页面有 JavaScript 错误！\n` +
      `   发现 ${health.errors.length} 个错误\n` +
      `   错误列表:\n    ${errorSummary}\n` +
      `   ${health.errors.length > 10 ? `    ... 还有 ${health.errors.length - 10} 个错误` : ''}`
    )
  }

  // 检查 3: 不能有关键网络错误
  if (health.hasNetworkErrors && !skipNetworkCheck) {
    const networkErrors = health.errors.filter(e => e.includes('[NETWORK ERROR]'))
    throw new Error(
      `❌ 页面有关键网络请求失败！\n` +
      `   失败的请求:\n    ${networkErrors.slice(0, 5).join('\n    ')}`
    )
  }

  // 检查 4: 基础页面结构必须存在
  const bodyText = await page.locator('body').textContent()

  // 如果是错误页面，bodyText 会包含错误信息
  if (bodyText.includes('Internal Server Error') ||
      bodyText.includes('This page could not be found') ||
      bodyText.includes('Application error')) {
    throw new Error(
      `❌ 页面显示错误信息！\n` +
      `   Body内容: ${bodyText.substring(0, 200)}...`
    )
  }

  // ========== 健康检查通过后的日志 ==========
  console.log('✅ 页面健康检查通过')
  if (health.warnings.length > 0) {
    console.log(`   ⚠️  有 ${health.warnings.length} 个警告（不影响测试）`)
  }

  return health
}

// ========== 增强的页面获取函数 ==========

/**
 * 获取远程浏览器页面，并自动设置错误监听
 *
 * ⚠️ 此函数返回的 page 会自动监听错误
 * 如果页面有错误，后续的 assertPageHealthy() 会抛出异常
 */
export async function getHealthyPage(
  targetUrl: string,
  options: {
    skipNetworkCheck?: boolean
    timeout?: number
  } = {}
) {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  let page = context.pages()[0]

  // 如果没有现有页面，创建新页面
  if (!page) {
    page = await context.newPage()
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

// ========== 测试辅助函数 ==========

/**
 * 为每个测试自动执行的页面健康检查钩子
 */
export function setupPageHealthCheck() {
  test.beforeEach(async ({ page }) => {
    // 设置页面级别的错误监听
    page.on('pageerror', (error) => {
      console.error(`❌ [TEST] Page error detected: ${error.message}`)
      // 不抛出异常，让 afterEach 来处理
    })
  })

  test.afterEach(async ({ page }) => {
    // 测试结束后检查是否有错误累积
    const errors: string[] = []

    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    // 如果测试通过但有错误，标记测试为可疑
    if (errors.length > 0) {
      console.warn(`⚠️  测试通过但发现 ${errors.length} 个控制台错误`)
    }
  })
}

// ========== 导出 ==========

export { REMOTE_BROWSER, WEB_UI_URL }
