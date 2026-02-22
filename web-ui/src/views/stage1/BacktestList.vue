<template>
  <div class="backtest-list-page">
    <!-- 固定的页面头部区域 -->
    <div class="fixed-header">
      <div class="page-header">
        <div class="header-left">
          <h1>策略回测</h1>
          <a-tag color="blue">{{ total }} 个任务</a-tag>
        </div>
        <div class="header-right">
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索任务..."
            style="width: 200px"
            allow-clear
          />
          <a-button type="primary" @click="showCreateModal = true">
            <template #icon><PlusOutlined /></template>
            创建回测
          </a-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <a-radio-group v-model:value="filterStatus" button-style="solid" size="small" @change="loadBacktests">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="created">待启动</a-radio-button>
          <a-radio-button value="pending">等待中</a-radio-button>
          <a-radio-button value="running">运行中</a-radio-button>
          <a-radio-button value="completed">已完成</a-radio-button>
          <a-radio-button value="failed">失败</a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <!-- 可滚动的内容区域 -->
    <div class="scrollable-content table-fill-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
      </div>

      <!-- 空状态 -->
      <a-empty v-else-if="filteredBacktests.length === 0" description="暂无回测任务">
        <a-button type="primary" @click="showCreateModal = true">创建第一个回测</a-button>
      </a-empty>

      <!-- 回测列表 -->
      <a-table
        v-else
        :columns="columns"
        :data-source="filteredBacktests"
        :loading="loading"
        :pagination="pagination"
        row-key="uuid"
        :custom-row="customRow"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'task_info'">
            <div>
              <div class="task-name">{{ record.name || '(未命名)' }}</div>
              <div class="task-uuid">{{ record.uuid }}</div>
            </div>
          </template>
          <template v-else-if="column.key === 'status'">
            <div class="status-cell">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusLabel(record.status) }}
              </a-tag>
              <!-- 运行中显示进度条 -->
              <a-progress
                v-if="record.status === 'running' || record.status === 'pending'"
                :percent="record.progress || 0"
                :show-info="true"
                :stroke-color="{ '0%': '#108ee9', '100%': '#87d068' }"
                size="small"
                style="width: 80px; margin-left: 8px;"
              />
            </div>
          </template>
          <template v-else-if="column.key === 'total_pnl'">
            <span :style="{ color: parseFloat(record.total_pnl) >= 0 ? '#52c41a' : '#f5222d' }">
              {{ formatPnL(record.total_pnl) }}
            </span>
          </template>
          <template v-else-if="column.key === 'max_drawdown'">
            <span :style="{ color: parseFloat(record.max_drawdown) <= 0.1 ? '#52c41a' : '#f5222d' }">
              {{ formatPercent(record.max_drawdown) }}
            </span>
          </template>
          <template v-else-if="column.key === 'sharpe_ratio'">
            <span :style="{ color: parseFloat(record.sharpe_ratio) >= 1 ? '#52c41a' : '#faad14' }">
              {{ formatDecimal(record.sharpe_ratio) }}
            </span>
          </template>
          <template v-else-if="column.key === 'duration'">
            {{ formatDuration(record.duration_seconds) }}
          </template>
          <template v-else-if="column.key === 'start_time'">
            {{ formatDateTime(record.start_time) }}
          </template>
          <template v-else-if="column.key === 'create_at'">
            {{ formatDateTime(record.create_at) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space @click.stop>
              <!-- 停止按钮：仅对 running 状态显示 -->
              <a-popconfirm
                v-if="record.status === 'running'"
                title="确定要停止此回测任务吗？"
                @confirm="handleStop(record)"
              >
                <a-button type="link" size="small" danger @click.stop>停止</a-button>
              </a-popconfirm>
              <a-button type="link" size="small" @click.stop="viewDetail(record)">
                详情
              </a-button>
              <a-button type="link" size="small" @click.stop="viewNetValue(record)">
                净值曲线
              </a-button>
              <a-popconfirm
                title="确定要删除此回测任务吗？"
                @confirm="handleDelete(record.uuid)"
              >
                <a-button type="link" size="small" danger @click.stop>
                  删除
                </a-button>
              </a-popconfirm>
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
          <a-select v-model:value="createForm.portfolio_id" placeholder="请选择 Portfolio">
            <a-select-option v-for="p in portfolios" :key="p.uuid" :value="p.uuid">
              {{ p.name }}
            </a-select-option>
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
import { PlusOutlined } from '@ant-design/icons-vue'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'
import { portfolioApi } from '@/api/modules/portfolio'
import { useWebSocket, useBacktestStatus, useListPage, commonSearchFilters } from '@/composables'
import { formatPercent, formatDuration, formatDateTime } from '@/utils/format'

const router = useRouter()

// 状态格式化
const { getColor: getStatusColor, getLabel: getStatusLabel } = useBacktestStatus()

// 列表页逻辑
const {
  loading,
  data: backtests,
  total,
  page,
  size,
  searchKeyword,
  pagination,
  filteredData: filteredBacktests,
  handleTableChange: baseHandleTableChange,
} = useListPage<BacktestTask, { page: number; size: number; status?: string }>({
  fetchFn: async (params) => {
    const res = await backtestApi.list(params)
    return { data: res.data || [], total: res.total || 0 }
  },
  defaultPageSize: 20,
  searchFilter: commonSearchFilters.byNameAndUuid,
})

// 额外状态
const creating = ref(false)
const portfolios = ref<any[]>([])
const filterStatus = ref('')
const showCreateModal = ref(false)
const showNetValueModal = ref(false)
const netValueLoading = ref(false)
const netValueData = ref<any>(null)
const currentTask = ref<BacktestTask | null>(null)
const chartRef = ref<HTMLElement | null>(null)

// 创建表单
const createForm = reactive({
  name: '',
  portfolio_id: '',
  startDate: null as any,
  endDate: null as any,
  initialCapital: 1000000,
})

// 表格列
const columns = [
  { title: '任务', key: 'task_info', width: 220 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 180 },
  { title: '总盈亏', dataIndex: 'total_pnl', key: 'total_pnl', width: 100 },
  { title: '订单数', dataIndex: 'total_orders', key: 'total_orders', width: 70 },
  { title: '信号数', dataIndex: 'total_signals', key: 'total_signals', width: 70 },
  { title: '创建时间', dataIndex: 'create_at', key: 'create_at', width: 140 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

// 加载回测列表（带筛选）
const loadBacktests = async () => {
  const params: any = {}
  if (filterStatus.value) {
    params.status = filterStatus.value
  }
  await (loading as any).value || loading
  // 直接调用 API 以支持筛选参数
  loading.value = true
  try {
    const res = await backtestApi.list({
      page: page.value,
      size: size.value,
      ...params,
    })
    backtests.value = res.data || []
    total.value = res.total || 0
  } catch (e: any) {
    console.error('Failed to load backtests:', e)
    message.error('加载回测列表失败')
  } finally {
    loading.value = false
  }
}

// 加载投资组合列表（用于创建表单）
const loadPortfolios = async () => {
  try {
    const res = await portfolioApi.list({ page: 0, size: 100 })
    portfolios.value = res.data || []
  } catch (e) {
    console.error('Failed to load portfolios:', e)
  }
}

// 表格变化处理（需要重新加载数据）
const handleTableChange = (pag: any) => {
  baseHandleTableChange(pag)
  loadBacktests()
}

// 创建回测
const handleCreate = async () => {
  if (!createForm.name || !createForm.portfolio_id || !createForm.startDate || !createForm.endDate) {
    message.warning('请填写必填项')
    return
  }

  creating.value = true
  try {
    const taskId = `BT_${Date.now()}`
    await backtestApi.create({
      name: createForm.name,
      run_id: taskId,
      portfolio_id: createForm.portfolio_id,
      start_date: createForm.startDate?.format('YYYY-MM-DD'),
      end_date: createForm.endDate?.format('YYYY-MM-DD'),
      config_snapshot: {
        initial_capital: createForm.initialCapital,
      },
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

// 删除回测
const handleDelete = async (uuid: string) => {
  try {
    await backtestApi.delete(uuid)
    message.success('删除成功')
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

// 停止回测
const handleStop = async (record: BacktestTask) => {
  try {
    await backtestApi.stop(record.uuid)
    message.success('回测任务已停止')
    loadBacktests()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '停止失败')
  }
}

// 查看详情
const viewDetail = (record: BacktestTask) => {
  router.push(`/stage1/backtest/${record.uuid}`)
}

// 表格行点击配置
const customRow = (record: BacktestTask) => ({
  style: { cursor: 'pointer' },
  onClick: () => viewDetail(record),
})

// 查看净值曲线
const viewNetValue = async (record: BacktestTask) => {
  currentTask.value = record
  showNetValueModal.value = true
  netValueLoading.value = true
  netValueData.value = null

  try {
    const res = await backtestApi.getNetValue(record.uuid)
    netValueData.value = res
    await nextTick()
    renderChart()
  } catch (e) {
    console.error('Failed to load net value:', e)
    message.error('加载净值数据失败')
  } finally {
    netValueLoading.value = false
  }
}

// 渲染图表
const renderChart = () => {
  if (!chartRef.value || !netValueData.value) return
  chartRef.value.innerHTML = '<p style="text-align: center; padding: 40px; color: #999;">净值曲线图表（待实现 ECharts 渲染）</p>'
}

// 重置表单
const resetForm = () => {
  createForm.name = ''
  createForm.portfolio_id = ''
  createForm.startDate = null
  createForm.endDate = null
  createForm.initialCapital = 1000000
}

// 格式化数字（保留两位小数）
const formatDecimal = (val: string) => {
  const num = parseFloat(val)
  if (isNaN(num)) return '-'
  return num.toFixed(2)
}

// 格式化盈亏
const formatPnL = (val: string) => {
  return formatDecimal(val)
}

onMounted(() => {
  loadBacktests()
  loadPortfolios()
})

// WebSocket 实时更新
const { subscribe } = useWebSocket()
let unsubscribe: (() => void) | null = null

onMounted(() => {
  unsubscribe = subscribe('*', (data) => {
    const taskId = data.task_id || data.task_uuid
    if (!taskId) return

    const task = backtests.value.find(b => b.uuid === taskId)
    if (!task) return

    if (data.type === 'progress') {
      if (data.progress !== undefined) task.progress = data.progress
      if (data.total_pnl !== undefined) task.total_pnl = data.total_pnl
      if (data.total_orders !== undefined) task.total_orders = data.total_orders
      if (data.total_signals !== undefined) task.total_signals = data.total_signals
    } else if (data.type === 'completed' || data.type === 'failed' || data.type === 'stopped') {
      task.status = data.type
      task.progress = 100
    }
  })
})

onUnmounted(() => {
  if (unsubscribe) unsubscribe()
})
</script>

<style scoped>
.backtest-list-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fixed-header {
  flex-shrink: 0;
  padding: 0 0 16px 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 12px;
}

.filter-bar {
  margin-bottom: 16px;
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
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

.task-name {
  font-weight: 500;
  color: #333;
}

.task-uuid {
  font-size: 11px;
  color: #999;
  font-family: monospace;
}

.status-cell {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
}

:deep(.ant-table-tbody > tr) {
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.ant-table-tbody > tr:hover) {
  background-color: #e6f4ff;
}
</style>
