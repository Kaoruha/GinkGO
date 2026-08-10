// 测试滚动加载 - 调试 Observer 状态
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  // 监听控制台
  page.on('console', msg => {
    const text = msg.text()
    if (text.includes('Observer') || text.includes('加载更多') || text.includes('数据加载') || text.includes('触发')) {
      console.log(`📋 ${text}`)
    }
  })

  console.log('=== 测试滚动加载 ===')

  await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(5000)

  const cardCount1 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`初始卡片数量: ${cardCount1}`)

  // 检查 store 状态
  const storeInfo = await page.evaluate(() => {
    const app = document.querySelector('#app')?.__vue_app__
    if (!app) return { error: 'Vue app not found' }

    // 尝试通过 $pinia 获取 stores
    const pinia = app.config.globalProperties.$pinia
    if (!pinia) return { error: 'Pinia not found' }

    const portfolioState = pinia._s.get('portfolio')?.$state || {}
    return {
      portfoliosCount: portfolioState.portfolios?.length || 0,
      hasMore: portfolioState.hasMore,
      loading: portfolioState.loading,
      loadingMore: portfolioState.loadingMore,
      total: portfolioState.total
    }
  })

  console.log('Store 状态:', JSON.stringify(storeInfo, null, 2))

  // 慢慢滚动，触发 Observer
  console.log('\n📍 开始滚动...')
  await page.evaluate(() => {
    const scrollable = document.querySelector('.scrollable-content')
    if (scrollable) {
      // 分步滚动，模拟真实用户行为
      let scrollTop = 0
      const targetScroll = scrollable.scrollHeight - scrollable.clientHeight
      const step = 200

      const scrollStep = () => {
        scrollTop = Math.min(scrollTop + step, targetScroll)
        scrollable.scrollTop = scrollTop
        if (scrollTop < targetScroll) {
          setTimeout(scrollStep, 300)
        }
      }

      scrollStep()
    }
  })

  await page.waitForTimeout(5000)

  const cardCount2 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`\n滚动后卡片数量: ${cardCount2}`)

  if (cardCount2 > cardCount1) {
    console.log('✅ 滚动加载成功!')
  } else {
    console.log('⚠️  滚动加载未触发')
  }

  // 不关闭浏览器，保持连接
  // await browser.close()
})()
