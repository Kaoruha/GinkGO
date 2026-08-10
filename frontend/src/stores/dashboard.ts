import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface DashboardStats {
  total_asset: number
  today_pnl: number
  position_count: number
  running_strategies: number
  system_status: 'ONLINE' | 'OFFLINE' | 'WARNING'
}

export const useDashboardStore = defineStore('dashboard', () => {
  const stats = ref<DashboardStats>({
    total_asset: 0,
    today_pnl: 0,
    position_count: 0,
    running_strategies: 0,
    system_status: 'ONLINE'
  })

  const loading = ref(false)

  async function fetchStats() {
    loading.value = true
    try {
      // TODO: 调用API获取仪表盘统计数据
      // const response = await dashboardApi.getStats()
      // stats.value = response
    } finally {
      loading.value = false
    }
  }

  return {
    stats,
    loading,
    fetchStats
  }
})
