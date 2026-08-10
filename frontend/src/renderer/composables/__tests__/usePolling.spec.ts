/**
 * usePolling 单元测试
 *
 * 策略:usePolling 内部依赖 onMounted/onUnmounted,必须在组件 setup 中调用。
 * 用 @vue/test-utils mount 一个薄包装组件,setup 内调 usePolling 并 expose start/stop。
 * vi.useFakeTimers 控制 setInterval;document.hidden 用 spyOn getter 模拟可见性。
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h } from 'vue'
import { mount } from '@vue/test-utils'
import { usePolling } from '../usePolling'

const mountWithPolling = (
  fn: () => void,
  interval: number,
  options: { immediate?: boolean; pauseWhenHidden?: boolean } = {},
) =>
  mount(
    defineComponent({
      setup() {
        const polling = usePolling(fn, interval, options)
        return { ...polling }
      },
      render: () => h('div'),
    }),
  )

describe('usePolling', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.restoreAllMocks()
  })

  it('挂载后按 interval 重复调用 fn(默认非 immediate)', () => {
    const fn = vi.fn()
    const wrapper = mountWithPolling(fn, 1000)
    expect(fn).toHaveBeenCalledTimes(0)
    vi.advanceTimersByTime(1000)
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(2000)
    expect(fn).toHaveBeenCalledTimes(3)
    wrapper.unmount()
  })

  it('immediate:true 挂载即调用一次,之后仍按 interval 轮询', () => {
    const fn = vi.fn()
    const wrapper = mountWithPolling(fn, 1000, { immediate: true })
    expect(fn).toHaveBeenCalledTimes(1)
    vi.advanceTimersByTime(1000)
    expect(fn).toHaveBeenCalledTimes(2)
    wrapper.unmount()
  })

  it('unmount 后 clearInterval,fn 不再被调用', () => {
    const fn = vi.fn()
    const wrapper = mountWithPolling(fn, 1000)
    vi.advanceTimersByTime(3000)
    const before = fn.mock.calls.length
    wrapper.unmount()
    vi.advanceTimersByTime(5000)
    expect(fn.mock.calls.length).toBe(before)
  })

  it('标签页隐藏暂停、恢复可见立即刷新一次并重启 interval', () => {
    const fn = vi.fn()
    const wrapper = mountWithPolling(fn, 1000)
    expect(fn).toHaveBeenCalledTimes(0)

    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    document.dispatchEvent(new Event('visibilitychange'))
    vi.advanceTimersByTime(5000)
    expect(fn).toHaveBeenCalledTimes(0) // 隐藏期间不调用

    vi.spyOn(document, 'hidden', 'get').mockReturnValue(false)
    document.dispatchEvent(new Event('visibilitychange'))
    expect(fn).toHaveBeenCalledTimes(1) // 恢复立即刷新
    vi.advanceTimersByTime(1000)
    expect(fn).toHaveBeenCalledTimes(2) // interval 已重启
    wrapper.unmount()
  })

  it('pauseWhenHidden:false 不响应 visibilitychange,继续轮询', () => {
    const fn = vi.fn()
    const addSpy = vi.spyOn(document, 'addEventListener')
    const wrapper = mountWithPolling(fn, 1000, { pauseWhenHidden: false })
    expect(addSpy.mock.calls.some(([e]) => e === 'visibilitychange')).toBe(false)

    vi.spyOn(document, 'hidden', 'get').mockReturnValue(true)
    document.dispatchEvent(new Event('visibilitychange'))
    vi.advanceTimersByTime(1000)
    expect(fn).toHaveBeenCalledTimes(1) // 隐藏仍按 interval 调用
    wrapper.unmount()
  })
})
