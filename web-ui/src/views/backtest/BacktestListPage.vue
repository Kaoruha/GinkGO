<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">回测中心</h1>
      <p class="page-description">所有组合的回测任务</p>
    </div>

    <div class="card">
      <div class="card-body">
        <table v-if="tasks.length" class="data-table">
          <thead>
            <tr>
              <th>任务</th>
              <th>组合</th>
              <th>状态</th>
              <th>收益率</th>
              <th>夏普</th>
              <th>最大回撤</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.uuid">
              <td>
                <router-link :to="`/portfolios/${t.portfolio_id}/backtests/${t.uuid}`" class="link">
                  {{ t.name || t.uuid?.slice(0, 8) }}
                </router-link>
              </td>
              <td class="mono">{{ t.portfolio_id?.slice(0, 8) }}</td>
              <td>{{ t.status }}</td>
              <td :class="Number(t.annual_return) >= 0 ? 'text-green' : 'text-red'">
                {{ t.annual_return != null ? (Number(t.annual_return) * 100).toFixed(2) + '%' : '-' }}
              </td>
              <td>{{ t.sharpe_ratio != null ? Number(t.sharpe_ratio).toFixed(2) : '-' }}</td>
              <td class="text-red">{{ t.max_drawdown != null ? (Number(t.max_drawdown) * 100).toFixed(2) + '%' : '-' }}</td>
              <td>{{ t.created_at?.replace('T', ' ').slice(0, 19) || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">暂无回测任务</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { backtestApi } from '@/api/modules/backtest'

const tasks = ref<any[]>([])

const fetchTasks = async () => {
  try {
    const res = await backtestApi.list({ page: 1, size: 100 })
    tasks.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => fetchTasks())
</script>

<style scoped>
.mono { font-family: monospace; font-size: 12px; color: #8a8a9a; }
.link { color: #3b82f6; text-decoration: none; }
.link:hover { text-decoration: underline; }
.text-green { color: #22c55e; }
.text-red { color: #ef4444; }
</style>
