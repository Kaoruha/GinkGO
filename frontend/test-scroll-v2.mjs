// 测试滚动加载 - 修正版
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER)
  const context = browser.contexts()[0] || await browser.newContext()
  const page = context.pages[0] || await context.newPage()

  console.log('=== 测试滚动加载 ===')

  await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 30000 })
  await page.waitForTimeout(5000)

  // 正确获取 store 状态
  const storeState = await page.evaluate(() => {
    // 从 Vue 组件中获取 store
    const app = document.querySelector('#app')?.__vue_app__
    if (!app) {
      return { error: 'Vue app not found' }
    }

    // 尝试获取 pinia stores
    const pinia = app?.appContext?.config?.globalProperties?.__PINIA__
    if (!pinia) {
      return { error: 'Pinia not found' }
    }

    // 获取所有 stores
    const stores = {}
    for (const key in pinia) {
      const store = pinia[key]
      if (store && typeof store === 'object') {
        stores[key] = {
          _state: store._state,
          $state: store.$state
        }
      }
    }

    return {
      storesFound: Object.keys(stores),
      portfolio: stores['portfolio']?.$state || stores['portfolio']?._state,
      auth: stores['auth']?.$state || stores['auth']?._state
    }
  })

  console.log('Store 访问结果:')
  console.log(JSON.stringify(storeState, null, 2))

  // 计算卡片数量
  const cardCount = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`\n卡片数量: ${cardCount}`)

  // 滚动到底部
  console.log('\n📍 滚动到底部...')
  await page.evaluate(() => {
    window.scrollTo(0, document.body.scrollHeight)
  })

  await page.waitForTimeout(5000)

  // 再次检查卡片数量
  const cardCount2 = await page.$$eval('.portfolio-card', cards => cards.length)
  console.log(`滚动后卡片数量: ${cardCount2}`)

  if (cardCount2 > cardCount) {
    console.log('✅ 滚动加载成功!')
  } else {
    console.log('⚠️  滚动加载未触发')

    // 检查 loadMoreTrigger 是否可见
    const triggerVisible = await page.evaluate(() => {
      const el = document.querySelector('.load-more-trigger')
      if (!el) return { exists: false }
      const rect = el.getBoundingClientRect()
      return {
        exists: true,
        visible: rect.top < window.innerHeight && rect.bottom > 0
      }
    })
    console.log(`触发器可见性: ${JSON.stringify(triggerVisible)}`)
  }

  await browser.close()
})()
