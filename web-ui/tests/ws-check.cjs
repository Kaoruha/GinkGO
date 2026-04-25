const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222', { timeout: 5000 }).catch(() => null);
  if (!browser) { console.log('SKIP: browser not reachable'); return; }
  const context = browser.contexts()[0];
  const page = await context.newPage();

  const consoleMsgs = [];
  const wsErrors = [];
  page.on('console', msg => {
    if (msg.text().includes('[WS]') || msg.text().includes('WebSocket')) {
      consoleMsgs.push(`[${msg.type()}] ${msg.text()}`);
    }
  });
  page.on('pageerror', e => wsErrors.push(e.message));

  try {
    // 1. Open backtest list
    await page.goto('http://192.168.50.12:5173/portfolios/be07e712ca3c456fb75246291241882d/backtests', {
      waitUntil: 'networkidle', timeout: 15000
    });
    await page.waitForTimeout(2000);

    // Check WS connection status
    const wsStatus = await page.evaluate(() => {
      // Check if WebSocket connected by looking at the composable state
      return { url: window.__wsUrl || 'unknown' };
    });

    // 2. Enter detail
    const card = page.locator('.task-card').first();
    if (await card.count() > 0) {
      await card.click({ timeout: 5000 });
      await page.waitForTimeout(2000);
      console.log(`Detail: ${page.url()}`);

      // 3. Switch to Components
      await page.locator('.tab-bar a:has-text("组件")').click({ timeout: 5000 });
      await page.waitForTimeout(1500);
      const activeTab = await page.locator('.tab-bar .tab-item.active').textContent();
      console.log(`Active tab: "${activeTab?.trim()}"`);

      // 4. Switch back to Backtests
      await page.locator('.tab-bar a:has-text("回测")').click({ timeout: 5000 });
      await page.waitForTimeout(1500);
      const activeTab2 = await page.locator('.tab-bar .tab-item.active').textContent();
      console.log(`Active tab: "${activeTab2?.trim()}"`);
      const cards = await page.locator('.task-card').count();
      console.log(`Task cards: ${cards}`);
    }

    await page.screenshot({ path: '/tmp/ws-check.png' });
    console.log('\n--- Console WS messages ---');
    consoleMsgs.forEach(m => console.log(m));
    if (consoleMsgs.length === 0) console.log('(none)');

    if (wsErrors.length > 0) {
      console.log('\n--- Page errors ---');
      wsErrors.forEach(e => console.log(e));
    } else {
      console.log('\nPage errors: none');
    }

    console.log('\nOK');
  } catch (e) {
    console.error(`FAIL: ${e.message}`);
    await page.screenshot({ path: '/tmp/ws-check-fail.png' }).catch(() => {});
  } finally {
    await page.close();
    await browser.close();
  }
})();
