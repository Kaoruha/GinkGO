/**
 * format.ts 单元测试
 */
import { describe, it, expect } from 'vitest'
import {
  formatDate,
  formatNumber,
  formatPercent,
  formatDuration,
  formatDateTime,
  formatMoney,
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
