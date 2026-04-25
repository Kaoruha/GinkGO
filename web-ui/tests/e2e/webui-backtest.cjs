const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const context = browser.contexts()[0] || await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Go to portfolio detail page
    await page.goto('http://192.168.50.12:5173/portfolios/7b9e73e0e3104251bda0a12e312a409f');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/wf-01-portfolio.png' });
    console.log('1. Portfolio page loaded');

    // 2. Find and click "新建回测" or similar button
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
      // Try any action button
      const buttons = await page.locator('button').allTextContents();
      console.log('Available buttons:', buttons.map(b => b.trim()).filter(Boolean));
      // Try clicking the first relevant one
      for (const b of buttons) {
        const trimmed = b.trim();
        if (trimmed && (trimmed.includes('回测') || trimmed.includes('backtest') || trimmed.includes('新建') || trimmed.includes('创建'))) {
          await page.locator(`button:has-text("${trimmed}")`).first().click();
          clicked = true;
          console.log(`2. Clicked "${trimmed}" button`);
          break;
        }
      }
    }
    await page.waitForTimeout(2000);
    await page.screenshot({ path: '/tmp/wf-02-create.png' });

    // 3. Fill in backtest form if it appeared
    const url = page.url();
    console.log('3. Current URL:', url);

    // Check for form fields
    const nameInput = page.locator('input[placeholder*="名称"], input[placeholder*="name"], input[label*="名称"]').first();
    if (await nameInput.count() > 0) {
      await nameInput.fill('E2E_test_task_id');
      console.log('  Filled name: E2E_test_task_id');
    }

    // Look for date inputs
    const dateInputs = await page.locator('input[type="date"], input[placeholder*="日期"], input[placeholder*="date"]').all();
    if (dateInputs.length >= 2) {
      await dateInputs[0].fill('2025-05-01');
      await dateInputs[1].fill('2026-03-01');
      console.log('  Set dates: 2025-05-01 ~ 2026-03-01');
    }

    await page.screenshot({ path: '/tmp/wf-03-form.png' });

    // 4. Submit the form
    const submitTexts = ['确定', '提交', '创建', '开始', '启动', 'Submit', 'Create', 'Start'];
    for (const t of submitTexts) {
      const btn = page.locator(`button:has-text("${t}")`).first();
      if (await btn.count() > 0) {
        await btn.click();
        console.log(`4. Clicked "${t}" to submit`);
        break;
      }
    }
    await page.waitForTimeout(3000);
    await page.screenshot({ path: '/tmp/wf-04-submitted.png' });
    console.log('5. URL after submit:', page.url());

    // 5. Wait for backtest to run and check results
    await page.waitForTimeout(5000);
    await page.screenshot({ path: '/tmp/wf-05-result.png' });

    const bodyText = await page.textContent('body');
    const hasProgress = /\d+%/.test(bodyText);
    const hasSignals = /信号|signal/i.test(bodyText);
    console.log('  Has progress indicator:', hasProgress);
    console.log('  Has signals mention:', hasSignals);

    console.log('\nDone. Screenshots: /tmp/wf-*.png');
  } catch (e) {
    console.error('Error:', e.message);
    await page.screenshot({ path: '/tmp/wf-error.png' });
  } finally {
    await page.close();
  }
})();
