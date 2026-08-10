// 测试滚动加载
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages()[0] || await context.newPage()

  console.log('=== 测试滚动加载 ===')

  await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(5000)

  // 检查初始状态
  const initialState = await page.evaluate(() => {
    const stores = window.__PINIA_STORES__ || {}
    const portfolioStore = stores.portfolio
    return {
      portfolioCount: portfolioStore?.state?.portfolios?.length || 0,
      total: portfolioStore?.state?.total || 0,
      hasMore: portfolioStore?.state?.hasMore || false,
      loading: portfolioStore?.state?.loading || false,
      loadingMore: portfolioStore?.state?.loadingMore || false
    }
  })

  console.log('初始状态:')
  console.log(`  portfolios: ${initialState.portfolioCount}`)
  console.log(`  total: ${initialState.total}`)
  console.log(`  hasMore: ${initialState.hasMore}`)

  // 检查页面元素
  const hasTrigger = await page.$('.load-more-trigger')
  console.log(`loadMoreTrigger 存在: ${!!hasTrigger}`)

  if (hasTrigger) {
    // 滚动到底部
    await page.evaluate(() => {
      window.scrollTo(0, document.body.scrollHeight)
    })
    await page.waitForTimeout(3000)

    // 检查是否加载了更多
    const afterScroll = await page.evaluate(() => {
      const stores = window.__PINIA_STORES__ || {}
      const portfolioStore = stores.portfolio
      return {
        portfolioCount: portfolioStore?.state?.portfolios?.length || 0,
        total: portfolioStore?.state?.total || 0,
        hasMore: portfolioStore?.state?.hasMore || false
      }
    })

    console.log('\n滚动后状态:')
    console.log(`  portfolios: ${afterScroll.portfolioCount}`)
    console.log(`  total: ${afterScroll.total}`)
    console.log(`  hasMore: ${afterScroll.hasMore}`)

    if (afterScroll.portfolioCount > initialState.portfolioCount) {
      console.log('✅ 滚动加载成功！')
    } else {
      console.log('⚠️  滚动加载未触发')
    }
  }

  await browser.close()
  console.log('\n=== 测试完成 ===')
})()
