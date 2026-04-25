const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const contexts = browser.contexts();
  const context = contexts[0] || await browser.newContext();
  const page = await context.newPage();
  await page.goto('https://www.baidu.com');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/baidu-test.png' });
  const title = await page.title();
  console.log('Title:', title);
  await page.close();
})();
