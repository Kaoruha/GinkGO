<template>
  <div class="backtest-compare-container">
    <div class="page-header">
      <h1 class="page-title">回测对比</h1>
      <p class="page-subtitle">选择多个回测任务进行对比分析</p>
    </div>

    <div class="card select-card">
      <div class="card-body">
        <form @submit.prevent>
          <div class="form-group">
            <label class="form-label">选择要对比的回测任务</label>
            <div class="multi-select">
              <div v-for="task in availableTasks" :key="task.uuid" class="multi-select-item">
                <label class="checkbox-label">
                  <input v-model="selectedTasks" type="checkbox" :value="task.uuid" />
                  <span>{{ task.name }}</span>
                  <span class="task-info">({{ formatDate(task.created_at, 'YYYY-MM-DD') }})</span>
                </label>
              </div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">选择对比指标</label>
            <div class="checkbox-grid">
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="total_return" />
                总收益率
              </label>
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="annual_return" />
                年化收益率
              </label>
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="sharpe_ratio" />
                夏普比率
              </label>
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="max_drawdown" />
                最大回撤
              </label>
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="win_rate" />
                胜率
              </label>
              <label class="checkbox-label">
                <input v-model="selectedMetrics" type="checkbox" value="profit_loss_ratio" />
                盈亏比
              </label>
            </div>
          </div>

          <div class="action-buttons">
            <button
              type="button"
              class="btn-primary"
              :disabled="selectedTasks.length < 2"
              @click="startCompare"
            >
              {{ comparing ? '对比中...' : '开始对比' }}
            </button>
            <button type="button" class="btn-secondary" @click="resetSelection">重置</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="comparisonResult" class="card result-card">
      <div class="card-header">
        <h4>对比结果</h4>
        <button class="btn-small" @click="exportComparison">导出对比数据</button>
      </div>
      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>指标</th>
                <th v-for="task in getSelectedTaskDetails()" :key="task.uuid">
                  {{ task.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="metric in selectedMetrics" :key="metric">
                <td class="metric-label">{{ metricLabels[metric] || metric }}</td>
                <td v-for="task in comparisonResult.tasks" :key="task.task_uuid">
                  <span :class="getValueClass(task.metrics[metric as keyof typeof task.metrics])">
                    {{ formatMetricValue(metric, task.metrics[metric as keyof typeof task.metrics]) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="!loading && availableTasks.length === 0" class="empty-state">
      <p>暂无可对比的回测任务</p>
      <button class="btn-primary" @click="goToBacktestList">去创建回测任务</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { backtestApi, type BacktestTask, type ComparisonResult } from '@/api/modules/backtest'
import { formatDate } from '@/utils/format'

const router = useRouter()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const loading = ref(false)
const comparing = ref(false)
const availableTasks = ref<BacktestTask[]>([])
const selectedTasks = ref<string[]>([])
const selectedMetrics = ref<string[]>(['total_return', 'annual_return', 'sharpe_ratio', 'max_drawdown', 'win_rate'])
const comparisonResult = ref<ComparisonResult | null>(null)

const metricLabels: Record<string, string> = {
  total_return: '总收益率',
  annual_return: '年化收益率',
  sharpe_ratio: '夏普比率',
  max_drawdown: '最大回撤',
  win_rate: '胜率',
  profit_loss_ratio: '盈亏比',
  volatility: '波动率',
  sortino_ratio: '索提诺比率'
}

const getSelectedTaskDetails = () => {
  return selectedTasks.value
    .map(uuid => availableTasks.value.find(t => t.uuid === uuid))
    .filter((t): t is BacktestTask => t !== undefined)
}

const loadAvailableTasks = async () => {
  loading.value = true
  try {
    const response = await backtestApi.list({ state: 'COMPLETED' })
    availableTasks.value = response.data?.items || []
  } catch (error: any) {
    showToast(`加载回测任务失败: ${error.message}`, 'error')
  } finally {
    loading.value = false
  }
}

const startCompare = async () => {
  if (selectedTasks.value.length < 2) {
    showToast('请选择至少2个回测任务进行对比', 'error')
    return
  }

  comparing.value = true
  try {
    const response = await backtestApi.compare(selectedTasks.value)
    comparisonResult.value = response.data || null
    showToast('对比完成')
  } catch (error: any) {
    showToast(`对比失败: ${error.message}`, 'error')
  } finally {
    comparing.value = false
  }
}

const resetSelection = () => {
  selectedTasks.value = []
  comparisonResult.value = null
}

const exportComparison = () => {
  if (!comparisonResult.value) return

  const data = JSON.stringify(comparisonResult.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `backtest-comparison-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  showToast('导出成功')
}

const formatMetricValue = (metric: string, value: number | undefined) => {
  if (value === undefined || value === null) return '-'

  if (['total_return', 'annual_return', 'max_drawdown', 'win_rate', 'volatility'].includes(metric)) {
    return `${(value * 100).toFixed(2)}%`
  }

  if (['sharpe_ratio', 'sortino_ratio', 'profit_loss_ratio'].includes(metric)) {
    return value.toFixed(2)
  }

  return value.toString()
}

const getValueClass = (value: number | undefined) => {
  if (value === undefined || value === null) return ''
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return ''
}

const goToBacktestList = () => {
  router.push('/backtest')
}

onMounted(() => {
  loadAvailableTasks()
})
</script>

<style scoped>
.backtest-compare-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 24px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 8px;
}

.multi-select {
  max-height: 200px;
  overflow-y: auto;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
}

.multi-select-item {
  padding: 8px 12px;
  border-bottom: 1px solid #3a3a4e;
}

.multi-select-item:last-child {
  border-bottom: none;
}

.checkbox-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #1890ff;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.task-info {
  color: #8a8a9a;
  font-size: 12px;
  margin-left: 8px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-primary {
  padding: 10px 20px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 10px 20px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tr:hover {
  background: #2a2a3e;
}

.metric-label {
  font-weight: 500;
  color: #ffffff;
}

.value-up {
  color: #f5222d;
  font-weight: 500;
}

.value-down {
  color: #52c41a;
  font-weight: 500;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0 0 16px 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .checkbox-grid {
    grid-template-columns: 1fr 1fr;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
