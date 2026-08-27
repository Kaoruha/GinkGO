/**
 * format.ts 单元测试
 */
import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatDecimal,
  formatNumber,
  formatPercent,
  formatDuration,
  formatDateTime,
  formatRelativeTime,
  formatMoney,
  heartbeatStaleLevel,
} from './format'

describe('formatDate', () => {
  it('应格式化有效日期', () => {
    const date = new Date('2024-03-15T14:30:00')
    expect(formatDate(date)).toBe('2024-03-15 14:30')
  })

  it('应处理字符串日期', () => {
    expect(formatDate('2024-03-15T14:30:00')).toBe('2024-03-15 14:30')
  })

  it('空值应返回空字符串', () => {
    expect(formatDate(null)).toBe('')
    expect(formatDate(undefined)).toBe('')
    expect(formatDate('')).toBe('')
  })

  it('无效日期应返回空字符串', () => {
    expect(formatDate('invalid')).toBe('')
  })
})

describe('formatNumber', () => {
  it('应添加千分位', () => {
    expect(formatNumber(1000)).toBe('1,000')
    expect(formatNumber(1234567)).toBe('1,234,567')
  })

  it('应处理字符串数字', () => {
    expect(formatNumber('1000')).toBe('1,000')
  })

  it('空值应返回 0', () => {
    expect(formatNumber(null)).toBe('0')
    expect(formatNumber(undefined)).toBe('0')
  })

  it('无效数字应返回 0', () => {
    expect(formatNumber('abc')).toBe('0')
  })
})

describe('formatDecimal', () => {
  it('应保留指定位数小数', () => {
    expect(formatDecimal(1.2345)).toBe('1.23')
    expect(formatDecimal(1.2345, 4)).toBe('1.2345')
    expect(formatDecimal(2, 0)).toBe('2')
  })

  it('空值与无效数字应返回 -', () => {
    expect(formatDecimal(null)).toBe('-')
    expect(formatDecimal(undefined)).toBe('-')
    expect(formatDecimal('abc')).toBe('-')
  })

  it('字符串入参应安全解析', () => {
    expect(formatDecimal('12.345')).toBe('12.35')
  })

  it('0 应正常展示而非落到 - 分支', () => {
    expect(formatDecimal(0)).toBe('0.00')
  })
})

describe('formatPercent', () => {
  it('应格式化百分比', () => {
    expect(formatPercent(0.1234)).toBe('12.34%')
    expect(formatPercent(0.5)).toBe('50.00%')
  })

  it('应支持自定义小数位数', () => {
    expect(formatPercent(0.123456, 4)).toBe('12.3456%')
  })

  it('应处理字符串输入', () => {
    expect(formatPercent('0.25')).toBe('25.00%')
  })

  it('空值应返回 -', () => {
    expect(formatPercent(null)).toBe('-')
    expect(formatPercent(undefined)).toBe('-')
  })
})

describe('formatDuration', () => {
  it('应格式化秒', () => {
    expect(formatDuration(30)).toBe('30秒')
  })

  it('应格式化分钟', () => {
    expect(formatDuration(90)).toBe('1分30秒')
    expect(formatDuration(120)).toBe('2分0秒')
  })

  it('应格式化小时', () => {
    expect(formatDuration(3661)).toBe('1时1分')
  })

  it('空值应返回 -', () => {
    expect(formatDuration(undefined)).toBe('-')
    expect(formatDuration(0)).toBe('-')
  })
})

describe('formatDateTime', () => {
  it('应格式化短日期时间', () => {
    expect(formatDateTime('2024-03-15T14:30:00')).toBe('3/15 14:30:00')
  })

  it('空值应返回 -', () => {
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('')).toBe('-')
  })

  it('无效日期应返回 -', () => {
    expect(formatDateTime('invalid')).toBe('-')
  })
})

describe('formatRelativeTime', () => {
  const now = new Date('2024-03-15T14:30:00')

  it('应格式化秒级差异', () => {
    expect(formatRelativeTime('2024-03-15T14:29:57', now)).toBe('3秒前')
  })

  it('应格式化分钟级差异', () => {
    expect(formatRelativeTime('2024-03-15T14:25:00', now)).toBe('5分钟前')
  })

  it('应格式化小时级差异', () => {
    expect(formatRelativeTime('2024-03-15T09:30:00', now)).toBe('5小时前')
  })

  it('应格式化天级差异', () => {
    expect(formatRelativeTime('2024-03-13T10:00:00', now)).toBe('2天前')
  })

  it('超过 30 天应回退为日期时间短格式', () => {
    expect(formatRelativeTime('2024-01-15T10:00:00', now)).toBe('1/15 10:00:00')
  })

  it('未来时间应回退为日期时间短格式', () => {
    expect(formatRelativeTime('2024-03-15T15:00:00', now)).toBe('3/15 15:00:00')
  })

  it('空值和无效值应返回 -', () => {
    expect(formatRelativeTime(null)).toBe('-')
    expect(formatRelativeTime(undefined)).toBe('-')
    expect(formatRelativeTime('invalid')).toBe('-')
  })
})

describe('formatMoney', () => {
  it('应格式化金额', () => {
    expect(formatMoney(1000)).toBe('¥1,000.00')
    expect(formatMoney(1234.5)).toBe('¥1,234.50')
  })

  it('应支持自定义前缀', () => {
    expect(formatMoney(1000, '$')).toBe('$1,000.00')
  })

  it('应处理字符串输入', () => {
    expect(formatMoney('1000')).toBe('¥1,000.00')
  })

  it('空值应返回 ¥0', () => {
    expect(formatMoney(null)).toBe('¥0')
    expect(formatMoney(undefined)).toBe('¥0')
  })
})

describe('heartbeatStaleLevel', () => {
  const now = new Date('2026-08-15T10:00:00')

  it('30s 内 → 0（新鲜）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:59:45', now)).toBe(0)
  })

  it('超 30s（TTL）→ 1（橙）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:59:20', now)).toBe(1)
  })

  it('超 60s（两倍 TTL）→ 2（红）', () => {
    expect(heartbeatStaleLevel('2026-08-15T09:58:50', now)).toBe(2)
  })

  it('空/非法输入 → 0（不告警）', () => {
    expect(heartbeatStaleLevel(null, now)).toBe(0)
    expect(heartbeatStaleLevel('garbage', now)).toBe(0)
  })
})
