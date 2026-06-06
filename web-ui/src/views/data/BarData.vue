<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <button class="back-btn" @click="$router.push('/data')">←</button>
        <span class="tag tag-green">K线</span>
        K线数据
        <span v-if="isLoadingMore" class="tag tag-blue" style="margin-left: 8px">
          <span class="spin">↻</span> 加载历史数据...
        </span>
      </div>
      <div class="header-controls">
        <span v-if="lastSyncTime" class="last-sync-hint">
          最近同步: {{ lastSyncTime }}
        </span>
        <button
          class="btn-sync"
          :disabled="!selectedCode || syncing"
          @click="handleSync"
        >
          <span v-if="syncing" class="spin">↻</span>
          {{ syncing ? '同步中...' : '同步' }}
        </button>
        <select v-model="selectedCode" class="form-select" @change="handleCodeChange">
          <option value="">选择股票</option>
          <option v-for="opt in stockOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- K线图表 + 行内统计 -->
    <div class="card">
      <div class="chart-header">
        <h3 class="card-title">K线图</h3>
        <div v-if="barData.length > 0" class="stats-inline">
          <span class="stat-item">最新 <strong>{{ latestBar?.close?.toFixed(2) }}</strong></span>
          <span class="stat-item" :class="priceChange >= 0 ? 'text-up' : 'text-down'">
            {{ priceChange >= 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
          </span>
          <span class="stat-item">高 {{ priceStats.high.toFixed(2) }}</span>
          <span class="stat-item">低 {{ priceStats.low.toFixed(2) }}</span>
          <span class="stat-item">量 {{ formatNumber(priceStats.totalVolume) }}</span>
          <span class="stat-item">{{ barData.length }} 条</span>
        </div>
      </div>
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
        <button @click="pagination.current = 1" :disabled="pagination.current === 1" class="btn-small">«</button>
        <button @click="pagination.current--" :disabled="pagination.current === 1" class="btn-small">‹</button>
        <span class="pagination-info">
          {{ (pagination.current - 1) * pagination.pageSize + 1 }} -
          {{ Math.min(pagination.current * pagination.pageSize, pagination.total) }} / {{ pagination.total }}
        </span>
        <button @click="pagination.current++" :disabled="pagination.current * pagination.pageSize >= pagination.total" class="btn-small">›</button>
        <button @click="pagination.current = Math.ceil(pagination.total / pagination.pageSize)" :disabled="pagination.current * pagination.pageSize >= pagination.total" class="btn-small">»</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import dayjs, { Dayjs } from 'dayjs'
import { dataApi } from '@/api'
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
const barData = ref<any[]>([])
const lastSyncTime = ref<string>('')
const syncing = ref(false)

const hasMoreHistory = ref(true)
const earliestDate = ref<Dayjs | null>(null)
const BATCH_SIZE = 300
const LOAD_THRESHOLD = 0.4
const MAX_DATA_POINTS = 3000

let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let isLoadingLocked = false

const pagination = reactive({ current: 1, pageSize: 50, total: 0 })

const stockOptions = [
  { value: '000001.SZ', label: '000001.SZ 平安银行' },
  { value: '000002.SZ', label: '000002.SZ 万科A' },
  { value: '600519.SH', label: '600519.SH 贵州茅台' },
]

const paginatedBars = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize
  return barData.value.slice(start, start + pagination.pageSize)
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
  return { high: Math.max(...closes), low: Math.min(...closes), totalVolume: volumes.reduce((a, b) => a + b, 0) }
})

const formatDate = (date: string) => dayjs(date).format('YYYY-MM-DD')
const formatNumber = (num: number): string => {
  if (!num) return '-'
  if (num >= 100000000) return (num / 100000000).toFixed(2) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(2) + '万'
  return num.toString()
}

const fetchBarsFromAPI = async (code: string, startDate: Dayjs, pageSize: number, endDate?: Dayjs): Promise<any[]> => {
  const res: any = await dataApi.getBars({
    code,
    start_date: startDate.format('YYYY-MM-DD'),
    end_date: (endDate || dayjs()).format('YYYY-MM-DD'),
    page: 1,
    page_size: pageSize,
  })
  const payload = (res as any)?.data !== undefined ? (res as any).data : res
  const items = Array.isArray(payload) ? payload : (payload?.items ?? payload?.data ?? [])
  return items.map((bar: any) => ({
    timestamp: bar.date || bar.timestamp,
    open: bar.open, high: bar.high, low: bar.low, close: bar.close,
    volume: bar.volume, amount: bar.amount, change: 0,
  }))
}

const computeChanges = (data: any[]) => {
  for (let i = 1; i < data.length; i++) {
    if (data[i - 1].close) data[i].change = ((data[i].close - data[i - 1].close) / data[i - 1].close) * 100
  }
}

const initChart = () => {
  if (!chartContainer.value) return
  if (chart) { chart.remove(); chart = null }

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 500,
    layout: { background: { type: ColorType.Solid, color: '#1a1a2e' }, textColor: '#ffffff' },
    grid: { vertLines: { color: '#2a2a3e' }, horzLines: { color: '#2a2a3e' } },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2962ff' },
      horzLine: { color: '#758696', width: 1, style: 3, labelBackgroundColor: '#2962ff' },
    },
    rightPriceScale: { borderColor: '#2a2a3e', scaleMargins: { top: 0.1, bottom: 0.25 } },
    timeScale: { borderColor: '#2a2a3e', timeVisible: true, secondsVisible: false },
  })

  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#ef5350', downColor: '#26a69a',
    borderUpColor: '#ef5350', borderDownColor: '#26a69a',
    wickUpColor: '#ef5350', wickDownColor: '#26a69a',
  })
  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a', priceFormat: { type: 'volume' }, priceScaleId: 'volume',
  })
  chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

  const checkLoadMore = () => {
    if (isLoadingLocked || !hasMoreHistory.value) return
    const logicalRange = chart?.timeScale().getVisibleLogicalRange()
    if (!logicalRange) return
    const totalBars = barData.value.length
    const visibleFrom = Math.floor(logicalRange.from as number)
    // 当可视区域左边缘接近数据起点时，加载更多
    if (totalBars > 0 && visibleFrom < totalBars * LOAD_THRESHOLD) loadMoreHistory()
  }

  chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    if (isLoadingLocked) return
    checkLoadMore()
  })

  window.addEventListener('resize', () => {
    if (chart && chartContainer.value) {
      chart.applyOptions({ width: chartContainer.value.clientWidth })
      // resize 后检查是否需要加载更多数据填充新宽度
      setTimeout(() => checkLoadMore(), 100)
    }
  })
}

let cachedCandleData: CandlestickData[] = []
let cachedVolumeData: HistogramData[] = []

const convertToChartData = (data: any[]) => {
  const candles: CandlestickData[] = [], volumes: HistogramData[] = []
  for (const item of data) {
    const time = dayjs(item.timestamp).format('YYYY-MM-DD') as any
    candles.push({ time, open: item.open, high: item.high, low: item.low, close: item.close })
    volumes.push({ time, value: item.volume, color: item.close >= item.open ? '#ef535080' : '#26a69a80' })
  }
  return { candles, volumes }
}

const updateChartDataPrepend = (newData: any[]) => {
  if (!candlestickSeries || !volumeSeries || newData.length === 0) return
  const { candles, volumes } = convertToChartData(newData)
  requestAnimationFrame(() => {
    if (!candlestickSeries || !volumeSeries) return
    cachedCandleData = [...candles, ...cachedCandleData]
    cachedVolumeData = [...volumes, ...cachedVolumeData]
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
  if (chart) chart.timeScale().scrollToRealTime()
}

const loadMoreHistory = async () => {
  if (!selectedCode.value || isLoadingLocked || !hasMoreHistory.value || !earliestDate.value) return
  isLoadingLocked = true
  isLoadingMore.value = true
  try {
    const newStartDate = earliestDate.value.subtract(BATCH_SIZE, 'day')
    const newEndDate = earliestDate.value.subtract(1, 'day')
    const scrollPosition = chart?.timeScale().scrollPosition()
    const historicalData = await fetchBarsFromAPI(selectedCode.value, newStartDate, BATCH_SIZE, newEndDate)
    computeChanges(historicalData)
    if (historicalData.length === 0) { hasMoreHistory.value = false; return }
    barData.value = [...historicalData, ...barData.value]
    earliestDate.value = dayjs(historicalData[0].timestamp)
    updateChartDataPrepend(historicalData)
    if (chart && scrollPosition !== undefined) {
      requestAnimationFrame(() => { chart?.timeScale().scrollToPosition(scrollPosition, false) })
    }
    pagination.total = barData.value.length
  } catch (error: any) {
    console.error(`加载历史数据失败: ${error.message}`)
  } finally {
    isLoadingMore.value = false
    setTimeout(() => { isLoadingLocked = false }, 800)
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

const fillChart = async () => {
  const TARGET_BARS = 1200
  let attempts = 0
  while (hasMoreHistory.value && barData.value.length < TARGET_BARS && attempts < 20) {
    isLoadingLocked = false
    await loadMoreHistory()
    if (!hasMoreHistory.value) break
    await new Promise(r => setTimeout(r, 900))
    attempts++
  }
}

const loadBars = async () => {
  if (!selectedCode.value) return
  loading.value = true
  hasMoreHistory.value = true
  isLoadingLocked = false
  cachedCandleData = []
  cachedVolumeData = []
  try {
    const data = await fetchBarsFromAPI(selectedCode.value, dayjs().subtract(6, 'month'), BATCH_SIZE)
    computeChanges(data)
    barData.value = data
    pagination.total = data.length
    pagination.current = 1
    if (data.length > 0) earliestDate.value = dayjs(data[0].timestamp)
    await nextTick()
    if (!chart) initChart()
    updateChartData()
    // 初始加载后自动填充图表左侧空白
    await fillChart()
  } catch (error: any) {
    console.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const fetchLastSyncTime = async () => {
  try {
    const res: any = await dataApi.getSyncHistory({ sync_type: 'bars', page: 1, page_size: 1 })
    const items: any[] = res?.data ?? []
    if (items.length > 0 && items[0].completed_at) {
      const d = new Date(items[0].completed_at)
      lastSyncTime.value = d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
    }
  } catch { /* ignore */ }
}

const handleSync = async () => {
  if (!selectedCode.value || syncing.value) return
  syncing.value = true
  try {
    await dataApi.sync({ type: 'bars', codes: [selectedCode.value] })
    await loadBars()
    await fetchLastSyncTime()
  } catch (e: any) {
    console.error('同步失败:', e.message)
  } finally {
    syncing.value = false
  }
}

onMounted(() => {
  selectedCode.value = (route.query.code as string) || stockOptions[0]?.value || ''
  if (selectedCode.value) loadBars()
  fetchLastSyncTime()
})

onUnmounted(() => { if (chart) { chart.remove(); chart = null } })
</script>

<style scoped>
.page-container { padding: 0; background: transparent; }
.page-container :deep(.card) { overflow: visible; }

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }

.last-sync-hint {
  font-size: 12px;
  color: #8a8a9a;
  white-space: nowrap;
}

.btn-sync {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(82, 196, 26, 0.15);
  border: 1px solid rgba(82, 196, 26, 0.3);
  border-radius: 6px;
  color: #52c41a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-sync:hover:not(:disabled) {
  background: rgba(82, 196, 26, 0.25);
  border-color: #52c41a;
}

.btn-sync:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.back-btn {
  background: none;
  border: 1px solid #2a2a3e;
  color: #8a8a9a;
  font-size: 16px;
  padding: 4px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.back-btn:hover { border-color: #1890ff; color: #1890ff; }

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title { font-size: 16px; font-weight: 600; color: #ffffff; margin: 0 0 16px 0; }
.chart-header .card-title { margin: 0; }

.stats-inline { display: flex; gap: 16px; font-size: 13px; color: #8a8a9a; }
.stats-inline strong { color: #ffffff; }
.stat-item { white-space: nowrap; }

.chart-wrapper { position: relative; }
.chart-container { width: 100%; height: 500px; position: relative; }

.chart-empty {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  z-index: 10;
  color: #8a8a9a;
}

.loading-more-indicator {
  position: absolute;
  top: 10px; left: 50%;
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

.text-up { color: #ef5350 !important; }
.text-down { color: #26a69a !important; }
.text-center { text-align: center; color: #8a8a9a; padding: 20px; }

.table-wrapper { overflow-x: auto; }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td {
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
.data-table td { color: #ffffff; font-size: 13px; }
.data-table tbody tr:hover { background: #2a2a3e; }

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 0;
  margin-top: 16px;
}

.pagination-info { color: #8a8a9a; font-size: 13px; }

.btn-small:hover:not(:disabled) { border-color: #1890ff; color: #1890ff; }
.btn-small:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
