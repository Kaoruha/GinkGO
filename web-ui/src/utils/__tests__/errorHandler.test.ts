/**
 * 错误处理器单元测试
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  handleApiError,
  withErrorHandling,
  extractErrorInfo,
  createApiError,
  ErrorCode
} from '../errorHandler'

// Mock ant-design-vue message
vi.mock('ant-design-vue', () => ({
  message: {
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
    success: vi.fn()
  }
}))

import { message } from 'ant-design-vue'

describe('errorHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Mock localStorage
    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn()
    } as any
    // Mock window.location
    delete (window as any).location
    window.location = { href: '' } as any
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('handleApiError', () => {
    it('应该忽略 AbortError', () => {
      const error = { name: 'AbortError', message: '请求已取消' }
      handleApiError(error)

      expect(message.error).not.toHaveBeenCalled()
      expect(message.warning).not.toHaveBeenCalled()
    })

    it('应该处理带有 code 的 ApiError', () => {
      const error = {
        code: ErrorCode.NOT_FOUND,
        message: '资源不存在'
      }
      handleApiError(error)

      expect(message.warning).toHaveBeenCalledWith('资源不存在')
    })

    it('应该处理未授权错误并跳转登录页', () => {
      const error = {
        code: ErrorCode.UNAUTHORIZED,
        message: '请先登录'
      }
      handleApiError(error)

      expect(message.error).toHaveBeenCalledWith('请先登录')
      expect(localStorage.removeItem).toHaveBeenCalledWith('access_token')
      expect(window.location.href).toBe('/login')
    })

    it('应该处理网络错误', () => {
      const error = {
        code: ErrorCode.NETWORK_ERROR,
        message: '网络连接失败'
      }
      handleApiError(error)

      expect(message.error).toHaveBeenCalledWith('网络连接失败')
    })

    it('应该处理 Axios 错误', () => {
      const error = {
        isAxiosError: true,
        response: {
          status: 404,
          data: { message: '资源不存在' }
        }
      }
      handleApiError(error)

      expect(message.warning).toHaveBeenCalledWith('资源不存在')
    })

    it('应该处理超时错误', () => {
      const error = {
        isAxiosError: true,
        code: 'ECONNABORTED'
      }
      handleApiError(error)

      expect(message.error).toHaveBeenCalledWith('请求超时，请稍后重试')
    })

    it('应该处理通用错误', () => {
      const error = new Error('操作失败')
      handleApiError(error)

      expect(message.error).toHaveBeenCalledWith('操作失败')
    })

    it('应该支持自定义错误消息', () => {
      const error = {
        code: ErrorCode.VALIDATION_ERROR,
        message: '验证失败'
      }
      handleApiError(error, true, '自定义错误消息')

      expect(message.error).toHaveBeenCalledWith('自定义错误消息')
    })

    it('应该支持不显示错误消息', () => {
      const error = {
        code: ErrorCode.VALIDATION_ERROR,
        message: '验证失败'
      }
      handleApiError(error, false)

      expect(message.error).not.toHaveBeenCalled()
    })
  })

  describe('withErrorHandling', () => {
    it('应该成功执行函数并返回结果', async () => {
      const fn = vi.fn().mockResolvedValue('success')
      const wrapped = withErrorHandling(fn)

      const result = await wrapped()

      expect(result).toBe('success')
      expect(fn).toHaveBeenCalledTimes(1)
    })

    it('应该捕获错误并调用错误处理器', async () => {
      const fn = vi.fn().mockRejectedValue(new Error('test error'))
      const errorCallback = vi.fn()
      const wrapped = withErrorHandling(fn, errorCallback)

      await expect(wrapped()).rejects.toThrow('test error')
      expect(errorCallback).toHaveBeenCalledTimes(1)
    })

    it('没有错误回调时应该使用默认错误处理', async () => {
      const fn = vi.fn().mockRejectedValue({ name: 'AbortError' })
      const wrapped = withErrorHandling(fn)

      await expect(wrapped()).rejects.toEqual({ name: 'AbortError' })
      expect(message.error).not.toHaveBeenCalled()
    })
  })

  describe('extractErrorInfo', () => {
    it('应该提取业务错误信息', () => {
      const error = {
        response: {
          data: {
            error: 'VALIDATION_ERROR',
            message: '验证失败'
          }
        }
      } as any

      const info = extractErrorInfo(error)

      expect(info).toEqual({
        code: 'VALIDATION_ERROR',
        message: '验证失败'
      })
    })

    it('应该提取 HTTP 状态码错误信息', () => {
      const error = {
        response: {
          status: 404,
          data: { message: 'Not Found' }
        }
      } as any

      const info = extractErrorInfo(error)

      expect(info).toEqual({
        code: 'HTTP_404',
        message: 'Not Found'
      })
    })

    it('应该提取超时错误信息', () => {
      const error = {
        code: 'ECONNABORTED'
      } as any

      const info = extractErrorInfo(error)

      expect(info).toEqual({
        code: ErrorCode.TIMEOUT_ERROR,
        message: '请求超时，请稍后重试'
      })
    })

    it('应该提取网络错误信息', () => {
      const error = {
        request: {}
      } as any

      const info = extractErrorInfo(error)

      expect(info).toEqual({
        code: ErrorCode.NETWORK_ERROR,
        message: '网络连接失败，请检查网络设置'
      })
    })

    it('应该返回默认错误信息', () => {
      const error = {
        message: 'Unknown error'
      } as any

      const info = extractErrorInfo(error)

      expect(info).toEqual({
        code: ErrorCode.INTERNAL_ERROR,
        message: 'Unknown error'
      })
    })
  })

  describe('createApiError', () => {
    it('应该创建标准错误对象', () => {
      const error = createApiError('TEST_ERROR', '测试错误', { detail: '详细错误' })

      expect(error).toEqual({
        code: 'TEST_ERROR',
        message: '测试错误',
        details: { detail: '详细错误' }
      })
    })

    it('应该创建不带详情的错误对象', () => {
      const error = createApiError('TEST_ERROR', '测试错误')

      expect(error).toEqual({
        code: 'TEST_ERROR',
        message: '测试错误'
      })
    })
  })
})
