/**
 * 统一的无限滚动处理composable
 * 用于减少各组件中重复的滚动加载逻辑
 */
import { ref, onMounted, onUnmounted, Ref } from 'vue'

/**
 * 无限滚动配置选项
 */
interface InfiniteScrollOptions {
  // 加载更多数据的函数
  loadMore: () => Promise<void>
  // 是否还有更多数据
  hasMore: Ref<boolean>
  // 是否正在加载
  loading: Ref<boolean>
  // 预加载距离（像素），默认200px
  distance?: number
  // 触发阈值（0-1），默认0.1
  threshold?: number
  // 根边距，默认'200px'
  rootMargin?: string
}

/**
 * 统一的无限滚动处理composable
 * @param options 配置选项
 * @returns 触发元素引用和设置方法
 */
export function useInfiniteScroll(options: InfiniteScrollOptions) {
  const triggerRef = ref<HTMLElement>()
  let observer: IntersectionObserver | null = null

  /**
   * IntersectionObserver回调
   */
  const handleIntersection = (entries: IntersectionObserverEntry[]) => {
    const entry = entries[0]
    if (!entry) return

    // 当触发元素进入视口且还有更多数据且不在加载中时
    if (entry.isIntersecting && options.hasMore.value && !options.loading.value) {
      options.loadMore()
    }
  }

  /**
   * 设置观察者
   */
  const setupObserver = () => {
    if (!triggerRef.value || observer) return

    observer = new IntersectionObserver(handleIntersection, {
      rootMargin: options.rootMargin || '200px',
      threshold: options.threshold ?? 0.1
    })

    observer.observe(triggerRef.value)
  }

  /**
   * 清理观察者
   */
  const cleanupObserver = () => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  }

  /**
   * 重新设置观察者（用于动态内容变化后重新绑定）
   */
  const resetObserver = () => {
    cleanupObserver()
    setupObserver()
  }

  // 组件挂载后设置观察者
  onMounted(() => {
    // 使用setTimeout确保DOM已渲染
    setTimeout(setupObserver, 0)
  })

  // 组件卸载时清理观察者
  onUnmounted(cleanupObserver)

  return {
    triggerRef,
    setupObserver,
    cleanupObserver,
    resetObserver
  }
}

/**
 * 简化版的列表无限滚动hook
 * 自动管理加载状态和分页
 */
export function useListInfiniteScroll<T>(
  fetchFunction: (page: number) => Promise<{ data: T[]; hasMore: boolean }>
) {
  const items = ref<T[]>([]) as Ref<T[]>
  const loading = ref(false)
  const currentPage = ref(1)
  const hasMore = ref(true)

  /**
   * 加载更多数据
   */
  const loadMore = async () => {
    if (loading.value || !hasMore.value) return

    loading.value = true
    try {
      const result = await fetchFunction(currentPage.value)
      items.value.push(...result.data)
      hasMore.value = result.hasMore
      currentPage.value++
    } catch (error) {
      console.error('加载更多数据失败:', error)
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置列表状态
   */
  const reset = () => {
    items.value = []
    currentPage.value = 1
    hasMore.value = true
    loading.value = false
  }

  /**
   * 刷新列表（重新加载第一页）
   */
  const refresh = async () => {
    reset()
    await loadMore()
  }

  const infiniteScroll = useInfiniteScroll({
    loadMore,
    hasMore,
    loading
  })

  return {
    items,
    loading,
    hasMore,
    currentPage,
    loadMore,
    reset,
    refresh,
    triggerRef: infiniteScroll.triggerRef
  }
}