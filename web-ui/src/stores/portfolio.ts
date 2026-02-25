import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
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
  }
})
