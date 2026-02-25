// 调试投资组合页面白屏问题
import { chromium } from 'playwright'

const REMOTE_BROWSER = 'http://192.168.50.10:9222'
const WEB_UI_URL = 'http://192.168.50.12:5173'

;(async () => {
  const browser = await chromium.connect(REMOTE_BROWSER)
  const context = browser.contexts()[0]
  let page = context.pages[0]

  if (!page) {
    page = await context.newPage()
  }

  console.log('=== 开始调试投资组合页面 ===')

  // 监听控制台
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`🔴 Console Error: ${msg.text()}`)
    } else if (msg.type() === 'warning') {
      console.log(`⚠️  Console Warning: ${msg.text()}`)
    }
  })

  // 监听页面错误
  page.on('pageerror', error => {
    console.log(`💥 Page Error: ${error.toString()}`)
  })

  // 监听请求失败
  page.on('requestfailed', request => {
    const failure = request.failure()
    if (failure && !failure.errorText.includes('favicon')) {
      console.log(`❌ Request Failed: ${request.url().substring(0, 80)} - ${failure.errorText}`)
    }
  })

  // 导航到页面
  console.log(`📍 导航到: ${WEB_UI_URL}/portfolio`)
  try {
    await page.goto(`${WEB_UI_URL}/portfolio`, { timeout: 30000 })
  } catch (e) {
    console.log(`⚠️  Navigation error: ${e.message}`)
  }

  // 等待页面加载
  await page.waitForTimeout(5000)

  console.log('\n=== 页面状态 ===')

  // 检查页面内容
  const bodyInfo = await page.evaluate(() => {
    const body = document.body
    return {
      textLength: body.innerText.length,
      textPreview: body.innerText.substring(0, 500),
      hasApp: !!document.querySelector('#app'),
      hasLayout: !!document.querySelector('.ant-layout'),
      hasPortfolioList: !!document.querySelector('.portfolio-list-page'),
      hasInitLoading: !!document.querySelector('.init-loading'),
      hasRouterView: !!document.querySelector('router-view'),
      cardCount: document.querySelectorAll('.portfolio-card').length,
      spinCount: document.querySelectorAll('.ant-spin').length,
      emptyCount: document.querySelectorAll('.ant-empty').length,
      bodyHTML: body.innerHTML.substring(0, 1000)
    }
  })

  console.log(`文本长度: ${bodyInfo.textLength}`)
  console.log(`#app 存在: ${bodyInfo.hasApp}`)
  console.log(`.ant-layout 存在: ${bodyInfo.hasLayout}`)
  console.log(`.portfolio-list-page 存在: ${bodyInfo.hasPortfolioList}`)
  console.log(`.init-loading 存在: ${bodyInfo.hasInitLoading}`)
  console.log(`router-view 存在: ${bodyInfo.hasRouterView}`)
  console.log(`卡片数量: ${bodyInfo.cardCount}`)
  console.log(`Spin 数量: ${bodyInfo.spinCount}`)
  console.log(`Empty 数量: ${bodyInfo.emptyCount}`)

  if (bodyInfo.textLength < 100) {
    console.log('\n⚠️  页面内容为空或很少!')
    console.log(`Body HTML:\n${bodyInfo.bodyHTML}`)
  } else {
    console.log(`\n文本预览:\n${bodyInfo.textPreview}`)
  }

  // 检查 Vue/Pinia 状态
  const appState = await page.evaluate(() => {
    return {
      route: window.__VUE_ROUTER__?.currentRoute?.path || 'unknown',
      stores: Object.keys(window.__PINIA_STORES__ || {}),
      hasToken: !!localStorage.getItem('access_token'),
      hasUser: !!localStorage.getItem('user_info'),
      vueApps: window.__VUE_DEVTOOLS_GLOBAL_HOOK__?.apps?.length || 0
    }
  })

  console.log(`\n应用状态:`)
  console.log(`  当前路由: ${appState.route}`)
  console.log(`  Pinia stores: ${JSON.stringify(appState.stores)}`)
  console.log(`  有 token: ${appState.hasToken}`)
  console.log(`  有 user: ${appState.hasUser}`)
  console.log(`  Vue apps: ${appState.vueApps}`)

  // 检查 authStore 状态
  const authInfo = await page.evaluate(() => {
    const authStore = window.__PINIA_STORES__?.auth
    if (!authStore) return { error: 'authStore not found' }

    const state = authStore.state
    return {
      isLoggedIn: state?.isLoggedIn || false,
      hasToken: !!state?.token,
      hasUser: !!state?.user
    }
  })

  console.log(`\nAuth Store:`)
  console.log(`  ${JSON.stringify(authInfo)}`)

  // 截图
  console.log('\n=== 截图 ===')
  await page.screenshot({ path: '/tmp/portfolio-debug.png', fullPage: true })
  console.log('📸 截图已保存到: /tmp/portfolio-debug.png')

  await browser.close()
  console.log('\n=== 调试完成 ===')
})()
