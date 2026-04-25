const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222', { timeout: 5000 }).catch(() => null);
  if (!browser) { console.log('SKIP: browser not reachable'); return; }
  const context = browser.contexts()[0];
  const page = await context.newPage();

  const errors = [];
  page.on('pageerror', e => errors.push(e.message));

  try {
    // 1. Go to backtest list
    await page.goto('http://192.168.50.12:5173/portfolios/be07e712ca3c456fb75246291241882d/backtests', {
      waitUntil: 'networkidle', timeout: 15000
    });
    await page.waitForTimeout(1000);

    // 2. Click first task card to enter detail
    const card = page.locator('.task-card').first();
    if (await card.count() === 0) {
      console.log('No tasks found');
      return;
    }
    await card.click({ timeout: 5000 });
    await page.waitForTimeout(1500);
    console.log(`Detail URL: ${page.url()}`);

    // Check we're on detail page
    if (!page.url().includes('/backtests/')) {
      console.log('FAIL: did not navigate to detail');
      return;
    }

    // 3. Now try switching to Components tab
    const componentsTab = page.locator('.tab-bar a:has-text("组件")');
    await componentsTab.click({ timeout: 5000 });
    await page.waitForTimeout(1500);
    console.log(`After Components click: ${page.url()}`);

    // 4. Verify active tab highlight
    const activeTabText = await page.locator('.tab-bar .tab-item.active').textContent();
    console.log(`Active tab: "${activeTabText?.trim()}"`);

    // 5. Check if ComponentsTab content is rendered (not BacktestTab)
    const hasBacktestContent = await page.locator('.task-card, .detail-content, .btn-back').count();
    const hasComponentsContent = await page.locator('[class*="component"], [class*="Components"]').count();
    console.log(`Backtest elements: ${hasBacktestContent}, Component elements: ${hasComponentsContent}`);

    // Take screenshot
    await page.screenshot({ path: '/tmp/tab-switch-test.png' });
    console.log('Screenshot: /tmp/tab-switch-test.png');

    if (errors.length > 0) {
      console.log(`\nPage errors (${errors.length}):`);
      errors.forEach(e => console.log(`  - ${e}`));
    }

    // 6. Switch back to Backtests
    const backtestsTab = page.locator('.tab-bar a:has-text("回测")');
    await backtestsTab.click({ timeout: 5000 });
    await page.waitForTimeout(1500);
    console.log(`\nAfter Backtests click: ${page.url()}`);
    const activeTabText2 = await page.locator('.tab-bar .tab-item.active').textContent();
    console.log(`Active tab: "${activeTabText2?.trim()}"`);
    const taskCards = await page.locator('.task-card').count();
    console.log(`Task cards visible: ${taskCards}`);

    await page.screenshot({ path: '/tmp/tab-switch-test2.png' });
    console.log('Screenshot: /tmp/tab-switch-test2.png');

    console.log('\nDONE');
  } catch (e) {
    console.error(`FAIL: ${e.message}`);
    await page.screenshot({ path: '/tmp/tab-switch-fail.png' }).catch(() => {});
  } finally {
    await page.close();
    await browser.close();
  }
})();
