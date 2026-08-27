<template>
  <PageLayout>
    <template #title>
      <PageTitle title="数据浏览" />
    </template>
    <template #meta>
      <!-- 上下文提示:当前查询对象(跨类型保留,避免重复输入) -->
      <span
        v-if="code"
        class="tag tag-blue"
      >{{ code }}</span>
      <span
        v-if="typeHasDate && startDate && endDate"
        class="tag"
      >{{ startDate }} ~ {{ endDate }}</span>
    </template>
    <div class="browser-body">
      <!-- 筛选条(2026-08-18 自标题栏 actions 移入内容区):核心筛选藏在页面
           右上角落用户找不到;置于类型切换与结果区之间,筛选-结果就近关联 -->
      <div class="filter-bar">
        <SearchSelect
          :search-fn="searchStocks"
          placeholder="搜索股票代码..."
          style="width: 220px;"
          @select="handleSelectStock"
        />
        <template v-if="typeHasDate">
          <DateField
            v-model="startDate"
            class="control-input"
          />
          <span class="filter-sep">~</span>
          <DateField
            v-model="endDate"
            class="control-input"
          />
        </template>
        <select
          v-if="type === 'bars'"
          v-model="frequency"
          class="control-select"
        >
          <option
            v-for="f in FREQ_OPTIONS"
            :key="f.value"
            :value="f.value"
          >
            {{ f.label }}
          </option>
        </select>
        <button
          class="btn-query"
          :disabled="!canQuery || querying"
          @click="runQuery"
        >
          {{ querying ? '查询中' : '查询' }}
        </button>
      </div>

      <!-- 类型切换:切类型保留 code/日期上下文,只换结果维度 -->
      <SegmentedControl
        :options="TYPE_OPTIONS"
        :model-value="type"
        @update:model-value="switchType"
      />

      <!-- K线图(TradingView Lightweight Charts,旧 BarData 同款):candlestick+成交量
           叠加、滚轮缩放/拖拽平移/十字线;向左滚动自动加载更早历史(300根/批)。
           v-show:实例随组件生命周期存活,类型切换仅隐藏 -->
      <div
        v-show="type === 'bars' && chartBars.length > 1"
        class="card chart-card"
      >
        <div class="chart-header">
          <span class="stat-item">{{ code }}</span>
          <span
            v-if="latestChartBar"
            class="stat-item"
          >最新 <strong>{{ Number(latestChartBar.close).toFixed(2) }}</strong></span>
          <span
            class="stat-item"
            :class="chartChangePct >= 0 ? 'val-up' : 'val-down'"
          >{{ chartChangePct >= 0 ? '+' : '' }}{{ chartChangePct.toFixed(2) }}%</span>
          <span class="stat-item">高 <strong>{{ chartStats.high }}</strong></span>
          <span class="stat-item">低 <strong>{{ chartStats.low }}</strong></span>
          <span class="stat-item">{{ chartBars.length }} 根</span>
          <span
            v-if="isLoadingMore"
            class="stat-item"
          >加载历史中…</span>
        </div>
        <div
          ref="lwChartContainer"
          class="chart-container"
        />
        <!-- 图表下方状态栏:可视区间随缩放/平移实时更新,与时间轴标尺并读 -->
        <div class="chart-footer">
          <span class="footer-range">
            可视范围
            <strong>{{ visibleRangeText || '--' }}</strong>
            <span class="footer-count">{{ visibleBarsCount }} / {{ chartBars.length }} 根</span>
          </span>
          <span class="footer-hint">{{
            hasMoreHistory ? '滚轮缩放 · 拖拽平移 · 左滚加载更早历史' : '已到最早数据 · 无更早历史'
          }}</span>
        </div>
        <!-- 区间导航条:全量缩略图+可拖窗口,与主图双向联动(拖拽选区间/缩放同步) -->
        <RangeNavigator
          ref="rangeNavRef"
          :data="navigatorData"
          @range-change="onNavigatorRange"
          @drag-state="onNavDragState"
        />
      </div>

      <ProTable
        :columns="columns"
        :data-source="rows"
        :loading="querying"
        row-key="uuid"
        flow
        :total="total"
        :page="page"
        :page-size="pageSize"
        server-pagination
        :empty-text="emptyText"
        @update:page="onPageChange"
      >
        <!-- 股票状态:布尔 → 上市/退市中文标签 -->
        <template #is_active="{ record }">
          <span :class="record.is_active ? 'tag tag-green' : 'tag tag-gray'">
            {{ record.is_active ? '上市' : '退市' }}
          </span>
        </template>
        <!-- Tick 方向:复用全站方向着色 -->
        <template #direction="{ record }">
          <span :class="directionColor(record.direction)">{{ directionLabel(record.direction) }}</span>
        </template>
        <!-- 涨跌幅:按当前页相邻收盘价派生,首页首行无前值 -->
        <template #change="{ record }">
          <span
            v-if="record.__change != null"
            :class="record.__change >= 0 ? 'val-up' : 'val-down'"
          >{{ (record.__change * 100).toFixed(2) }}%</span>
          <span
            v-else
            class="val-muted"
          >-</span>
        </template>
      </ProTable>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
/**
 * 数据浏览器(2026-08-18 数据区交互重构):股票/K线/Tick/复权因子四页合一。
 *
 * 设计要点:
 * - 类型 SegmentedControl 切换,code/日期上下文跨类型保留——同一标的连续
 *   查四类数据不再重复输入(旧 4 页各输一次);
 * - 查询条件全量进 URL query(type/code/start/end/freq/page):可刷新保持、
 *   可分享深链(概览页数据资产卡直达即带 query);
 * - 统一骨架:SearchSelect(股票搜索) + DateField + ProTable 服务端分页;
 * - 枚举中文化:is_active→上市/退市、tick direction→买/卖(directionLabel);
 *   bars 涨跌幅由页内相邻收盘价派生(后端无该字段)。
 */
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs, { Dayjs } from 'dayjs'
import utc from 'dayjs/plugin/utc'
dayjs.extend(utc)
// K线用 TradingView Lightweight Charts(旧 BarData 同款):滚轮缩放/拖拽平移/
// 十字线交互为金融场景标配;ECharts 版已移除(单一实现原则)
import {
  createChart, IChartApi, ISeriesApi,
  CandlestickData, HistogramData, ColorType, CrosshairMode,
} from 'lightweight-charts'
import { useChartTheme, cssColor, upColor, downColor } from '@/composables/useChartTheme'
import RangeNavigator from '@/components/charts/RangeNavigator.vue'
import { formatDay } from '@/utils/format'
import PageLayout from '@/components/common/PageLayout.vue'
import PageTitle from '@/components/common/PageTitle.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import SearchSelect, { type SearchOption } from '@/components/common/SearchSelect.vue'
import ProTable from '@/components/common/ProTable.vue'
import DateField from '@/components/common/DateField.vue'
import { dataApi } from '@/api/modules/data'
import { directionLabel, directionColor } from '@/composables/useBacktestFormatters'
import { useAsyncAction } from '@/composables'

const route = useRoute()
const router = useRouter()

// ---- 类型注册表:新增数据类型在此扩一行 ----
type DataType = 'stocks' | 'bars' | 'ticks' | 'adjust'
const TYPE_OPTIONS: { key: DataType; label: string }[] = [
  { key: 'stocks', label: '股票信息' },
  { key: 'bars', label: 'K线数据' },
  { key: 'ticks', label: 'Tick 数据' },
  { key: 'adjust', label: '复权因子' },
]
const FREQ_OPTIONS = [
  { value: 'day', label: '日频' },
  { value: 'week', label: '周频' },
  { value: 'month', label: '月频' },
]

// ---- 查询状态(镜像 URL query,单一事实源在 query) ----
const type = ref<DataType>('stocks')
const code = ref('')
const startDate = ref('')
const endDate = ref('')
const frequency = ref('day')
const page = ref(1)
const pageSize = 20

const typeHasDate = computed(() => type.value !== 'stocks')
// stocks 全量浏览不需要 code;其余类型按 code 查
const canQuery = computed(() => type.value === 'stocks' || !!code.value)

const rows = ref<any[]>([])
const total = ref(0)
const { running: querying, run: runQuery } = useAsyncAction(fetchData)

// ---- 列定义:日期列名后端各异(stocks.list_date / bars.date / ticks.timestamp...),此处归一 ----
const columns = computed(() => {
  switch (type.value) {
    case 'stocks':
      return [
        { title: '代码', dataIndex: 'code' },
        { title: '名称', dataIndex: 'name' },
        { title: '交易所', dataIndex: 'exchange' },
        { title: '状态', dataIndex: 'is_active' },
        { title: '上市日期', dataIndex: 'list_date' },
      ]
    case 'bars':
      return [
        { title: '代码', dataIndex: 'code' },
        { title: '日期', dataIndex: 'date' },
        { title: '开盘', dataIndex: 'open' },
        { title: '最高', dataIndex: 'high' },
        { title: '最低', dataIndex: 'low' },
        { title: '收盘', dataIndex: 'close' },
        { title: '涨跌幅', dataIndex: 'change' },
        { title: '成交量', dataIndex: 'volume' },
        { title: '成交额', dataIndex: 'amount' },
        { title: '频率', dataIndex: 'period' },
      ]
    case 'ticks':
      return [
        { title: '代码', dataIndex: 'code' },
        { title: '时间', dataIndex: 'timestamp' },
        { title: '价格', dataIndex: 'price' },
        { title: '成交量', dataIndex: 'volume' },
        { title: '方向', dataIndex: 'direction' },
      ]
    default: // adjust
      return [
        { title: '代码', dataIndex: 'code' },
        { title: '日期', dataIndex: 'timestamp' },
        { title: '前复权', dataIndex: 'foreadjustfactor' },
        { title: '后复权', dataIndex: 'backadjustfactor' },
        { title: '复权因子', dataIndex: 'adjustfactor' },
      ]
  }
})

const emptyText = computed(() =>
  canQuery.value ? '暂无数据,试试调整筛选条件' : `输入股票代码查询${TYPE_OPTIONS.find(t => t.key === type.value)?.label || ''}`)

async function fetchData() {
  const params: Record<string, any> = {
    page: page.value,
    page_size: pageSize,
  }
  if (type.value !== 'stocks') {
    params.code = code.value
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value
  }
  if (type.value === 'bars') params.frequency = frequency.value

  try {
    let res: any
    if (type.value === 'stocks') res = await dataApi.listStocks({ query: code.value || undefined, ...params })
    else if (type.value === 'bars') res = await dataApi.getBars(params as any)
    else if (type.value === 'ticks') res = await dataApi.getTicks(params as any)
    else res = await dataApi.getAdjustFactors(params as any)

    const items = (res?.items ?? res ?? []) as any[]
    // bars 涨跌幅:相邻收盘派生(API 无该字段);后端按日期倒序,前值=下一行
    if (type.value === 'bars') {
      items.forEach((r, i) => {
        const prev = items[i + 1]
        r.__change = prev?.close ? (r.close - prev.close) / prev.close : null
      })
    }
    rows.value = items
    total.value = res?.total ?? items.length
  } catch {
    rows.value = []
    total.value = 0
  }
  // bars:图表自治加载(独立分页/滚动填充),与表格分页互不干扰
  if (type.value === 'bars' && code.value) loadChartBars()
}

// ---- K线图(TradingView Lightweight Charts,自旧 BarData 迁移) ----
// 图表数据自治(chartBars):首屏按筛选范围拉 300 根,后台静默填充至 1200,
// 向左滚动到数据起点附近自动向前 prepend 300 根(表格仍走服务端分页,互不干扰)
const lwChartContainer = ref<HTMLElement | null>(null)
const chartBars = ref<any[]>([])
const isLoadingMore = ref(false)
const hasMoreHistory = ref(true)
const earliestDate = ref<Dayjs | null>(null)
const BATCH_SIZE = 300
// 触发提前(2026-08-18):比例阈值 0.4→0.6 + 绝对余量 80 根(先到先触发)。
// 原 0.4 贴边,左拖到数据尽头才拉取,用户能感知"数据没了"的空窗
const LOAD_THRESHOLD = 0.6
const LOAD_HEADROOM_BARS = 150
const MAX_DATA_POINTS = 3000
const { theme } = useChartTheme()

let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let isLoadingLocked = false
let resizeObserver: ResizeObserver | null = null

// 最新两根按 date 取最大:loadMoreHistory 会向前 prepend 历史批次,数组[0]
// 不再可靠(是历史批次的最新,非全序列最新);dedup 后按日期排序取头两项
const chartBarsByDateDesc = computed(() =>
  [...chartBars.value].sort((a, b) => String(b.date || '').localeCompare(String(a.date || ''))))
const latestChartBar = computed(() => chartBarsByDateDesc.value[0])
const prevChartBar = computed(() => chartBarsByDateDesc.value[1])

// 升序视图(setData 同序):可视区间指示按逻辑索引映射回日期
const chartBarsByDateAsc = computed(() => [...chartBarsByDateDesc.value].reverse())
const visibleRangeText = ref('')
const visibleBarsCount = ref(0)
const fmtDate = (d: any) => String(d || '').slice(0, 10)

// ---- 区间导航条:全量缩略图数据(升序去重) + 双向联动 ----
const rangeNavRef = ref<InstanceType<typeof RangeNavigator> | null>(null)
const navigatorData = computed(() => {
  const seen = new Map<string, { time: string; close: number }>()
  for (const b of chartBarsByDateAsc.value) {
    const t = fmtDate(b.date)
    if (t) seen.set(t, { time: t, close: Number(b.close) || 0 })
  }
  return [...seen.values()].sort((a, b) => a.time.localeCompare(b.time))
})
// 导航条拖拽态:拖拽中每帧 emit range,若顺带触发懒加载会形成加载风暴
// (每 400ms 一批,与拖拽时序交错 → 窗口/视图乱跳)。拖拽中挂起,松手补一次
let navDragging = false
function onNavDragState(dragging: boolean) {
  navDragging = dragging
  if (!dragging) maybeLoadByNavigator()
}

// 导航条拖拽 → 主图跟随
function onNavigatorRange(r: { from: string; to: string }) {
  try { chart?.timeScale().setVisibleRange({ from: r.from as any, to: r.to as any }) } catch { /* 区间越界忽略 */ }
  if (!navDragging) maybeLoadByNavigator(r)
}

/** 窗口左缘落在数据最前 30 根内(≈1.5%)→ 加载更早一批 */
function maybeLoadByNavigator(r?: { from: string }) {
  const nav = navigatorData.value
  if (nav.length < 2) return
  const from = r?.from ?? xToTimeByIndex(0)
  const idx = nav.findIndex(x => x.time >= from)
  if (idx >= 0 && idx < 30) loadMoreHistory()
}
function xToTimeByIndex(_i: number): string { return navigatorData.value[0]?.time ?? '' }
// 当前可视区间(时间) → 导航条窗口同步(主图缩放 → 导航条)。
// 用 getVisibleRange(时间区间)而非逻辑索引取整:floor/ceil 每轮丢宽度,
// 与拖拽迭代混合会越拖越窄;时间端点无损映射
function syncNavigator() {
  if (!chart || chartBarsByDateAsc.value.length === 0) return
  const tr = chart.timeScale().getVisibleRange()
  if (!tr) return
  const from = normTime(tr.from), to = normTime(tr.to)
  if (from && to && from !== to) rangeNavRef.value?.setRange(from, to)
}
// lw Time 归一为 'YYYY-MM-DD':字符串直取;UTC 秒转日期;BusinessDay 拼装
function normTime(t: any): string {
  if (t == null) return ''
  const s = String(t)
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10)
  if (/^\d+$/.test(s)) return dayjs.utc(Number(s) * 1000).format('YYYY-MM-DD')
  if (typeof t === 'object' && t.year) return `${t.year}-${String(t.month).padStart(2, '0')}-${String(t.day).padStart(2, '0')}`
  return ''
}
const chartChangePct = computed(() => {
  if (!latestChartBar.value || !prevChartBar.value) return 0
  const prev = Number(prevChartBar.value.close), cur = Number(latestChartBar.value.close)
  return prev ? ((cur - prev) / prev) * 100 : 0
})
const chartStats = computed(() => {
  if (chartBars.value.length === 0) return { high: '0.00', low: '0.00' }
  const highs = chartBars.value.map(b => Number(b.high) || 0)
  const lows = chartBars.value.map(b => Number(b.low) || Infinity)
  return {
    high: Math.max(...highs).toFixed(2),
    low: Math.min(...lows.filter(v => v > 0)).toFixed(2),
  }
})

function initChart() {
  if (!lwChartContainer.value) return
  if (chart) { chart.remove(); chart = null }
  chart = createChart(lwChartContainer.value, {
    width: lwChartContainer.value.clientWidth,
    height: 420,
    layout: { background: { type: ColorType.Solid, color: cssColor('--card') }, textColor: cssColor('--muted-foreground') },
    grid: { vertLines: { color: cssColor('--border') }, horzLines: { color: cssColor('--border') } },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: cssColor('--border'), width: 1, style: 3, labelBackgroundColor: cssColor('--primary') },
      horzLine: { color: cssColor('--border'), width: 1, style: 3, labelBackgroundColor: cssColor('--primary') },
    },
    rightPriceScale: { borderColor: cssColor('--border'), scaleMargins: { top: 0.1, bottom: 0.25 } },
    // 时间轴(图表底部):交易日粒度标尺;minBarSpacing 保证缩放到底仍有可读间距
    timeScale: {
      borderColor: cssColor('--border'),
      timeVisible: false, secondsVisible: false,   // 日频K线:日期粒度,不显时分秒
      fixRightEdge: true, fixLeftEdge: false,
      minBarSpacing: 2,
    },
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

  // 可视区间指示:缩放/平移实时更新(from~to 日期 + 可见根数)
  chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (!range) { visibleRangeText.value = ''; visibleBarsCount.value = 0; return }
    const total = chartBars.value.length
    const from = Math.max(0, Math.floor(range.from as number))
    const to = Math.min(total - 1, Math.ceil(range.to as number))
    const bars = chartBarsByDateAsc.value.slice(from, to + 1)
    visibleBarsCount.value = bars.length
    const f = bars[0], t = bars[bars.length - 1]
    visibleRangeText.value = (f && t)
      ? `${fmtDate(f.date)} ~ ${fmtDate(t.date)}`
      : ''
    syncNavigator()  // 主图缩放/平移 → 导航条窗口跟随
  })

  // 向左滚接近数据起点 → 提前拉取更早历史(比例阈值 + 绝对余量双触发)
  chart.timeScale().subscribeVisibleLogicalRangeChange(() => {
    if (isLoadingLocked || !hasMoreHistory.value) return
    const logicalRange = chart?.timeScale().getVisibleLogicalRange()
    if (!logicalRange) return
    if (navDragging) return   // 导航条拖拽中:挂起,松手后补
    const totalBars = chartBars.value.length
    const visibleFrom = Math.floor(logicalRange.from as number)
    if (totalBars > 0 && (visibleFrom < totalBars * LOAD_THRESHOLD || visibleFrom < LOAD_HEADROOM_BARS)) {
      loadMoreHistory()
    }
  })

  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => {
    if (chart && lwChartContainer.value) chart.applyOptions({ width: lwChartContainer.value.clientWidth })
  })
  resizeObserver.observe(lwChartContainer.value)
}

// 主题切换重绘:canvas 不认 CSS var,须重读 token 调 applyOptions(ADR-045)
function applyChartTheme() {
  if (!chart) return
  chart.applyOptions({
    layout: { background: { type: ColorType.Solid, color: cssColor('--card') }, textColor: cssColor('--muted-foreground') },
    grid: { vertLines: { color: cssColor('--border') }, horzLines: { color: cssColor('--border') } },
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

// 去重(按 time)+升序:lightweight-charts setData 要求时间严格升序,否则断言失败
const dedupAndSort = <T extends { time: any }>(arr: T[]): T[] =>
  [...new Map(arr.map(d => [d.time, d])).values()]
    .sort((a, b) => String(a.time).localeCompare(String(b.time)))

function convertToChartData(data: any[]) {
  const candles: CandlestickData[] = [], volumes: HistogramData[] = []
  for (const item of data) {
    const time = formatDay(item.date || item.timestamp) as any
    candles.push({ time, open: Number(item.open), high: Number(item.high), low: Number(item.low), close: Number(item.close) })
    volumes.push({ time, value: Number(item.volume) || 0 })
  }
  return { candles, volumes }
}

/** setData 全量重灌后恢复视图。
 *  用逻辑索引(浮点)而非时间区间恢复:时间区间的端点会被 lw snap 到 bar
 *  边界,每批 prepend 损耗 0~1 根,批次累积=可视K线逐次变少(2026-08-18
 *  实测);逻辑索引 + prependCount 位移是无损的。
 *  prependCount: 本次新前置的历史根数(批量加载传入;首拉为 0) */
function setChartData(preserveView = true, prependCount = 0) {
  if (!candlestickSeries || !volumeSeries || chartBars.value.length === 0) return
  const lr = preserveView ? (chart?.timeScale().getVisibleLogicalRange() ?? null) : null
  const { candles, volumes } = convertToChartData(chartBars.value)
  candlestickSeries.setData(dedupAndSort(candles).slice(-MAX_DATA_POINTS))
  volumeSeries.setData(dedupAndSort(volumes).slice(-MAX_DATA_POINTS))
  if (chart && lr) {
    try {
      chart.timeScale().setVisibleLogicalRange({
        from: (lr.from as number) + prependCount,
        to: (lr.to as number) + prependCount,
      })
    } catch { /* 区间越界(数据被截到 MAX)时放弃恢复,保持默认 */ }
  }
}

async function fetchBarsBatch(code: string, from: Dayjs, size: number, to?: Dayjs): Promise<any[]> {
  const res: any = await dataApi.getBars({
    code, page: 1, page_size: size,
    start_date: from.format('YYYY-MM-DD'),
    end_date: (to || dayjs()).format('YYYY-MM-DD'),
    // 升序(最早在前):earliestDate=data[0] 的语义依赖首元素=最早;API 默认 desc
    // (最新在前)时 earliest 恒=最新,滑动窗口永远停在最近一年,fill 拉去重后
    // 0 新增即误判"已到头"(2026-08-18 实测停在 202 根=DB 最近一年交易日数)
    order: 'asc',
  } as any)
  return res?.items ?? []
}

// 查询代际(2026-08-18):每次 loadChartBars 自增;历史加载后台循环(fill/lazy)
// 每步校验代际——旧查询的循环在新查询发起后自然死亡。此前无代际:切 code/
// 切类型回来时旧 fill 循环存活,继续向新数据 prepend 旧批次(chartBars 膨胀
// 出大量重复,DB 241 根页面 2130),且错乱的 earliestDate 令某轮拉 0 条 →
// hasMoreHistory 永久 false → 之后一切懒加载静默失效
let loadGeneration = 0

function dedupBars(arr: any[]): any[] {
  return [...new Map(arr.map((b: any) => [String(b.date), b])).values()]
}

// 连续无新增计数:并发双加载器(fill 循环+range 事件回调)会重复拉同一窗口,
// 后到者 added=0 不应立即判"到头"(历史真到头是 historical.length===0);
// 连续 2 次无新增才判死,容忍一次并发重复
let noNewCount = 0

async function loadMoreHistory(_preserveView = true, gen = loadGeneration) {
  if (gen !== loadGeneration) return                       // 旧代际:废弃
  if (!code.value || isLoadingLocked || !hasMoreHistory.value || !earliestDate.value) return
  isLoadingLocked = true
  isLoadingMore.value = true
  try {
    const newStart = earliestDate.value.subtract(BATCH_SIZE, 'day')
    const newEnd = earliestDate.value.subtract(1, 'day')
    const historical = await fetchBarsBatch(code.value, newStart, BATCH_SIZE, newEnd)
    if (gen !== loadGeneration) return                     // await 期间换代:丢弃
    if (historical.length === 0) { hasMoreHistory.value = false; return }
    const merged = dedupBars([...historical, ...chartBars.value])
    const added = merged.length - chartBars.value.length
    if (added <= 0) {
      noNewCount += 1
      if (noNewCount >= 2) hasMoreHistory.value = false    // 连续重复:窗口真到头
      return
    }
    noNewCount = 0
    chartBars.value = merged
    earliestDate.value = dayjs(String(merged[0].date))
    // 保视图:逻辑索引+prepend 根数位移恢复(见 setChartData 注释)
    setChartData(true, added)
  } catch { /* 历史加载失败不阻断,保留当前视图 */ }
  finally {
    isLoadingMore.value = false
    setTimeout(() => { isLoadingLocked = false }, 400)
  }
}

// bars 查询入口(code/日期/频率变化):重置并首拉
async function loadChartBars() {
  if (!code.value) return
  const gen = ++loadGeneration     // 换代:旧 fill/lazy 循环全部作废
  hasMoreHistory.value = true
  isLoadingLocked = false
  noNewCount = 0
  try {
    // 纯懒加载(2026-08-18 定稿):首屏只拉一年,不做后台预填充——其余历史
    // 由左拖/缩放触底时按批(300根)加载;曾用 FILL_TARGET 后台填充被否,
    // 用户要按需加载,首屏轻量
    const from = startDate.value ? dayjs(startDate.value) : dayjs().subtract(1, 'year')
    const to = endDate.value ? dayjs(endDate.value) : dayjs()
    const data = await fetchBarsBatch(code.value, from, BATCH_SIZE, to)
    if (gen !== loadGeneration) return
    chartBars.value = dedupBars(data)
    if (data.length > 0) earliestDate.value = dayjs(String(data[0].date))
    else hasMoreHistory.value = false
    await nextTick()
    if (!chart) initChart()
    setChartData(false)
    // 首屏可视=最近 3 个月(与导航窗口默认一致;不设则 lw 自动 fit 的宽度
    // 会经 syncNavigator 回写,覆盖导航窗口的 45 天初值)
    if (chart && data.length > 1) {
      const lastTime = String(data[data.length - 1].date).slice(0, 10)
      const from = dayjs(lastTime).subtract(90, 'day').format('YYYY-MM-DD')
      const startBar = data.find((b: any) => String(b.date).slice(0, 10) >= from)
      try {
        chart.timeScale().setVisibleRange({ from: (startBar ? String(startBar.date).slice(0, 10) : lastTime) as any, to: lastTime as any })
      } catch { chart.timeScale().scrollToRealTime() }
    } else if (chart) {
      chart.timeScale().scrollToRealTime()
    }
  } catch {
    if (gen === loadGeneration) chartBars.value = []
  }
}

onUnmounted(() => {
  resizeObserver?.disconnect()
  chart?.remove()
  chart = null
})

// ---- URL query 双向同步:外部导航(菜单/概览卡)→ 状态;查询 → replace 回写 ----
function syncFromQuery() {
  const q = route.query
  const t = String(q.type || 'stocks') as DataType
  type.value = (TYPE_OPTIONS as readonly { key: string }[]).some(o => o.key === t) ? t : 'stocks'
  code.value = String(q.code || '').toUpperCase()
  startDate.value = String(q.start || '')
  endDate.value = String(q.end || '')
  frequency.value = String(q.freq || 'day')
  page.value = Number(q.page) || 1
}

function writeQuery(resetPage = true) {
  if (resetPage) page.value = 1
  router.replace({
    query: {
      ...route.query,
      type: type.value,
      code: code.value || undefined,
      start: startDate.value || undefined,
      end: endDate.value || undefined,
      freq: type.value === 'bars' ? frequency.value : undefined,
      page: page.value > 1 ? String(page.value) : undefined,
    },
  })
}

// 路由变化(菜单直达/深链/分享)→ 拉数据
watch(() => route.query, () => {
  const hadCode = code.value
  syncFromQuery()
  // 仅当查询实质变化时重拉,避免 replace 回写自身触发循环
  if (canQuery.value && (hadCode !== code.value || page.value === 1)) runQuery()
}, { immediate: false })

function switchType(t: string) {
  type.value = t as DataType
  writeQuery()
  // 切到需 code 的类型但当前无选中(如从 stocks 直切 K线):自动选第一只
  if (t !== 'stocks' && !code.value) autoSelectFirstCode()
}

// 默认选中第一只(2026-08-18):免搜索直达——K线/Tick/复权都需 code,空态要求
// 用户先搜是多余一步;进页/切型即取股票列表首只填充并查询
async function autoSelectFirstCode() {
  try {
    const res: any = await dataApi.listStocks({ page: 1, page_size: 1 })
    const first = (res?.items ?? [])[0]
    if (!first?.code) return
    code.value = String(first.code).toUpperCase()
    writeQuery()
    runQuery()
  } catch { /* 股票列表不可得则维持空态,用户可手动搜索 */ }
}

function onPageChange(p: number) {
  page.value = p
  writeQuery(false)
  runQuery()
}

const searchStocks = async (query: string): Promise<SearchOption[]> => {
  if (!query.trim()) return []
  const res: any = await dataApi.listStocks({ query, page_size: 20 })
  return (res?.items ?? []).map((s: any) => ({
    value: s.code,
    label: `${s.code} ${s.name || ''}`,
    data: s,
  }))
}

const handleSelectStock = (opt: SearchOption) => {
  code.value = opt.value.toUpperCase()
  writeQuery()
  runQuery()
}

onMounted(() => {
  syncFromQuery()
  if (code.value || type.value === 'stocks') {
    if (canQuery.value) runQuery()
  } else {
    autoSelectFirstCode()  // 无 code 深链(如概览卡直达 bars):默认第一只
  }
})
</script>

<style scoped>
.browser-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* K线图卡 */
.chart-card { padding: 12px 14px; }
.chart-header {
  display: flex;
  gap: 18px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
  padding: 2px 4px 8px;
}
.chart-header .stat-item strong { color: hsl(var(--foreground)); }
.chart-container { width: 100%; height: 380px; }

/* 图表下方状态栏:可视区间 + 操作提示 */
.chart-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: 8px 4px 0;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  border-top: 1px solid hsl(var(--border));
  margin-top: 6px;
}
.footer-range strong {
  color: hsl(var(--foreground));
  font-family: monospace;
  margin: 0 6px 0 4px;
}
.footer-count { color: hsl(var(--primary)); }
.footer-hint { font-size: 11px; opacity: 0.85; }

.control-input { width: 150px; }
.control-select {
  padding: 5px 8px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  background: hsl(var(--card));
  color: hsl(var(--foreground));
  font-size: 13px;
}
/* 筛选条:内容区首行,筛选-结果就近关联 */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 10px 14px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
}
.filter-sep { color: hsl(var(--muted-foreground)); font-size: 12px; }

.btn-query {
  padding: 6px 16px;
  border: 1px solid hsl(var(--primary) / 0.4);
  border-radius: var(--radius-sm);
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 13px;
  cursor: pointer;
}
.btn-query:disabled { opacity: 0.5; cursor: not-allowed; }

.val-up { color: hsl(var(--success)); }
.val-down { color: hsl(var(--error)); }
.val-muted { color: hsl(var(--muted-foreground)); }
.tag-green {
  color: hsl(var(--success));
  background: hsl(var(--success) / 0.1);
  border: 1px solid hsl(var(--success) / 0.3);
}
.tag-gray {
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted-foreground) / 0.08);
  border: 1px solid hsl(var(--border));
}
</style>
