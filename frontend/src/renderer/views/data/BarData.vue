<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-green">K线</span>
      K线数据
      <span
        v-if="selectedCode"
        class="tag tag-blue"
      >{{ selectedLabel || selectedCode }}</span>
      <span
        v-if="isLoadingMore"
        class="tag tag-blue"
        style="margin-left: 8px"
      >
        <span class="spin">↻</span> 加载中...
      </span>
    </template>
    <template #actions>
      <span
        v-if="lastSyncTime"
        class="last-sync-hint"
      >{{ lastSyncTime }}</span>
      <button
        class="btn-sync"
        :disabled="!selectedCode || syncing"
        @click="handleSync"
      >
        <span
          v-if="syncing"
          class="spin"
        >↻</span>
        {{ syncing ? '同步中' : '同步' }}
      </button>
      <SearchSelect
        :search-fn="searchStocks"
        placeholder="搜索股票代码..."
        style="width: 200px;"
        @select="handleSelectStock"
      />
    </template>

    <!-- K线图表 + 行内统计 -->
    <div class="card">
      <div class="chart-header">
        <div
          v-if="barData.length > 0"
          class="stats-inline"
        >
          <span class="stat-item">最新 <strong>{{ formatDecimal(latestBar?.close) }}</strong></span>
          <!-- 数据不足(或 0 涨跌)不渲染涨跌:0 着色会被误读为方向 -->
          <span
            v-if="latestBar && prevBar && priceChange !== 0"
            class="stat-item"
            :class="priceChange > 0 ? 'text-up' : 'text-down'"
          >
            {{ priceChange > 0 ? '+' : '' }}{{ priceChange.toFixed(2) }}%
          </span>
          <span class="stat-item">高 {{ priceStats.high.toFixed(2) }}</span>
          <span class="stat-item">低 {{ priceStats.low.toFixed(2) }}</span>
          <span class="stat-item">量 {{ formatCompact(priceStats.totalVolume) }}</span>
          <span class="stat-item">{{ barData.length }} 条</span>
        </div>
      </div>
      <div class="chart-wrapper">
        <div
          ref="chartContainer"
          class="chart-container"
        >
          <div
            v-if="isLoadingMore"
            class="loading-more-indicator"
          >
            <span class="spin">↻</span>
            <span>正在加载历史数据...</span>
          </div>
        </div>
        <div
          v-if="!selectedCode"
          class="chart-empty"
        >
          <p>请选择股票查看K线图</p>
        </div>
        <div
          v-if="selectedCode && !hasMoreHistory"
          class="no-more-data"
        >
          已加载全部历史数据 (共 {{ barData.length }} 条)
        </div>
      </div>
    </div>

    <!-- K线数据表格:ProTable 自带卡片外壳 -->
    <h3 class="card-title">
      数据明细
    </h3>
    <ProTable
      :columns="barColumns"
      :data-source="barData"
      :loading="loading"
      :page="tablePage"
      :page-size="50"
      :page-sizes="[50]"
      :max-height="340"
      row-key="timestamp"
      :context-menu="rowMenu"
      @update:page="tablePage = $event"
    >
      <template #timestamp="{ record }">
        {{ formatDay(record.timestamp) }}
      </template>
      <template #open="{ record }">
        {{ formatDecimal(record.open) }}
      </template>
      <template #high="{ record }">
        {{ formatDecimal(record.high) }}
      </template>
      <template #low="{ record }">
        {{ formatDecimal(record.low) }}
      </template>
      <template #close="{ record }">
        {{ formatDecimal(record.close) }}
      </template>
      <template #change="{ record }">
        <span
          v-if="record.change == null"
          style="color: hsl(var(--muted-foreground))"
        >--</span>
        <span
          v-else
          :class="record.change > 0 ? 'text-up' : record.change < 0 ? 'text-down' : ''"
        >
          {{ record.change > 0 ? '+' : '' }}{{ record.change.toFixed(2) }}%
        </span>
      </template>
      <template #volume="{ record }">
        {{ formatCompact(record.volume) }}
      </template>
      <template #amount="{ record }">
        {{ formatCompact(record.amount) }}
      </template>
    </ProTable>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { useRoute } from 'vue-router'
import ProTable from '@/components/common/ProTable.vue'
import SearchSelect from '@/components/common/SearchSelect.vue'
import dayjs, { Dayjs } from 'dayjs'
import { dataApi } from '@/api'
import { formatCompact, formatDay, formatDateTime, formatDecimal } from '@/utils/format'
import { message as toast } from '@/utils/toast'
import type { MenuItem } from '@/composables/useContextMenu'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  ColorType,
  CrosshairMode,
  Time,
} from 'lightweight-charts'
import { useChartTheme, cssColor, upColor, downColor } from '@/composables/useChartTheme'
import { useAsyncAction } from '@/composables/useAsyncAction'

const route = useRoute()
const { theme } = useChartTheme()
const loading = ref(false)
const isLoadingMore = ref(false)
const chartContainer = ref<HTMLElement | null>(null)
const selectedCode = ref<string>('')
const barData = ref<any[]>([])
const lastSyncTime = ref<string>('')
// syncing 由 useAsyncAction 的 running 提供(见 handleSync)
const selectedLabel = ref('')

const hasMoreHistory = ref(true)
const earliestDate = ref<Dayjs | null>(null)
const BATCH_SIZE = 300
const LOAD_THRESHOLD = 0.4
const MAX_DATA_POINTS = 3000

let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let isLoadingLocked = false
let resizeObserver: ResizeObserver | null = null

const tablePage = ref(1)

/** 行右键菜单:复制行情值 */
const rowMenu = (record: any): MenuItem[] => [
  { label: '复制日期', action: () => { navigator.clipboard.writeText(formatDay(record.timestamp)); toast.success('已复制') } },
  { label: '复制收盘价', action: () => { navigator.clipboard.writeText(String(record.close ?? '')); toast.success('已复制') } },
  { label: '复制代码', action: () => { navigator.clipboard.writeText(selectedCode.value); toast.success('已复制') } },
]

const barColumns = [
  { title: '日期', dataIndex: 'timestamp' },
  { title: '开盘', dataIndex: 'open' },
  { title: '最高', dataIndex: 'high' },
  { title: '最低', dataIndex: 'low' },
  { title: '收盘', dataIndex: 'close' },
  { title: '涨跌幅', dataIndex: 'change' },
  { title: '成交量', dataIndex: 'volume' },
  { title: '成交额', dataIndex: 'amount' },
]

const searchStocks = async (query: string) => {
  // 拦截器已拆信封:分页端点 = {items, total, ...},直接取 .items(二次 .data 解包=静默空数据)
  const res: any = await dataApi.listStocks({ query, page_size: 50 })
  const items = res?.items ?? []
  return items.map((s: any) => ({
    value: s.code,
    label: `${s.code} ${s.name || ''}`,
  }))
}

// API 返回降序(新→旧):最新=首元素,前一日=次元素
// (旧版误取末元素,「最新」实际显示的是最早已加载日的价格)
const latestBar = computed(() => barData.value[0])
const prevBar = computed(() => barData.value[1])
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
    volume: bar.volume, amount: bar.amount,
    // null = 参照日未加载(未知),区别于 0(真实平盘);展示为 --
    change: null as number | null,
  }))
}

// 涨跌幅:数组为降序(新→旧),须与后一元素(更早一日收盘)比较。
// 旧版方向取反(涨跌幅变号)且每页首行无参照恒 0,与相邻收盘价明显矛盾。
// 全量最早一行的参照日可能未加载,保持 null(展示 --)。
const computeChanges = (data: any[]) => {
  for (const d of data) d.change = null
  for (let i = 0; i < data.length - 1; i++) {
    const prev = data[i + 1].close
    if (prev) data[i].change = ((data[i].close - prev) / prev) * 100
  }
}

const initChart = () => {
  if (!chartContainer.value) return
  if (chart) { chart.remove(); chart = null }

  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: 500,
    layout: { background: { type: ColorType.Solid, color: cssColor('--card') }, textColor: cssColor('--muted-foreground') },
    grid: { vertLines: { color: cssColor('--border') }, horzLines: { color: cssColor('--border') } },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: cssColor('--border'), width: 1, style: 3, labelBackgroundColor: cssColor('--primary') },
      horzLine: { color: cssColor('--border'), width: 1, style: 3, labelBackgroundColor: cssColor('--primary') },
    },
    rightPriceScale: { borderColor: cssColor('--border'), scaleMargins: { top: 0.1, bottom: 0.25 } },
    timeScale: { borderColor: cssColor('--border'), timeVisible: true, secondsVisible: false, fixRightEdge: true, fixLeftEdge: false },
  })

  candlestickSeries = chart.addCandlestickSeries({
    upColor: upColor(), downColor: downColor(),
    borderUpColor: upColor(), borderDownColor: downColor(),
    wickUpColor: upColor(), wickDownColor: downColor(),
  })
  volumeSeries = chart.addHistogramSeries({
    color: cssColor('--muted-foreground', 0.5), priceFormat: { type: 'volume' }, priceScaleId: 'volume',
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

  // 监听容器尺寸变化
  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => {
    if (chart && chartContainer.value) {
      chart.applyOptions({ width: chartContainer.value.clientWidth })
    }
  })
  resizeObserver.observe(chartContainer.value)
}

// 主题切换重绘:canvas 不认 CSS var,须重读 token 调 applyOptions(ADR-045)。
const applyChartTheme = () => {
  if (!chart) return
  chart.applyOptions({
    layout: { background: { type: ColorType.Solid, color: cssColor('--card') }, textColor: cssColor('--muted-foreground') },
    grid: { vertLines: { color: cssColor('--border') }, horzLines: { color: cssColor('--border') } },
    crosshair: {
      vertLine: { color: cssColor('--border'), labelBackgroundColor: cssColor('--primary') },
      horzLine: { color: cssColor('--border'), labelBackgroundColor: cssColor('--primary') },
    },
    rightPriceScale: { borderColor: cssColor('--border') },
    timeScale: { borderColor: cssColor('--border') },
  })
  candlestickSeries?.applyOptions({
    upColor: upColor(), downColor: downColor(),
    borderUpColor: upColor(), borderDownColor: downColor(),
    wickUpColor: upColor(), wickDownColor: downColor(),
  })
  volumeSeries?.applyOptions({ color: cssColor('--muted-foreground', 0.5) })
}
watch(theme, applyChartTheme)

let cachedCandleData: CandlestickData[] = []
let cachedVolumeData: HistogramData[] = []

const convertToChartData = (data: any[]) => {
  const candles: CandlestickData[] = [], volumes: HistogramData[] = []
  for (const item of data) {
    const time = formatDay(item.timestamp) as any
    candles.push({ time, open: item.open, high: item.high, low: item.low, close: item.close })
    volumes.push({ time, value: item.volume })
  }
  return { candles, volumes }
}

// 去重(按 time) + 升序;lightweight-charts setData 要求时间严格升序,否则断言失败
// time 为 'YYYY-MM-DD' 字符串(ISO 格式字典序=时间序),String() 兜底防 Time 类型漂移
const dedupAndSort = <T extends { time: any }>(arr: T[]): T[] =>
  [...new Map(arr.map(d => [d.time, d])).values()]
    .sort((a, b) => String(a.time).localeCompare(String(b.time)))

const updateChartDataPrepend = (_newData: any[], visibleTimeRange: { from: Time; to: Time } | null) => {
  if (!candlestickSeries || !volumeSeries || barData.value.length === 0) return

  // 从 barData（source of truth）重建，避免缓存不同步
  const { candles, volumes } = convertToChartData(barData.value)

  // 去重 + 升序排列
  const deduped = dedupAndSort

  cachedCandleData = deduped(candles).slice(-MAX_DATA_POINTS)
  cachedVolumeData = deduped(volumes).slice(-MAX_DATA_POINTS)

  candlestickSeries.setData(cachedCandleData)
  volumeSeries.setData(cachedVolumeData)

  // 用时间范围恢复（不受逻辑索引位移影响）
  if (chart && visibleTimeRange) {
    chart.timeScale().setVisibleRange(visibleTimeRange)
  }
}

const updateChartData = () => {
  if (!candlestickSeries || !volumeSeries || barData.value.length === 0) return
  const { candles, volumes } = convertToChartData(barData.value)
  cachedCandleData = dedupAndSort(candles)
  cachedVolumeData = dedupAndSort(volumes)
  candlestickSeries.setData(cachedCandleData)
  volumeSeries.setData(cachedVolumeData)
  if (chart) chart.timeScale().scrollToRealTime()
}

const loadMoreHistory = async (preserveView = true) => {
  if (!selectedCode.value || isLoadingLocked || !hasMoreHistory.value || !earliestDate.value) return
  isLoadingLocked = true
  isLoadingMore.value = true
  try {
    const newStartDate = earliestDate.value.subtract(BATCH_SIZE, 'day')
    const newEndDate = earliestDate.value.subtract(1, 'day')
    const visibleTimeRange = preserveView ? (chart?.timeScale().getVisibleRange() ?? null) : null
    const historicalData = await fetchBarsFromAPI(selectedCode.value, newStartDate, BATCH_SIZE, newEndDate)
    if (historicalData.length === 0) { hasMoreHistory.value = false; return }
    // 先并再全量重算:新批最旧一行的参照日可能在旧数据尾部,逐批独立算会漏
    barData.value = [...historicalData, ...barData.value]
    computeChanges(barData.value)
    earliestDate.value = dayjs(historicalData[0].timestamp)
    updateChartDataPrepend(historicalData, visibleTimeRange)
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

const handleSelectStock = (opt: { value: string; label: string }) => {
  selectedCode.value = opt.value
  selectedLabel.value = opt.label
  handleCodeChange()
}

const fillChart = async () => {
  const TARGET_BARS = 1200
  let attempts = 0
  while (hasMoreHistory.value && barData.value.length < TARGET_BARS && attempts < 20) {
    isLoadingLocked = false
    await loadMoreHistory(false)
    if (!hasMoreHistory.value) break
    await new Promise(r => setTimeout(r, 300))
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
    tablePage.value = 1
    if (data.length > 0) earliestDate.value = dayjs(data[0].timestamp)
    await nextTick()
    if (!chart) initChart()
    updateChartData()
    // 初始数据已就绪，立即解除表格 loading
    loading.value = false
    // 后台静默填充历史数据，不阻塞表格
    fillChart().then(() => { if (chart) chart.timeScale().scrollToRealTime() })
  } catch (error: any) {
    console.error(`加载失败: ${error.message}`)
  }
}

const fetchLastSyncTime = async () => {
  try {
    const res: any = await dataApi.getSyncHistory({ sync_type: 'bars', page: 1, page_size: 1 })
    // 拦截器已拆信封:分页响应重组为 {items,total};旧读 res.data 恒 undefined 致 lastSyncTime 永不显示
    const items: any[] = res?.items ?? (Array.isArray(res) ? res : [])
    if (items.length > 0 && items[0].completed_at) {
      lastSyncTime.value = formatDateTime(items[0].completed_at)
    }
  } catch { /* ignore */ }
}

const { running: syncing, run: handleSync } = useAsyncAction(async () => {
  if (!selectedCode.value) return
  await dataApi.sync({ type: 'bars', codes: [selectedCode.value] })
  await loadBars()
  await fetchLastSyncTime()
}, { success: false })

onMounted(async () => {
  const code = route.query.code as string
  if (code) {
    selectedCode.value = code
    loadBars()
  } else {
    // 无指定代码时，默认选择第一只可用股票
    try {
      const opts = await searchStocks('')
      if (opts.length > 0) {
        selectedCode.value = opts[0].value
        selectedLabel.value = opts[0].label
        loadBars()
      }
    } catch { /* ignore */ }
  }
  fetchLastSyncTime()
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (chart) { chart.remove(); chart = null }
})
</script>

<style scoped>
:deep(.card) { overflow: visible; }

.last-sync-hint {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
}

.btn-sync {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: hsl(var(--success) / 0.15);
  border: 1px solid hsl(var(--success) / 0.3);
  border-radius: var(--radius);
  color: hsl(var(--success));
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.btn-sync:hover:not(:disabled) {
  background: hsl(var(--success) / 0.25);
  border-color: hsl(var(--success));
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

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title { font-size: 16px; font-weight: 600; color: hsl(var(--foreground)); margin: 0 0 16px 0; }
.chart-header .card-title { margin: 0; }

.stats-inline { display: flex; gap: 16px; font-size: 13px; color: hsl(var(--muted-foreground)); }
.stats-inline strong { color: hsl(var(--foreground)); }
.stat-item { white-space: nowrap; }

.chart-wrapper { position: relative; }
.chart-container { width: 100%; height: 500px; position: relative; }

.chart-empty {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--border));
  z-index: 10;
  color: hsl(var(--muted-foreground));
}

.loading-more-indicator {
  position: absolute;
  top: 10px; left: 50%;
  transform: translateX(-50%);
  background: hsl(var(--primary) / 0.9);
  color: hsl(var(--primary-foreground));
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 20;
}

.no-more-data {
  text-align: center;
  padding: 8px;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  background: hsl(var(--border));
  border-top: 1px solid hsl(var(--secondary));
  margin-top: 8px;
}

.text-up { color: hsl(var(--success)) !important; }
.text-down { color: hsl(var(--error)) !important; }
</style>
