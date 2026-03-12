<template>
  <div class="page-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-title">回测任务</div>
      <div class="header-actions">
        <a-button @click="loadBacktests">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="showCreateModal = true">
          <template #icon><PlusOutlined /></template>
          创建回测
        </a-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.size > 0" class="batch-action-bar">
      <div class="batch-info">已选择 {{ selectedIds.size }} 个任务</div>
      <div class="batch-buttons">
        <a-button size="small" :disabled="!canBatchStart" @click="handleBatchStart">批量启动</a-button>
        <a-button size="small" :disabled="!canBatchStop" @click="handleBatchStop">批量停止</a-button>
        <a-button size="small" :disabled="!canBatchCancel" @click="handleBatchCancel">批量取消</a-button>
        <a-button size="small" @click="clearSelection">取消选择</a-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :span="6">
        <a-statistic title="总任务数" :value="backtestStore.total" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="已完成" :value="completedCount" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="运行中" :value="backtestStore.runningCount" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="失败" :value="failedCount" />
      </a-col>
    </a-row>

    <!-- 筛选器 -->
    <div v-show="selectedIds.size === 0" class="filters-bar">
      <a-space>
        <span>状态:</span>
        <a-radio-group v-model:value="filterStatus" button-style="solid" size="small" @change="loadBacktests">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="created">待调度</a-radio-button>
          <a-radio-button value="pending">排队中</a-radio-button>
          <a-radio-button value="running">进行中</a-radio-button>
          <a-radio-button value="completed">已完成</a-radio-button>
          <a-radio-button value="stopped">已停止</a-radio-button>
          <a-radio-button value="failed">失败</a-radio-button>
        </a-radio-group>
      </a-space>
      <a-input-search
        v-model:value="searchKeyword"
        placeholder="搜索任务..."
        style="width: 200px; margin-left: auto"
        allow-clear
        @search="handleSearch"
      />
    </div>

    <!-- 任务列表 -->
    <div class="table-container">
      <a-table
        :columns="columns"
        :data-source="backtestStore.tasks"
        :loading="backtestStore.loading"
        :pagination="pagination"
        :row-selection="rowSelection"
        row-key="uuid"
        @change="handleTableChange"
      >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'task_info'">
          <div class="task-info">
            <div class="task-name">{{ record.name || '(未命名)' }}</div>
            <div class="task-uuid">{{ record.uuid }}</div>
          </div>
        </template>
        <template v-else-if="column.key === 'status'">
          <div class="status-cell">
            <StatusTag :status="record.status" type="backtest" />
            <a-progress
              v-if="record.status === 'running' || record.status === 'pending'"
              :percent="record.progress || 0"
              :show-info="false"
              :stroke-color="record.status === 'running' ? '#1890ff' : '#52c41a'"
              size="small"
              style="margin-top: 4px; max-width: 100px;"
            />
            <span
              v-if="record.status === 'running' || record.status === 'pending'"
              class="progress-text"
            >
              {{ (record.progress || 0).toFixed(1) }}%
            </span>
          </div>
        </template>
        <template v-else-if="column.key === 'total_pnl'">
          <span :style="{ color: getPNLColor(record.total_pnl) }">
            {{ formatDecimal(record.total_pnl) }}
          </span>
        </template>
        <template v-else-if="column.key === 'max_drawdown'">
          <span :style="{ color: getDrawdownColor(record.max_drawdown) }">
            {{ formatPercent(record.max_drawdown) }}
          </span>
        </template>
        <template v-else-if="column.key === 'sharpe_ratio'">
          <span :style="{ color: getSharpeColor(record.sharpe_ratio) }">
            {{ formatDecimal(record.sharpe_ratio) }}
          </span>
        </template>
        <template v-else-if="column.key === 'create_at'">
          {{ formatDateTime(record.create_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <!-- 启动按钮：已完成/失败/已停止状态显示 -->
            <a-tooltip v-if="canStartTask(record)" :title="getStartTooltip(record)">
              <a-button
                type="link"
                size="small"
                :disabled="!backtestStore.canStartTask(record)"
                @click="handleStart(record)"
              >
                启动
              </a-button>
            </a-tooltip>
            <!-- 停止按钮：进行中状态显示 -->
            <a-tooltip v-if="canStopTask(record)" :title="getStopTooltip(record)">
              <a-button
                type="link"
                size="small"
                danger
                :disabled="!backtestStore.canStopTask(record)"
                @click="handleStop(record)"
              >
                停止
              </a-button>
            </a-tooltip>
            <!-- 取消按钮：created/pending 状态显示 -->
            <a-tooltip v-if="canCancelTask(record)" :title="getCancelTooltip(record)">
              <a-button
                type="link"
                size="small"
                :disabled="!backtestStore.canCancelTask(record)"
                @click="handleCancel(record)"
              >
                取消
              </a-button>
            </a-tooltip>
            <a-button type="link" size="small" @click="router.push(`/stage1/backtest/${record.uuid}`)">
              查看详情
            </a-button>
          </a-space>
        </template>
      </template>
    </a-table>
    </div>

  <!-- 创建回测模态框 -->
  <a-modal
    v-model:open="showCreateModal"
    title="创建回测任务"
    width="600px"
    :confirm-loading="creating"
    @ok="handleCreate"
    @cancel="resetForm"
  >
    <a-form :model="createForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
      <a-form-item label="任务名称" required>
        <a-input v-model:value="createForm.name" placeholder="请输入任务名称" />
      </a-form-item>
      <a-form-item label="选择 Portfolio" required>
        <a-select
          v-model:value="createForm.portfolio_id"
          placeholder="请选择 Portfolio"
          show-search
          :filter-option="filterPortfolio"
          :options="portfolioOptions"
        >
        </a-select>
      </a-form-item>
      <a-form-item label="开始日期" required>
        <a-date-picker v-model:value="createForm.startDate" style="width: 100%" />
      </a-form-item>
      <a-form-item label="结束日期" required>
        <a-date-picker v-model:value="createForm.endDate" style="width: 100%" />
      </a-form-item>
      <a-form-item label="初始资金">
        <a-input-number v-model:value="createForm.initialCapital" :min="10000" :step="10000" style="width: 100%" />
      </a-form-item>
    </a-form>
  </a-modal>

  <!-- 净值曲线模态框 -->
  <a-modal
    v-model:open="showNetValueModal"
    :title="`${currentTask?.run_id || ''} 净值曲线`"
    width="800px"
    :footer="null"
  >
    <div v-if="netValueLoading" class="loading-container">
      <a-spin />
    </div>
    <div v-else-if="netValueData" class="net-value-chart">
      <div ref="chartRef" style="height: 400px;"></div>
    </div>
    <a-empty v-else description="暂无净值数据" />
  </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons-vue'
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
  startDate: null as any,
  endDate: null as any,
  initialCapital: 1000000,
})

// ========== 计算属性 ==========
const pagination = computed(() => ({
  current: page.value + 1,
  pageSize: size.value,
  total: backtestStore.total,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (t: number) => `共 ${t} 条`,
}))

const portfolios = computed(() => portfolioStore.portfolios)

// Portfolio 选择器选项（带格式化标签）
const portfolioOptions = computed(() =>
  portfolioStore.portfolios.map(p => ({
    label: `${p.name} (${p.mode === 0 ? '回测' : p.mode === 1 ? '模拟' : '实盘'}) - ¥${(p.initial_cash || 0).toLocaleString()}`,
    value: p.uuid
  }))
)

// Portfolio 搜索过滤
const filterPortfolio = (input: string, option: { label: string; value: string }) => {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

// 表格列
const columns = [
  { title: '任务', key: 'task_info', width: 220 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 120 },
  { title: '总盈亏', dataIndex: 'total_pnl', key: 'total_pnl', width: 100 },
  { title: '订单数', dataIndex: 'total_orders', key: 'total_orders', width: 70 },
  { title: '信号数', dataIndex: 'total_signals', key: 'total_signals', width: 70 },
  { title: '创建时间', dataIndex: 'create_at', key: 'create_at', width: 160 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

// 行选择配置
const rowSelection = computed(() => ({
  selectedRowKeys: Array.from(selectedIds.value),
  onChange: (keys: any[]) => {
    selectedIds.value = new Set(keys)
  },
}))

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

// 批量操作
const clearSelection = () => {
  selectedIds.value.clear()
}

const handleBatchStart = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canStartByState(t.status)
  )
  if (selectedTasks.length === 0) {
    message.warning('没有可启动的任务')
    return
  }

  const results = await backtestStore.batchStart(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  if (failed > 0) {
    message.warning(`批量启动完成：成功 ${succeeded} 个，失败 ${failed} 个`)
  } else {
    message.success(`成功启动 ${succeeded} 个任务`)
  }
  clearSelection()
  loadBacktests()
}

const handleBatchStop = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canStopByState(t.status)
  )
  if (selectedTasks.length === 0) {
    message.warning('没有可停止的任务')
    return
  }

  const results = await backtestStore.batchStop(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  if (failed > 0) {
    message.warning(`批量停止完成：成功 ${succeeded} 个，失败 ${failed} 个`)
  } else {
    message.success(`成功停止 ${succeeded} 个任务`)
  }
  clearSelection()
  loadBacktests()
}

const handleBatchCancel = async () => {
  const selectedTasks = backtestStore.tasks.filter(t =>
    selectedIds.value.has(t.uuid) && canCancelByState(t.status)
  )
  if (selectedTasks.length === 0) {
    message.warning('没有可取消的任务')
    return
  }

  const results = await backtestStore.batchCancel(selectedTasks.map(t => t.uuid))
  const succeeded = results.filter(r => r.success).length
  const failed = results.length - succeeded

  if (failed > 0) {
    message.warning(`批量取消完成：成功 ${succeeded} 个，失败 ${failed} 个`)
  } else {
    message.success(`成功取消 ${succeeded} 个任务`)
  }
  clearSelection()
  loadBacktests()
}

// 单个任务操作
const handleStart = async (task: BacktestTask) => {
  try {
    // 从配置快照中解析日期参数
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
    message.success('任务已启动')
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '启动失败')
  }
}

const handleStop = async (task: BacktestTask) => {
  try {
    await backtestStore.stopTask(task.uuid)
    message.success('任务已停止')
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '停止失败')
  }
}

const handleCancel = async (task: BacktestTask) => {
  try {
    await backtestStore.cancelTask(task.uuid)
    message.success('任务已取消')
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '取消失败')
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

const loadPortfolios = async () => {
  if (portfolioStore.portfolios.length === 0) {
    await portfolioStore.fetchPortfolios()
  }
}

const handleTableChange = (pag: any) => {
  page.value = pag.current - 1
  size.value = pag.pageSize
  loadBacktests()
}

// 从回测任务中提取日期参数（用于复制功能）
const extractStartDate = (task: BacktestTask): string => {
  if (task.config_snapshot) {
    try {
      const config = JSON.parse(task.config_snapshot)
      return config.start_date || config.backtest_start_date || ''
    } catch {
      return task.start_time ? task.start_time.split('T')[0] : ''
    }
  }
  return task.start_time ? task.start_time.split('T')[0] : ''
}

const extractEndDate = (task: BacktestTask): string => {
  if (task.config_snapshot) {
    try {
      const config = JSON.parse(task.config_snapshot)
      return config.end_date || config.backtest_end_date || ''
    } catch {
      return task.end_time ? task.end_time.split('T')[0] : ''
    }
  }
  return task.end_time ? task.end_time.split('T')[0] : ''
}

const extractInitialCash = (task: BacktestTask): number => {
  if (task.config_snapshot) {
    try {
      const config = JSON.parse(task.config_snapshot)
      return config.initial_cash || config.initial_capital || 100000
    } catch {
      return 100000
    }
  }
  return 100000
}

const handleCreate = async () => {
  if (!createForm.name || !createForm.portfolio_id || !createForm.startDate || !createForm.endDate) {
    message.warning('请填写必填项')
    return
  }
  creating.value = true
  try {
    // 格式化日期为 YYYY-MM-DD
    const formatDate = (date: any) => {
      if (!date) return ''
      if (typeof date === 'string') return date
      if (date.format) return date.format('YYYY-MM-DD')
      return new Date(date).toISOString().split('T')[0]
    }

    await backtestStore.createTask({
      name: createForm.name,
      portfolio_id: createForm.portfolio_id,
      start_date: formatDate(createForm.startDate),
      end_date: formatDate(createForm.endDate),
    })
    message.success('回测任务创建成功')
    showCreateModal.value = false
    resetForm()
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
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
    message.error('加载净值数据失败')
  } finally {
    netValueLoading.value = false
  }
}

const renderChart = () => {
  if (!chartRef.value || !netValueData.value) return
  chartRef.value.innerHTML = '<p style="text-align: center; padding: 40px; color: #999;">净值曲线图表</p>'
}

const resetForm = () => {
  createForm.name = ''
  createForm.portfolio_id = ''
  createForm.startDate = null
  createForm.endDate = null
  createForm.initialCapital = 1000000
}

const formatDecimal = (val: string) => {
  const num = parseFloat(val)
  return isNaN(num) ? '-' : num.toFixed(2)
}

const customRow = (record: BacktestTask) => ({
  style: { cursor: 'pointer' },
  onClick: () => router.push(`/stage1/backtest/${record.uuid}`),
})

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
  height: calc(100vh - 64px);
  padding: 24px;
  background: #f0f2f5;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #262626;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.batch-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: #e6f7ff;
  border: 1px solid #91d5ff;
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

.stats-row {
  margin-bottom: 16px;
}

.stats-row :deep(.ant-statistic) {
  background: white;
  padding: 16px;
  border-radius: 8px;
}

.filters-bar {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: white;
  border-radius: 8px;
}

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-weight: 500;
  color: #262626;
}

.task-uuid {
  font-size: 11px;
  color: #8c8c8c;
  font-family: monospace;
}

.status-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}

.progress-text {
  font-size: 11px;
  color: #1890ff;
  font-weight: 500;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
}

.net-value-chart {
  padding: 16px 0;
}

.table-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

:deep(.ant-table-wrapper) {
  background: white;
  border-radius: 8px;
  padding: 16px;
}

:deep(.ant-table-tbody > tr:hover) {
  background-color: #e6f4ff;
}
</style>
