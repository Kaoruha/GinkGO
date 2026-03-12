/**
 * 调试页面结构
 */

import { test } from '@playwright/test'
import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

test('调试页面结构', async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  // 监听控制台错误
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('浏览器控制台错误:', msg.text())
    }
  })

  page.on('pageerror', error => {
    console.log('页面错误:', error.message)
  })

  await page.goto(`${WEB_UI_URL}/stage1/backtest`)
  await page.waitForTimeout(5000)

  // 截图
  await page.screenshot({ path: '/tmp/backtest-list-page.png', fullPage: true })
  console.log('截图已保存: /tmp/backtest-list-page.png')

  // 获取页面信息
  console.log('页面标题:', await page.title())
  console.log('当前 URL:', page.url())

  const bodyText = await page.locator('body').textContent()
  console.log('页面包含 404:', bodyText.includes('404'))
  console.log('页面包含 NotFound:', bodyText.includes('NotFound'))
  console.log('页面包含 回测任务:', bodyText.includes('回测任务'))

  // 检查关键元素
  const table = await page.locator('.ant-table').count()
  console.log('表格数量:', table)

  const pageContainer = await page.locator('.page-container').count()
  console.log('page-container 数量:', pageContainer)

  await browser.close()
})
