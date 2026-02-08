/**
 * useRequestCancelable 单元测试
 * 测试可取消请求 Composable 的功能
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { ref } from 'vue'
import { useRequestCancelable, useMultiRequestCancelable } from '../useRequestCancelable'

describe('useRequestCancelable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('基本功能', () => {
    it('应该正确初始化状态', () => {
      const { loading, error } = useRequestCancelable()

      expect(loading.value).toBe(false)
      expect(error.value).toBe(null)
    })

    it('应该在请求时设置 loading 为 true', async () => {
      const { loading, execute } = useRequestCancelable()

      const mockRequest = vi.fn((signal) => {
        return new Promise((resolve) => {
          setTimeout(() => resolve('data'), 100)
        })
      })

      const promise = execute(mockRequest)
      expect(loading.value).toBe(true)

      await promise
      expect(loading.value).toBe(false)
    })

    it('应该在成功时调用 onSuccess 回调', async () => {
      const onSuccess = vi.fn()
      const { execute } = useRequestCancelable()

      const mockRequest = vi.fn().mockResolvedValue('test data')

      await execute(mockRequest, { onSuccess })

      expect(onSuccess).toHaveBeenCalledWith('test data')
    })

    it('应该在失败时调用 onError 回调', async () => {
      const onError = vi.fn()
      const { execute, error } = useRequestCancelable()

      const mockError = new Error('Network error')
      const mockRequest = vi.fn().mockRejectedValue(mockError)

      try {
        await execute(mockRequest, { onError })
      } catch (e) {
        // Expected to throw
      }

      expect(onError).toHaveBeenCalledWith(mockError)
      expect(error.value).toBe(mockError)
    })
  })

  describe('请求取消功能', () => {
    it('应该能够取消请求', async () => {
      const { execute, cancel, loading } = useRequestCancelable()

      const mockRequest = vi.fn((signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 1000)
        })
      })

      const promise = execute(mockRequest)

      // 立即取消
      cancel()

      const result = await promise
      expect(result).toBe(null)
      expect(loading.value).toBe(false)
    })

    it('应该在取消时不调用 onError', async () => {
      const onError = vi.fn()
      const { execute, cancel } = useRequestCancelable()

      const mockRequest = vi.fn((signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 100)
        })
      })

      const promise = execute(mockRequest, { onError })
      cancel()

      await promise
      expect(onError).not.toHaveBeenCalled()
    })

    it('应该在执行新请求时取消之前的请求', async () => {
      const { execute } = useRequestCancelable()

      let abortCount = 0
      const mockRequest = (signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            abortCount++
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 100)
        })
      }

      const promise1 = execute(mockRequest)
      const promise2 = execute(mockRequest)

      await Promise.all([promise1, promise2])

      expect(abortCount).toBe(1) // 第一个请求应该被取消
    })
  })

  describe('onFinally 回调', () => {
    it('应该在成功时调用 onFinally', async () => {
      const onFinally = vi.fn()
      const { execute } = useRequestCancelable()

      const mockRequest = vi.fn().mockResolvedValue('data')

      await execute(mockRequest, { onFinally })

      expect(onFinally).toHaveBeenCalled()
    })

    it('应该在失败时调用 onFinally', async () => {
      const onFinally = vi.fn()
      const { execute } = useRequestCancelable()

      const mockRequest = vi.fn().mockRejectedValue(new Error('Error'))

      try {
        await execute(mockRequest, { onFinally })
      } catch (e) {
        // Expected to throw
      }

      expect(onFinally).toHaveBeenCalled()
    })

    it('应该在取消时调用 onFinally', async () => {
      const onFinally = vi.fn()
      const { execute, cancel } = useRequestCancelable()

      const mockRequest = (signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 100)
        })
      }

      const promise = execute(mockRequest, { onFinally })
      cancel()

      await promise
      expect(onFinally).toHaveBeenCalled()
    })
  })
})

describe('useMultiRequestCancelable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('多请求管理', () => {
    it('应该能够同时管理多个请求', async () => {
      const { execute, isLoading } = useMultiRequestCancelable()

      const mockRequest1 = vi.fn().mockResolvedValue('data1')
      const mockRequest2 = vi.fn().mockResolvedValue('data2')

      const promise1 = execute('request1', mockRequest1)
      const promise2 = execute('request2', mockRequest2)

      expect(isLoading('request1')).toBe(true)
      expect(isLoading('request2')).toBe(true)

      await Promise.all([promise1, promise2])

      expect(isLoading('request1')).toBe(false)
      expect(isLoading('request2')).toBe(false)
    })

    it('应该能够取消特定请求', async () => {
      const { execute, cancel, isLoading } = useMultiRequestCancelable()

      const mockRequest = (signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 100)
        })
      }

      const promise1 = execute('request1', mockRequest)
      const promise2 = execute('request2', mockRequest)

      // 只取消 request1
      cancel('request1')

      await promise1
      expect(isLoading('request1')).toBe(false)

      await promise2
      expect(isLoading('request2')).toBe(false)
    })

    it('应该能够取消所有请求', async () => {
      const { execute, cancel, isLoading } = useMultiRequestCancelable()

      const mockRequest = (signal) => {
        return new Promise((resolve, reject) => {
          signal.addEventListener('abort', () => {
            const error = new Error('Aborted')
            error.name = 'AbortError'
            reject(error)
          })
          setTimeout(() => resolve('data'), 100)
        })
      }

      const promise1 = execute('request1', mockRequest)
      const promise2 = execute('request2', mockRequest)

      // 取消所有请求
      cancel()

      await Promise.all([promise1, promise2])

      expect(isLoading('request1')).toBe(false)
      expect(isLoading('request2')).toBe(false)
    })

    it('应该能够获取错误信息', async () => {
      const { execute, getError } = useMultiRequestCancelable()

      const mockError = new Error('Request failed')
      const mockRequest = vi.fn().mockRejectedValue(mockError)

      try {
        await execute('request1', mockRequest)
      } catch (e) {
        // Expected to throw
      }

      expect(getError('request1')).toBe(mockError)
    })
  })
})
