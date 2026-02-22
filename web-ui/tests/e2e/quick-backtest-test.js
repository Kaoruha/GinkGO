/**
 * 快速 E2E 测试 - 验证回测完整流程
 */

import { chromium } from 'playwright';

const REMOTE_BROWSER = 'http://192.168.50.10:9222';
const WEB_UI_URL = 'http://192.168.50.12:5173';

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function test() {
  console.log('=== 连接浏览器 ===');
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER);
  const context = browser.contexts()[0];
  const page = context.pages()[0];

  // Step 1: 访问回测列表
  console.log('\n=== 1. 访问回测列表 ===');
  await page.goto(WEB_UI_URL + '/stage1/backtest');
  await page.waitForLoadState('networkidle');
  await sleep(3000);

  // 获取当前任务数
  let rows = await page.$$('.ant-table-tbody tr');
  console.log(`当前任务数: ${rows.length}`);

  // 找一个已完成的任务来验证数据
  let targetTask = null;
  for (const row of rows) {
    const statusCell = await row.$('td:nth-child(2)');
    if (statusCell) {
      const status = await statusCell.textContent();
      if (status && status.includes('完成')) {
        targetTask = row;
        break;
      }
    }
  }

  if (!targetTask && rows.length > 0) {
    // 如果没有已完成的，尝试运行第一个任务
    console.log('\n=== 2. 没有已完成任务，尝试运行第一个 ===');
    const firstRow = rows[0];
    const runBtn = await firstRow.$('button:has-text("运行")');
    if (runBtn) {
      await runBtn.click();
      console.log('>>> 点击了运行按钮 <<<');
      await sleep(5000);

      // 等待完成（最多2分钟）
      for (let i = 0; i < 24; i++) {
        await sleep(5000);
        await page.reload();
        await page.waitForLoadState('networkidle');
        await sleep(1000);

        rows = await page.$$('.ant-table-tbody tr');
        if (rows.length > 0) {
          const statusCell = await rows[0].$('td:nth-child(2)');
          const status = statusCell ? await statusCell.textContent() : '';
          console.log(`  [${i+1}/24] 状态: ${status?.trim()}`);
          if (status?.includes('完成')) {
            targetTask = rows[0];
            break;
          }
        }
      }
    }
  }

  if (!targetTask) {
    console.log('没有可用的回测任务');
    return;
  }

  // Step 3: 进入详情页
  console.log('\n=== 3. 进入详情页 ===');
  const detailBtn = await targetTask.$('button:has-text("详情")');
  if (detailBtn) {
    await detailBtn.click();
    console.log('>>> 进入详情页 <<<');
    await sleep(3000);
  } else {
    console.log('未找到详情按钮');
    return;
  }

  console.log('当前URL:', page.url());

  // Step 4: 点击交易记录标签
  const tradesTab = await page.$('.ant-tabs-tab:has-text("交易记录")');
  if (tradesTab) {
    await tradesTab.click();
    console.log('>>> 点击交易记录标签 <<<');
    await sleep(2000);
  }

  // Step 5: 检查数据
  console.log('\n=== 4. 检查数据 ===');

  const results = { signal: 0, order: 0, position: 0 };

  // 检查信号
  const signalsTab = await page.$('.trade-records-panel .ant-tabs-tab:has-text("信号")');
  if (signalsTab) {
    await signalsTab.click();
    await sleep(1500);
    const signalRows = await page.$$('.trade-records-panel .ant-tabs-tabpane-active .ant-table-tbody tr');
    results.signal = signalRows.length;
    console.log(`信号: ${results.signal} 条`);
  }

  // 检查订单
  const ordersTab = await page.$('.trade-records-panel .ant-tabs-tab:has-text("订单")');
  if (ordersTab) {
    await ordersTab.click();
    await sleep(1500);
    const orderRows = await page.$$('.trade-records-panel .ant-tabs-tabpane-active .ant-table-tbody tr');
    results.order = orderRows.length;
    console.log(`订单: ${results.order} 条`);
  }

  // 检查持仓
  const positionsTab = await page.$('.trade-records-panel .ant-tabs-tab:has-text("持仓")');
  if (positionsTab) {
    await positionsTab.click();
    await sleep(1500);
    const positionRows = await page.$$('.trade-records-panel .ant-tabs-tabpane-active .ant-table-tbody tr');
    results.position = positionRows.length;
    console.log(`持仓: ${results.position} 条`);
  }

  // 输出结果
  console.log('\n========== 测试结果 ==========');
  console.log(`信号: ${results.signal} 条`);
  console.log(`订单: ${results.order} 条`);
  console.log(`持仓: ${results.position} 条`);
  console.log(results.order > 0 ? '✅ 订单持久化正常' : '❌ 订单为空');
  console.log(results.position > 0 ? '✅ 持仓持久化正常' : '❌ 持仓为空');
  console.log('==============================');

  console.log('\n>>> 测试完成，请在浏览器上确认结果 <<<');
}

test().catch(e => { console.error(e); process.exit(1); });
