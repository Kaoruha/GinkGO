<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        分段稳定性
      </h1>
      <p class="page-description">将回测区间等分为多段，对比各段表现是否一致</p>
    </div>

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
                v-for="opt in presetSegments"
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
                @keydown.enter="addCustomSegment"
                @blur="addCustomSegment"
              />
              <button v-else class="segment-tag segment-tag-add" @click="openCustomInput">+</button>
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
                  <th>段</th>
                  <th>收益</th>
                  <th>夏普</th>
                  <th>最大回撤</th>
                  <th>胜率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(seg, i) in w.segments" :key="i">
                  <td>{{ i + 1 }}</td>
                  <td :class="seg.total_return >= 0 ? 'stat-success' : 'stat-danger'">
                    {{ (seg.total_return * 100).toFixed(2) }}%
                  </td>
                  <td>{{ seg.sharpe.toFixed(2) }}</td>
                  <td class="stat-danger">{{ (seg.max_drawdown * 100).toFixed(2) }}%</td>
                  <td>{{ (seg.win_rate * 100).toFixed(1) }}%</td>
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
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
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
const showCustomInput = ref(false)
const customValue = ref<number | null>(null)
const customInputRef = ref<HTMLInputElement | null>(null)
const config = reactive({
  taskId: '',
})

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

// 概览图
const overviewChartRef = ref<HTMLDivElement | null>(null)
let overviewChart: echarts.ECharts | null = null

const initOverviewChart = () => {
  if (!overviewChartRef.value || !result.value) return
  if (overviewChart) overviewChart.dispose()

  overviewChart = echarts.init(overviewChartRef.value)

  const windows = result.value.windows
  const xData = windows.map((w: any) => `${w.n_segments}段`)

  overviewChart.setOption({
    backgroundColor: '#1a1a2e',
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['收益率', '夏普比率', '最大回撤', '胜率'],
      textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
      top: 0,
    },
    grid: { top: 40, right: 120, bottom: 30, left: 60 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: 'rgba(255,255,255,0.6)' },
      axisLine: { lineStyle: { color: '#2a2a3e' } },
    },
    yAxis: [
      {
        type: 'value',
        name: '收益率',
        nameTextStyle: { color: '#3b82f6', fontSize: 11 },
        axisLabel: { color: '#3b82f6', formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#2a2a3e' } },
      },
      {
        type: 'value',
        name: '夏普',
        nameTextStyle: { color: '#eab308', fontSize: 11 },
        axisLabel: { color: '#eab308' },
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '回撤',
        nameTextStyle: { color: '#ef4444', fontSize: 11 },
        axisLabel: { color: '#ef4444', formatter: '{value}%' },
        splitLine: { show: false },
        offset: 60,
      },
    ],
    series: [
      {
        name: '收益率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.total_return, 0) / w.segments.length
          return (avg * 100).toFixed(2)
        }),
        yAxisIndex: 0,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 8,
      },
      {
        name: '夏普比率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.sharpe, 0) / w.segments.length
          return avg.toFixed(2)
        }),
        yAxisIndex: 1,
        itemStyle: { color: '#eab308' },
        lineStyle: { width: 2 },
        symbol: 'diamond',
        symbolSize: 8,
      },
      {
        name: '最大回撤',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.max_drawdown, 0) / w.segments.length
          return (avg * 100).toFixed(2)
        }),
        yAxisIndex: 2,
        itemStyle: { color: '#ef4444' },
        lineStyle: { width: 2 },
        symbol: 'triangle',
        symbolSize: 8,
      },
      {
        name: '胜率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.win_rate, 0) / w.segments.length
          return (avg * 100).toFixed(1)
        }),
        yAxisIndex: 0,
        itemStyle: { color: '#22c55e' },
        lineStyle: { width: 2, type: 'dashed' },
        symbol: 'rect',
        symbolSize: 8,
      },
    ],
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

    const xData = w.segments.map((_: any, i: number) => `段${i + 1}`)

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['收益', '最大回撤'],
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
      yAxis: [
        {
          type: 'value',
          name: '收益',
          nameTextStyle: { color: '#22c55e', fontSize: 11 },
          axisLabel: { color: '#22c55e', formatter: '{value}%' },
          splitLine: { lineStyle: { color: '#2a2a3e' } },
        },
        {
          type: 'value',
          name: '回撤',
          nameTextStyle: { color: '#ef4444', fontSize: 11 },
          axisLabel: { color: '#ef4444', formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '收益',
          type: 'line',
          data: w.segments.map((seg: any) => (seg.total_return * 100).toFixed(2)),
          yAxisIndex: 0,
          itemStyle: { color: '#22c55e' },
          lineStyle: { width: 2 },
          symbol: 'circle',
          symbolSize: 6,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34,197,94,0.2)' },
              { offset: 1, color: 'rgba(34,197,94,0)' },
            ]),
          },
        },
        {
          name: '最大回撤',
          type: 'line',
          data: w.segments.map((seg: any) => (seg.max_drawdown * 100).toFixed(2)),
          yAxisIndex: 1,
          itemStyle: { color: '#ef4444' },
          lineStyle: { width: 2 },
          symbol: 'triangle',
          symbolSize: 6,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239,68,68,0.15)' },
              { offset: 1, color: 'rgba(239,68,68,0)' },
            ]),
          },
        },
      ],
    })
  }
}

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
.page-container {
  height: auto;
  min-height: 100%;
  overflow: visible;
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
