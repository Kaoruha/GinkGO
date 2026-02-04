import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { portfolioApi, type Portfolio, type PortfolioDetail } from '@/api/modules/portfolio'

export const usePortfolioStore = defineStore('portfolio', () => {
  // 状态
  const portfolios = ref<Portfolio[]>([])
  const currentPortfolio = ref<PortfolioDetail | null>(null)
  const loading = ref(false)

  // 计算属性
  const runningPortfolios = computed(() =>
    portfolios.value.filter(p => p.state === 'RUNNING')
  )

  const totalAsset = computed(() => {
    if (!currentPortfolio.value) return 0
    return currentPortfolio.value.current_cash +
      currentPortfolio.value.positions.reduce((sum, p) => sum + p.volume * p.current_price, 0)
  })

  // 操作
  async function fetchPortfolios(params?: { mode?: string }) {
    loading.value = true
    try {
      portfolios.value = await portfolioApi.list(params)
    } finally {
      loading.value = false
    }
  }

  async function fetchPortfolio(uuid: string) {
    loading.value = true
    try {
      currentPortfolio.value = await portfolioApi.get(uuid)
    } finally {
      loading.value = false
    }
  }

  async function createPortfolio(data: {
    name: string
    initial_cash: number
    risk_config?: Record<string, unknown>
  }) {
    const result = await portfolioApi.create(data)
    portfolios.value.push(result)
    return result
  }

  function setCurrentPortfolio(portfolio: PortfolioDetail | null) {
    currentPortfolio.value = portfolio
  }

  return {
    portfolios,
    currentPortfolio,
    loading,
    runningPortfolios,
    totalAsset,
    fetchPortfolios,
    fetchPortfolio,
    createPortfolio,
    setCurrentPortfolio
  }
})
