import { ref } from 'vue'
import { message as toast } from '@/utils/toast'

export interface UseAsyncActionOptions {
  /** 成功 toast 文案;false = 不弹(默认不弹,由调用方在 onSuccess 里自行提示) */
  success?: string | false
  /** 失败 toast 文案;false = 静默(默认 e.message) */
  error?: string | false
  /** 成功后回调(如刷新列表/关弹窗) */
  onSuccess?: () => void | Promise<void>
}

/**
 * 提交态样板收敛:saving + try/catch/toast → { running, run }
 * run 返回是否成功;并发重入直接拒绝(返回 false)
 */
export function useAsyncAction<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: UseAsyncActionOptions = {},
) {
  const running = ref(false)

  const run = async (...args: Parameters<T>): Promise<boolean> => {
    if (running.value) return false
    running.value = true
    try {
      await fn(...args)
      if (options.success !== false && options.success !== undefined) {
        toast.success(options.success)
      }
      if (options.onSuccess) await options.onSuccess()
      return true
    } catch (e: any) {
      if (options.error === false) {
        // 静默:调用方自行处理
      } else {
        toast.error(options.error ?? e?.message ?? '操作失败')
      }
      return false
    } finally {
      running.value = false
    }
  }

  return { running, run }
}
