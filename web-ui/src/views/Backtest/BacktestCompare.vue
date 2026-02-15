<template>
  <div class="backtest-compare-container">
    <div class="page-header">
      <h1 class="page-title">回测对比</h1>
      <p class="page-subtitle">选择多个回测任务进行对比分析</p>
    </div>

    <a-card class="select-card">
      <a-form layout="vertical">
        <a-row :gutter="16">
          <a-col :span="24">
            <a-form-item label="选择要对比的回测任务">
              <a-select
                v-model:value="selectedTasks"
                mode="multiple"
                placeholder="请选择至少2个回测任务"
                style="width: 100%"
                :max-tag-count="5"
                :loading="loading"
              >
                <a-select-option
                  v-for="task in availableTasks"
                  :key="task.uuid"
                  :value="task.uuid"
                >
                  {{ task.name }}
                  <span class="task-info">({{ formatDate(task.created_at, 'YYYY-MM-DD') }})</span>
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="24">
            <a-form-item label="选择对比指标">
              <a-checkbox-group v-model:value="selectedMetrics">
                <a-row :gutter="[8, 8]">
                  <a-col :span="6">
                    <a-checkbox value="total_return">总收益率</a-checkbox>
                  </a-col>
                  <a-col :span="6">
                    <a-checkbox value="annual_return">年化收益率</a-checkbox>
                  </a-col>
                  <a-col :span="6">
                    <a-checkbox value="sharpe_ratio">夏普比率</a-checkbox>
                  </a-col>
                  <a-col :span="6">
                    <a-checkbox value="max_drawdown">最大回撤</a-checkbox>
                  </a-col>
                  <a-col :span="6">
                    <a-checkbox value="win_rate">胜率</a-checkbox>
                  </a-col>
                  <a-col :span="6">
                    <a-checkbox value="profit_loss_ratio">盈亏比</a-checkbox>
                  </a-col>
                </a-row>
              </a-checkbox-group>
            </a-form-item>
          </a-col>
        </a-row>

        <div class="action-buttons">
          <a-space>
            <a-button
              type="primary"
              :disabled="selectedTasks.length < 2"
              :loading="comparing"
              @click="startCompare"
            >
              开始对比
            </a-button>
            <a-button @click="resetSelection">
              重置
            </a-button>
          </a-space>
        </div>
      </a-form>
    </a-card>

    <a-card
      v-if="comparisonResult"
      title="对比结果"
      class="result-card"
    >
      <template #extra>
        <a-button @click="exportComparison">
          导出对比数据
        </a-button>
      </template>

      <a-table
        :columns="metricColumns"
        :data-source="metricTableData"
        :pagination="false"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.is_metric">
            <span :class="getValueClass(record[column.dataIndex])">
              {{ formatMetricValue(record.metric, record[column.dataIndex]) }}
            </span>
          </template>
          <template v-else-if="column.dataIndex === 'metric'">
            <span class="metric-label">{{ record.label }}</span>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-empty
      v-if="!loading && availableTasks.length === 0"
      description="暂无可对比的回测任务"
    >
      <a-button type="primary" @click="goToBacktestList">
        去创建回测任务
      </a-button>
    </a-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { backtestApi, type BacktestTask, type ComparisonResult } from '@/api/modules/backtest'
import { formatDate } from '@/utils/format'

const router = useRouter()

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

const metricColumns = computed(() => {
  const columns: any[] = [
    { title: '指标', dataIndex: 'metric', key: 'metric', width: 150, fixed: 'left' }
  ]

  selectedTasks.value.forEach(uuid => {
    const task = availableTasks.value.find(t => t.uuid === uuid)
    columns.push({
      title: task?.name || uuid.slice(0, 8),
      dataIndex: uuid,
      key: uuid,
      is_metric: true
    })
  })

  return columns
})

const metricTableData = computed(() => {
  if (!comparisonResult.value) return []

  return selectedMetrics.value.map(metric => {
    const row: any = {
      key: metric,
      metric: metric,
      label: metricLabels[metric] || metric
    }

    comparisonResult.value!.tasks.forEach(task => {
      row[task.task_uuid] = task.metrics[metric as keyof typeof task.metrics]
    })

    return row
  })
})

const loadAvailableTasks = async () => {
  loading.value = true
  try {
    const response = await backtestApi.list({ state: 'COMPLETED' })
    availableTasks.value = response.data?.items || []
  } catch (error: any) {
    message.error(`加载回测任务失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const startCompare = async () => {
  if (selectedTasks.value.length < 2) {
    message.warning('请选择至少2个回测任务进行对比')
    return
  }

  comparing.value = true
  try {
    const response = await backtestApi.compare(selectedTasks.value)
    comparisonResult.value = response.data || null
    message.success('对比完成')
  } catch (error: any) {
    message.error(`对比失败: ${error.message}`)
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
  message.success('导出成功')
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
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.select-card,
.result-card {
  margin-bottom: 24px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.task-info {
  color: #8c8c8c;
  font-size: 12px;
  margin-left: 8px;
}

.action-buttons {
  margin-top: 16px;
}

.metric-label {
  font-weight: 500;
  color: #1a1a1a;
}

.value-up {
  color: #f5222d;
  font-weight: 500;
}

.value-down {
  color: #52c41a;
  font-weight: 500;
}
</style>
