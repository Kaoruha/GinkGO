import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi, type Portfolio, type PortfolioDetail } from '@/api/modules/portfolio'
import { useLoadingStore } from './loading'

export const usePortfolioStore = defineStore('portfolio', () => {
  // 注入 loading store
  const loadingStore = useLoadingStore()

  // 状态
  const portfolios = ref<Portfolio[]>([])
  const currentPortfolio = ref<PortfolioDetail | null>(null)
  const error = ref<string | null>(null)
  const filterMode = ref<'BACKTEST' | 'PAPER' | 'LIVE' | ''>('')

  // 请求取消控制器
  const _abortControllers = ref<Map<string, AbortController>>(new Map())

  // 计算属性
  const runningPortfolios = computed(() =>
    portfolios.value.filter(p => p.state === 'RUNNING')
  )

  const backtestPortfolios = computed(() =>
    portfolios.value.filter(p => p.mode === 'BACKTEST')
  )

  const paperPortfolios = computed(() =>
    portfolios.value.filter(p => p.mode === 'PAPER')
  )

  const livePortfolios = computed(() =>
    portfolios.value.filter(p => p.mode === 'LIVE')
  )

  const filteredPortfolios = computed(() => {
    if (!filterMode.value) return portfolios.value
    return portfolios.value.filter(p => p.mode === filterMode.value)
  })

  const totalAsset = computed(() => {
    if (!currentPortfolio.value) return 0
    return currentPortfolio.value.current_cash +
      currentPortfolio.value.positions.reduce((sum, p) => sum + p.volume * p.current_price, 0)
  })

  // 统计数据
  const stats = computed(() => {
    const filtered = filterMode.value
      ? portfolios.value.filter(p => p.mode === filterMode.value)
      : portfolios.value

    return {
      total: filtered.length,
      running: filtered.filter(p => p.state === 'RUNNING').length,
      avgNetValue: filtered.length > 0
        ? filtered.reduce((sum, p) => sum + p.net_value, 0) / filtered.length
        : 0,
      totalAssets: filtered.length > 0
        ? filtered.reduce((sum, p) => sum + p.net_value * 100000, 0)
        : 0
    }
  })

  /**
   * 取消指定请求
   */
  function _cancelRequest(key: string) {
    const controller = _abortControllers.value.get(key)
    if (controller) {
      controller.abort()
      _abortControllers.value.delete(key)
    }
  }

  /**
   * 创建 AbortController 并返回
   */
  function _createController(key: string): AbortController {
    _cancelRequest(key)
    const controller = new AbortController()
    _abortControllers.value.set(key, controller)
    return controller
  }

  // 操作
  async function fetchPortfolios(params?: { mode?: string }) {
    const controller = _createController('fetchPortfolios')
    loadingStore.startLoading('portfolio-list')
    error.value = null
    try {
      const response = await portfolioApi.list(params, { signal: controller.signal })
      portfolios.value = response.data || []
      if (params?.mode) {
        filterMode.value = params.mode as any
      }
    } catch (e: any) {
      // 忽略取消操作的错误
      if (e.name !== 'AbortError') {
        error.value = e.message
        throw e
      }
    } finally {
      loadingStore.endLoading('portfolio-list')
      _abortControllers.value.delete('fetchPortfolios')
    }
  }

  async function fetchPortfolio(uuid: string) {
    const controller = _createController(`fetchPortfolio-${uuid}`)
    loadingStore.startLoading('portfolio-detail')
    error.value = null
    try {
      const response = await portfolioApi.get(uuid, { signal: controller.signal })
      currentPortfolio.value = response.data || null
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        error.value = e.message
        throw e
      }
    } finally {
      loadingStore.endLoading('portfolio-detail')
      _abortControllers.value.delete(`fetchPortfolio-${uuid}`)
    }
  }

  async function createPortfolio(data: {
    name: string
    initial_cash: number
    risk_config?: Record<string, unknown>
  }) {
    loadingStore.startLoading('portfolio-create')
    try {
      const response = await portfolioApi.create(data as any)
      const result = response.data
      portfolios.value.unshift(result)
      return result
    } finally {
      loadingStore.endLoading('portfolio-create')
    }
  }

  async function deletePortfolio(uuid: string) {
    const controller = _createController(`deletePortfolio-${uuid}`)
    loadingStore.startLoading('portfolio-delete')
    try {
      await portfolioApi.delete(uuid, { signal: controller.signal })
      portfolios.value = portfolios.value.filter(p => p.uuid !== uuid)
      if (currentPortfolio.value?.uuid === uuid) {
        currentPortfolio.value = null
      }
    } finally {
      loadingStore.endLoading('portfolio-delete')
      _abortControllers.value.delete(`deletePortfolio-${uuid}`)
    }
  }

  async function updatePortfolio(uuid: string, data: Partial<Portfolio>) {
    const controller = _createController(`updatePortfolio-${uuid}`)
    loadingStore.startLoading('portfolio-update')
    try {
      const response = await portfolioApi.update(uuid, data as any, { signal: controller.signal })
      const updated = response.data
      const index = portfolios.value.findIndex(p => p.uuid === uuid)
      if (index !== -1) {
        portfolios.value[index] = updated
      }
      if (currentPortfolio.value?.uuid === uuid) {
        currentPortfolio.value = updated as PortfolioDetail
      }
      return updated
    } finally {
      loadingStore.endLoading('portfolio-update')
      _abortControllers.value.delete(`updatePortfolio-${uuid}`)
    }
  }

  /**
   * 取消所有进行中的请求
   */
  function cancelAllRequests() {
    _abortControllers.value.forEach((controller) => controller.abort())
    _abortControllers.value.clear()
    loadingStore.clearAll()
  }

  /**
   * Store 销毁时清理
   */
  function $dispose() {
    cancelAllRequests()
  }

  function setCurrentPortfolio(portfolio: PortfolioDetail | null) {
    currentPortfolio.value = portfolio
  }

  function setFilterMode(mode: typeof filterMode.value) {
    filterMode.value = mode
  }

  function clearError() {
    error.value = null
  }

  return {
    // 状态
    portfolios,
    currentPortfolio,
    error,
    filterMode,

    // 计算属性
    runningPortfolios,
    backtestPortfolios,
    paperPortfolios,
    livePortfolios,
    filteredPortfolios,
    totalAsset,
    stats,

    // 操作
    fetchPortfolios,
    fetchPortfolio,
    createPortfolio,
    deletePortfolio,
    updatePortfolio,
    setCurrentPortfolio,
    setFilterMode,
    clearError,
    cancelAllRequests,
    $dispose
  }
}, {
  persist: {
    key: 'portfolio-store',
    storage: localStorage,
    paths: ['filterMode'] // 只持久化筛选模式
  }
})
