// #6071: DataSync.vue sendCommand 不再硬编码 success:true，
// 改为读后端 ok() 响应里的 failed 计数。本测试锁定提取逻辑。
//
// 真实形状：dataApi.sync() 经 request.ts 响应拦截器 `return response.data`
// 已剥掉 axios 外层，返回后端 ok() body 本身。
import { describe, it, expect } from 'vitest'
import { extractSyncFailed } from './syncResult'

describe('extractSyncFailed', () => {
  it('body.data.failed>0 → 返回该数（部分失败）', () => {
    const body = { code: 0, data: { type: 'bars', failed: 2, total: 3, success_count: 1 } }
    expect(extractSyncFailed(body)).toBe(2)
  })

  it('failed=0 → 0（全部成功，前端显示成功）', () => {
    const body = { code: 0, data: { type: 'bars', failed: 0, total: 2, success_count: 2 } }
    expect(extractSyncFailed(body)).toBe(0)
  })

  it('无 failed 字段（旧后端/非 bars-ticks 分支）→ 0（向后兼容，不误报失败）', () => {
    const body = { code: 0, data: { type: 'stockinfo' } }
    expect(extractSyncFailed(body)).toBe(0)
  })

  it('data 缺失（异常响应）→ 0 不抛错', () => {
    expect(extractSyncFailed({ code: 0 })).toBe(0)
    expect(extractSyncFailed(null)).toBe(0)
    expect(extractSyncFailed(undefined)).toBe(0)
  })
})
