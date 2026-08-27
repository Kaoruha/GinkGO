/**
 * 回测展示格式化与着色(BacktestTab 专有)。
 *
 * 阶段 4 抽取:这些函数均为纯函数(无 reactive 依赖),原先散落在 BacktestTab.vue
 * script 区。归集于此便于复用与单测。通用格式化(percent/money/number)见 utils/format。
 *
 * 注:方向映射有两套——directionLabel/directionColor 用于 signal/order/position 表格列
 * (数字键),dirLabel 用于日志列(字符串键,含 LONG/SHORT 直通)。
 */
import dayjs from 'dayjs'

// ========== 日期格式化 ==========

export const formatShortDate = (d?: string | null) => {
  if (!d) return '-'
  return dayjs(d).format('YYYY-MM-DD HH:mm')
}

export const formatLogTime = (ts?: string | null) => {
  if (!ts) return '-'
  const d = dayjs(ts)
  if (d.year() < 2000) return '-'
  return d.format('YYYY-MM-DD HH:mm:ss')
}

// ========== 数值格式化 ==========

export const formatDecimal = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '-' : n.toFixed(2)
}

// ========== 着色(返回 hsl(var) 内联 style 值)==========

export const getPnLColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  // ADR-045 §2 西式涨绿跌红(原中式 #cf1322=红涨/#3f8600=绿跌 → 反转)
  // 0 为中性(无盈亏)——绿色会误导,尤其失败任务指标落 0 的场景
  return isNaN(n) || n === 0 ? 'hsl(var(--muted-foreground))' : n > 0 ? 'hsl(var(--success))' : 'hsl(var(--error))'
}

export const getSharpeColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? 'hsl(var(--muted-foreground))' : n >= 1 ? 'hsl(var(--success))' : 'hsl(var(--warning))'
}

export const getDrawdownColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? 'hsl(var(--muted-foreground))' : n <= 0.1 ? 'hsl(var(--success))' : 'hsl(var(--error))'
}

// ========== 方向(表格列:signal/order/position)==========

const DIR_MAP: Record<number, string> = { 1: '买入', 2: '卖出' }
export const directionLabel = (d: number | string) => DIR_MAP[Number(d)] || String(d)
export const directionColor = (d: number | string) => (Number(d) === 1 ? 'text-green' : 'text-red')

// ========== 方向(日志列:支持字符串直通)==========

const DIR_LABEL_MAP: Record<string, string> = { '1': 'LONG', '2': 'SHORT', LONG: 'LONG', SHORT: 'SHORT' }
export const dirLabel = (d: string | number | null) => DIR_LABEL_MAP[String(d)] || String(d ?? '')

// ========== 分析器指标(按名分流)==========

export const fmtAnalyzer = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return '-'
  const nl = name.toLowerCase()
  if (['max_drawdown', 'win_rate', 'trade_win_rate', 'hold_pct', 'annual_return'].some(a => nl.includes(a))) return `${(value * 100).toFixed(2)}%`
  if (['sharpe', 'sortino', 'calmar'].some(a => nl.includes(a))) return value.toFixed(3)
  if (['signal_count', 'trade_count', 'order_count', 'max_consecutive_losses'].some(a => nl.includes(a))) return Math.round(value).toString()
  if (['net_value', 'profit', 'pnl', 'capital'].some(a => nl.includes(a))) return `¥${value.toFixed(2)}`
  if (['profit_factor', 'avg_win_loss_ratio'].some(a => nl.includes(a))) return value.toFixed(2)
  if (nl.includes('avg_holding_period')) return value.toFixed(1) + ' 天'
  return value.toFixed(4)
}

export const getAnalyzerColor = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return 'hsl(var(--muted-foreground))'
  const nl = name.toLowerCase()
  if (nl.includes('drawdown')) return value <= 0.1 ? 'hsl(var(--success))' : value <= 0.2 ? 'hsl(var(--warning))' : 'hsl(var(--error))'
  if (nl.includes('return') || nl.includes('win_rate')) return value >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))'
  if (nl.includes('sharpe') || nl.includes('sortino')) return value >= 1 ? 'hsl(var(--success))' : value >= 0 ? 'hsl(var(--warning))' : 'hsl(var(--error))'
  if (nl.includes('profit') || nl.includes('pnl')) return value >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))'
  return 'hsl(var(--muted-foreground))'
}

// ========== 日志分类(返回 style class)==========

export const levelClass = (level?: string | null) => {
  if (!level) return ''
  const l = level.toUpperCase()
  if (l === 'ERROR' || l === 'CRITICAL') return 'level-error'
  if (l === 'WARNING') return 'level-warning'
  if (l === 'INFO') return 'level-info'
  if (l === 'DEBUG') return 'level-debug'
  return ''
}

export const eventClass = (et?: string | null) => {
  if (!et) return ''
  const e = et.toUpperCase()
  if (e === 'SIGNALGENERATION' || e === 'STRATEGYSIGNAL') return 'event-signal'
  if (e.startsWith('ORDER')) return 'event-order'
  if (e === 'POSITIONUPDATE') return 'event-position'
  if (e === 'CAPITALUPDATE') return 'event-capital'
  if (e.startsWith('ENGINE')) return 'event-engine'
  if (e === 'PRICERECEIVED' || e === 'PRICEUPDATE') return 'event-price'
  if (e.startsWith('RISK')) return 'event-risk'
  if (e.startsWith('T1') || e === 'TIMEADVANCE') return 'event-t1'
  return ''
}
