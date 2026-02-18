import { chromium } from 'playwright';

const WEB_UI = 'http://192.168.50.12:5173';

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

async function check(page, route) {
  try {
    await page.goto(WEB_UI + route.path, { waitUntil: 'domcontentloaded', timeout: 10000 });
    await page.waitForTimeout(600);
    if (page.url().includes('/login')) return { status: 'redirect', note: '需登录' };

    const card = await page.locator('.ant-card').count();
    const table = await page.locator('.ant-table').count();
    const form = await page.locator('.ant-form').count();

    if (card || table || form) return { status: 'ok', note: `c:${card} t:${table} f:${form}` };
    return { status: 'empty', note: '无内容' };
  } catch (e) {
    return { status: 'error', note: e.message.substring(0, 25) };
  }
}

(async () => {
  console.log('🚀 全页面扫描\n');
  const browser = await chromium.connectOverCDP('http://192.168.50.10:9222');
  const page = browser.contexts()[0].pages()[0];

  const results = [];
  const icons = { ok: '✅', empty: '⚠️', error: '❌', redirect: '🔐' };

  for (const r of ROUTES) {
    const res = await check(page, r);
    results.push({ ...r, ...res });
    console.log(`${icons[res.status]} ${r.name.padEnd(10)} | ${r.path.padEnd(25)} | ${res.note}`);
  }

  console.log('\n📊 统计:');
  console.log('  ✅ 正常:', results.filter(r => r.status === 'ok').length);
  console.log('  ⚠️  空白:', results.filter(r => r.status === 'empty').length);
  console.log('  ❌ 错误:', results.filter(r => r.status === 'error').length);
  console.log('  📄 总计:', results.length);

  const issues = results.filter(r => r.status !== 'ok');
  if (issues.length) {
    console.log('\n⚠️  需关注:');
    issues.forEach(r => console.log(`   - ${r.name} (${r.path}) ${r.note}`));
  }
  console.log('\n✨ 完成');
})();
