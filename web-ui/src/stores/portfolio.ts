import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi } from '@/api'
import type { Portfolio, PortfolioCreateRequest } from '@/api'

export const usePortfolioStore = defineStore('portfolio', () => {
  const portfolios = ref<Portfolio[]>([])
  const currentPortfolio = ref<Portfolio | null>(null)
  const loading = ref(false)
  const filterMode = ref<string>('')

  // 统计数据
  const stats = computed(() => ({
    total: portfolios.value.length,
    running: portfolios.value.filter(p => p.state === 'RUNNING').length,
    avgNetValue: portfolios.value.length > 0
      ? portfolios.value.reduce((sum, p) => sum + p.net_value, 0) / portfolios.value.length
      : 1,
    totalAssets: portfolios.value.reduce((sum, p) => sum + p.initial_cash, 0),
  }))

  // 筛选后的列表
  const filteredPortfolios = computed(() => {
    if (!filterMode.value) return portfolios.value
    return portfolios.value.filter(p => String(p.mode) === filterMode.value)
  })

  // 获取列表
  async function fetchPortfolios(params?: { mode?: string }) {
    loading.value = true
    try {
      const result = await portfolioApi.list(params)
      portfolios.value = result.data || []
      return result
    } catch (error) {
      console.error('Failed to fetch portfolios:', error)
      return null
    } finally {
      loading.value = false
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

  return {
    portfolios,
    currentPortfolio,
    loading,
    filterMode,
    stats,
    filteredPortfolios,
    fetchPortfolios,
    fetchPortfolio,
    createPortfolio,
    updatePortfolio,
    deletePortfolio,
    startPortfolio,
    stopPortfolio,
  }
})
