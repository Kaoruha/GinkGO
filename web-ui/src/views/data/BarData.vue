<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-green">K线</span>
        K线数据
        <span v-if="isLoadingMore" class="tag tag-blue" style="margin-left: 8px">
          <span class="spin">↻</span> 加载历史数据...
        </span>
      </div>
      <div class="header-controls">
        <select v-model="selectedCode" class="form-select" @change="handleCodeChange">
          <option value="">选择股票</option>
          <option v-for="opt in stockOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
        <input
          type="date"
          :value="dateRange[0]?.format('YYYY-MM-DD') || ''"
          @change="onStartDateChange"
          class="form-input"
        />
        <input
          type="date"
          :value="dateRange[1]?.format('YYYY-MM-DD') || ''"
          @change="onEndDateChange"
          class="form-input"
        />
        <select v-model="frequency" class="form-select" @change="loadBars">
          <option value="day">日线</option>
          <option value="week">周线</option>
          <option value="month">月线</option>
        </select>
        <select v-model="adjustment" class="form-select" @change="loadBars">
          <option value="fore">前复权</option>
          <option value="back">后复权</option>
          <option value="none">不复权</option>
        </select>
        <button class="btn-primary" :disabled="loading" @click="loadBars">
          <span v-if="loading" class="spin">↻</span>
          刷新
        </button>
      </div>
    </div>

    <!-- K线图表 -->
    <div class="card">
      <h3 class="card-title">K线图</h3>
      <div class="chart-wrapper">
        <div ref="chartContainer" class="chart-container">
          <div v-if="isLoadingMore" class="loading-more-indicator">
            <span class="spin">↻</span>
            <span>正在加载历史数据...</span>
          </div>
        </div>
        <div v-if="!selectedCode" class="chart-empty">
          <p>请选择股票查看K线图</p>
        </div>
        <div v-if="selectedCode && !hasMoreHistory" class="no-more-data">
          已加载全部历史数据 (共 {{ barData.length }} 条)
        </div>
      </div>
    </div>

    <!-- 数据统计 -->
    <div class="stats-grid">
      <div class="stat-card-small">
        <div class="stat-value-small">{{ barData.length }}</div>
        <div class="stat-label-small">数据条数</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ latestBar?.close?.toFixed(2) || '-' }}</div>
        <div class="stat-label-small">最新价</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small" :class="priceChange >= 0 ? 'text-up' : 'text-down'">
          {{ priceChange >= 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
        </div>
        <div class="stat-label-small">涨跌幅</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ priceStats.high.toFixed(2) || '-' }}</div>
        <div class="stat-label-small">最高</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ priceStats.low.toFixed(2) || '-' }}</div>
        <div class="stat-label-small">最低</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ formatNumber(priceStats.totalVolume) }}</div>
        <div class="stat-label-small">成交量</div>
      </div>
    </div>

    <!-- K线数据表格 -->
    <div class="card">
      <h3 class="card-title">数据明细</h3>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>日期</th>
              <th>开盘</th>
              <th>最高</th>
              <th>最低</th>
              <th>收盘</th>
              <th>涨跌幅</th>
              <th>成交量</th>
              <th>成交额</th>
            </tr>
          </thead>
          <tbody v-if="!loading && barData.length > 0">
            <tr v-for="(bar, idx) in paginatedBars" :key="idx">
              <td>{{ formatDate(bar.timestamp) }}</td>
              <td>{{ bar.open?.toFixed(2) }}</td>
              <td>{{ bar.high?.toFixed(2) }}</td>
              <td>{{ bar.low?.toFixed(2) }}</td>
              <td>{{ bar.close?.toFixed(2) }}</td>
              <td :class="bar.change >= 0 ? 'text-up' : 'text-down'">
                {{ bar.change >= 0 ? '+' : '' }}{{ bar.change?.toFixed(2) }}%
              </td>
              <td>{{ formatNumber(bar.volume) }}</td>
              <td>{{ formatNumber(bar.amount) }}</td>
            </tr>
          </tbody>
          <tbody v-else-if="loading">
            <tr>
              <td colspan="8" class="text-center">加载中...</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="8" class="text-center">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="barData.length > 0" class="pagination">
        <button @click="prevPage" :disabled="pagination.current === 1" class="btn-small">上一页</button>
        <span class="pagination-info">
          {{ (pagination.current - 1) * pagination.pageSize + 1 }} -
          {{ Math.min(pagination.current * pagination.pageSize, pagination.total) }} / {{ pagination.total }}
        </span>
        <button @click="nextPage" :disabled="pagination.current * pagination.pageSize >= pagination.total" class="btn-small">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import dayjs, { Dayjs } from 'dayjs'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  ColorType,
  CrosshairMode,
  Time,
  Range,
} from 'lightweight-charts'

const route = useRoute()
const loading = ref(false)
const isLoadingMore = ref(false)
const chartContainer = ref<HTMLElement | null>(null)
const selectedCode = ref<string>('')
const dateRange = ref<[Dayjs, Dayjs]>([
  dayjs().subtract(6, 'month'),
  dayjs()
])
const frequency = ref('day')
const adjustment = ref('fore')
const barData = ref<any[]>([])

// 懒加载状态
const hasMoreHistory = ref(true)
const earliestDate = ref<Dayjs | null>(null)
const BATCH_SIZE = 300
const LOAD_THRESHOLD = 0.4
const MAX_DATA_POINTS = 3000

// 图表相关
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let isLoadingLocked = false

const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0
})

const stockOptions = [
  { value: '000001.SZ', label: '000001.SZ 平安银行' },
  { value: '000002.SZ', label: '000002.SZ 万科A' },
  { value: '600519.SH', label: '600519.SH 贵州茅台' },
]

const paginatedBars = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  return barData.value.slice(start, end)
})

const latestBar = computed(() => barData.value[barData.value.length - 1])
const prevBar = computed(() => barData.value[barData.value.length - 2])

const priceChange = computed(() => {
  if (!latestBar.value || !prevBar.value) return 0
  return ((latestBar.value.close - prevBar.value.close) / prevBar.value.close) * 100
})

const priceStats = computed(() => {
  if (barData.value.length === 0) return { high: 0, low: 0, totalVolume: 0 }
  const closes = barData.value.map(b => b.close)
  const volumes = barData.value.map(b => b.volume || 0)
  return {
    high: Math.max(...closes),
    low: Math.min(...closes),
    totalVolume: volumes.reduce((a, b) => a + b, 0)
  }
})

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

const formatNumber = (num: number): string => {
  if (!num) return '-'
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(2) + '万'
  return num.toString()
}

const onStartDateChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  dateRange.value[0] = dayjs(target.value)
  loadBars()
}

const onEndDateChange = (e: Event) => {
  const target = e.target as HTMLInputElement
  dateRange.value[1] = dayjs(target.value)
  loadBars()
}

const prevPage = () => {
  if (pagination.current > 1) {
    pagination.current--
  }
}

const nextPage = () => {
  if (pagination.current * pagination.pageSize < pagination.total) {
    pagination.current++
  }
}

// 模拟 API 获取数据
const fetchBarsFromAPI = async (code: string, startDate: Dayjs, count: number): Promise<any[]> => {
  await new Promise(resolve => setTimeout(resolve, 500))

  const mockData = []
  let price = 10 + Math.random() * 100

  for (let i = 0; i < count; i++) {
    const currentDate = startDate.add(i, 'day')
    if (currentDate.day() === 0 || currentDate.day() === 6) continue

    const change = (Math.random() - 0.5) * 5
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * 2
    const low = Math.min(open, close) - Math.random() * 2

    mockData.push({
      timestamp: currentDate.toISOString(),
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume: Math.floor(Math.random() * 10000000),
      amount: Math.floor(Math.random() * 1000000000),
      change: 0
    })
    price = close
  }

  for (let i = 1; i < mockData.length; i++) {
    mockData[i].change = ((mockData[i].close - mockData[i-1].close) / mockData[i-1].close * 100)
  }

  return mockData
}

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return

  if (chart) {
    chart.remove()
    chart = null
  }

  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = 500

  chart = createChart(chartContainer.value, {
    width: containerWidth,
    height: containerHeight,
    layout: {
      background: { type: ColorType.Solid, color: '#1a1a2e' },
      textColor: '#ffffff',
    },
    grid: {
      vertLines: { color: '#2a2a3e' },
      horzLines: { color: '#2a2a3e' },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2962ff' },
      horzLine: { color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2962ff' },
    },
    rightPriceScale: {
      borderColor: '#2a2a3e',
      scaleMargins: { top: 0.1, bottom: 0.25 },
    },
    timeScale: {
      borderColor: '#2a2a3e',
      timeVisible: true,
      secondsVisible: false,
    },
  })

  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#ef5350',
    downColor: '#26a69a',
    borderUpColor: '#ef5350',
    borderDownColor: '#26a69a',
    wickUpColor: '#ef5350',
    wickDownColor: '#26a69a',
  })

  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: { type: 'volume' },
    priceScaleId: 'volume',
  })

  chart.priceScale('volume').applyOptions({
    scaleMargins: { top: 0.8, bottom: 0 },
  })

  chart.timeScale().subscribeVisibleTimeRangeChange((range: Range<Time> | null) => {
    if (!range || isLoadingLocked) return
    handleVisibleRangeChange(range)
  })

  const handleResize = () => {
    if (chart && chartContainer.value) {
      chart.applyOptions({ width: chartContainer.value.clientWidth })
    }
  }
  window.addEventListener('resize', handleResize)
}

const handleVisibleRangeChange = async (range: Range<Time>) => {
  if (!chart || isLoadingLocked || !hasMoreHistory.value || isLoadingMore.value) return

  const logicalRange = chart.timeScale().getVisibleLogicalRange()
  if (!logicalRange) return

  const totalBars = barData.value.length
  const visibleFrom = Math.max(0, Math.floor(logicalRange.from as number))
  const positionRatio = totalBars > 0 ? visibleFrom / totalBars : 0

  if (positionRatio < LOAD_THRESHOLD) {
    await loadMoreHistory()
  }
}

const loadMoreHistory = async () => {
  if (!selectedCode.value || isLoadingLocked || !hasMoreHistory.value || !earliestDate.value) return

  isLoadingLocked = true
  isLoadingMore.value = true

  try {
    const newStartDate = earliestDate.value.subtract(BATCH_SIZE, 'day')
    const minDate = dayjs().subtract(10, 'year')
    if (newStartDate.isBefore(minDate)) {
      hasMoreHistory.value = false
      return
    }

    const scrollPosition = chart?.timeScale().scrollPosition()
    const historicalData = await fetchBarsFromAPI(selectedCode.value, newStartDate, BATCH_SIZE)

    if (historicalData.length === 0) {
      hasMoreHistory.value = false
      return
    }

    barData.value = [...historicalData, ...barData.value]
    earliestDate.value = dayjs(historicalData[0].timestamp)
    updateChartDataPrepend(historicalData)

    if (chart && scrollPosition !== undefined) {
      requestAnimationFrame(() => {
        chart?.timeScale().scrollToPosition(scrollPosition, false)
      })
    }

    pagination.total = barData.value.length
  } catch (error: any) {
    console.error(`加载历史数据失败: ${error.message}`)
  } finally {
    isLoadingMore.value = false
    setTimeout(() => {
      isLoadingLocked = false
    }, 800)
  }
}

let cachedCandleData: CandlestickData[] = []
let cachedVolumeData: HistogramData[] = []

const convertToChartData = (data: any[]): { candles: CandlestickData[], volumes: HistogramData[] } => {
  const candles: CandlestickData[] = []
  const volumes: HistogramData[] = []

  for (const item of data) {
    const time = dayjs(item.timestamp).format('YYYY-MM-DD') as any
    candles.push({
      time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    })
    volumes.push({
      time,
      value: item.volume,
      color: item.close >= item.open ? '#ef535080' : '#26a69a80',
    })
  }

  return { candles, volumes }
}

const updateChartDataPrepend = (newData: any[]) => {
  if (!candlestickSeries || !volumeSeries || newData.length === 0) return

  const { candles: newCandles, volumes: newVolumes } = convertToChartData(newData)

  requestAnimationFrame(() => {
    if (!candlestickSeries || !volumeSeries) return

    cachedCandleData = [...newCandles, ...cachedCandleData]
    cachedVolumeData = [...newVolumes, ...cachedVolumeData]

    if (cachedCandleData.length > MAX_DATA_POINTS) {
      cachedCandleData = cachedCandleData.slice(0, MAX_DATA_POINTS)
      cachedVolumeData = cachedVolumeData.slice(0, MAX_DATA_POINTS)
    }

    candlestickSeries.setData(cachedCandleData)
    volumeSeries.setData(cachedVolumeData)
  })
}

const updateChartData = () => {
  if (!candlestickSeries || !volumeSeries || barData.value.length === 0) return

  const { candles, volumes } = convertToChartData(barData.value)
  cachedCandleData = candles
  cachedVolumeData = volumes

  candlestickSeries.setData(cachedCandleData)
  volumeSeries.setData(cachedVolumeData)

  if (chart) {
    chart.timeScale().scrollToRealTime()
  }
}

const handleCodeChange = () => {
  hasMoreHistory.value = true
  earliestDate.value = null
  isLoadingLocked = false
  cachedCandleData = []
  cachedVolumeData = []
  loadBars()
}

const loadBars = async () => {
  if (!selectedCode.value) return

  loading.value = true
  hasMoreHistory.value = true
  isLoadingLocked = false
  cachedCandleData = []
  cachedVolumeData = []

  try {
    const startDate = dateRange.value[0]
    const data = await fetchBarsFromAPI(selectedCode.value, startDate, BATCH_SIZE)

    barData.value = data
    pagination.total = data.length

    if (data.length > 0) {
      earliestDate.value = dayjs(data[0].timestamp)
    }

    await nextTick()
    if (!chart) {
      initChart()
    }
    updateChartData()
  } catch (error: any) {
    console.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (route.query.code) {
    selectedCode.value = route.query.code as string
    loadBars()
  }
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
    chart = null
  }
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tag {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-green {
  background: #52c41a;
  color: #ffffff;
}

.tag-blue {
  background: #1890ff;
  color: #ffffff;
}

.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.form-select,
.form-input {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-family: inherit;
  cursor: pointer;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.btn-primary {
  padding: 8px 20px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.chart-wrapper {
  position: relative;
}

.chart-container {
  width: 100%;
  height: 500px;
  position: relative;
}

.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  z-index: 10;
  color: #8a8a9a;
}

.loading-more-indicator {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(24, 144, 255, 0.9);
  color: white;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 20;
}

.no-more-data {
  text-align: center;
  padding: 8px;
  color: #8a8a9a;
  font-size: 12px;
  background: #2a2a3e;
  border-top: 1px solid #3a3a4e;
  margin-top: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card-small {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value-small {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 4px;
}

.stat-label-small {
  font-size: 12px;
  color: #8a8a9a;
}

.text-up {
  color: #ef5350 !important;
}

.text-down {
  color: #26a69a !important;
}

.text-center {
  text-align: center;
  color: #8a8a9a;
  padding: 20px;
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
  font-size: 12px;
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 13px;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  margin-top: 16px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 13px;
}

.btn-small {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
