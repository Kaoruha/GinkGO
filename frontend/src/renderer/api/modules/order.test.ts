/**
 * order.ts 双重解包修复测试 (#5544)
 *
 * 根因：request.ts 响应拦截器已 `return data`（=后端 body），
 *   request.get() 返回的已经是 body 本身 {code, data, message}。
 *   order.ts 4 方法却 `return response.data` 再解一层，
 *   实际返回的是 body.data（订单/持仓数组），与签名 {data, total} 不符，
 *   调用方解构 {data, total} 拿到 undefined。
 *
 * 修复：移除多余 .data，返回 body 本身（与 data.ts 正确模式一致）。
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

describe('order.ts 双重解包修复 (#5544)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('orderApi.list 返回 body 本身（含 code/data/message），而非订单数组', async () => {
    const mockOrders = [{ uuid: 'o1', code: '000001.SZ' }]
    // 后端 ok(data=orders) 的 body 形态
    const mockBody = { code: 0, data: mockOrders, message: 'Paper orders retrieved successfully' }
    vi.mocked(request.get).mockResolvedValue(mockBody)

    const result = await orderApi.list()

    // result 应是 body 本身（拦截器已解包），不再是数组
    expect(result).toBe(mockBody)
    expect(result.code).toBe(0)
    expect(result.data).toBe(mockOrders)
    // 双重解包 bug 下 result 会变成 mockOrders 数组，这里守住
    expect(Array.isArray(result)).toBe(false)
  })

  it('orderApi.get 返回 body 本身（含 data=单订单），而非订单对象', async () => {
    const mockOrder = { uuid: 'o1', code: '000001.SZ', status: 1 }
    const mockBody = { code: 0, data: mockOrder, message: 'ok' }
    vi.mocked(request.get).mockResolvedValue(mockBody)

    const result = await orderApi.get('o1')

    expect(result).toBe(mockBody)
    expect(result.code).toBe(0)
    expect(result.data).toBe(mockOrder)
  })

  it('positionApi.list 返回 body 本身（含 data=持仓数组）', async () => {
    const mockPositions = [{ uuid: 'p1', code: '000001.SZ', volume: 100 }]
    const mockBody = { code: 0, data: mockPositions, message: 'Paper positions retrieved successfully' }
    vi.mocked(request.get).mockResolvedValue(mockBody)

    const result = await positionApi.list()

    expect(result).toBe(mockBody)
    expect(result.code).toBe(0)
    expect(result.data).toBe(mockPositions)
    expect(Array.isArray(result)).toBe(false)
  })

  it('positionApi.get 返回 body 本身（含 data=单持仓）', async () => {
    const mockPosition = { uuid: 'p1', code: '000001.SZ', volume: 100 }
    const mockBody = { code: 0, data: mockPosition, message: 'ok' }
    vi.mocked(request.get).mockResolvedValue(mockBody)

    const result = await positionApi.get('p1')

    expect(result).toBe(mockBody)
    expect(result.code).toBe(0)
    expect(result.data).toBe(mockPosition)
  })

  it('list 请求带 params 参数透传给 request.get', async () => {
    const mockBody = { code: 0, data: [], message: 'ok' }
    vi.mocked(request.get).mockResolvedValue(mockBody)

    await orderApi.list({ portfolio_id: 'pf1', status: 'filled' })

    expect(request.get).toHaveBeenCalledWith('/api/v1/orders', {
      params: { portfolio_id: 'pf1', status: 'filled' },
    })
  })
})
