<template>
  <div class="backtest-result-container">
    <div class="page-header">
      <a-button type="text" @click="goBack">
        <ArrowLeftOutlined /> 返回
      </a-button>
      <div class="title-section">
        <h1 class="page-title">回测报告</h1>
        <p class="page-subtitle">{{ backtestName || '加载中...' }}</p>
      </div>
      <div class="header-actions">
        <a-tag v-if="backtestState" :color="getStateColor(backtestState)">
          {{ getStateLabel(backtestState) }}
        </a-tag>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <a-spin size="large" tip="正在加载报告..." />
    </div>

    <div v-else class="result-content">
      <a-card title="回测配置" class="config-card">
        <a-descriptions :column="3" bordered size="small">
          <a-descriptions-item label="回测周期">
            {{ config.startDate }} ~ {{ config.endDate }}
          </a-descriptions-item>
          <a-descriptions-item label="交易日数">
            {{ config.tradingDays }} 天
          </a-descriptions-item>
          <a-descriptions-item label="手续费率">
            {{ (config.commissionRate * 100).toFixed(4) }}%
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <a-card title="关键指标" class="metrics-card">
        <a-row :gutter="16">
          <a-col :span="6" v-for="metric in displayMetrics" :key="metric.key">
            <div class="metric-item">
              <div class="metric-label">{{ metric.label }}</div>
              <div class="metric-value" :class="metric.class">
                {{ formatMetricValue(metric) }}
              </div>
            </div>
          </a-col>
        </a-row>
      </a-card>

      <a-row :gutter="16">
        <a-col :span="16">
          <a-card title="净值曲线" class="chart-card">
            <div ref="netValueChartRef" class="chart-container" style="height: 400px"></div>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card title="回撤分析" class="chart-card">
            <div ref="drawdownChartRef" class="chart-container" style="height: 400px"></div>
          </a-card>
        </a-col>
      </a-row>

      <a-card title="交易记录" class="trades-card">
        <a-table
          :columns="tradeColumns"
          :data-source="trades"
          :pagination="{ pageSize: 20 }"
          :scroll="{ x: 1000 }"
          size="small"
          row-key="uuid"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.dataIndex === 'direction'">
              <a-tag :color="record.direction === 'LONG' ? 'red' : 'green'">
                {{ record.direction === 'LONG' ? '做多' : '做空' }}
              </a-tag>
            </template>
            <template v-if="column.dataIndex === 'profit'">
              <span :style="{ color: record.profit >= 0 ? '#f5222d' : '#52c41a' }">
                {{ record.profit?.toFixed(2) }}
              </span>
            </template>
          </template>
        </a-table>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import * as echarts from 'echarts'
import { backtestApiExtended, type BacktestReport } from '@/api/modules/backtest'

const route = useRoute()
const router = useRouter()
const backtestId = route.params.uuid as string

// 状态
const loading = ref(true)
const backtestName = ref('')
const backtestState = ref('')

// 配置
const config = reactive({
  startDate: '',
  endDate: '',
  tradingDays: 0,
  commissionRate: 0.0003,
  slippageRate: 0.0001
})

// 指标
const metrics = reactive({
  totalReturn: 0,
  annualReturn: 0,
  sharpeRatio: 0,
  maxDrawdown: 0,
  winRate: 0,
  profitLossRatio: 0,
  volatility: 0
})

// 交易记录
const trades = ref<any[]>([])

// 图表refs
const netValueChartRef = ref<HTMLDivElement>()
const drawdownChartRef = ref<HTMLDivElement>()
let netValueChart: echarts.ECharts | null = null
let drawdownChart: echarts.ECharts | null = null

// 净值数据
const netValueData = ref<any[]>([])
const drawdownData = ref<any[]>([])

// 显示的指标
const displayMetrics = computed(() => [
  { key: 'totalReturn', label: '总收益率', value: metrics.totalReturn, class: getValueClass(metrics.totalReturn), format: 'percent' },
  { key: 'annualReturn', label: '年化收益率', value: metrics.annualReturn, class: getValueClass(metrics.annualReturn), format: 'percent' },
  { key: 'sharpeRatio', label: '夏普比率', value: metrics.sharpeRatio, class: '', format: 'number' },
  { key: 'maxDrawdown', label: '最大回撤', value: metrics.maxDrawdown, class: 'value-down', format: 'percent' },
  { key: 'winRate', label: '胜率', value: metrics.winRate, class: '', format: 'percent' },
  { key: 'profitLossRatio', label: '盈亏比', value: metrics.profitLossRatio, class: '', format: 'number' },
  { key: 'volatility', label: '波动率', value: metrics.volatility, class: '', format: 'percent' }
])

// 表格列
const tradeColumns = [
  { title: '代码', dataIndex: 'code', width: 100, fixed: 'left' },
  { title: '方向', dataIndex: 'direction', width: 80 },
  { title: '数量', dataIndex: 'volume', width: 100, align: 'right' },
  { title: '买入价', dataIndex: 'buyPrice', width: 100, align: 'right' },
  { title: '卖出价', dataIndex: 'sellPrice', width: 100, align: 'right' },
  { title: '买入时间', dataIndex: 'buyTime', width: 150 },
  { title: '卖出时间', dataIndex: 'sellTime', width: 150 },
  { title: '收益', dataIndex: 'profit', width: 100, align: 'right' }
]

const goBack = () => {
  router.back()
}

const getStateLabel = (state: string) => {
  const labels: Record<string, string> = {
    PENDING: '等待中',
    RUNNING: '运行中',
    COMPLETED: '已完成',
    FAILED: '失败',
    CANCELLED: '已取消'
  }
  return labels[state] || state
}

const getStateColor = (state: string) => {
  const colors: Record<string, string> = {
    PENDING: 'default',
    RUNNING: 'processing',
    COMPLETED: 'success',
    FAILED: 'error',
    CANCELLED: 'default'
  }
  return colors[state] || 'default'
}

const getValueClass = (value: number) => {
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return ''
}

const formatMetricValue = (metric: any) => {
  if (metric.value === undefined || metric.value === null) return '-'
  if (metric.format === 'percent') {
    return `${(metric.value * 100).toFixed(2)}%`
  }
  return metric.value.toFixed(2)
}

const loadReport = async () => {
  loading.value = true
  try {
    const response = await backtestApiExtended.getReport(backtestId)
    const report = response.data

    if (report) {
      backtestName.value = report.task_name || ''
      backtestState.value = report.state || ''

      // 配置
      if (report.config) {
        config.startDate = report.config.start_date || ''
        config.endDate = report.config.end_date || ''
        config.commissionRate = report.config.commission_rate || 0.0003
        config.slippageRate = report.config.slippage_rate || 0.0001
      }

      // 指标
      if (report.metrics) {
        metrics.totalReturn = report.metrics.total_return || 0
        metrics.annualReturn = report.metrics.annual_return || 0
        metrics.sharpeRatio = report.metrics.sharpe_ratio || 0
        metrics.maxDrawdown = report.metrics.max_drawdown || 0
        metrics.winRate = report.metrics.win_rate || 0
        metrics.profitLossRatio = report.metrics.profit_loss_ratio || 0
        metrics.volatility = report.metrics.volatility || 0
      }

      // 净值数据
      if (report.net_value) {
        netValueData.value = report.net_value
        config.tradingDays = report.net_value.length
        renderNetValueChart()
      }

      // 回撤数据
      if (report.drawdown) {
        drawdownData.value = report.drawdown
        renderDrawdownChart()
      }

      // 交易记录
      if (report.trades) {
        trades.value = report.trades
      }
    }
  } catch (error: any) {
    message.error(`加载报告失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const renderNetValueChart = () => {
  if (!netValueChartRef.value || netValueData.value.length === 0) return

  netValueChart = echarts.init(netValueChartRef.value)

  const dates = netValueData.value.map(d => d.date)
  const values = netValueData.value.map(d => d.value)

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '净值' },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      lineStyle: { color: '#1890ff', width: 2 },
      areaStyle: { color: 'rgba(24, 144, 255, 0.1)' }
    }],
    grid: { left: '10%', right: '5%', top: '10%', bottom: '10%' }
  }

  netValueChart.setOption(option)
}

const renderDrawdownChart = () => {
  if (!drawdownChartRef.value || drawdownData.value.length === 0) return

  drawdownChart = echarts.init(drawdownChartRef.value)

  const dates = drawdownData.value.map(d => d.date)
  const values = drawdownData.value.map(d => d.value)

  const option = {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '回撤%' },
    series: [{
      type: 'line',
      data: values,
      lineStyle: { color: '#f5222d' },
      areaStyle: { color: 'rgba(245, 34, 45, 0.2)' }
    }],
    grid: { left: '10%', right: '5%', top: '10%', bottom: '10%' }
  }

  drawdownChart.setOption(option)
}

const handleResize = () => {
  netValueChart?.resize()
  drawdownChart?.resize()
}

onMounted(() => {
  loadReport()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  netValueChart?.dispose()
  drawdownChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.backtest-result-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 8px 0 0 0;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.config-card,
.metrics-card,
.chart-card,
.trades-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.metric-item {
  text-align: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.metric-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

.chart-container {
  width: 100%;
}
</style>
