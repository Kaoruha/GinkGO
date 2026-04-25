const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const contexts = browser.contexts();
  const context = contexts[0] || await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Navigate to portfolio detail
    await page.goto('http://192.168.50.12:5173/portfolios/b3e54c90c6624de5a16893d43b7acead');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/rerun-01-portfolio.png' });
    console.log('1. Portfolio page loaded');

    // 2. Click "新建回测" or similar button
    const btnTexts = ['新建回测', '创建回测', '运行回测', 'Run Backtest', 'New Backtest'];
    let clicked = false;
    for (const t of btnTexts) {
      const btn = page.locator(`button:has-text("${t}")`).first();
      if (await btn.count() > 0) {
        await btn.click();
        clicked = true;
        console.log(`2. Clicked "${t}" button`);
        break;
      }
    }
    if (!clicked) {
      const buttons = await page.locator('button').allTextContents();
      console.log('Available buttons:', buttons.map(b => b.trim()).filter(Boolean));
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/rerun-02-create.png' });
    console.log('3. URL:', page.url());

    // 3. Fill form if needed
    const nameInput = page.locator('input[placeholder*="名称"], input[placeholder*="name"]').first();
    if (await nameInput.count() > 0) {
      await nameInput.fill('E2E_rerun_with_data');
      console.log('  Filled name');
    }

    // 4. Submit
    const submitTexts = ['确定', '提交', '创建', '开始', 'Submit', 'Create', 'Start'];
    for (const t of submitTexts) {
      const btn = page.locator(`button:has-text("${t}")`).first();
      if (await btn.count() > 0) {
        await btn.click();
        console.log(`4. Clicked "${t}" to submit`);
        break;
      }
    }
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/rerun-03-submitted.png' });
    console.log('5. URL after submit:', page.url());

    // 5. Wait for backtest to complete (poll)
    console.log('6. Waiting for backtest to run...');
    for (let i = 0; i < 30; i++) {
      await page.waitForTimeout(5000);
      const bodyText = await page.textContent('body');
      const hasProgress = /完成|completed|100%|99%/.test(bodyText);
      const hasData = /信号|signal|订单|order|持仓|position/i.test(bodyText);
      console.log(`  Poll ${i+1}: progress=${hasProgress}, hasData=${hasData}`);
      if (hasData || hasProgress) {
        await page.screenshot({ path: `/tmp/rerun-04-result-${i}.png` });
        if (hasData) break;
      }
    }

    await page.screenshot({ path: '/tmp/rerun-05-final.png' });
    const bodyText = await page.textContent('body');
    const hasSignals = /信号|signal/i.test(bodyText);
    const hasOrders = /订单|order/i.test(bodyText);
    console.log(`\nResult: signals=${hasSignals}, orders=${hasOrders}`);
    console.log('Done. Screenshots: /tmp/rerun-*.png');
  } catch (e) {
    console.error('Error:', e.message);
    await page.screenshot({ path: '/tmp/rerun-error.png' });
  } finally {
    await page.close();
  }
})();
