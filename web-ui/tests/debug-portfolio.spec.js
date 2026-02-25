// 调试投资组合页面白屏问题
import { test, chromium } from '@playwright/test';

const REMOTE_BROWSER = 'http://192.168.50.10:9222';
const WEB_UI_URL = 'http://192.168.50.12:5173';

test('debug portfolio page', async () => {
  const browser = await chromium.connect(REMOTE_BROWSER);
  const context = browser.contexts()[0];
  let page = context.pages[0];

  if (!page) {
    page = await context.newPage();
  }

  console.log('=== 开始调试投资组合页面 ===');

  // 监听控制台
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log(`🔴 Console Error: ${msg.text()}`);
    }
  });

  // 监听页面错误
  page.on('pageerror', error => {
    console.log(`💥 Page Error: ${error.toString()}`);
  });

  // 导航到页面
  console.log(`📍 导航到: ${WEB_UI_URL}/portfolio`);
  await page.goto(`${WEB_UI_URL}/portfolio`, { timeout: 30000 });
  await page.waitForTimeout(5000);

  console.log('\n=== 页面状态 ===');

  // 检查页面内容
  const bodyInfo = await page.evaluate(() => {
    const body = document.body;
    return {
      textLength: body.innerText.length,
      textPreview: body.innerText.substring(0, 300),
      hasApp: !!document.querySelector('#app'),
      hasLayout: !!document.querySelector('.ant-layout'),
      hasPortfolioList: !!document.querySelector('.portfolio-list-page'),
      bodyHTML: body.innerHTML.substring(0, 800)
    };
  });

  console.log(`文本长度: ${bodyInfo.textLength}`);
  console.log(`文本预览: ${bodyInfo.textPreview}`);
  console.log(`#app 存在: ${bodyInfo.hasApp}`);
  console.log(`.ant-layout 存在: ${bodyInfo.hasLayout}`);
  console.log(`.portfolio-list-page 存在: ${bodyInfo.hasPortfolioList}`);
  console.log(`\nBody HTML:\n${bodyInfo.bodyHTML}`);

  // 检查 Vue/Pinia
  const appState = await page.evaluate(() => {
    return {
      route: window.__VUE_ROUTER__?.currentRoute?.path || 'unknown',
      stores: Object.keys(window.__PINIA_STORES__ || {}),
      hasToken: !!localStorage.getItem('access_token')
    };
  });

  console.log(`\n路由: ${appState.route}`);
  console.log(`Stores: ${JSON.stringify(appState.stores)}`);
  console.log(`有 token: ${appState.hasToken}`);

  // 截图
  await page.screenshot({ path: '/tmp/portfolio-debug.png', fullPage: true });
  console.log('\n📸 截图: /tmp/portfolio-debug.png');

  await browser.close();
});
