/**
 * 调试：检查远程浏览器的登录状态
 */

import { chromium } from 'playwright'

async function investigate() {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222')
  const context = browser.contexts()[0]
  const page = context.pages()[0] || await context.newPage()

  console.log('当前页面 URL:', page.url())
  console.log('页面标题:', await page.title())

  // 检查是否有登录相关的元素
  const loginForms = await page.locator('form, input[type="password"]').count()
  console.log('登录表单数量:', loginForms)

  // 检查 localStorage
  const storage = await page.evaluate(() => {
    return {
      localStorage: Object.keys(localStorage),
      hasToken: !!localStorage.getItem('access_token'),
      hasUser: !!localStorage.getItem('user_info')
    }
  })
  console.log('本地存储状态:', storage)

  // 检查 cookies
  const cookies = await page.context().cookies()
  console.log('Cookies:', cookies.map(c => c.name))

  // 访问回测列表页面
  await page.goto('http://192.168.50.12:5174/backtest')
  await page.waitForTimeout(3000)

  console.log('回测页 URL:', page.url())
  console.log('回测页标题:', await page.title())

  // 截图
  await page.screenshot({ path: '/tmp/backtest-page-debug.png' })
  console.log('截图保存到: /tmp/backtest-page-debug.png')

  // 检查是否能看到表格
  const table = await page.locator('.ant-table').count()
  console.log('表格数量:', table)

  // 检查是否有"查看详情"链接
  const detailLinks = await page.locator('a:has-text("查看详情")').count()
  console.log('"查看详情"链接数量:', detailLinks)

  await browser.close()
}

investigate().catch(console.error)
