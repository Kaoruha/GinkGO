// 调试投资组合页面白屏问题
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  console.log('=== 开始调试投资组合页面 ===')

  // 监听控制台
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`🔴 Error: ${msg.text()}`)
    } else if (msg.type() === 'warning') {
      console.log(`⚠️  Warning: ${msg.text()}`)
    }
  })

  // 监听页面错误
  page.on('pageerror', error => {
    console.log(`💥 Page Error: ${error.message}`)
  })

  // 导航到页面
  console.log(`📍 当前 URL: ${page.url()}`)
  console.log(`📍 导航到: ${WEB_UI_URL}/portfolio`)

  try {
    await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'domcontentloaded', timeout: 30000 })
  } catch (e) {
    console.log(`⚠️  Navigation error: ${e.message}`)
  }

  await page.waitForTimeout(5000)

  console.log('\n=== 页面状态 ===')
  console.log(`当前 URL: ${page.url()}`)
  console.log(`页面标题: ${await page.title()}`)

  // 获取页面内容
  const pageInfo = await page.evaluate(() => {
    const body = document.body
    return {
      hasApp: !!document.querySelector('#app'),
      hasLayout: !!document.querySelector('.ant-layout'),
      hasContent: !!document.querySelector('.portfolio-list-page'),
      bodyText: body.innerText.substring(0, 500),
      cardCount: document.querySelectorAll('.portfolio-card').length,
      initLoading: !!document.querySelector('.init-loading'),
      spinCount: document.querySelectorAll('.ant-spin').length
    }
  })

  console.log(`#app 存在: ${pageInfo.hasApp}`)
  console.log(`.ant-layout 存在: ${pageInfo.hasLayout}`)
  console.log(`有内容: ${pageInfo.hasContent}`)
  console.log(`卡片数量: ${pageInfo.cardCount}`)
  console.log(`加载中: ${pageInfo.initLoading}`)
  console.log(`Spin 数量: ${pageInfo.spinCount}`)
  console.log(`\n页面文本:\n${pageInfo.bodyText}`)

  // 检查 store 状态
  const storeInfo = await page.evaluate(() => {
    const authStore = window.__PINIA_STORES__?.auth
    const portfolioStore = window.__PINIA_STORES__?.portfolio

    return {
      hasAuthStore: !!authStore,
      authIsLoggedIn: authStore?.state?.isLoggedIn || false,
      hasPortfolioStore: !!portfolioStore,
      portfolioLoading: portfolioStore?.state?.loading || false,
      portfolioCount: portfolioStore?.state?.portfolios?.length || 0,
      route: window.__VUE_ROUTER__?.currentRoute?.path || 'unknown'
    }
  })

  console.log(`\nStore 状态:`)
  console.log(`  ${JSON.stringify(storeInfo, null, 2)}`)

  // 截图
  await page.screenshot({ path: '/tmp/portfolio-debug.png', fullPage: true })
  console.log('\n📸 截图: /tmp/portfolio-debug.png')

  await browser.close()
  console.log('\n=== 调试完成 ===')
})()
