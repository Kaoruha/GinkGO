const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const context = browser.contexts()[0];
  const page = await context.newPage();

  try {
    // 1. 打开 portfolio 详情
    await page.goto('http://192.168.50.12:5173/portfolios/be07e712ca3c456fb75246291241882d/backtests', {
      waitUntil: 'networkidle', timeout: 15000
    });
    await page.waitForTimeout(1500);
    console.log(`1. Backtest list: ${page.url()}`);

    // 2. 查看列表中的任务项
    const items = await page.locator('.task-card, .task-item, [class*="task"]').allTextContents();
    console.log(`   Task items: ${items.length}`);

    // 3. 点击第一个任务进入详情
    const firstTask = page.locator('.task-name, [class*="task-name"]').first();
    if (await firstTask.count() > 0) {
      const taskName = await firstTask.textContent();
      console.log(`2. Clicking task: "${taskName?.trim()}"`);
      await firstTask.click({ timeout: 5000 });
      await page.waitForTimeout(2000);
      console.log(`   URL: ${page.url()}`);
    } else {
      // 尝试其他选择器
      const pageText = await page.locator('body').innerText();
      const lines = pageText.split('\n').filter(l => l.trim()).slice(0, 20);
      console.log('   Page lines:', JSON.stringify(lines));

      // 用文本匹配点击任务
      const taskLink = page.locator('text=待启动').first();
      if (await taskLink.count() > 0) {
        // 点击待启动任务的父元素
        await taskLink.locator('..').click({ timeout: 5000 });
        await page.waitForTimeout(2000);
        console.log(`   URL after click: ${page.url()}`);
      }
    }

    await page.screenshot({ path: '/tmp/backtest-detail.png' });

    // 4. 现在在详情页，尝试切换 tab
    console.log('\n3. Now trying to switch tabs from detail page...');
    const tabBar = page.locator('.tab-bar');

    console.log('   -> Switching to Components...');
    await tabBar.locator('a:has-text("组件")').click({ timeout: 5000 });
    await page.waitForTimeout(2000);
    console.log(`   URL: ${page.url()}`);

    console.log('   -> Switching to Overview...');
    await tabBar.locator('a:has-text("概况")').click({ timeout: 5000 });
    await page.waitForTimeout(2000);
    console.log(`   URL: ${page.url()}`);

    console.log('   -> Switching back to Backtests...');
    await tabBar.locator('a:has-text("回测")').click({ timeout: 5000 });
    await page.waitForTimeout(2000);
    console.log(`   URL: ${page.url()}`);

    console.log('\nAll switches OK');

  } catch (e) {
    console.error(`FAIL: ${e.message.split('\n')[0]}`);
    console.log(`URL: ${page.url()}`);
    await page.screenshot({ path: '/tmp/nav-fail.png' });
  } finally {
    await page.close();
  }
})();
