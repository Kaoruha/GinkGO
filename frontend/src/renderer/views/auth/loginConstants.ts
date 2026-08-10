/**
 * 登录页固定内容数据(阶段 5 从 Login.vue 抽取)。
 * 纯数据,与动画逻辑分离;视觉口径见 Login.vue <style> 注释(ADR-045 §5)。
 */

/** BIOS 开机自检序列(打字机逐行输出) */
export const bootSequence: string[] = [
  '> BIOS v2.0.11 initialized',
  '> Memory check: 65536KB OK',
  '> Loading kernel modules...',
  '> Initializing neural network...',
  '> Connecting to market data feed...',
  '> Loading quantitative models...',
  '> System ready.',
]

/** 跑马灯模拟股票报价 */
export const stocks = [
  { code: 'AAPL', price: 185.92, change: 2.34 },
  { code: 'GOOGL', price: 141.80, change: -0.89 },
  { code: 'MSFT', price: 378.91, change: 1.56 },
  { code: 'TSLA', price: 248.50, change: -2.15 },
  { code: 'NVDA', price: 495.22, change: 3.78 },
  { code: 'AMZN', price: 178.25, change: 0.67 },
  { code: 'META', price: 505.95, change: 1.23 },
  { code: 'BRK.B', price: 408.32, change: -0.45 },
  { code: 'JPM', price: 198.45, change: 0.89 },
  { code: 'V', price: 279.30, change: 1.12 },
  { code: '000001.SZ', price: 12.85, change: 0.78 },
  { code: '600519.SH', price: 1756.00, change: -1.23 },
  { code: '000858.SZ', price: 168.50, change: 2.45 },
  { code: '601318.SH', price: 45.32, change: -0.56 },
]

/** 终端打字机轮播文案 */
export const terminalMessages: string[] = [
  'Loading market data...',
  'Analyzing price patterns...',
  'Computing alpha signals...',
  'Backtesting strategy...',
  'Optimizing portfolio allocation...',
  'Monitoring real-time positions...',
  'Calculating risk metrics...',
  'Fetching tick data...',
]
