import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
<<<<<<< HEAD
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
=======
import { portfolioApi } from '@/api'
import type { Portfolio, PortfolioCreateRequest } from '@/api'

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolios = ref<Portfolio[]>([])
  const currentPortfolio = ref<Portfolio | null>(null)
  const loading = ref(false)
  const loadingMore = ref(false)
  const filterMode = ref<string>('')

  // 分页状态
  const currentPage = ref(0)
  const pageSize = ref(20)
  const total = ref(0)
  const hasMore = computed(() => portfolios.value.length < total.value)

  // 统计数据（从 API 获取）
  const statsData = ref<{ total: number; running: number; avgNetValue: number; totalAssets: number }>({
    total: 0,
    running: 0,
    avgNetValue: 1,
    totalAssets: 0
  })

  // 统计数据
  const stats = computed(() => statsData.value)

  // 筛选后的列表
  const filteredPortfolios = computed(() => {
    if (!filterMode.value) return portfolios.value
    return portfolios.value.filter(p => String(p.mode) === filterMode.value)
  })

  // 获取列表
  async function fetchPortfolios(params?: { mode?: string; page?: number; page_size?: number; append?: boolean; keyword?: string }) {
    const append = params?.append || false
    const page = params?.page ?? (append ? currentPage.value + 1 : 0)
    const page_size = params?.page_size ?? pageSize.value

    if (append) {
      loadingMore.value = true
    } else {
      loading.value = true
      currentPage.value = 0
    }

    try {
      // 只传递 API 需要的参数，不传递 append
      const apiParams: { mode?: string; page?: number; page_size?: number; keyword?: string } = {
        page,
        page_size
      }
      if (params?.mode) apiParams.mode = params.mode
      if (params?.keyword) apiParams.keyword = params.keyword

      const result = await portfolioApi.list(apiParams)
      const newData = result.data || []

      if (append) {
        portfolios.value.push(...newData)
      } else {
        portfolios.value = newData
      }

      currentPage.value = page
      total.value = result.total || 0
      return result
    } catch (error) {
      console.error('Failed to fetch portfolios:', error)
      return null
    } finally {
      loading.value = false
      loadingMore.value = false
    }
  }

  // 获取单个
  async function fetchPortfolio(uuid: string) {
    loading.value = true
    try {
      const result = await portfolioApi.get(uuid)
      currentPortfolio.value = result
      return result
    } catch (error) {
      console.error('Failed to fetch portfolio:', error)
      return null
    } finally {
      loading.value = false
    }
  }

  // 创建
  async function createPortfolio(data: PortfolioCreateRequest) {
    loading.value = true
    try {
      const result = await portfolioApi.create(data)
      portfolios.value.push(result)
      return result
    } catch (error) {
      console.error('Failed to create portfolio:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 更新
  async function updatePortfolio(uuid: string, data: Partial<Portfolio>) {
    loading.value = true
    try {
      const result = await portfolioApi.update(uuid, data)
      const index = portfolios.value.findIndex(p => p.uuid === uuid)
      if (index !== -1) {
        portfolios.value[index] = result
      }
      return result
    } catch (error) {
      console.error('Failed to update portfolio:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 删除
  async function deletePortfolio(uuid: string) {
    loading.value = true
    try {
      await portfolioApi.delete(uuid)
      portfolios.value = portfolios.value.filter(p => p.uuid !== uuid)
      return true
    } catch (error) {
      console.error('Failed to delete portfolio:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 启动
  async function startPortfolio(uuid: string) {
    try {
      await portfolioApi.start(uuid)
      const portfolio = portfolios.value.find(p => p.uuid === uuid)
      if (portfolio) portfolio.state = 'RUNNING'
      return true
    } catch (error) {
      console.error('Failed to start portfolio:', error)
      throw error
    }
  }

  // 停止
  async function stopPortfolio(uuid: string) {
    try {
      await portfolioApi.stop(uuid)
      const portfolio = portfolios.value.find(p => p.uuid === uuid)
      if (portfolio) portfolio.state = 'STOPPED'
      return true
    } catch (error) {
      console.error('Failed to stop portfolio:', error)
      throw error
    }
  }

  // 获取统计数据
  async function fetchStats() {
    try {
      const result = await portfolioApi.getStats()
      statsData.value = {
        total: result.total || 0,
        running: result.running || 0,
        avgNetValue: result.avg_net_value || 1,
        totalAssets: result.total_assets || 0
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  return {
    portfolios,
    currentPortfolio,
    loading,
    loadingMore,
    filterMode,
    currentPage,
    pageSize,
    total,
    hasMore,
    stats,
    statsData,
    filteredPortfolios,
    fetchPortfolios,
    fetchPortfolio,
    fetchStats,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    startPortfolio,
    stopPortfolio,
>>>>>>> 011-quant-research
  }
})
