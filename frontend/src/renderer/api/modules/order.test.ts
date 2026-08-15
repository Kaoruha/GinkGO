/**
 * order.ts 透传测试（拦截器深模块化后）
 *
 * 设计：request.ts 响应拦截器已把信封 {code,data,message} 解包为业务 payload，
 *   code!==0 转 reject，分页端点（data 数组 + meta.total）重组为 PaginatedData。
 *   order.ts 只透传 request.get() 返回值，不再做 .data 二次解包。
 *   实盘 order/position 是裸数组（无分页 meta），故 order.list→Promise<Order[]>。
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('../request', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

import request from '../request'
import { orderApi, positionApi } from './order'

describe('order.ts 透传拦截器 payload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('orderApi.list 透传 request.get 返回的订单数组（拦截器已解包）', async () => {
    const mockOrders = [{ uuid: 'o1', code: '000001.SZ' }]
    // 拦截器解包后，request.get 直接返回业务 payload（订单数组）
    vi.mocked(request.get).mockResolvedValue(mockOrders)

    const result = await orderApi.list()

    expect(result).toBe(mockOrders)
    expect(Array.isArray(result)).toBe(true)
  })

  it('orderApi.get 透传单订单', async () => {
    const mockOrder = { uuid: 'o1', code: '000001.SZ', status: 1 }
    vi.mocked(request.get).mockResolvedValue(mockOrder)

    const result = await orderApi.get('o1')

    expect(result).toBe(mockOrder)
  })

  it('positionApi.list 透传持仓数组', async () => {
    const mockPositions = [{ uuid: 'p1', code: '000001.SZ', volume: 100 }]
    vi.mocked(request.get).mockResolvedValue(mockPositions)

    const result = await positionApi.list()

    expect(result).toBe(mockPositions)
    expect(Array.isArray(result)).toBe(true)
  })

  it('positionApi.get 透传单持仓', async () => {
    const mockPosition = { uuid: 'p1', code: '000001.SZ', volume: 100 }
    vi.mocked(request.get).mockResolvedValue(mockPosition)

    const result = await positionApi.get('p1')

    expect(result).toBe(mockPosition)
  })

  it('list 请求带 params 参数透传给 request.get', async () => {
    vi.mocked(request.get).mockResolvedValue([])

    await orderApi.list({ portfolio_id: 'pf1', status: 'filled' })

    expect(request.get).toHaveBeenCalledWith('/api/v1/orders', {
      params: { portfolio_id: 'pf1', status: 'filled' },
    })
  })
})
