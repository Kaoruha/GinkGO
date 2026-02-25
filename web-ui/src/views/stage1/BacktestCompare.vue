<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="blue">回测</a-tag>
        回测对比
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="runCompare" :loading="loading" :disabled="selectedIds.length < 2">
          开始对比
        </a-button>
      </div>
    </div>

    <!-- 选择回测任务 -->
    <a-card title="选择回测任务" style="margin-bottom: 16px">
      <a-alert message="请选择 2-5 个回测任务进行对比" type="info" show-icon style="margin-bottom: 16px" />
      <a-table
        :columns="selectColumns"
        :dataSource="backtestList"
        :rowKey="(record: BacktestItem) => record.run_id"
        :rowSelection="rowSelection"
        :pagination="false"
        size="small"
        :loading="listLoading"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">{{ getStatusText(record.status) }}</a-tag>
          </template>
          <template v-else-if="column.key === 'sharpe_ratio'">
            {{ record.sharpe_ratio?.toFixed(2) || '-' }}
          </template>
          <template v-else-if="column.key === 'total_return'">
            <span :style="{ color: (record.total_return || 0) >= 0 ? '#cf1322' : '#3f8600' }">
              {{ ((record.total_return || 0) * 100).toFixed(2) }}%
            </span>
          </template>
        </template>
      </a-table>
      <div style="margin-top: 16px">
        <span>已选择 {{ selectedIds.length }} 个回测任务</span>
      </div>
    </a-card>

    <!-- 对比结果 -->
    <template v-if="compareResult">
      <!-- 指标对比表 -->
      <a-card title="指标对比" style="margin-bottom: 16px">
        <a-table
          :columns="compareColumns"
          :dataSource="compareResult.metrics"
          :rowKey="(record: MetricItem) => record.name"
          :pagination="false"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key.startsWith('value_')">
              <span :class="{ 'best-value': record.best === column.dataIndex }">
                {{ formatValue(record[column.dataIndex], record.type) }}
              </span>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 净值曲线图 -->
      <a-card title="净值曲线对比">
        <a-alert message="图表功能开发中" type="info" />
      </a-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi } from '@/api'
import type { BacktestTask } from '@/api'

interface MetricItem {
  name: string
  type: string
  [key: string]: any
}

interface CompareResult {
  metrics: MetricItem[]
  netvalues: Record<string, { date: string; value: number }[]>
}

const listLoading = ref(false)
const loading = ref(false)
const backtestList = ref<BacktestTask[]>([])
const selectedIds = ref<string[]>([])
const compareResult = ref<CompareResult | null>(null)

const selectColumns = [
  { title: '任务ID', dataIndex: 'run_id', width: 150 },
  { title: '名称', dataIndex: 'name', width: 200 },
  { title: '状态', key: 'status', width: 100 },
  { title: '总收益', key: 'total_return', width: 120 },
  { title: '夏普比率', key: 'sharpe_ratio', width: 100 },
  { title: '最大回撤', dataIndex: 'max_drawdown', width: 100 },
]

const rowSelection = computed(() => ({
  selectedRowKeys: selectedIds.value,
  onChange: (keys: string[]) => {
    if (keys.length > 5) {
      message.warning('最多选择 5 个回测任务')
      return
    }
    selectedIds.value = keys
  },
  getCheckboxProps: (record: BacktestTask) => ({
    disabled: record.status !== 'completed',
  }),
}))

const compareColumns = computed(() => {
  const cols = [
    { title: '指标', dataIndex: 'name', width: 150, fixed: 'left' as const },
  ]
  selectedIds.value.forEach((id, index) => {
    cols.push({
      title: `回测 ${index + 1}`,
      key: `value_${id}`,
      dataIndex: `value_${id}`,
      width: 120,
    })
  })
  return cols
})

const getStatusColor = (status: string) => {
  const map: Record<string, string> = {
    completed: 'green',
    running: 'blue',
    failed: 'red',
    pending: 'default',
  }
  return map[status] || 'default'
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

const fetchBacktestList = async () => {
  listLoading.value = true
  try {
    const response = await backtestApi.list({ size: 50 })
    backtestList.value = response.data || []
  } catch (e) {
    message.error('获取回测列表失败')
  } finally {
    listLoading.value = false
  }
}

const runCompare = async () => {
  if (selectedIds.value.length < 2) {
    message.warning('请至少选择 2 个回测任务')
    return
  }

  loading.value = true
  try {
    const response = await backtestApi.compare(selectedIds.value)
    compareResult.value = response.data || null
  } catch (e) {
    message.error('对比失败')
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
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.best-value {
  font-weight: bold;
  color: #1890ff;
}
</style>
