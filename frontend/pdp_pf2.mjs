import { chromium } from 'playwright';

const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages()[0];
await page.goto('http://192.168.50.12:5173/#/portfolios/1ff27ed721994e749148d2f43df957e1', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

const grab = () => page.evaluate(() => {
  const vis = s => [...document.querySelectorAll(s)].filter(e => e.offsetParent !== null);
  const txt = el => el ? el.innerText.trim().replace(/\n+/g, ' | ').slice(0, 400) : null;
  return {
    url: location.href,
    cards: vis('[class*=card],[class*=stat]').map(e => txt(e)).filter(t => t && t.length < 200).slice(0, 8),
    tables: vis('table').map(t => ({ rows: t.querySelectorAll('tbody tr').length, head: txt(t.querySelector('thead'))?.slice(0, 160) })),
  };
});

// 只点 tabs-nav 内的 tab(避开侧边栏)
const clickTab = (label) => page.evaluate((lbl) => {
  const nav = document.querySelector('.tabs-nav, [class*=tabs-nav]');
  const t = nav ? [...nav.querySelectorAll('button,a')].find(e => e.textContent.trim() === lbl) : null;
  if (t) { t.click(); return true; } return false;
}, label);

console.log('click 回测:', await clickTab('回测'));
await page.waitForTimeout(1500);
console.log('== pf backtest tab =='); console.log(JSON.stringify(await grab()));
await page.screenshot({ path: '/tmp/pfolio_backtests.png' });

console.log('click 组件:', await clickTab('组件'));
await page.waitForTimeout(1500);
console.log('== pf components tab =='); console.log(JSON.stringify(await grab(), null, 1));
await page.screenshot({ path: '/tmp/pfolio_components.png' });

await b.close();
