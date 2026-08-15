/**
 * system store 导出面回归：start/stop worker 假能力已删（后端无端点，点击必 404）。
 * 此测试防止未来误加回。页面定位收口为纯监控（spec 2026-08-15）。
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useSystemStore } from '../system'

describe('useSystemStore 导出面（纯监控化）', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('不再暴露 startWorker/stopWorker（后端端点不存在）', () => {
    const store = useSystemStore()
    expect((store as any).startWorker).toBeUndefined()
    expect((store as any).stopWorker).toBeUndefined()
  })

  it('监控核心能力保留：fetchWorkers/fetchStatus/enableAutoRefresh', () => {
    const store = useSystemStore()
    expect(typeof store.fetchWorkers).toBe('function')
    expect(typeof store.fetchStatus).toBe('function')
    expect(typeof store.enableAutoRefresh).toBe('function')
  })
})
