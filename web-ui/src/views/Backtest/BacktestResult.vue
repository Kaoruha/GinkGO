<template>
  <div class="backtest-result-container">
    <div class="page-header">
      <button class="btn-text" @click="goBack">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回
      </button>
      <div class="title-section">
        <h1 class="page-title">回测报告</h1>
        <p class="page-subtitle">{{ backtestName || '加载中...' }}</p>
      </div>
      <div class="header-actions">
        <span v-if="backtestState" class="tag" :class="getStateTagClass(backtestState)">
          {{ getStateLabel(backtestState) }}
        </span>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
      <p>正在加载报告...</p>
    </div>

    <div v-else class="result-content">
      <div class="card">
        <div class="card-header">
          <h4>回测配置</h4>
        </div>
        <div class="card-body">
          <div class="config-grid">
            <div class="config-item">
              <span class="config-label">回测周期</span>
              <span class="config-value">{{ config.startDate }} ~ {{ config.endDate }}</span>
            </div>
            <div class="config-item">
              <span class="config-label">交易日数</span>
              <span class="config-value">{{ config.tradingDays }} 天</span>
            </div>
            <div class="config-item">
              <span class="config-label">手续费率</span>
              <span class="config-value">{{ (config.commissionRate * 100).toFixed(4) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h4>关键指标</h4>
        </div>
        <div class="card-body">
          <div class="metrics-grid">
            <div v-for="metric in displayMetrics" :key="metric.key" class="metric-item">
              <span class="metric-label">{{ metric.label }}</span>
              <span class="metric-value" :class="metric.class">
                {{ formatMetricValue(metric) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="charts-grid">
        <div class="card">
          <div class="card-header">
            <h4>净值曲线</h4>
          </div>
          <div class="card-body">
            <div ref="netValueChartRef" class="chart-container"></div>
          </div>
        </div>
        <div class="card">
          <div class="card-header">
            <h4>回撤分析</h4>
          </div>
          <div class="card-body">
            <div ref="drawdownChartRef" class="chart-container"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h4>交易记录</h4>
        </div>
        <div class="card-body">
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>方向</th>
                  <th>数量</th>
                  <th>买入价</th>
                  <th>卖出价</th>
                  <th>买入时间</th>
                  <th>卖出时间</th>
                  <th>收益</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in trades" :key="record.uuid">
                  <td>{{ record.code }}</td>
                  <td>
                    <span class="tag" :class="record.direction === 'LONG' ? 'tag-red' : 'tag-green'">
                      {{ record.direction === 'LONG' ? '做多' : '做空' }}
                    </span>
                  </td>
                  <td class="text-right">{{ record.volume }}</td>
                  <td class="text-right">{{ record.buyPrice?.toFixed(2) }}</td>
                  <td class="text-right">{{ record.sellPrice?.toFixed(2) }}</td>
                  <td>{{ record.buyTime }}</td>
                  <td>{{ record.sellTime }}</td>
                  <td class="text-right" :style="{ color: record.profit >= 0 ? '#f5222d' : '#52c41a' }">
                    {{ record.profit?.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { backtestApiExtended } from '@/api/modules/backtest'

const route = useRoute()
const router = useRouter()
const backtestId = route.params.uuid as string

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

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

const getStateTagClass = (state: string) => {
  const classes: Record<string, string> = {
    PENDING: 'tag-gray',
    RUNNING: 'tag-blue',
    COMPLETED: 'tag-green',
    FAILED: 'tag-red',
    CANCELLED: 'tag-gray'
  }
  return classes[state] || 'tag-gray'
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
    showToast(`加载报告失败: ${error.message}`, 'error')
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
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.btn-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-text:hover {
  background: #2a2a3e;
}

.title-section {
  flex: 1;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 8px 0 0 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.loading-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  gap: 16px;
  color: #8a8a9a;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
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

.config-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.config-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-label {
  font-size: 13px;
  color: #8a8a9a;
}

.config-value {
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-item {
  text-align: center;
  padding: 16px;
  background: #2a2a3e;
  border-radius: 8px;
}

.metric-label {
  display: block;
  font-size: 14px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.metric-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.chart-container {
  width: 100%;
  height: 400px;
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
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tr:hover {
  background: #2a2a3e;
}

.text-right {
  text-align: right;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-gray {
  background: #2a2a3e;
  color: #8a8a9a;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.tag-orange {
  background: rgba(250, 140, 22, 0.2);
  color: #fa8c16;
}

.tag-cyan {
  background: rgba(19, 194, 194, 0.2);
  color: #13c2c2;
}

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
