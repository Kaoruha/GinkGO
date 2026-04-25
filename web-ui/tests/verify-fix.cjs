const { chromium } = require('playwright');

const REMOTE_BROWSER = 'http://192.168.50.10:9222';
const WEB_UI_URL = 'http://192.168.50.12:5173';
const API_URL = 'http://192.168.50.12:8000';

(async () => {
  const browser = await chromium.connectOverCDP(REMOTE_BROWSER);
  const context = browser.contexts()[0] || await browser.newContext();
  const page = await context.newPage();

  try {
    // 打开页面获取 auth token
    await page.goto(`${WEB_UI_URL}/portfolio`, { waitUntil: 'networkidle', timeout: 15000 });

    // 从 localStorage 拿 token
    const token = await page.evaluate(() => localStorage.getItem('token') || localStorage.getItem('auth_token') || '');
    console.log(`Token: ${token ? token.substring(0, 20) + '...' : 'NOT FOUND'}`);

    // 列出 localStorage keys
    const keys = await page.evaluate(() => Object.keys(localStorage));
    console.log(`localStorage keys: ${JSON.stringify(keys)}`);

    // 尝试从 cookies 拿
    const cookies = await context.cookies();
    const authCookie = cookies.find(c => c.name.includes('token') || c.name.includes('auth'));
    console.log(`Auth cookie: ${authCookie ? authCookie.name + '=' + authCookie.value.substring(0, 20) + '...' : 'NOT FOUND'}`);

    // 用 page.evaluate 调 API（浏览器内同源，可能不需要 token）
    console.log('\n--- Testing API from browser context ---');
    const portfolios = await page.evaluate(async () => {
      const res = await fetch('/api/portfolio/');
      return res.json();
    });
    console.log(`List portfolios: code=${portfolios.code}, count=${portfolios.data?.length || 0}`);

    if (portfolios.data?.length > 0) {
      // 拿第一个 portfolio 的详情
      const firstUuid = portfolios.data[0].uuid;
      const detail = await page.evaluate(async (uuid) => {
        const res = await fetch(`/api/portfolio/${uuid}`);
        return res.json();
      }, firstUuid);

      if (detail.data) {
        console.log(`\nPortfolio: ${detail.data.name}`);
        console.log(`  Selectors: ${JSON.stringify(detail.data.selectors?.map(s => ({name: s.name, config: s.config})))}`);
        console.log(`  Strategies: ${JSON.stringify(detail.data.strategies?.map(s => ({name: s.name, config: s.config})))}`);
        console.log(`  Sizers: ${JSON.stringify(detail.data.sizers?.map(s => ({name: s.name, config: s.config})))}`);
      }
    }

    // 创建新 portfolio
    console.log('\n--- Creating test portfolio ---');
    const newPortfolio = await page.evaluate(async () => {
      const res = await fetch('/api/portfolio/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: `VerifyFix_${Date.now().toString(36)}`,
          initial_cash: 100000,
          selectors: [{"component_uuid": "03696e3ae44240608bc12f1afa9ff893", "config": {"codes": "000001.SZ,000002.SZ"}}],
          sizer_uuid: "1999997be44240608bc12f1afa9ff893",
          sizer_config: {"volume": 100},
          strategies: [{"component_uuid": "93897248e44240608bc12f1afa9ff893", "config": {"buy_probability": 0.3, "sell_probability": 0.3, "signal_reason_template": "test-{direction}-{index}", "max_signals": -1}}],
          risk_managers: []
        })
      });
      return res.json();
    });

    console.log(`Create result: code=${newPortfolio.code}`);
    const newUuid = newPortfolio.data?.uuid;
    console.log(`New portfolio UUID: ${newUuid}`);

    if (newUuid) {
      // 验证存储的参数
      const verifyDetail = await page.evaluate(async (uuid) => {
        const res = await fetch(`/api/portfolio/${uuid}`);
        return res.json();
      }, newUuid);

      if (verifyDetail.data) {
        console.log(`\n=== Stored Parameter Verification ===`);
        console.log(`Name: ${verifyDetail.data.name}`);

        for (const sel of verifyDetail.data.selectors || []) {
          console.log(`Selector: ${sel.name}, config: ${JSON.stringify(sel.config)}`);
        }
        for (const strat of verifyDetail.data.strategies || []) {
          console.log(`Strategy: ${strat.name}, config: ${JSON.stringify(strat.config)}`);
        }
        for (const sz of verifyDetail.data.sizers || []) {
          console.log(`Sizer: ${sz.name}, config: ${JSON.stringify(sz.config)}`);
        }

        // 直接查数据库验证参数存储格式
        const dbCheck = await page.evaluate(async (uuid) => {
          // 通过 mapping service 的 API（如果有）或者直接检查
          const res = await fetch(`/api/portfolio/${uuid}`);
          const data = res.json();
          return data;
        }, newUuid);

        // 提交回测
        console.log('\n--- Submitting backtest ---');
        const backtestResult = await page.evaluate(async (uuid) => {
          const res = await fetch('/api/backtest/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              portfolio_uuid: uuid,
              start_date: '2025-11-01',
              end_date: '2025-11-10',
              initial_cash: 100000
            })
          });
          return res.json();
        }, newUuid);
        console.log(`Backtest result: ${JSON.stringify(backtestResult)}`);
      }
    }

  } catch (e) {
    console.error('Error:', e.message);
  } finally {
    await page.close();
  }
})();
