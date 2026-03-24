<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">回测任务</h1>
      <div class="header-actions">
        <button class="btn-secondary" @click="loadBacktests">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
            <path d="M16 21h5v-5"></path>
          </svg>
          刷新
        </button>
        <button class="btn-primary" @click="showCreateModal = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          创建回测
        </button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.size > 0" class="batch-action-bar">
      <div class="batch-info">已选择 {{ selectedIds.size }} 个任务</div>
      <div class="batch-buttons">
        <button class="btn-small" :disabled="!canBatchStart" @click="handleBatchStart">批量启动</button>
        <button class="btn-small" :disabled="!canBatchStop" @click="handleBatchStop">批量停止</button>
        <button class="btn-small" :disabled="!canBatchCancel" @click="handleBatchCancel">批量取消</button>
        <button class="btn-small btn-secondary" @click="clearSelection">取消选择</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-value">{{ backtestStore.total }}</div>
        <div class="stat-label">总任务数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ completedCount }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-running">{{ backtestStore.runningCount }}</div>
        <div class="stat-label">运行中</div>
      </div>
      <div class="stat-card">
        <div class="stat-value stat-failed">{{ failedCount }}</div>
        <div class="stat-label">失败</div>
      </div>
    </div>

    <!-- 筛选器 -->
    <div v-show="selectedIds.size === 0" class="filters-bar">
      <div class="filter-group">
        <span class="filter-label">状态:</span>
        <div class="radio-group">
          <button
            v-for="option in statusOptions"
            :key="option.value"
            class="radio-button"
            :class="{ active: filterStatus === option.value }"
            @click="setStatusFilter(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
      <div class="search-box">
        <input
          v-model="searchKeyword"
          type="search"
          placeholder="搜索任务..."
          class="search-input"
          @keyup.enter="handleSearch"
        />
        <button class="search-btn" @click="handleSearch">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- 任务列表 -->
    <div class="table-container">
      <div v-if="backtestStore.loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else-if="backtestStore.tasks.length === 0" class="empty-state">
        <p>暂无回测任务</p>
      </div>
      <div v-else class="custom-table">
        <table class="data-table">
          <thead>
            <tr>
              <th class="checkbox-col">
                <input type="checkbox" :checked="isAllSelected" @change="toggleSelectAll" />
              </th>
              <th>任务</th>
              <th>状态</th>
              <th>总盈亏</th>
              <th>订单数</th>
              <th>信号数</th>
              <th>创建时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="record in backtestStore.tasks"
              :key="record.uuid"
              :class="{ selected: selectedIds.has(record.uuid) }"
              @click="handleRowClick(record)"
            >
              <td class="checkbox-col" @click.stop>
                <input type="checkbox" :checked="selectedIds.has(record.uuid)" @change="toggleSelect(record.uuid)" />
              </td>
              <td>
                <div class="task-info">
                  <div class="task-name">{{ record.name || '(未命名)' }}</div>
                  <div class="task-uuid">{{ record.uuid }}</div>
                </div>
              </td>
              <td>
                <div class="status-cell">
                  <StatusTag :status="record.status" type="backtest" />
                  <div v-if="record.status === 'running' || record.status === 'pending'" class="progress-wrapper">
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: (record.progress || 0) + '%' }"></div>
                    </div>
                    <span class="progress-text">{{ (record.progress || 0).toFixed(1) }}%</span>
                  </div>
                </div>
              </td>
              <td>
                <span :style="{ color: getPNLColor(record.total_pnl) }">
                  {{ formatDecimal(record.total_pnl) }}
                </span>
              </td>
              <td>{{ record.total_orders || 0 }}</td>
              <td>{{ record.total_signals || 0 }}</td>
              <td>{{ formatDateTime(record.create_at) }}</td>
              <td @click.stop>
                <div class="action-buttons">
                  <button
                    v-if="canStartTask(record)"
                    class="link-button"
                    :title="getStartTooltip(record)"
                    :disabled="!backtestStore.canStartTask(record)"
                    @click="handleStart(record)"
                  >
                    启动
                  </button>
                  <button
                    v-if="canStopTask(record)"
                    class="link-button link-danger"
                    :title="getStopTooltip(record)"
                    :disabled="!backtestStore.canStopTask(record)"
                    @click="handleStop(record)"
                  >
                    停止
                  </button>
                  <button
                    v-if="canCancelTask(record)"
                    class="link-button"
                    :title="getCancelTooltip(record)"
                    :disabled="!backtestStore.canCancelTask(record)"
                    @click="handleCancel(record)"
                  >
                    取消
                  </button>
                  <button class="link-button" @click="router.push(`/stage1/backtest/${record.uuid}`)">
                    查看详情
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 分页 -->
      <div v-if="backtestStore.tasks.length > 0" class="pagination">
        <button class="btn-small" :disabled="page.value === 0" @click="prevPage">上一页</button>
        <span class="pagination-info">
          {{ page.value * size.value + 1 }} - {{ Math.min((page.value + 1) * size.value, backtestStore.total) }} / {{ backtestStore.total }}
        </span>
        <button class="btn-small" :disabled="(page.value + 1) * size.value >= backtestStore.total" @click="nextPage">下一页</button>
        <select v-model="size.value" @change="loadBacktests" class="page-size-select">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
        </select>
      </div>
    </div>

    <!-- 创建回测模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="resetForm">
      <div class="modal-content">
        <div class="modal-header">
          <h3>创建回测任务</h3>
          <button class="btn-close" @click="resetForm">×</button>
        </div>
        <div class="modal-body">
          <form class="form" @submit.prevent="handleCreate">
            <div class="form-item">
              <label class="form-label">任务名称 <span class="required">*</span></label>
              <input v-model="createForm.name" type="text" placeholder="请输入任务名称" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">选择 Portfolio <span class="required">*</span></label>
              <select v-model="createForm.portfolio_id" class="form-select" placeholder="请选择 Portfolio">
                <option value="">请选择 Portfolio</option>
                <option v-for="p in portfolios" :key="p.uuid" :value="p.uuid">
                  {{ p.name }} ({{ p.mode === 0 ? '回测' : p.mode === 1 ? '模拟' : '实盘' }}) - ¥{{ (p.initial_cash || 0).toLocaleString() }}
                </option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">开始日期 <span class="required">*</span></label>
              <input v-model="createForm.startDate" type="date" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">结束日期 <span class="required">*</span></label>
              <input v-model="createForm.endDate" type="date" class="form-input" />
            </div>
            <div class="form-item">
              <label class="form-label">初始资金</label>
              <input v-model.number="createForm.initialCapital" type="number" min="10000" step="10000" class="form-input" />
            </div>
          </form>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="resetForm">取消</button>
          <button class="btn-primary" :disabled="creating" @click="handleCreate">
            {{ creating ? '创建中...' : '确定' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 净值曲线模态框 -->
    <div v-if="showNetValueModal" class="modal-overlay" @click.self="showNetValueModal = false">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h3>{{ currentTask?.run_id || '' }} 净值曲线</h3>
          <button class="btn-close" @click="showNetValueModal = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="netValueLoading" class="loading-container">
            <div class="spinner"></div>
          </div>
          <div v-else-if="netValueData" class="chart-container" ref="chartRef">
            <p style="text-align: center; padding: 40px; color: #999;">净值曲线图表</p>
          </div>
          <div v-else class="empty-state">
            <p>暂无净值数据</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useBacktestStore, usePortfolioStore } from '@/stores'
import { useWebSocket } from '@/composables'
import { formatPercent, formatDateTime } from '@/utils/format'
import { StatusTag } from '@/components/common'
import type { BacktestTask } from '@/api'
import { BACKTEST_STATES, canStartByState, canStopByState, canCancelByState } from '@/constants/backtest'

const router = useRouter()

// ========== Stores ==========
const backtestStore = useBacktestStore()
const portfolioStore = usePortfolioStore()

// 计算完成和失败任务数量
const completedCount = computed(() =>
  backtestStore.tasks.filter(t => t.status === BACKTEST_STATES.COMPLETED).length
)
const failedCount = computed(() =>
  backtestStore.tasks.filter(t => t.status === BACKTEST_STATES.FAILED).length
)

// ========== 本地状态 ==========
const searchKeyword = ref('')
const filterStatus = ref('')
const showCreateModal = ref(false)
const showNetValueModal = ref(false)
const netValueLoading = ref(false)
const netValueData = ref<any>(null)
const currentTask = ref<BacktestTask | null>(null)
const chartRef = ref<HTMLElement | null>(null)
const creating = ref(false)

// 选中状态
const selectedIds = ref<Set<string>>(new Set())

// 分页参数
const page = ref(0)
const size = ref(20)

// 创建表单
const createForm = reactive({
  name: '',
  portfolio_id: '',
  startDate: '',
  endDate: '',
  initialCapital: 1000000,
})

// 状态选项
const statusOptions = [
  { value: '', label: '全部' },
  { value: 'created', label: '待调度' },
  { value: 'pending', label: '排队中' },
  { value: 'running', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'stopped', label: '已停止' },
  { value: 'failed', label: '失败' },
]

// ========== 计算属性 ==========
const portfolios = computed(() => portfolioStore.portfolios)

// 批量操作权限计算
const canBatchStart = computed(() => {
  return Array.from(selectedIds.value).some(id => {
    const task = backtestStore.tasks.find(t => t.uuid === id)
    return task && canStartByState(task.status) && backtestStore.canStartTask(task)
  })
})

const canBatchStop = computed(() => {
  return Array.from(selectedIds.value).some(id => {
    const task = backtestStore.tasks.find(t => t.uuid === id)
    return task && canStopByState(task.status) && backtestStore.canStopTask(task)
  })
})

const canBatchCancel = computed(() => {
  return Array.from(selectedIds.value).some(id => {
    const task = backtestStore.tasks.find(t => t.uuid === id)
    return task && canCancelByState(task.status) && backtestStore.canCancelTask(task)
  })
})

const isAllSelected = computed(() => {
  return backtestStore.tasks.length > 0 && selectedIds.value.size === backtestStore.tasks.length
})

// ========== 方法 ==========

// 状态检查函数
const canStartTask = (task: BacktestTask) => {
  return canStartByState(task.status)
}

const canStopTask = (task: BacktestTask) => {
  return canStopByState(task.status)
}

const canCancelTask = (task: BacktestTask) => {
  return canCancelByState(task.status)
}

// Tooltip 函数
const getStartTooltip = (task: BacktestTask) => {
  if (!backtestStore.canStartTask(task)) {
    return '你没有权限操作此任务'
  }
  return '重新运行此任务'
}

const getStopTooltip = (task: BacktestTask) => {
  if (!backtestStore.canStopTask(task)) {
    return '你没有权限操作此任务'
  }
  return '停止运行中的任务'
}

const getCancelTooltip = (task: BacktestTask) => {
  if (!backtestStore.canCancelTask(task)) {
    return '你没有权限操作此任务'
  }
  return '取消排队中的任务'
}

// 选择操作
const toggleSelect = (id: string) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value.clear()
  } else {
    backtestStore.tasks.forEach(t => selectedIds.value.add(t.uuid))
  }
}

const clearSelection = () => {
  selectedIds.value.clear()
}

const handleRowClick = (record: BacktestTask) => {
  router.push(`/stage1/backtest/${record.uuid}`)
}

// 分页操作
const prevPage = () => {
  if (page.value > 0) {
    page.value--
    loadBacktests()
  }
}

const nextPage = () => {
  if ((page.value + 1) * size.value < backtestStore.total) {
    page.value++
    loadBacktests()
  }
}

// 批量操作
const handleBatchStart = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canStartByState(t.status)
  )
  if (selectedTasks.length === 0) {
    console.warn('没有可启动的任务')
    return
  }

  const results = await backtestStore.batchStart(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  console.log(failed > 0 ? `批量启动完成：成功 ${succeeded} 个，失败 ${failed} 个` : `成功启动 ${succeeded} 个任务`)
  clearSelection()
  loadBacktests()
}

const handleBatchStop = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canStopByState(t.status)
  )
  if (selectedTasks.length === 0) {
    console.warn('没有可停止的任务')
    return
  }

  const results = await backtestStore.batchStop(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  console.log(failed > 0 ? `批量停止完成：成功 ${succeeded} 个，失败 ${failed} 个` : `成功停止 ${succeeded} 个任务`)
  clearSelection()
  loadBacktests()
}

const handleBatchCancel = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canCancelByState(t.status)
  )
  if (selectedTasks.length === 0) {
    console.warn('没有可取消的任务')
    return
  }

  const results = await backtestStore.batchCancel(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  console.log(failed > 0 ? `批量取消完成：成功 ${succeeded} 个，失败 ${failed} 个` : `成功取消 ${succeeded} 个任务`)
  clearSelection()
  loadBacktests()
}

// 单个任务操作
const handleStart = async (task: BacktestTask) => {
  try {
    let params: { start_date?: string; end_date?: string } = {}
    if (task.config_snapshot) {
      try {
        const config = typeof task.config_snapshot === 'string'
          ? JSON.parse(task.config_snapshot)
          : task.config_snapshot
        params = {
          start_date: config.start_date,
          end_date: config.end_date
        }
      } catch (e) {
        console.warn('Failed to parse config_snapshot:', e)
      }
    }

    await backtestStore.startTask(task.uuid, params)
    console.log('任务已启动')
    loadBacktests()
  } catch (e: any) {
    console.error(e.response?.data?.detail || '启动失败')
  }
}

const handleStop = async (task: BacktestTask) => {
  try {
    await backtestStore.stopTask(task.uuid)
    console.log('任务已停止')
    loadBacktests()
  } catch (e: any) {
    console.error(e.response?.data?.detail || '停止失败')
  }
}

const handleCancel = async (task: BacktestTask) => {
  try {
    await backtestStore.cancelTask(task.uuid)
    console.log('任务已取消')
    loadBacktests()
  } catch (e: any) {
    console.error(e.response?.data?.detail || '取消失败')
  }
}

// 颜色辅助函数
const getPNLColor = (val: string) => {
  const num = parseFloat(val)
  return isNaN(num) ? '#666' : num >= 0 ? '#cf1322' : '#3f8600'
}

const getDrawdownColor = (val: string) => {
  const num = parseFloat(val)
  return isNaN(num) ? '#666' : num <= 0.1 ? '#52c41a' : '#f5222d'
}

const getSharpeColor = (val: string) => {
  const num = parseFloat(val)
  return isNaN(num) ? '#666' : num >= 1 ? '#52c41a' : '#faad14'
}

const loadBacktests = async () => {
  const params: any = { page: page.value, size: size.value }
  if (filterStatus.value) params.status = filterStatus.value
  if (searchKeyword.value) params.keyword = searchKeyword.value
  await backtestStore.fetchList(params)
}

const handleSearch = () => {
  page.value = 0
  loadBacktests()
}

const setStatusFilter = (value: string) => {
  filterStatus.value = value
  loadBacktests()
}

const loadPortfolios = async () => {
  if (portfolioStore.portfolios.length === 0) {
    await portfolioStore.fetchPortfolios()
  }
}

const handleCreate = async () => {
  if (!createForm.name || !createForm.portfolio_id || !createForm.startDate || !createForm.endDate) {
    console.warn('请填写必填项')
    return
  }
  creating.value = true
  try {
    await backtestStore.createTask({
      name: createForm.name,
      portfolio_id: createForm.portfolio_id,
      start_date: createForm.startDate,
      end_date: createForm.endDate,
    })
    console.log('回测任务创建成功')
    showCreateModal.value = false
    resetForm()
    loadBacktests()
  } catch (e: any) {
    console.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

const viewNetValue = async (record: BacktestTask) => {
  currentTask.value = record
  showNetValueModal.value = true
  netValueLoading.value = true
  netValueData.value = null

  try {
    const res = await backtestStore.fetchNetValue(record.uuid)
    netValueData.value = res
    await nextTick()
    renderChart()
  } catch {
    console.error('加载净值数据失败')
  } finally {
    netValueLoading.value = false
  }
}

const renderChart = () => {
  if (!chartRef.value || !netValueData.value) return
  chartRef.value.innerHTML = '<p style="text-align: center; padding: 40px; color: #999;">净值曲线图表</p>'
}

const resetForm = () => {
  showCreateModal.value = false
  createForm.name = ''
  createForm.portfolio_id = ''
  createForm.startDate = ''
  createForm.endDate = ''
  createForm.initialCapital = 1000000
}

const formatDecimal = (val: string) => {
  const num = parseFloat(val)
  return isNaN(num) ? '-' : num.toFixed(2)
}

// ========== 生命周期 ==========
onMounted(() => {
  loadBacktests()
  loadPortfolios()
})

const { subscribe } = useWebSocket()
let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = subscribe('*', (data) => {
    const taskId = data.task_id || data.task_uuid
    if (!taskId) return
    backtestStore.updateProgress({
      task_id: taskId,
      status: data.type === 'progress' ? undefined : data.type,
      progress: data.progress,
    })
  })
})

onUnmounted(() => {
  if (unsubscribe) unsubscribe()
})
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  background: transparent;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 按钮 */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
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
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.link-button {
  background: none;
  border: none;
  color: #1890ff;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;
}

.link-button:hover:not(:disabled) {
  color: #40a9ff;
}

.link-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.link-danger {
  color: #f5222d;
}

.link-danger:hover:not(:disabled) {
  color: #ff4d4f;
}

/* 批量操作栏 */
.batch-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: rgba(24, 144, 255, 0.1);
  border: 1px solid #1890ff;
  border-radius: 8px;
}

.batch-info {
  font-size: 14px;
  color: #1890ff;
  font-weight: 500;
}

.batch-buttons {
  display: flex;
  gap: 8px;
}

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.stat-running {
  color: #52c41a;
}

.stat-failed {
  color: #f5222d;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
}

/* 筛选栏 */
.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  flex-wrap: wrap;
  gap: 16px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-label {
  font-size: 14px;
  color: #8a8a9a;
}

.radio-group {
  display: inline-flex;
  background: #2a2a3e;
  border-radius: 4px;
  padding: 2px;
}

.radio-button {
  padding: 4px 12px;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-button:hover {
  color: #ffffff;
}

.radio-button.active {
  background: #1890ff;
  color: #ffffff;
}

/* 搜索框 */
.search-box {
  display: flex;
  align-items: center;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  overflow: hidden;
}

.search-input {
  padding: 6px 12px;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 13px;
  width: 180px;
  outline: none;
}

.search-input::placeholder {
  color: #8a8a9a;
}

.search-btn {
  padding: 6px 10px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover {
  color: #ffffff;
}

/* 表格容器 */
.table-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
  color: #8a8a9a;
}

/* 自定义表格 */
.custom-table {
  width: 100%;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
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
  font-size: 13px;
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 13px;
}

.data-table tbody tr {
  cursor: pointer;
  transition: background-color 0.2s;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.data-table tbody tr.selected {
  background: rgba(24, 144, 255, 0.1);
}

.checkbox-col {
  width: 40px;
  text-align: center;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-weight: 500;
  color: #ffffff;
}

.task-uuid {
  font-size: 11px;
  color: #8a8a9a;
  font-family: monospace;
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: #2a2a3e;
  border-radius: 2px;
  overflow: hidden;
  min-width: 60px;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 0.3s;
}

.progress-text {
  font-size: 11px;
  color: #1890ff;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  margin-top: 16px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 13px;
}

.page-size-select {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  width: 90%;
  max-width: 500px;
}

.modal-large {
  max-width: 800px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.btn-close {
  background: none;
  border: none;
  color: #8a8a9a;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.modal-body {
  flex: 1;
  overflow: auto;
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
}

/* 表单 */
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 13px;
  color: #ffffff;
  font-weight: 500;
}

.required {
  color: #f5222d;
}

.form-input,
.form-select {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
}

.form-input:focus,
.form-select:focus {
  border-color: #1890ff;
}

.form-input::placeholder {
  color: #8a8a9a;
}

.chart-container {
  padding: 16px 0;
  height: 400px;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .filters-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .radio-group {
    flex-wrap: wrap;
  }
}
</style>
