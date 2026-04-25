const { chromium } = require('@playwright/test');

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const contexts = browser.contexts();
  const context = contexts[0] || await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto('http://192.168.50.12:5173/portfolios/7b9e73e0e3104251bda0a12e312a409f/backtests/eaf76afa1d69448591e9542dd5e5b65e');
    await page.waitForTimeout(3000);
    console.log('1. URL:', page.url());

    // Find tabs
    const tabs = await page.locator('[role="tab"]').all();
    console.log(`   Found ${tabs.length} tabs:`);
    for (const tab of tabs) {
      const text = (await tab.textContent()).trim();
      console.log(`     - "${text}"`);
    }

    // Click through tabs
    const tabNames = ['概览', '信号', '订单', '净值', '持仓', '分析', '日志'];
    let idx = 10;
    for (const name of tabNames) {
      const tab = page.locator(`[role="tab"]:has-text("${name}")`).first();
      if (await tab.count() > 0) {
        await tab.click();
        await page.waitForTimeout(2000);
        idx++;
        await page.screenshot({ path: `/tmp/e2e-${idx}-${name}.png`, fullPage: false });
        const content = await page.textContent('body');
        const hasEmpty = content.includes('暂无数据') || content.includes('将在后续版本') || content.includes('No data');
        console.log(`   Tab "${name}": empty=${hasEmpty}`);
      }
    }
    console.log('Done');
  } catch (e) {
    console.error('Error:', e.message);
  } finally {
    await page.close();
  }
})();
