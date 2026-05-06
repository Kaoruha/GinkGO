<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        分段稳定性
      </h1>
      <p class="page-description">将回测区间等分为多段，对比各段表现是否一致</p>
    </div>

    <div class="page-content">
    <div class="card">
      <div class="card-header"><h3>分析配置</h3></div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select class="form-select" v-model="config.taskId">
              <option value="">请选择任务</option>
              <option v-for="t in backtestList" :key="t.uuid" :value="t.uuid">
                {{ t.name || t.uuid?.slice(0, 8) }} ({{ t.status }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分段数</label>
            <div class="segment-tags">
              <button
                v-for="opt in allSegmentOptions"
                :key="opt"
                class="segment-tag"
                :class="{ active: selectedSegments.has(opt) }"
                @click="toggleSegment(opt)"
              >{{ opt }}</button>
              <input
                v-if="showCustomInput"
                ref="customInputRef"
                class="segment-tag-input"
                v-model.number="customValue"
                type="number"
                min="2"
                placeholder="输入"
                @keydown.enter.prevent="addCustomSegment"
                @blur="nextTick(addCustomSegment)"
              />
              <button v-else class="segment-tag segment-tag-add" @click="openCustomInput">+</button>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">
              分析指标
              <span v-if="availableMetrics.length" class="metric-count">已选 {{ selectedMetrics.size }} / {{ availableMetrics.length }}</span>
            </label>
            <div class="segment-tags" v-if="availableMetrics.length">
              <button
                v-for="m in availableMetrics"
                :key="m.name"
                class="segment-tag"
                :class="{ active: selectedMetrics.has(m.name) }"
                @click="toggleMetric(m.name)"
              >{{ m.label }}</button>
            </div>
            <div v-else class="metric-placeholder">
              {{ config.taskId ? '加载中...' : '请先选择任务' }}
            </div>
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="loading || !config.taskId" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <template v-if="result">
      <div class="stats-grid">
        <div class="stat-card" v-for="w in result.windows" :key="w.n_segments">
          <div class="stat-value">{{ w.n_segments }} 段</div>
          <div class="stat-label">稳定性评分</div>
          <div class="stat-value" :class="scoreClass(w.stability_score)">
            {{ (w.stability_score * 100).toFixed(1) }}%
          </div>
        </div>
      </div>

      <!-- 跨 window 对比概览图 -->
      <div class="card overview-chart-card">
        <div class="card-header"><h3>跨分段对比概览</h3></div>
        <div class="card-body">
          <div ref="overviewChartRef" class="overview-chart"></div>
        </div>
      </div>

      <!-- 双列详情网格 -->
      <div class="detail-grid">
        <div class="card" v-for="w in result.windows" :key="'detail-' + w.n_segments">
          <div class="card-header">
            <h3>{{ w.n_segments }} 段分析</h3>
            <span :class="scoreClass(w.stability_score)">评分 {{ (w.stability_score * 100).toFixed(1) }}%</span>
          </div>
          <div class="card-body">
            <div :ref="(el: any) => setDetailChartRef(w.n_segments)(el)" class="detail-chart"></div>
            <table class="data-table">
              <thead>
                <tr>
                  <th>时间段</th>
                  <th v-for="metric in (w.available_metrics || [])" :key="metric">{{ metricLabel(metric) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(seg, i) in w.segments" :key="i">
                  <td>{{ seg._start }} ~ {{ seg._end }}</td>
                  <td v-for="metric in (w.available_metrics || [])" :key="metric">
                    {{ formatMetricValue(seg[metric]) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="!loading" class="card">
      <div class="empty-state">选择回测任务并点击分析</div>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { validationApi } from '@/api/modules/validation'
import { backtestApi } from '@/api/modules/backtest'

const props = defineProps<{
  portfolioId?: string
}>()

const loading = ref(false)
const result = ref<any>(null)
const backtestList = ref<any[]>([])
const presetSegments = [2, 4, 8, 16, 32]
const selectedSegments = reactive(new Set([2, 4, 8]))
const allSegmentOptions = computed(() => {
  const custom = Array.from(selectedSegments).filter(n => !presetSegments.includes(n))
  return [...presetSegments, ...custom.sort((a, b) => a - b)]
})
const showCustomInput = ref(false)
const customValue = ref<number | null>(null)
const customInputRef = ref<HTMLInputElement | null>(null)
const config = reactive({
  taskId: '',
})

const availableMetrics = ref<{ name: string; label: string }[]>([])
const selectedMetrics = reactive(new Set<string>(['annualized_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']))
const metricsLoading = ref(false)

const CHART_COLORS = ['#3b82f6', '#eab308', '#ef4444', '#22c55e', '#a855f7', '#f97316', '#06b6d4', '#ec4899']

const ANALYZER_LABELS: Record<string, string> = {
  net_value: '净值', ProfitAna: '每日盈亏', annualized_return: '年化收益',
  sharpe_ratio: '夏普比率', max_drawdown: '最大回撤', win_rate: '胜率',
  hold_pct: '仓位占比', order_count: '订单数', signal_count: '信号数',
  sortino_ratio: 'Sortino 比率', calmar_ratio: 'Calmar 比率', volatility: '波动率',
  underwater_time: '水下时间', var_cvar: 'VaR', skew_kurtosis: '偏度/峰度',
  consecutive_pnl: '连续盈亏', trade_win_rate: '交易胜率', avg_win_loss_ratio: '盈亏比',
  profit_factor: '利润因子', avg_holding_period: '平均持仓天数', max_consecutive_losses: '最大连续亏损',
}

const toggleMetric = (name: string) => {
  if (selectedMetrics.has(name)) {
    if (selectedMetrics.size > 1) selectedMetrics.delete(name)
  } else {
    selectedMetrics.add(name)
  }
}

const metricLabel = (name: string) => availableMetrics.value.find(m => m.name === name)?.label || ANALYZER_LABELS[name] || name

const formatMetricValue = (val: number | undefined) => {
  if (val === undefined || val === null) return '-'
  if (Math.abs(val) < 10) return val.toFixed(4)
  return val.toFixed(2)
}

const scoreClass = (score: number) => {
  if (score >= 0.7) return 'stat-success'
  if (score >= 0.4) return 'stat-warning'
  return 'stat-danger'
}

const toggleSegment = (n: number) => {
  if (selectedSegments.has(n)) {
    selectedSegments.delete(n)
  } else {
    selectedSegments.add(n)
  }
}

const openCustomInput = () => {
  showCustomInput.value = true
  nextTick(() => customInputRef.value?.focus())
}

const addCustomSegment = () => {
  if (!showCustomInput.value) return
  const v = customValue.value
  if (v && v >= 2 && !selectedSegments.has(v)) {
    selectedSegments.add(v)
  }
  customValue.value = null
  showCustomInput.value = false
}

const runAnalysis = async () => {
  if (!config.taskId) return
  loading.value = true
  result.value = null
  try {
    const segments = Array.from(selectedSegments).sort((a, b) => a - b)
    const res = await validationApi.segmentStability({
      task_id: config.taskId,
      portfolio_id: props.portfolioId || '',
      n_segments: segments.length ? segments : undefined,
      metrics: Array.from(selectedMetrics),
    })
    result.value = (res as any).data
  } catch (e: any) {
    alert('分析失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

const fetchBacktestList = async () => {
  try {
    const params: any = { page: 1, size: 50, status: 'completed' }
    if (props.portfolioId) {
      params.portfolio_id = props.portfolioId
    }
    const res = await backtestApi.list(params)
    backtestList.value = res.data || []
  } catch { /* ignore */ }
}

const fetchAvailableMetrics = async () => {
  if (!config.taskId) { availableMetrics.value = []; return }
  metricsLoading.value = true
  try {
    const res = await validationApi.availableMetrics({
      task_id: config.taskId,
      portfolio_id: props.portfolioId || '',
    })
    availableMetrics.value = (res as any).data?.metrics || []
    const names = new Set(availableMetrics.value.map(m => m.name))
    for (const s of Array.from(selectedMetrics)) {
      if (!names.has(s)) selectedMetrics.delete(s)
    }
  } catch { /* ignore */ }
  finally { metricsLoading.value = false }
}

// 概览图
const overviewChartRef = ref<HTMLDivElement | null>(null)
let overviewChart: echarts.ECharts | null = null

const initOverviewChart = () => {
  if (!overviewChartRef.value || !result.value) return
  if (overviewChart) overviewChart.dispose()

  overviewChart = echarts.init(overviewChartRef.value)

  const windows = result.value.windows
  const xData = windows.map((w: any) => `${w.n_segments}段`)

  // Collect all metrics from available_metrics across windows
  const metricsSet = new Set<string>()
  for (const w of windows) {
    for (const m of (w.available_metrics || [])) {
      metricsSet.add(m)
    }
  }
  const metrics = Array.from(metricsSet)

  // Create up to 3 Y-axes, metrics beyond 3 share the closest axis
  const yAxisDefs = metrics.slice(0, 3).map((m, i) => ({
    type: 'value' as const,
    name: metricLabel(m),
    nameTextStyle: { color: CHART_COLORS[i % CHART_COLORS.length], fontSize: 11 },
    axisLabel: { color: CHART_COLORS[i % CHART_COLORS.length] },
    splitLine: i === 0 ? { lineStyle: { color: '#2a2a3e' } } : { show: false },
    ...(i >= 2 ? { offset: 60 } : {}),
  }))

  const series = metrics.map((m, i) => {
    const color = CHART_COLORS[i % CHART_COLORS.length]
    const axisIdx = i < 3 ? i : (i % 3)
    return {
      name: metricLabel(m),
      type: 'line',
      data: windows.map((w: any) => {
        const segs = w.segments || []
        if (!segs.length) return null
        const avg = segs.reduce((s: number, seg: any) => s + (seg[m] ?? 0), 0) / segs.length
        return Number(avg.toFixed(4))
      }),
      yAxisIndex: axisIdx,
      itemStyle: { color },
      lineStyle: { width: 2, ...(i >= 4 ? { type: 'dashed' as const } : {}) },
      symbol: 'circle',
      symbolSize: 8,
    }
  })

  overviewChart.setOption({
    backgroundColor: '#1a1a2e',
    tooltip: { trigger: 'axis' },
    legend: {
      data: metrics.map(m => metricLabel(m)),
      textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
      top: 0,
    },
    grid: { top: 40, right: 120 + (yAxisDefs.length > 2 ? 60 : 0), bottom: 30, left: 60 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: 'rgba(255,255,255,0.6)' },
      axisLine: { lineStyle: { color: '#2a2a3e' } },
    },
    yAxis: yAxisDefs.length ? yAxisDefs : [{ type: 'value' as const, splitLine: { lineStyle: { color: '#2a2a3e' } } }],
    series,
  })
}

// 详情图
const detailChartRefs = ref<Map<number, HTMLDivElement>>(new Map())
const detailCharts = new Map<number, echarts.ECharts>()

const setDetailChartRef = (nSegments: number) => (el: any) => {
  if (el) detailChartRefs.value.set(nSegments, el as HTMLDivElement)
}

const initDetailCharts = () => {
  if (!result.value) return
  detailCharts.forEach(c => c.dispose())
  detailCharts.clear()

  for (const w of result.value.windows) {
    const el = detailChartRefs.value.get(w.n_segments)
    if (!el) continue

    const chart = echarts.init(el)
    detailCharts.set(w.n_segments, chart)

    const xData = w.segments.map((seg: any) => `${seg._start?.slice(5) || ''}~${seg._end?.slice(5) || ''}`)
    const metrics = w.available_metrics || []

    const yAxisDefs = metrics.slice(0, 2).map((m: string, i: number) => ({
      type: 'value' as const,
      name: metricLabel(m),
      nameTextStyle: { color: CHART_COLORS[i % CHART_COLORS.length], fontSize: 11 },
      axisLabel: { color: CHART_COLORS[i % CHART_COLORS.length] },
      splitLine: i === 0 ? { lineStyle: { color: '#2a2a3e' } } : { show: false },
    }))

    const series = metrics.map((m: string, i: number) => {
      const color = CHART_COLORS[i % CHART_COLORS.length]
      const axisIdx = i < 2 ? i : (i % 2)
      return {
        name: metricLabel(m),
        type: 'line',
        data: w.segments.map((seg: any) => {
          const val = seg[m]
          return val !== undefined ? Number(val.toFixed(4)) : null
        }),
        yAxisIndex: axisIdx,
        itemStyle: { color },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 6,
        ...(i < 2 ? {
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: color.replace(')', ',0.2)').replace('rgb', 'rgba') },
              { offset: 1, color: 'transparent' },
            ]),
          },
        } : {}),
      }
    })

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: metrics.map((m: string) => metricLabel(m)),
        textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        top: 0,
      },
      grid: { top: 36, right: 60, bottom: 24, left: 50 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        axisLine: { lineStyle: { color: '#2a2a3e' } },
      },
      yAxis: yAxisDefs.length ? yAxisDefs : [{ type: 'value' as const, splitLine: { lineStyle: { color: '#2a2a3e' } } }],
      series,
    })
  }
}

watch(() => config.taskId, () => {
  fetchAvailableMetrics()
})

watch(result, () => {
  nextTick(() => {
    initOverviewChart()
    initDetailCharts()
  })
})

const handleResize = () => {
  overviewChart?.resize()
  detailCharts.forEach(c => c.resize())
}

onMounted(() => {
  fetchBacktestList()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  overviewChart?.dispose()
  overviewChart = null
  detailCharts.forEach(c => c.dispose())
  detailCharts.clear()
})
</script>

<style scoped>
.page-content {
  display: flex;
  flex-direction: column;
}

.card {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.stats-grid {
  margin-top: 16px;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.stat-warning { color: #eab308; }
.stat-success { color: #22c55e; }
.stat-danger { color: #ef4444; }

.segment-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.segment-tag {
  padding: 6px 14px;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  background: #1a1a2e;
  color: rgba(255, 255, 255, 0.6);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.segment-tag:hover {
  border-color: #3a3a5e;
  color: rgba(255, 255, 255, 0.9);
}

.segment-tag.active {
  background: rgba(59, 130, 246, 0.15);
  border-color: #3b82f6;
  color: #3b82f6;
  font-weight: 600;
}

.segment-tag-add {
  border-style: dashed;
  color: rgba(255, 255, 255, 0.35);
}

.segment-tag-add:hover {
  color: #3b82f6;
  border-color: #3b82f6;
}

.segment-tag-input {
  width: 64px;
  padding: 6px 10px;
  border: 1px solid #3b82f6;
  border-radius: 6px;
  background: #1a1a2e;
  color: #fff;
  font-size: 13px;
  outline: none;
}

.metric-count {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.35);
  margin-left: 8px;
  font-weight: 400;
}

.metric-placeholder {
  color: rgba(255, 255, 255, 0.35);
  font-size: 13px;
  padding: 6px 0;
}

.overview-chart-card {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.overview-chart {
  width: 100%;
  height: 300px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.detail-chart {
  width: 100%;
  height: 250px;
  margin-bottom: 12px;
}
</style>
