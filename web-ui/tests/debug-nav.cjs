const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const context = browser.contexts()[0];
  const page = await context.newPage();

  // 收集控制台错误
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });
  page.on('pageerror', err => errors.push(`PAGEERROR: ${err.message}`));

  try {
    // 1. 进入回测列表
    await page.goto('http://192.168.50.12:5173/portfolios/be07e712ca3c456fb75246291241882d/backtests', {
      waitUntil: 'networkidle', timeout: 15000
    });
    await page.waitForTimeout(1000);
    console.log(`1. List page: ${page.url()}`);

    // 2. 点击第一个任务进入详情
    const firstTask = page.locator('.task-name').first();
    if (await firstTask.count() > 0) {
      const name = await firstTask.textContent();
      console.log(`2. Clicking task: "${name?.trim()}"`);
      await firstTask.click({ timeout: 5000 });
      await page.waitForTimeout(2000);
      console.log(`   Detail URL: ${page.url()}`);
    }

    // 3. 截图当前详情页
    await page.screenshot({ path: '/tmp/detail-before-switch.png' });

    // 4. 尝试点击"组件"tab
    console.log('\n3. Clicking Components tab...');
    const compTab = page.locator('.tab-bar .tab-item:has-text("组件")');
    console.log(`   Found: ${await compTab.count()}`);
    if (await compTab.count() > 0) {
      await compTab.click({ timeout: 5000 });
      await page.waitForTimeout(2000);
      console.log(`   URL after click: ${page.url()}`);
    }

    await page.screenshot({ path: '/tmp/detail-after-switch.png' });

    // 5. 再试概况
    console.log('\n4. Clicking Overview tab...');
    const overviewTab = page.locator('.tab-bar .tab-item:has-text("概况")');
    if (await overviewTab.count() > 0) {
      await overviewTab.click({ timeout: 5000 });
      await page.waitForTimeout(2000);
      console.log(`   URL after click: ${page.url()}`);
    }

    await page.screenshot({ path: '/tmp/detail-after-overview.png' });

    // 输出控制台错误
    if (errors.length > 0) {
      console.log('\n=== Console Errors ===');
      errors.forEach(e => console.log(e));
    } else {
      console.log('\nNo console errors');
    }

  } catch (e) {
    console.error(`FAIL: ${e.message.split('\n')[0]}`);
    await page.screenshot({ path: '/tmp/nav-fail2.png' });
    if (errors.length > 0) {
      console.log('\n=== Console Errors ===');
      errors.forEach(e => console.log(e));
    }
  } finally {
    await page.close();
  }
})();
