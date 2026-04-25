<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">回测</span>
        回测对比
      </div>
      <div class="page-actions">
        <button class="btn btn-primary" :disabled="loading || selectedIds.length < 2" @click="runCompare">
          {{ loading ? '对比中...' : '开始对比' }}
        </button>
      </div>
    </div>

    <!-- 选择回测任务 -->
    <div class="card">
      <div class="card-header">
        <h3>选择回测任务</h3>
      </div>
      <div class="card-body">
        <div class="info-alert" style="margin-bottom: 16px">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          请选择 2-5 个回测任务进行对比
        </div>

        <div v-if="listLoading" class="loading-container">
          <div class="spinner"></div>
        </div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th width="40"></th>
                <th width="150">任务ID</th>
                <th width="200">名称</th>
                <th width="100">状态</th>
                <th width="120">总收益</th>
                <th width="100">夏普比率</th>
                <th width="100">最大回撤</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in backtestList" :key="record.task_id">
                <td>
                  <input
                    type="checkbox"
                    :disabled="record.status !== 'completed'"
                    :checked="selectedIds.includes(record.task_id)"
                    @change="toggleSelect(record.task_id, $event)"
                  />
                </td>
                <td>{{ record.task_id }}</td>
                <td>{{ record.name }}</td>
                <td>
                  <span class="tag" :class="`tag-${getStatusColorClass(record.status)}`">
                    {{ getStatusText(record.status) }}
                  </span>
                </td>
                <td>
                  <span :class="(record.total_return || 0) >= 0 ? 'text-danger' : 'text-success'">
                    {{ ((record.total_return || 0) * 100).toFixed(2) }}%
                  </span>
                </td>
                <td>{{ record.sharpe_ratio?.toFixed(2) || '-' }}</td>
                <td>{{ record.max_drawdown?.toFixed(2) || '-' }}</td>
              </tr>
            </tbody>
          </table>
          <div v-if="backtestList.length === 0" class="empty-state">
            <p>暂无回测数据</p>
          </div>
        </div>
        <div style="margin-top: 16px">
          <span class="text-muted">已选择 {{ selectedIds.length }} 个回测任务</span>
        </div>
      </div>
    </div>

    <!-- 对比结果 -->
    <template v-if="compareResult">
      <!-- 指标对比表 -->
      <div class="card">
        <div class="card-header">
          <h3>指标对比</h3>
        </div>
        <div class="card-body">
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th width="150">指标</th>
                  <th v-for="(_, index) in selectedIds" :key="`header-${index}`" width="120">
                    回测 {{ index + 1 }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in compareResult.metrics" :key="record.name">
                  <td>{{ record.name }}</td>
                  <td v-for="id in selectedIds" :key="`value-${id}`">
                    <span :class="{ 'best-value': record.best === `value_${id}` }">
                      {{ formatValue(record[`value_${id}`], record.type) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 净值曲线图 -->
      <div class="card">
        <div class="card-header">
          <h3>净值曲线对比</h3>
        </div>
        <div class="card-body">
          <div class="info-alert">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            图表功能开发中
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

interface BacktestItem {
  task_id: string
  name: string
  status: string
  total_return?: number
  sharpe_ratio?: number
  max_drawdown?: number
}

interface MetricItem {
  name: string
  type: string
  best?: string
  [key: string]: any
}

interface CompareResult {
  metrics: MetricItem[]
  netvalues: Record<string, { date: string; value: number }[]>
}

const listLoading = ref(false)
const loading = ref(false)
const backtestList = ref<BacktestItem[]>([])
const selectedIds = ref<string[]>([])
const compareResult = ref<CompareResult | null>(null)

const getStatusColorClass = (status: string) => {
  const map: Record<string, string> = {
    completed: 'green',
    running: 'blue',
    failed: 'red',
    pending: 'gray',
  }
  return map[status] || 'gray'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    running: '运行中',
    failed: '失败',
    pending: '待执行',
  }
  return map[status] || status
}

const formatValue = (value: any, type: string) => {
  if (value === null || value === undefined) return '-'
  if (type === 'percent') return (value * 100).toFixed(2) + '%'
  if (type === 'number') return Number(value).toFixed(2)
  return value
}

const toggleSelect = (id: string, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  if (checked) {
    if (selectedIds.value.length >= 5) {
      showToast('最多选择 5 个回测任务', 'warning')
      return
    }
    selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(sid => sid !== id)
  }
}

const fetchBacktestList = async () => {
  listLoading.value = true
  try {
    // Mock data - replace with actual API call
    backtestList.value = [
      { task_id: 'bt001', name: '回测任务1', status: 'completed', total_return: 0.15, sharpe_ratio: 1.5, max_drawdown: -0.1 },
      { task_id: 'bt002', name: '回测任务2', status: 'completed', total_return: 0.2, sharpe_ratio: 1.8, max_drawdown: -0.08 },
    ]
  } catch (e) {
    showToast('获取回测列表失败', 'error')
  } finally {
    listLoading.value = false
  }
}

const runCompare = async () => {
  if (selectedIds.value.length < 2) {
    showToast('请至少选择 2 个回测任务', 'warning')
    return
  }

  loading.value = true
  try {
    // Mock data - replace with actual API call
    compareResult.value = {
      metrics: [
        { name: '总收益率', type: 'percent', value_bt001: 0.15, value_bt002: 0.2, best: 'value_bt002' },
        { name: '夏普比率', type: 'number', value_bt001: 1.5, value_bt002: 1.8, best: 'value_bt002' },
      ],
      netvalues: {}
    }
  } catch (e) {
    showToast('对比失败', 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})

watch(() => selectedIds.value, () => {
  compareResult.value = null
})
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #ffffff;
}

.best-value {
  font-weight: bold;
  color: #1890ff;
}

.text-danger {
  color: #f5222d;
}

.text-success {
  color: #52c41a;
}

.text-muted {
  color: #8a8a9a;
}

/* Card */

/* Info Alert */
.info-alert {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: rgba(24, 144, 255, 0.1);
  border: 1px solid rgba(24, 144, 255, 0.3);
  border-radius: 4px;
  color: #1890ff;
  font-size: 13px;
}

.info-alert svg {
  flex-shrink: 0;
}

/* Loading */

/* Table */
.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.data-table input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

/* Tag */

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
}

/* Button */

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

</style>
