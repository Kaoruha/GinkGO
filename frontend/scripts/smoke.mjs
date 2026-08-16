// Ginkgo 前端 smoke：登录 → 巡检关键页面 → 收集 console 错误 + 截图
// 用法: node /tmp/ginkgo-smoke.mjs [页面路径,页面路径,...]  (默认巡检内置清单)
import { chromium } from 'playwright'
import fs from 'node:fs'

const BASE = process.env.SMOKE_BASE || 'http://localhost:5173'
const SHOT_DIR = process.env.SMOKE_SHOTS || '/tmp/ginkgo-shots'
const DEFAULT_PAGES = [
  '/dashboard', '/portfolios', '/backtests', '/components/strategy',
  '/admin/users', '/admin/api-keys', '/admin/workers', '/admin/system',
  '/data/stocks', '/data/bars', '/data/ticks', '/live/market',
]
const pages = process.argv[2] ? process.argv[2].split(',') : DEFAULT_PAGES

fs.mkdirSync(SHOT_DIR, { recursive: true })
const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
const errors = []
page.on('console', m => { if (m.type() === 'error') errors.push(`[console] ${m.text().slice(0, 200)}`) })
page.on('pageerror', e => errors.push(`[pageerror] ${String(e).slice(0, 200)}`))

// 登录(hash 路由,登录页占位符为英文)
await page.goto(`${BASE}/`, { waitUntil: 'networkidle' })
await page.getByPlaceholder(/username/i).fill('admin')
await page.getByPlaceholder(/password/i).fill('admin123')
await page.getByRole('button', { name: /EXECUTE|登录|submit/i }).click()
await page.waitForURL(u => !String(u).includes('/login'), { timeout: 15000 }).catch(() => {})
const loggedIn = !page.url().includes('/login')
console.log(`login: ${loggedIn ? 'OK' : 'FAIL (' + page.url() + ')'}`)
if (!loggedIn) { console.log(errors.join('\n')); process.exit(1) }

const results = []
for (const p of pages) {
  const errBefore = errors.length
  let status = 'OK'
  try {
    await page.goto(`${BASE}/#${p}`, { waitUntil: 'networkidle', timeout: 30000 })
    await page.waitForTimeout(800)
    const shot = `${SHOT_DIR}/${p.replace(/\//g, '_')}.png`
    await page.screenshot({ path: shot, fullPage: false })
  } catch (e) {
    status = `NAV-FAIL ${String(e).slice(0, 80)}`
  }
  const newErr = errors.slice(errBefore)
  if (newErr.length) status += ` (+${newErr.length} console errors)`
  results.push({ p, status, newErr })
}
for (const r of results) {
  console.log(`${r.status.padEnd(20)} ${r.p}`)
  r.newErr.slice(0, 3).forEach(e => console.log(`    ${e}`))
}
const bad = results.filter(r => !r.status.startsWith('OK'))
console.log(`\n${results.length - bad.length}/${results.length} pages clean, ${errors.length} total console errors`)
await browser.close()
process.exit(bad.length ? 1 : 0)
