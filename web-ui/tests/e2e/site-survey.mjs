/**
 * Site Survey Script - 遍历整个网站并记录各页面状态
 */

import { chromium } from 'playwright';

const REMOTE_BROWSER = process.env.REMOTE_BROWSER || 'http://192.168.50.10:9222';
const WEB_UI_URL = process.env.WEB_UI_URL || 'http://192.168.50.12:5173';

// 所有需要测试的路由
const ROUTES = [
  { path: '/login', name: '登录页' },
  { path: '/dashboard', name: '概览' },
  { path: '/portfolio', name: '组合列表' },
  { path: '/portfolio/create', name: '创建组合' },
  { path: '/stage1/backtest', name: '回测列表' },
  { path: '/stage1/backtest/create', name: '创建回测' },
  { path: '/stage1/backtest/compare', name: '回测对比' },
  { path: '/stage2/walkforward', name: '走步验证' },
  { path: '/stage2/montecarlo', name: '蒙特卡洛' },
  { path: '/stage2/sensitivity', name: '敏感性分析' },
  { path: '/stage3/paper', name: '模拟交易' },
  { path: '/stage3/paper/config', name: '模拟配置' },
  { path: '/stage3/paper/orders', name: '模拟订单' },
  { path: '/stage4/live', name: '实盘监控' },
  { path: '/stage4/live/orders', name: '实盘订单' },
  { path: '/stage4/live/positions', name: '实盘持仓' },
  { path: '/research/ic', name: 'IC分析' },
  { path: '/research/layering', name: '因子分层' },
  { path: '/research/orthogonal', name: '因子正交' },
  { path: '/research/comparison', name: '因子比较' },
  { path: '/research/decay', name: '因子衰减' },
  { path: '/optimization/grid', name: '网格搜索' },
  { path: '/optimization/genetic', name: '遗传算法' },
  { path: '/optimization/bayesian', name: '贝叶斯优化' },
  { path: '/components/strategies', name: '策略组件' },
  { path: '/components/risks', name: '风控组件' },
  { path: '/components/sizers', name: '仓位组件' },
  { path: '/data', name: '数据概览' },
  { path: '/data/stocks', name: '股票信息' },
  { path: '/data/bars', name: 'K线数据' },
  { path: '/data/sync', name: '数据同步' },
  { path: '/system/status', name: '系统状态' },
  { path: '/system/workers', name: 'Worker管理' },
  { path: '/system/users', name: '用户管理' },
  { path: '/system/groups', name: '用户组管理' },
  { path: '/system/notifications', name: '通知管理' },
  { path: '/system/alerts', name: '告警中心' },
];

async function login(page) {
  console.log('🔐 登录中...');
  await page.goto(`${WEB_UI_URL}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[placeholder="enter username"]', 'admin');
  await page.fill('input[placeholder="enter password"]', 'admin123');
  await page.click('button:has-text("EXECUTE")');
  await page.waitForURL('**/dashboard**', { timeout: 10000 }).catch(() => {});
  await page.waitForTimeout(1000);
  console.log('✅ 登录完成\n');
}

async function checkPage(page, route) {
  const result = { path: route.path, name: route.name, status: 'unknown', note: '' };
  try {
    await page.goto(`${WEB_UI_URL}${route.path}`, { waitUntil: 'networkidle', timeout: 15000 });
    await page.waitForTimeout(800);

    // 检查是否重定向到登录
    if (page.url().includes('/login')) {
      result.status = 'redirect';
      result.note = '需登录';
      return result;
    }

    // 检查404
    const bodyText = await page.locator('body').innerText();
    if (bodyText.includes('404') || bodyText.includes('页面未找到')) {
      result.status = '404';
      result.note = '页面不存在';
      return result;
    }

    // 检查内容
    const hasCard = await page.locator('.ant-card').count();
    const hasTable = await page.locator('.ant-table').count();
    const hasForm = await page.locator('.ant-form').count();
    const hasContent = await page.locator('.ant-layout-content').count();

    if (hasCard || hasTable || hasForm || hasContent) {
      result.status = 'ok';
      result.note = `card:${hasCard} table:${hasTable} form:${hasForm}`;
    } else {
      result.status = 'empty';
      result.note = '无可见内容';
    }

  } catch (e) {
    result.status = 'error';
    result.note = e.message.substring(0, 40);
  }
  return result;
}

async function main() {
  console.log('🚀 Ginkgo Web UI 状态扫描\n');

  const browser = await chromium.connectOverCDP(REMOTE_BROWSER);
  const context = browser.contexts()[0] || await browser.newContext();
  const page = context.pages()[0] || await context.newPage();

  await login(page);

  console.log('状态  | 页面         | 路径');
  console.log('-'.repeat(60));

  const results = [];
  for (const route of ROUTES) {
    const r = await checkPage(page, route);
    results.push(r);
    const icon = { ok: '✅', empty: '⚠️', error: '❌', '404': '🔍', redirect: '🔐' }[r.status] || '❓';
    console.log(`${icon} ${r.status.padEnd(6)} | ${r.name.padEnd(12)} | ${r.path.padEnd(25)} | ${r.note}`);
  }

  console.log('\n📊 统计:');
  console.log(`  ✅ 正常: ${results.filter(r => r.status === 'ok').length}`);
  console.log(`  ⚠️  空白: ${results.filter(r => r.status === 'empty').length}`);
  console.log(`  ❌ 错误: ${results.filter(r => r.status === 'error').length}`);
  console.log(`  📄 总计: ${results.length}`);

  console.log('\n✨ 完成');
}

main().catch(e => { console.error('❌', e.message); process.exit(1); });
