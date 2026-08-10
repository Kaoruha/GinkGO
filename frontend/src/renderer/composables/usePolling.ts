import { onMounted, onUnmounted } from 'vue'

export interface UsePollingOptions {
  /** 挂载后立即执行一次 fn(默认 false,沿用 setInterval 首次延迟语义) */
  immediate?: boolean
  /** 标签页隐藏时暂停;恢复可见时立即执行一次并重启 interval(默认 true) */
  pauseWhenHidden?: boolean
}

/**
 * 通用轮询 composable:封装 setInterval + onUnmounted 清理 + 可见性暂停。
 *
 * 消除 AccountInfo(10s 刷新)/ 各 layout(1s 时钟)等处各自重复的
 * setInterval + clearInterval 样板。必须在组件 setup 顶层调用
 * (内部依赖 onMounted / onUnmounted)。
 *
 * @param fn       轮询回调(可为 async);可见性恢复时也用它立即刷新
 * @param interval 轮询间隔(ms)
 * @param options  immediate / pauseWhenHidden
 */
export function usePolling(
  fn: () => void | Promise<void>,
  interval: number,
  options: UsePollingOptions = {},
) {
  const { immediate = false, pauseWhenHidden = true } = options
  let timer: ReturnType<typeof setInterval> | null = null

  const start = () => {
    if (timer !== null) return
    timer = setInterval(fn, interval)
  }

  const stop = () => {
    if (timer !== null) {
      clearInterval(timer)
      timer = null
    }
  }

  const handleVisibility = () => {
    if (document.hidden) {
      stop()
    } else {
      // 恢复可见:隐藏期间数据可能已过期,立即刷新一次再重启 interval
      fn()
      start()
    }
  }

  onMounted(() => {
    if (immediate) fn()
    start()
    if (pauseWhenHidden) {
      document.addEventListener('visibilitychange', handleVisibility)
    }
  })

  onUnmounted(() => {
    stop()
    if (pauseWhenHidden) {
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  })

  return { start, stop }
}
