// 测试滚动加载 - 检查网络请求
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  // 监听请求
  page.on('request', request => {
    if (request.url().includes('/api/v1/portfolio')) {
      console.log(`🌐 Request: ${request.url()}`)
    }
  })

  page.on('response', response => {
    if (response.url().includes('/api/v1/portfolio')) {
      console.log(`📦 Response: ${response.url()} - ${response.status()}`)
    }
  })

  console.log('=== 测试滚动加载 ===')

  await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(5000)

  const cardCount = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`\n卡片数量: ${cardCount}`)

  // 获取 store 状态
  const storeInfo = await page.evaluate(() => {
    const app = document.querySelector('#app')?.__vue_app__
    if (!app) return { error: 'Vue app not found' }

    const pinia = app.config.globalProperties.$pinia
    if (!pinia) return { error: 'Pinia not found' }

    const portfolioState = pinia._s.get('portfolio')?.$state || {}
    return {
      portfoliosCount: portfolioState.portfolios?.length || 0,
      hasMore: portfolioState.hasMore,
      loading: portfolioState.loading,
      loadingMore: portfolioState.loadingMore,
      total: portfolioState.total,
      currentPage: portfolioState.currentPage
    }
  })

  console.log('Store 状态:', JSON.stringify(storeInfo, null, 2))

  // 滚动
  console.log('\n📍 滚动到底部...')
  await page.evaluate(() => {
    const scrollable = document.querySelector('.scrollable-content')
    if (scrollable) {
      scrollable.scrollTop = scrollable.scrollHeight
    }
  })

  await page.waitForTimeout(5000)

  const cardCount2 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`\n滚动后卡片数量: ${cardCount2}`)

  // 不关闭浏览器
  // await browser.close()
})()
