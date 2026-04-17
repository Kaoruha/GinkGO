<template>
  <div class="backtest-list-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">回测任务</h1>
        <p class="page-subtitle">管理和监控您的所有回测任务</p>
      </div>
      <div class="header-actions">
        <div class="radio-group">
          <label v-for="status in filterOptions" :key="status.value" class="radio-label" :class="{ active: filterStatus === status.value }">
            <input v-model="filterStatus" type="radio" :value="status.value" @change="handleFilterChange" />
            {{ status.label }}
          </label>
        </div>
        <button class="btn-icon" :disabled="refreshing" @click="handleRefresh">
          <svg v-if="!refreshing" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
          </svg>
          <span v-else class="loading-spinner"></span>
        </button>
        <button class="btn-primary" @click="goToCreate">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          创建回测
        </button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.size > 0" class="batch-action-bar">
      <div class="batch-info">
        已选择 <strong>{{ selectedIds.size }}</strong> 项
      </div>
      <div class="batch-actions">
        <button class="btn-small" :disabled="!canBatchStart" :loading="batchOperationLoading" @click="handleBatchStart">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polygon points="10 8 16 12 10 16 10 8"></polygon>
          </svg>
          批量启动
        </button>
        <button class="btn-small" :disabled="!canBatchStop" :loading="batchOperationLoading" @click="handleBatchStop">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="6" width="12" height="12"></rect>
          </svg>
          批量停止
        </button>
        <button class="btn-small" :disabled="!canBatchCancel" :loading="batchOperationLoading" @click="handleBatchCancel">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          批量取消
        </button>
        <button class="btn-small btn-secondary" @click="handleClearSelection">取消选择</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card stat-blue">
        <div class="stat-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">总任务数</div>
          <div class="stat-value">{{ stats.total }}</div>
        </div>
      </div>
      <div class="stat-card stat-green">
        <div class="stat-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">已完成</div>
          <div class="stat-value">{{ stats.completed }}</div>
        </div>
      </div>
      <div class="stat-card stat-orange">
        <div class="stat-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">运行中</div>
          <div class="stat-value">{{ stats.running }}</div>
        </div>
      </div>
      <div class="stat-card stat-red">
        <div class="stat-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">失败</div>
          <div class="stat-value">{{ stats.failed }}</div>
        </div>
      </div>
    </div>

    <!-- 回测任务列表 -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
    </div>
    <div v-else-if="tasks.length === 0" class="empty-container">
      <p>暂无回测任务</p>
      <button class="btn-primary" @click="goToCreate">创建第一个回测任务</button>
    </div>
    <div v-else class="table-card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th style="width: 40px">
                <input type="checkbox" :checked="selectedIds.size > 0 && selectedIds.size === tasks.length" @change="toggleSelectAll" />
              </th>
              <th>任务名称</th>
              <th>状态</th>
              <th>进度</th>
              <th>创建时间</th>
              <th>运行时长</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in tasks" :key="record.uuid">
              <td>
                <input type="checkbox" :checked="selectedIds.has(record.uuid)" :disabled="!canOperateTask(record)" @change="toggleSelect(record.uuid)" />
              </td>
              <td>
                <div class="name-cell">
                  <span class="task-name">{{ record.name }}</span>
                  <span class="portfolio-name">{{ record.portfolio_name }}</span>
                </div>
              </td>
              <td>
                <span class="tag" :class="getStatusTagClass(record.status)">{{ getStatusLabel(record.status) }}</span>
              </td>
              <td>
                <div class="progress-bar">
                  <div class="progress-fill" :class="getProgressClass(record.status)" :style="{ width: record.progress + '%' }"></div>
                </div>
                <span class="progress-text">{{ record.progress }}%</span>
              </td>
              <td>{{ formatDate(record.created_at) }}</td>
              <td>{{ formatDuration(record.started_at, record.completed_at) }}</td>
              <td>
                <div class="action-links">
                  <a class="link" @click="viewDetail(record)">查看详情</a>
                  <template v-if="!canOperateTask(record)">
                    <span class="disabled-action">无权限</span>
                  </template>
                  <template v-else>
                    <a v-if="canStartTask(record)" class="link" @click="handleStart(record)">启动</a>
                    <a v-if="canStopTask(record)" class="link" @click="handleStop(record)">停止</a>
                    <a v-if="canCancelTask(record)" class="link" @click="handleCancel(record)">取消</a>
                    <a v-if="canDeleteTask(record)" class="link link-danger" @click="handleDelete(record)">删除</a>
                  </template>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <div class="pagination-info">共 {{ tasks.length }} 条</div>
        <div class="pagination-controls">
          <button class="pagination-btn" :disabled="currentPage === 1" @click="currentPage--">上一页</button>
          <span class="pagination-current">{{ currentPage }}</span>
          <button class="pagination-btn" :disabled="currentPage >= totalPages" @click="currentPage++">下一页</button>
        </div>
      </div>
    </div>

    <!-- 结果弹窗 -->
    <div v-if="showResultModal" class="modal-overlay" @click.self="showResultModal = false">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>回测结果</h3>
          <button class="modal-close" @click="showResultModal = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="selectedBacktest" class="result-content">
            <div class="result-info">
              <div class="info-row">
                <span class="info-label">任务名称</span>
                <span class="info-value">{{ selectedBacktest.name }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">投资组合</span>
                <span class="info-value">{{ selectedBacktest.portfolio_name }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">开始日期</span>
                <span class="info-value">{{ selectedBacktest.config?.start_date }}</span>
              </div>
              <div class="info-row">
                <span class="info-label">结束日期</span>
                <span class="info-value">{{ selectedBacktest.config?.end_date }}</span>
              </div>
            </div>

            <div v-if="selectedBacktest.result" class="result-stats">
              <div class="result-stat">
                <span class="stat-label">总收益率</span>
                <span class="stat-value" :class="getChangeClass(selectedBacktest.result.total_return)">
                  {{ (selectedBacktest.result.total_return * 100).toFixed(2) }}%
                </span>
              </div>
              <div class="result-stat">
                <span class="stat-label">年化收益率</span>
                <span class="stat-value" :class="getChangeClass(selectedBacktest.result.annual_return)">
                  {{ (selectedBacktest.result.annual_return * 100).toFixed(2) }}%
                </span>
              </div>
              <div class="result-stat">
                <span class="stat-label">夏普比率</span>
                <span class="stat-value">{{ selectedBacktest.result.sharpe_ratio.toFixed(2) }}</span>
              </div>
              <div class="result-stat">
                <span class="stat-label">最大回撤</span>
                <span class="stat-value value-down">
                  {{ (selectedBacktest.result.max_drawdown * 100).toFixed(2) }}%
                </span>
              </div>
              <div class="result-stat">
                <span class="stat-label">胜率</span>
                <span class="stat-value">{{ (selectedBacktest.result.win_rate * 100).toFixed(2) }}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 确认对话框 -->
    <div v-if="confirmModalVisible" class="modal-overlay" @click.self="confirmModalVisible = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>{{ confirmModal.title }}</h3>
          <button class="modal-close" @click="confirmModalVisible = false">×</button>
        </div>
        <div class="modal-body">
          <p>{{ confirmModal.content }}</p>
          <div class="form-actions">
            <button class="btn-primary" @click="confirmModal.onOk">确定</button>
            <button class="btn-secondary" @click="confirmModalVisible = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'

const router = useRouter()

// 模拟数据和状态
const loading = ref(false)
const refreshing = ref(false)
const batchOperationLoading = ref(false)
const tasks = ref<any[]>([
  {
    uuid: '1',
    name: '双均线策略回测',
    portfolio_name: '测试组合',
    status: 'completed',
    progress: 100,
    created_at: '2024-01-10 09:30:00',
    started_at: '2024-01-10 09:30:00',
    completed_at: '2024-01-10 10:30:00',
    config: { start_date: '2023-01-01', end_date: '2023-12-31' },
    result: {
      total_return: 0.256,
      annual_return: 0.183,
      sharpe_ratio: 1.25,
      max_drawdown: -0.125,
      win_rate: 0.583
    }
  },
  {
    uuid: '2',
    name: '因子策略回测',
    portfolio_name: '因子组合',
    status: 'running',
    progress: 65,
    created_at: '2024-01-10 14:00:00',
    started_at: '2024-01-10 14:00:00'
  }
])

const filterStatus = ref<string>('')
const selectedIds = ref<Set<string>>(new Set())
const showResultModal = ref(false)
const selectedBacktest = ref<any>(null)

const currentPage = ref(1)
const totalPages = ref(1)

// 确认对话框
const confirmModalVisible = ref(false)
const confirmModal = ref({
  title: '',
  content: '',
  onOk: () => {}
})

const filterOptions = [
  { value: '', label: '全部' },
  { value: 'pending', label: '排队中' },
  { value: 'running', label: '进行中' },
  { value: 'completed', label: '已完成' }
]

const stats = ref({
  total: 156,
  completed: 142,
  running: 8,
  failed: 6
})

// 批量操作权限判断
const canBatchStart = computed(() => {
  return Array.from(selectedIds.value).some(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canStartTask(task)
  })
})

const canBatchStop = computed(() => {
  return Array.from(selectedIds.value).some(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canStopTask(task)
  })
})

const canBatchCancel = computed(() => {
  return Array.from(selectedIds.value).some(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canCancelTask(task)
  })
})

// 辅助函数
const getStatusTagClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'tag-gray',
    running: 'tag-blue',
    completed: 'tag-green',
    failed: 'tag-red',
    cancelled: 'tag-orange'
  }
  return classes[status] || 'tag-gray'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '排队中',
    running: '进行中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const getProgressClass = (status: string) => {
  if (status === 'failed') return 'progress-error'
  if (status === 'completed') return 'progress-success'
  return 'progress-active'
}

const getChangeClass = (value: number) => {
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return 'value-flat'
}

const canOperateTask = (task: any) => true
const canStartTask = (task: any) => task.status === 'pending' || task.status === 'cancelled'
const canStopTask = (task: any) => task.status === 'running'
const canCancelTask = (task: any) => task.status === 'pending' || task.status === 'running'
const canDeleteTask = (task: any) => task.status === 'completed' || task.status === 'failed' || task.status === 'cancelled'

// 事件处理
const handleFilterChange = () => {
  console.log('筛选变化:', filterStatus.value)
}

const handleRefresh = async () => {
  refreshing.value = true
  await new Promise(resolve => setTimeout(resolve, 1000))
  refreshing.value = false
}

const handleSelectionChange = (selectedKeys: string[]) => {
  selectedIds.value = new Set(selectedKeys)
}

const toggleSelect = (uuid: string) => {
  if (selectedIds.value.has(uuid)) {
    selectedIds.value.delete(uuid)
  } else {
    selectedIds.value.add(uuid)
  }
}

const toggleSelectAll = () => {
  if (selectedIds.value.size === tasks.value.length) {
    selectedIds.value.clear()
  } else {
    tasks.value.forEach(t => selectedIds.value.add(t.uuid))
  }
}

const handleClearSelection = () => {
  selectedIds.value.clear()
}

const showConfirm = (title: string, content: string, onOk: () => void | Promise<void>) => {
  confirmModal.value = { title, content, onOk }
  confirmModalVisible.value = true
}

const handleBatchStart = async () => {
  showConfirm('确认批量启动', `确定要启动 ${selectedIds.value.size} 个回测任务吗？`, async () => {
    console.log('批量启动:', Array.from(selectedIds.value))
    handleClearSelection()
  })
}

const handleBatchStop = async () => {
  showConfirm('确认批量停止', `确定要停止 ${selectedIds.value.size} 个回测任务吗？`, async () => {
    console.log('批量停止:', Array.from(selectedIds.value))
    handleClearSelection()
  })
}

const handleBatchCancel = async () => {
  showConfirm('确认批量取消', `确定要取消 ${selectedIds.value.size} 个回测任务吗？`, async () => {
    console.log('批量取消:', Array.from(selectedIds.value))
    handleClearSelection()
  })
}

const goToCreate = () => {
  router.push('/backtest/create')
}

const viewDetail = (task: any) => {
  router.push(`/backtest/${task.uuid}`)
}

const handleStart = (task: any) => {
  showConfirm('确认启动', `确定要启动回测任务"${task.name}"吗？`, async () => {
    console.log('启动任务:', task.uuid)
    task.status = 'running'
  })
}

const handleStop = (task: any) => {
  showConfirm('确认停止', `确定要停止回测任务"${task.name}"吗？`, async () => {
    console.log('停止任务:', task.uuid)
    task.status = 'stopped'
  })
}

const handleCancel = (task: any) => {
  showConfirm('确认取消', `确定要取消回测任务"${task.name}"吗？`, async () => {
    console.log('取消任务:', task.uuid)
    task.status = 'cancelled'
  })
}

const handleDelete = (task: any) => {
  showConfirm('确认删除', `确定要删除回测任务"${task.name}"吗？此操作不可恢复。`, async () => {
    console.log('删除任务:', task.uuid)
    const idx = tasks.value.findIndex(t => t.uuid === task.uuid)
    if (idx > -1) tasks.value.splice(idx, 1)
  })
}

const formatDate = (date: string) => {
  return date
}

const formatDuration = (startAt?: string, endAt?: string) => {
  if (!startAt) return '-'
  const start = dayjs(startAt)
  const end = endAt ? dayjs(endAt) : dayjs()
  const duration = end.diff(start, 'second')

  if (duration < 60) return `${duration}秒`
  if (duration < 3600) return `${Math.floor(duration / 60)}分钟`
  return `${Math.floor(duration / 3600)}小时${Math.floor((duration % 3600) / 60)}分钟`
}

onMounted(() => {
  // 初始化
})

onUnmounted(() => {
  // 清理
})
</script>

<style scoped>
.backtest-list-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left .page-title {
  font-size: 28px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.header-left .page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.radio-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.radio-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-label:hover {
  border-color: #3a3a4e;
}

.radio-label.active {
  background: #1890ff;
  border-color: #1890ff;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-small:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.batch-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 12px;
}

.batch-info {
  font-size: 14px;
  color: #ffffff;
}

.batch-info strong {
  color: #1890ff;
  font-size: 16px;
}

.batch-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-icon {
  flex-shrink: 0;
  padding: 12px;
  border-radius: 8px;
}

.stat-blue .stat-icon { color: #1890ff; background: rgba(24, 144, 255, 0.1); }
.stat-green .stat-icon { color: #52c41a; background: rgba(82, 196, 26, 0.1); }
.stat-orange .stat-icon { color: #fa8c16; background: rgba(250, 140, 22, 0.1); }
.stat-red .stat-icon { color: #f5222d; background: rgba(245, 34, 45, 0.1); }

.empty-container {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-container p {
  margin: 0 0 16px 0;
}

.table-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
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
  border-bottom: 1px solid #2a2a3e;
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

.data-table input[type="checkbox"] {
  cursor: pointer;
}

.name-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-weight: 500;
}

.portfolio-name {
  font-size: 12px;
  color: #8a8a9a;
}

.progress-bar {
  display: inline-block;
  width: 80px;
  height: 6px;
  background: #2a2a3e;
  border-radius: 3px;
  overflow: hidden;
  margin-right: 8px;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s;
}

.progress-success { background: #52c41a; }
.progress-error { background: #f5222d; }
.progress-active { background: #1890ff; }

.progress-text {
  font-size: 12px;
  color: #ffffff;
}

.action-links {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.link {
  color: #1890ff;
  cursor: pointer;
  font-size: 13px;
}

.link:hover {
  text-decoration: underline;
}

.disabled-action {
  color: #5a5a6e;
  font-size: 13px;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.pagination-btn {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  color: #ffffff;
  font-size: 14px;
}

/* 模态框样式 */

.result-content {
  padding: 16px 0;
}

.result-info {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
}

.info-label {
  font-weight: 500;
  color: #8a8a9a;
}

.info-value {
  color: #ffffff;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.result-stat {
  padding: 16px;
  background: #2a2a3e;
  border-radius: 8px;
  text-align: center;
}

.result-stat .stat-label {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.result-stat .stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .result-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
  }

  .radio-group {
    width: 100%;
    justify-content: center;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .result-info {
    grid-template-columns: 1fr;
  }

  .result-stats {
    grid-template-columns: 1fr;
  }

  .batch-action-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .batch-actions {
    flex-direction: column;
  }
}
</style>
