<template>
  <PageLayout>
    <template #title>
      <PageTitle
        title="Tick 数据"
      >
        <template #prefix><span class="tag tag-orange">Tick</span></template>
      </PageTitle>
    </template>
    <template #meta>
      <span v-if="selectedCode" class="tag tag-blue">{{ selectedLabel || selectedCode }}</span>
    </template>
    <template #actions>
      <input v-model="startDate" type="date" class="control-input" />
      <input v-model="endDate" type="date" class="control-input" />
      <button class="btn-query" :disabled="!selectedCode || loading" @click="loadData">
        {{ loading ? '查询中' : '查询' }}
      </button>
      <SearchSelect
        :search-fn="searchStocks"
        placeholder="搜索股票代码..."
        style="width: 200px;"
        @select="handleSelectStock"
      />
    </template>

    <!-- K线图 + 成交量 -->
    <div class="card" v-if="tickData.length > 0">
      <div class="chart-header">
        <div class="stats-inline">
          <span class="stat-item">最新 <strong>{{ stats.latestPrice }}</strong></span>
          <span class="stat-item">总量 {{ formatVolume(stats.totalVolume) }}</span>
          <span class="stat-item" :class="stats.buyRatio >= 0.5 ? 'text-up' : 'text-down'">
            买入 {{ (stats.buyRatio * 100).toFixed(1) }}%
          </span>
          <span class="stat-item">{{ stats.totalTicks }} 条</span>
          <span class="stat-item" v-if="ohlcBuckets.length > 0">
            聚合为 {{ ohlcBuckets.length }} 根K线
          </span>
        </div>
        <div class="bucket-selector">
          <button
            v-for="b in bucketOptions" :key="b.value"
            class="bucket-btn" :class="{ active: bucketSize === b.value }"
            @click="bucketSize = b.value"
          >{{ b.label }}</button>
        </div>
      </div>
      <div class="chart-wrapper">
        <div ref="chartContainer" class="chart-container"></div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="card">
      <h3 class="card-title">数据明细</h3>
      <DataTable
        :columns="tickColumns"
        :data-source="tickData"
        :loading="loading"
        :page="tablePage"
        :page-size="tablePageSize"
        :max-height="340"
        row-key="uuid"
        :context-menu="rowMenu"
        @update:page="tablePage = $event"
        @update:page-size="tablePageSize = $event"
      >
        <template #colTime="{ record }">{{ formatTime(record.timestamp) }}</template>
        <template #colPrice="{ record }">{{ record.price?.toFixed(2) }}</template>
        <template #colVolume="{ record }">{{ formatVolume(record.volume) }}</template>
        <template #colDirection="{ record }">
          <span :class="directionClass(record.direction)">{{ directionLabel(record.direction) }}</span>
        </template>
      </DataTable>
      <!-- 查询失败:区别于"无数据",提供重试 -->
      <div v-if="!loading && loadError" class="empty-state">
        <p class="error-text">{{ loadError }}</p>
        <button class="btn-retry" @click="loadData">重试</button>
      </div>
      <div v-else-if="!loading && selectedCode && tickData.length === 0 && searched" class="empty-state">
        当前股票在所选日期范围内无 Tick 数据，请尝试其他股票
      </div>
      <div v-if="!loading && !selectedCode" class="empty-state">
        请搜索并选择一只股票
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import PageTitle from '@/components/common/PageTitle.vue'
import { useRoute } from 'vue-router'
import DataTable from '@/components/data/DataTable.vue'
import SearchSelect from '@/components/common/SearchSelect.vue'
import * as echarts from 'echarts'
import { useChartTheme, cssColor, upColor, downColor } from '@/composables/useChartTheme'
import { dataApi } from '@/api/modules/data'
import type { TickData } from '@/api/modules/data'
import dayjs from 'dayjs'
import { message as toast } from '@/utils/toast'
import type { MenuItem } from '@/composables/useContextMenu'

const route = useRoute()
const { theme } = useChartTheme()

const loading = ref(false)
const searched = ref(false)
// 查询失败(后端 5xx/网络断):须与"无 Tick 数据"空态区分,否则误导用户换股票重查
const loadError = ref('')
const selectedCode = ref('')
const selectedLabel = ref('')
const startDate = ref(dayjs().subtract(1, 'year').format('YYYY-MM-DD'))
const endDate = ref(dayjs().format('YYYY-MM-DD'))
const tickData = ref<TickData[]>([])

// 表格客户端分页（全量数据已加载，前端切页）
const tablePage = ref(1)
const tablePageSize = ref(50)

/** 行右键菜单:复制行情值 */
const rowMenu = (record: TickData): MenuItem[] => [
  { label: '复制时间', action: () => { navigator.clipboard.writeText(formatTime(record.timestamp)); toast.success('已复制') } },
  { label: '复制价格', action: () => { navigator.clipboard.writeText(String(record.price ?? '')); toast.success('已复制') } },
  { label: '复制代码', action: () => { navigator.clipboard.writeText(record.code || selectedCode.value); toast.success('已复制') } },
]

// 图表：时间桶聚合
const bucketSize = ref(5) // 分钟
const bucketOptions = [
  { label: '1分', value: 1 },
  { label: '5分', value: 5 },
  { label: '15分', value: 15 },
  { label: '1时', value: 60 },
  { label: '1日', value: 1440 },
]

interface OHLCBucket {
  time: string
  ts: number
  open: number
  close: number
  high: number
  low: number
  volume: number
  buyCount: number
  sellCount: number
  count: number
}

/** 将逐笔 tick 聚合为 OHLC 桶 */
function aggregateTicks(data: TickData[], bucketMinutes: number): OHLCBucket[] {
  if (data.length === 0) return []
  const sorted = [...data].sort((a, b) =>
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )
  const bucketMs = bucketMinutes * 60 * 1000
  const map = new Map<number, { prices: number[]; vol: number; buy: number; sell: number }>()

  for (const tick of sorted) {
    const ts = new Date(tick.timestamp).getTime()
    const key = Math.floor(ts / bucketMs) * bucketMs
    if (!map.has(key)) map.set(key, { prices: [], vol: 0, buy: 0, sell: 0 })
    const b = map.get(key)!
    b.prices.push(tick.price)
    b.vol += tick.volume || 0
    if (tick.direction === 1) b.buy++
    else if (tick.direction === -1) b.sell++
  }

  const result: OHLCBucket[] = []
  for (const [ts, b] of map) {
    result.push({
      time: new Date(ts).toISOString().replace('T', ' ').slice(0, 16),
      ts,
      open: b.prices[0],
      close: b.prices[b.prices.length - 1],
      high: Math.max(...b.prices),
      low: Math.min(...b.prices),
      volume: b.vol,
      buyCount: b.buy,
      sellCount: b.sell,
      count: b.prices.length,
    })
  }
  return result.sort((a, b) => a.ts - b.ts)
}

const ohlcBuckets = computed(() => aggregateTicks(tickData.value, bucketSize.value))

const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

const tickColumns = [
  { title: '时间', dataIndex: 'timestamp', slotName: 'colTime' },
  { title: '代码', dataIndex: 'code' },
  { title: '价格', dataIndex: 'price', slotName: 'colPrice' },
  { title: '成交量', dataIndex: 'volume', slotName: 'colVolume' },
  { title: '方向', dataIndex: 'direction', slotName: 'colDirection' },
]

const searchStocks = async (query: string) => {
  const res: any = await dataApi.listStocks({ query, page_size: 50 })
  const items = res?.items ?? []
  return items.map((s: any) => ({
    value: s.code,
    label: `${s.code} ${s.name || ''}`,
  }))
}

const stats = computed(() => {
  if (tickData.value.length === 0) return { totalTicks: 0, latestPrice: '-', totalVolume: 0, buyRatio: 0 }
  const data = tickData.value
  const latest = data[data.length - 1]
  const totalVol = data.reduce((s, t) => s + (t.volume || 0), 0)
  const buyCount = data.filter(t => t.direction === 1).length
  return {
    totalTicks: data.length,
    latestPrice: latest?.price?.toFixed(2) || '-',
    totalVolume: totalVol,
    buyRatio: data.length > 0 ? buyCount / data.length : 0,
  }
})

function formatVolume(v: number) {
  if (!v) return '-'
  if (v >= 100000000) return (v / 100000000).toFixed(2) + '亿'
  if (v >= 10000) return (v / 10000).toFixed(2) + '万'
  return v.toLocaleString()
}

function formatTime(t: string) {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

function directionLabel(d: number) {
  if (d === 1) return '买入'
  if (d === -1) return '卖出'
  return '中性'
}

function directionClass(d: number) {
  if (d === 1) return 'text-up'
  if (d === -1) return 'text-down'
  return 'text-neutral'
}

function extractItems(res: any): { items: any[]; total: number } {
  const items = res?.items ?? []
  const total = res?.total ?? items.length ?? 0
  return { items, total }
}

/** 加载 tick 供图表聚合 + 表格客户端分页。
 *  后端 page_size 上限 le=500 (core.pagination.DEFAULT_MAX_PAGE_SIZE),超出 422。
 *  取上限拉满;若业务需更多历史,改后端上限或前端循环分页聚合。 */
const CHART_PAGE_SIZE = 500

async function loadData() {
  if (!selectedCode.value) return
  loading.value = true
  searched.value = true
  loadError.value = ''
  tablePage.value = 1
  try {
    const res: any = await dataApi.getTicks({
      code: selectedCode.value,
      start_date: startDate.value,
      end_date: endDate.value,
      page: 1,
      page_size: CHART_PAGE_SIZE,
    })
    const { items } = extractItems(res)
    tickData.value = items
    nextTick(() => updateChart())
  } catch (e: any) {
    tickData.value = []
    const st = e?.response?.status
    loadError.value = st ? `Tick 数据加载失败（HTTP ${st}）` : 'Tick 数据加载失败，请检查网络后重试'
  } finally {
    loading.value = false
  }
}

function handleSelectStock(opt: { value: string; label: string }) {
  selectedCode.value = opt.value
  selectedLabel.value = opt.label
  loadData()
}

async function autoSelectStock() {
  const opts = await searchStocks('')
  if (opts.length === 0) return

  const maxTries = Math.min(opts.length, 10)
  for (let i = 0; i < maxTries; i++) {
    selectedCode.value = opts[i].value
    selectedLabel.value = opts[i].label
    searched.value = true
    loading.value = true
    try {
      const res: any = await dataApi.getTicks({
        code: opts[i].value,
        start_date: startDate.value,
        end_date: endDate.value,
        page: 1,
        page_size: CHART_PAGE_SIZE,
      })
      const { items } = extractItems(res)
      tickData.value = items
      if (items.length > 0) {
        nextTick(() => updateChart())
        return
      }
    } catch { /* continue */ }
    finally { loading.value = false }
  }
}

// ---- 图表 ----

function initChart() {
  if (!chartContainer.value) return
  if (chart) { chart.dispose(); chart = null }
  chart = echarts.init(chartContainer.value)
  resizeObserver?.disconnect()
  resizeObserver = new ResizeObserver(() => { chart?.resize() })
  resizeObserver.observe(chartContainer.value)
}

function updateChart() {
  if (!chartContainer.value || tickData.value.length === 0) return
  if (!chart) initChart()

  const buckets = ohlcBuckets.value
  if (buckets.length === 0) return

  const times = buckets.map(b => b.time)
  // ECharts candlestick: [open, close, low, high]
  const ohlc = buckets.map(b => [+b.open.toFixed(2), +b.close.toFixed(2), +b.low.toFixed(2), +b.high.toFixed(2)])
  const volumes = buckets.map(b => b.volume)
  const volColors = buckets.map(b => {
    const ratio = b.buyCount / (b.buyCount + b.sellCount || 1)
    return ratio >= 0.5 ? upColor(0.6) : downColor(0.6)
  })

  chart!.setOption({
    backgroundColor: cssColor('--card'),
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any) => {
        const idx = params[0]?.dataIndex
        if (idx == null || !buckets[idx]) return ''
        const b = buckets[idx]
        const chg = b.close - b.open
        const chgPct = b.open ? ((chg / b.open) * 100).toFixed(2) : '0.00'
        const color = chg >= 0 ? upColor() : downColor()
        return `<div style="font-size:12px">
          <div style="margin-bottom:4px;color:${cssColor('--muted-foreground')}">${b.time}</div>
          <div>开 <strong>${b.open.toFixed(2)}</strong> 高 <strong>${b.high.toFixed(2)}</strong></div>
          <div>低 <strong>${b.low.toFixed(2)}</strong> 收 <strong>${b.close.toFixed(2)}</strong></div>
          <div style="color:${color}">涨跌 ${chg >= 0 ? '+' : ''}${chg.toFixed(2)} (${chgPct}%)</div>
          <div>量 ${formatVolume(b.volume)} | ${b.count} 笔</div>
          <div>买 ${b.buyCount} 卖 ${b.sellCount}</div>
        </div>`
      },
    },
    legend: { data: ['K线', '成交量'], top: 4, textStyle: { color: cssColor('--muted-foreground') } },
    grid: [
      { left: 60, right: 30, top: 40, height: '52%' },
      { left: 60, right: 30, top: '72%', height: '18%' },
    ],
    xAxis: [
      { type: 'category', data: times, gridIndex: 0, axisLabel: { color: cssColor('--muted-foreground'), fontSize: 10 }, axisLine: { lineStyle: { color: cssColor('--border') } }, splitLine: { show: false } },
      { type: 'category', data: times, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: cssColor('--border') } }, splitLine: { show: false } },
    ],
    yAxis: [
      { type: 'value', scale: true, gridIndex: 0, axisLabel: { color: cssColor('--muted-foreground'), fontSize: 10 }, splitLine: { lineStyle: { color: cssColor('--border') } } },
      { type: 'value', gridIndex: 1, axisLabel: { color: cssColor('--muted-foreground'), fontSize: 10 }, splitLine: { lineStyle: { color: cssColor('--border') } } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], top: '93%', height: 16, borderColor: cssColor('--border'), fillerColor: cssColor('--primary', 0.15), handleStyle: { color: cssColor('--primary') }, textStyle: { color: cssColor('--muted-foreground') } },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: ohlc,
        xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: {
          color: upColor(), color0: downColor(),
          borderColor: upColor(), borderColor0: downColor(),
        },
      },
      {
        name: '成交量', type: 'bar', data: volumes,
        xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: {
          color: (params: any) => volColors[params.dataIndex] || cssColor('--muted-foreground', 0.4),
        },
      },
    ],
  }, true)
}

// 桶大小变化时刷新图表（数据不变，只需重新聚合渲染）
watch(bucketSize, () => { nextTick(() => updateChart()) })

// 主题切换重绘:setOption 用 notMerge 全量替换,token 重读即生效
watch(theme, () => { nextTick(() => updateChart()) })

onMounted(async () => {
  const code = route.query.code as string
  if (code) {
    selectedCode.value = code
    loadData()
  } else {
    try { await autoSelectStock() } catch { /* ignore */ }
  }
})

onUnmounted(() => {
  resizeObserver?.disconnect()
  if (chart) { chart.dispose(); chart = null }
})
</script>

<style scoped>
:deep(.card) { overflow: visible; }

.control-input {
  padding: 7px 12px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 13px; width: 140px;
}
.control-input:focus { outline: none; border-color: hsl(var(--primary)); }

.btn-query {
  display: inline-flex; align-items: center; padding: 7px 16px;
  background: hsl(var(--primary)); border: none; border-radius: var(--radius-sm); color: hsl(var(--primary-foreground));
  font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.btn-query:hover:not(:disabled) { background: hsl(var(--primary)); }
.btn-query:disabled { opacity: 0.5; cursor: not-allowed; }

.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; flex-wrap: wrap; gap: 8px;
}

.card-title { font-size: 16px; font-weight: 600; color: hsl(var(--foreground)); margin: 0 0 16px 0; }

.stats-inline { display: flex; gap: 16px; font-size: 13px; color: hsl(var(--muted-foreground)); }
.stats-inline strong { color: hsl(var(--foreground)); }
.stat-item { white-space: nowrap; }

.bucket-selector { display: flex; gap: 4px; }
.bucket-btn {
  padding: 4px 10px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm); color: hsl(var(--muted-foreground)); font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.bucket-btn:hover { border-color: hsl(var(--primary)); color: hsl(var(--primary)); }
.bucket-btn.active { background: hsl(var(--primary)); border-color: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }

.chart-wrapper { position: relative; }
.chart-container { width: 100%; height: 420px; }

.empty-state {
  padding: 40px 16px; text-align: center; color: hsl(var(--muted-foreground));
  font-size: 13px; border-top: 1px solid hsl(var(--border));
}

.empty-state .error-text { color: hsl(var(--error)); margin: 0 0 12px; }
.btn-retry {
  padding: 6px 16px; background: transparent; border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm); color: hsl(var(--foreground));
  font-size: 13px; cursor: pointer;
}
.btn-retry:hover { border-color: hsl(var(--primary)); color: hsl(var(--primary)); }

.text-up { color: hsl(var(--success)) !important; }
.text-down { color: hsl(var(--error)) !important; }
.text-neutral { color: hsl(var(--muted-foreground)); }

.tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
</style>
