/**
 * useStatusFormat composable 单元测试
 */
import { describe, it, expect } from 'vitest'
import {
  useStatusFormat,
  useBacktestStatus,
  usePortfolioMode,
  usePortfolioState,
  BACKTEST_STATUS_CONFIG,
  PORTFOLIO_MODE_CONFIG,
  PORTFOLIO_STATE_CONFIG,
} from './useStatusFormat'

describe('useStatusFormat', () => {
  it('应返回正确的颜色', () => {
    const config = {
      active: { tagClass: 'tag-green', label: '激活' },
      inactive: { tagClass: 'tag-default', label: '未激活' },
    } as Record<string, import('./useStatusFormat').StatusConfig>
    const { getTagClass } = useStatusFormat(config)

    expect(getTagClass('active')).toBe('tag-green')
    expect(getTagClass('inactive')).toBe('tag-default')
  })

  it('应返回正确的标签', () => {
    const config = {
      active: { tagClass: 'tag-green', label: '激活' },
      inactive: { tagClass: 'tag-default', label: '未激活' },
    } as Record<string, import('./useStatusFormat').StatusConfig>
    const { getLabel } = useStatusFormat(config)

    expect(getLabel('active')).toBe('激活')
    expect(getLabel('inactive')).toBe('未激活')
  })

  it('未知状态应返回默认值', () => {
    const config = {
      active: { tagClass: 'tag-green', label: '激活' },
    } as Record<string, import('./useStatusFormat').StatusConfig>
    const { getTagClass, getLabel } = useStatusFormat(config)

    expect(getTagClass('unknown' as any)).toBe('tag-gray')
    expect(getLabel('unknown' as any)).toBe('unknown')
  })
})

describe('useBacktestStatus', () => {
  it('应返回正确的回测状态颜色', () => {
    const { getTagClass } = useBacktestStatus()

    expect(getTagClass('created')).toBe('tag-gray')
    expect(getTagClass('pending')).toBe('tag-orange')
    expect(getTagClass('running')).toBe('tag-blue')
    expect(getTagClass('completed')).toBe('tag-green')
    expect(getTagClass('failed')).toBe('tag-red')
  })

  it('应返回正确的回测状态标签', () => {
    const { getLabel } = useBacktestStatus()

    expect(getLabel('created')).toBe('待启动')
    expect(getLabel('pending')).toBe('等待中')
    expect(getLabel('running')).toBe('运行中')
    expect(getLabel('completed')).toBe('已完成')
    expect(getLabel('failed')).toBe('失败')
    expect(getLabel('stopped')).toBe('已停止')
  })
})

describe('usePortfolioMode', () => {
  it('应返回正确的模式颜色', () => {
    const { getTagClass } = usePortfolioMode()

    expect(getTagClass(0)).toBe('tag-blue')
    expect(getTagClass(1)).toBe('tag-orange')
    expect(getTagClass(2)).toBe('tag-red')
  })

  it('应返回正确的模式标签', () => {
    const { getLabel } = usePortfolioMode()

    expect(getLabel(0)).toBe('回测')
    expect(getLabel(1)).toBe('模拟')
    expect(getLabel(2)).toBe('实盘')
  })

  it('未知模式应返回默认值', () => {
    const { getTagClass, getLabel } = usePortfolioMode()

    expect(getTagClass(99)).toBe('tag-gray')
    expect(getLabel(99)).toBe('未知')
  })
})

describe('usePortfolioState', () => {
  it('应返回正确的状态颜色', () => {
    const { getTagClass } = usePortfolioState()

    expect(getTagClass(0)).toBe('tag-gray')
    expect(getTagClass(1)).toBe('tag-green')
    expect(getTagClass(2)).toBe('tag-blue')
    expect(getTagClass(3)).toBe('tag-red')
  })

  it('应返回正确的状态标签', () => {
    const { getLabel } = usePortfolioState()

    expect(getLabel(0)).toBe('已停止')
    expect(getLabel(1)).toBe('运行中')
    expect(getLabel(2)).toBe('已完成')
    expect(getLabel(3)).toBe('错误')
  })
})

describe('状态配置导出', () => {
  it('BACKTEST_STATUS_CONFIG 应包含所有状态', () => {
    expect(BACKTEST_STATUS_CONFIG.created).toBeDefined()
    expect(BACKTEST_STATUS_CONFIG.pending).toBeDefined()
    expect(BACKTEST_STATUS_CONFIG.running).toBeDefined()
    expect(BACKTEST_STATUS_CONFIG.completed).toBeDefined()
    expect(BACKTEST_STATUS_CONFIG.failed).toBeDefined()
    expect(BACKTEST_STATUS_CONFIG.stopped).toBeDefined()
  })

  it('PORTFOLIO_MODE_CONFIG 应包含所有模式', () => {
    expect(PORTFOLIO_MODE_CONFIG[0]).toBeDefined()
    expect(PORTFOLIO_MODE_CONFIG[1]).toBeDefined()
    expect(PORTFOLIO_MODE_CONFIG[2]).toBeDefined()
  })

  it('PORTFOLIO_STATE_CONFIG 应包含所有状态', () => {
    expect(PORTFOLIO_STATE_CONFIG[0]).toBeDefined()
    expect(PORTFOLIO_STATE_CONFIG[1]).toBeDefined()
    expect(PORTFOLIO_STATE_CONFIG[2]).toBeDefined()
    expect(PORTFOLIO_STATE_CONFIG[3]).toBeDefined()
  })
})
