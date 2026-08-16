import { chromium } from 'playwright';

const b = await chromium.connectOverCDP('http://localhost:9222');
const page = b.contexts()[0].pages()[0];
await page.reload({ waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

const info = await page.evaluate(() => {
  const q = s => document.querySelector(s);
  const vis = s => [...document.querySelectorAll(s)].filter(e => e.offsetParent !== null);
  const txt = el => el ? el.innerText.trim().replace(/\n+/g, ' | ').slice(0, 250) : null;
  return {
    url: location.href,
    title: txt(q('h1,h2,.page-title')),
    meta: txt(vis('.page-meta, [class*=meta]')[0]),
    tabs: vis('button,a').map(e => e.innerText.trim()).filter(t => t && t.length <= 5 && /概览|分析|交易|日志/.test(t)),
    tables: vis('table').map(t => ({ rows: t.querySelectorAll('tbody tr').length, head: txt(t.querySelector('thead'))?.slice(0, 180) })),
    metricCount: vis('[class*=metric]').length,
    selects: vis('select').map(e => e.selectedOptions[0]?.textContent?.trim()),
    bodyH: document.body.scrollHeight,
    innerH: innerHeight,
  };
});
console.log(JSON.stringify(info, null, 1));
await page.screenshot({ path: '/tmp/pdp_trades.png' });
await b.close();
