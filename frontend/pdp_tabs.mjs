import { chromium } from 'playwright';

const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages()[0];

const shot = async (name) => page.screenshot({ path: `/tmp/${name}.png` });
const grab = () => page.evaluate(() => {
  const vis = s => [...document.querySelectorAll(s)].filter(e => e.offsetParent !== null);
  const txt = el => el ? el.innerText.trim().replace(/\n+/g, ' | ').slice(0, 400) : null;
  return {
    url: location.href,
    cards: vis('[class*=card], [class*=stat]').map(e => txt(e)).filter(t => t && t.length < 120).slice(0, 12),
    tables: vis('table').map(t => ({ rows: t.querySelectorAll('tbody tr').length, head: txt(t.querySelector('thead'))?.slice(0, 150) })),
    selects: vis('select').map(e => e.selectedOptions[0]?.textContent?.trim()),
    charts: vis('canvas, svg').length,
    bodyH: document.body.scrollHeight,
  };
});

// 概览
await page.goto('http://192.168.50.12:5173/#/backtests/c47ab00838634eb5aab9ee55357c52c2?tab=overview', { waitUntil: 'networkidle' });
await page.waitForTimeout(1800);
console.log('== overview =='); console.log(JSON.stringify(await grab()));
await shot('pdp_overview');

// 日志
await page.goto('http://192.168.50.12:5173/#/backtests/c47ab00838634eb5aab9ee55357c52c2?tab=logs', { waitUntil: 'networkidle' });
await page.waitForTimeout(1800);
console.log('== logs =='); console.log(JSON.stringify(await grab()));
await shot('pdp_logs');

await b.close();
