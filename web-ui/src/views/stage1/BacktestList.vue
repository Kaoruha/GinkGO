<template>
  <ListPageLayout
    title="策略回测"
    :loading="backtestStore.loading"
    :empty="filteredBacktests.length === 0"
    empty-text="暂无回测任务"
    empty-action-text="创建第一个回测"
    :show-search="false"
    @create="showCreateModal = true"
  >
    <template #stats>
      <a-space>
        <a-tag color="blue">{{ backtestStore.total }} 个任务</a-tag>
        <a-tag v-if="backtestStore.runningCount > 0" color="green">
          {{ backtestStore.runningCount }} 个运行中
        </a-tag>
      </a-space>
    </template>

    <template #actions>
      <a-input-search
        v-model:value="searchKeyword"
        placeholder="搜索任务..."
        style="width: 200px"
        allow-clear
      />
    </template>

    <template #filters>
      <a-radio-group v-model:value="filterStatus" button-style="solid" size="small" @change="loadBacktests">
        <a-radio-button value="">全部</a-radio-button>
        <a-radio-button value="created">待启动</a-radio-button>
        <a-radio-button value="pending">等待中</a-radio-button>
        <a-radio-button value="running">运行中</a-radio-button>
        <a-radio-button value="completed">已完成</a-radio-button>
        <a-radio-button value="failed">失败</a-radio-button>
      </a-radio-group>
    </template>

    <a-table
      :columns="columns"
      :data-source="filteredBacktests"
      :loading="backtestStore.loading"
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
            <StatusTag :status="record.status" type="backtest" />
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
          <span :style="{ color: parseFloat(record.total_pnl) >= 0 ? '#cf1322' : '#3f8600' }">
            {{ formatDecimal(record.total_pnl) }}
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
        <template v-else-if="column.key === 'create_at'">
          {{ formatDateTime(record.create_at) }}
        </template>
        <template v-else-if="column.key === 'action'">
          <TableActions
            :record="record"
            :actions="tableActions"
            @action="handleAction"
          />
        </template>
      </template>
    </a-table>
  </ListPageLayout>

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
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useBacktestStore, usePortfolioStore } from '@/stores'
import { useWebSocket } from '@/composables'
import { formatPercent, formatDuration, formatDateTime } from '@/utils/format'
import { ListPageLayout, StatusTag, TableActions } from '@/components/common'
import type { BacktestTask } from '@/api'
import type { TableAction } from '@/components/common/TableActions.vue'

const router = useRouter()

// ========== Stores ==========
const backtestStore = useBacktestStore()
const portfolioStore = usePortfolioStore()

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
const filteredBacktests = computed(() => {
  let result = backtestStore.tasks
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(t =>
      t.name?.toLowerCase().includes(keyword) ||
      t.uuid?.toLowerCase().includes(keyword) ||
      t.run_id?.toLowerCase().includes(keyword)
    )
  }
  return result
})

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
  { title: '状态', dataIndex: 'status', key: 'status', width: 180 },
  { title: '总盈亏', dataIndex: 'total_pnl', key: 'total_pnl', width: 100 },
  { title: '订单数', dataIndex: 'total_orders', key: 'total_orders', width: 70 },
  { title: '信号数', dataIndex: 'total_signals', key: 'total_signals', width: 70 },
  { title: '创建时间', dataIndex: 'create_at', key: 'create_at', width: 140 },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

// 表格操作按钮
const tableActions = computed<TableAction[]>(() => [
  { key: 'stop', label: '停止', confirm: '确定要停止此回测任务吗？', show: currentTask?.value?.status === 'running' },
  { key: 'detail', label: '详情' },
  { key: 'netvalue', label: '净值曲线' },
  { key: 'delete', label: '删除', confirm: '确定要删除此回测任务吗？' },
])

// ========== 方法 ==========
const loadBacktests = async () => {
  const params: any = { page: page.value, size: size.value }
  if (filterStatus.value) params.status = filterStatus.value
  await backtestStore.fetchList(params)
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

const handleAction = async (key: string, record: BacktestTask) => {
  switch (key) {
    case 'detail':
      router.push(`/stage1/backtest/${record.uuid}`)
      break
    case 'netvalue':
      await viewNetValue(record)
      break
    case 'stop':
      await backtestStore.stopTask(record.uuid)
      message.success('回测任务已停止')
      break
    case 'delete':
      await backtestStore.deleteTask(record.uuid)
      message.success('删除成功')
      break
  }
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

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
}

.net-value-chart {
  padding: 16px 0;
}

:deep(.ant-table-tbody > tr) {
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.ant-table-tbody > tr:hover) {
  background-color: #e6f4ff;
}
</style>
