const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const context = browser.contexts()[0] || await browser.newContext();
  const page = await context.newPage();

  // Navigate to Web UI home
  await page.goto('http://192.168.50.12:5173');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: '/tmp/ui-00-home.png' });
  console.log('1. Home page, URL:', page.url());

  // Find backtest or portfolio navigation
  const navLinks = await page.locator('nav a, aside a, [class*="nav"] a, [class*="menu"] a').allTextContents();
  console.log('Nav links:', navLinks.map(s => s.trim()).filter(Boolean).slice(0, 15));

  // Click portfolio item or navigate to the Demo portfolio
  const portfolioLink = page.locator('text=组合').first();
  if (await portfolioLink.count() > 0) {
    await portfolioLink.click();
    await page.waitForTimeout(2000);
    console.log('2. Portfolio page, URL:', page.url());
    await page.screenshot({ path: '/tmp/ui-01-portfolio.png' });
  }

  // Navigate to backtest detail
  await page.goto('http://192.168.50.12:5173/portfolios/7b9e73e0e3104251bda0a12e312a409f/backtests/eaf76afa1d69448591e9542dd5e5b65e');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: '/tmp/ui-02-backtest.png' });
  console.log('3. Backtest detail, URL:', page.url());

  // Find and click through tabs
  const tabLabels = ['概览', '信号', '订单', '净值', '持仓', '分析', '日志'];
  for (const name of tabLabels) {
    const el = page.locator(`button:has-text("${name}"), [role="tab"]:has-text("${name}"), [class*="tab"]:has-text("${name}")`).first();
    if (await el.count() > 0) {
      await el.click();
      await page.waitForTimeout(1500);
      await page.screenshot({ path: `/tmp/ui-03-${name}.png` });
      const body = await page.textContent('body');
      const empty = body.includes('暂无数据') || body.includes('将在后续版本') || body.includes('No data');
      const hasData = /000001|998426|277|579|346/.test(body);
      console.log(`  Tab "${name}": empty=${empty}, hasData=${hasData}`);
    } else {
      console.log(`  Tab "${name}": NOT FOUND`);
    }
  }

  console.log('Done');
  await page.close();
})();
