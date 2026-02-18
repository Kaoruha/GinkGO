/**
 * 开发调试脚本 - 快速测试远程浏览器
 *
 * 用法: node tests/e2e/dev-test.mjs [url] [--screenshot]
 * 示例: node tests/e2e/dev-test.mjs http://192.168.50.12:5173/login
 *       node tests/e2e/dev-test.mjs http://192.168.50.12:5173/login --screenshot
 */

import { chromium } from 'playwright'

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222'
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173'

async function main() {
  const args = process.argv.slice(2)
  const shouldScreenshot = args.includes('--screenshot')
  const targetUrl = args.find(a => !a.startsWith('--')) || `${WEB_UI_URL}/login`

  console.log(`🔗 连接远程浏览器: ${REMOTE_BROWSER}`)
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  console.log('✅ 已连接')

  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  console.log(`📄 访问: ${targetUrl}`)
  await page.goto(targetUrl, { waitUntil: 'networkidle' })

  console.log(`📌 标题: ${await page.title()}`)
  console.log(`🔗 URL: ${page.url()}`)

  if (shouldScreenshot) {
    const screenshotPath = `test-results/dev-${Date.now()}.png`
    await page.screenshot({ path: screenshotPath, fullPage: true })
    console.log(`📷 截图: ${screenshotPath}`)
  }

  console.log('\n✅ 完成')
  process.exit(0)
}

main().catch(err => {
  console.error('❌ 错误:', err.message)
  process.exit(1)
})
