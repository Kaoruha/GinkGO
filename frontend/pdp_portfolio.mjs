import { chromium } from 'playwright';

const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages()[0];

// 从回测详情跳组合详情(点击头部组合链接)
await page.goto('http://192.168.50.12:5173/#/backtests/c47ab00838634eb5aab9ee55357c52c2?tab=overview', { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);
const pid = await page.evaluate(async () => {
  const el = [...document.querySelectorAll('a,button,span')].find(e => /present_portfolio/.test(e.textContent || '') && e.offsetParent);
  if (el) { el.click(); await new Promise(r => setTimeout(r, 800)); return location.hash; }
  return 'NOT_FOUND';
});
console.log('nav:', pid);
await page.waitForTimeout(1500);

const grab = () => page.evaluate(() => {
  const vis = s => [...document.querySelectorAll(s)].filter(e => e.offsetParent !== null);
  const txt = el => el ? el.innerText.trim().replace(/\n+/g, ' | ').slice(0, 300) : null;
  return {
    url: location.href,
    title: txt(document.querySelector('h1,h2,.page-title')),
    meta: txt(vis('[class*=meta]')[0]),
    tabs: vis('button,a').map(e => e.innerText.trim()).filter(t => t && t.length <= 4 && /概览|回测|验证|组件|运行|分析/.test(t)),
    cards: vis('[class*=card], [class*=stat]').map(e => txt(e)).filter(t => t && t.length < 150).slice(0, 10),
    bodyH: document.body.scrollHeight,
  };
});
console.log(JSON.stringify(await grab(), null, 1));
await page.screenshot({ path: '/tmp/pfolio_overview.png' });

// 回测 tab
await page.evaluate(() => { const t = [...document.querySelectorAll('button,a')].find(e => e.textContent.trim() === '回测' && e.offsetParent); t?.click(); });
await page.waitForTimeout(1500);
console.log('== backtest tab =='); console.log(JSON.stringify(await grab(), null, 1));
await page.screenshot({ path: '/tmp/pfolio_backtests.png' });

// 组件 tab
await page.evaluate(() => { const t = [...document.querySelectorAll('button,a')].find(e => e.textContent.trim() === '组件' && e.offsetParent); t?.click(); });
await page.waitForTimeout(1200);
console.log('== components tab =='); console.log(JSON.stringify(await grab(), null, 1));
await page.screenshot({ path: '/tmp/pfolio_components.png' });

await b.close();
