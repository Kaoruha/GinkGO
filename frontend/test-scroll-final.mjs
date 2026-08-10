// 测试滚动加载 - 最终版
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages[0] || await context.newPage()

  console.log('=== 测试滚动加载 ===')

  await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(3000)

  const cardCount1 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`初始卡片数量: ${cardCount1}`)

  // 检查滚动区域
  const scrollInfo = await page.evaluate(() => {
    const scrollable = document.querySelector('.scrollable-content')
    if (!scrollable) return { error: '.scrollable-content not found' }

    const trigger = document.querySelector('.load-more-trigger')
    if (!trigger) return { error: '.load-more-trigger not found' }

    const scrollRect = scrollable.getBoundingClientRect()
    const triggerRect = trigger.getBoundingClientRect()

    return {
      scrollableHeight: scrollRect.height,
      scrollableScrollTop: scrollable.scrollTop,
      scrollHeight: scrollable.scrollHeight,
      triggerTop: triggerRect.top,
      triggerBottom: triggerRect.bottom,
      windowHeight: window.innerHeight,
      distanceToBottom: scrollable.scrollHeight - scrollable.scrollTop - scrollRect.height
    }
  })

  console.log('滚动区域信息:')
  console.log(JSON.stringify(scrollInfo, null, 2))

  // 在正确的滚动区域内滚动
  console.log('\n📍 滚动到底部...')
  await page.evaluate(() => {
    const scrollable = document.querySelector('.scrollable-content')
    if (scrollable) {
      scrollable.scrollTop = scrollable.scrollHeight
    }
  })

  await page.waitForTimeout(3000)

  const cardCount2 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`滚动后卡片数量: ${cardCount2}`)

  if (cardCount2 > cardCount1) {
    console.log('✅ 滚动加载成功!')
  } else {
    console.log('⚠️  滚动加载未触发')

    // 检查触发器位置
    const triggerInfo = await page.evaluate(() => {
      const trigger = document.querySelector('.load-more-trigger')
      const scrollable = document.querySelector('.scrollable-content')
      if (!trigger || !scrollable) return {}

      const triggerRect = trigger.getBoundingClientRect()
      const scrollableRect = scrollable.getBoundingClientRect()

      return {
        triggerVisible: triggerRect.top < scrollableRect.bottom && triggerRect.bottom > scrollableRect.top,
        triggerTop: triggerRect.top,
        scrollableBottom: scrollableRect.bottom,
        distance: triggerRect.top - scrollableRect.top
      }
    })
    console.log(`触发器状态: ${JSON.stringify(triggerInfo)}`)
  }

  await browser.close()
})()
