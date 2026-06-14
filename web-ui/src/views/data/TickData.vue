<template>
  <!-- TickData.vue（数据管理页） -->
  <div class="page-container">
    <div class="page-header" style="flex-direction: row !important; align-items: center; gap: 12px; flex-wrap: wrap;">
      <div class="page-title" style="margin-bottom: 0;">
        <button class="back-btn" @click="$router.push('/data')">←</button>
        <span class="tag tag-orange">Tick</span>
        Tick 数据
        <span v-if="selectedCode" class="tag tag-blue">{{ selectedLabel || selectedCode }}</span>
      </div>
      <span style="flex: 1;"></span>
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
    </div>

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
      <div v-if="!loading && selectedCode && tickData.length === 0 && searched" class="empty-state">
        当前股票在所选日期范围内无 Tick 数据，请尝试其他股票
      </div>
      <div v-if="!loading && !selectedCode" class="empty-state">
        请搜索并选择一只股票
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import DataTable from '@/components/data/DataTable.vue'
import SearchSelect from '@/components/common/SearchSelect.vue'
import * as echarts from 'echarts'
import { dataApi } from '@/api/modules/data'
import type { TickData } from '@/api/modules/data'
import dayjs from 'dayjs'

const route = useRoute()

const loading = ref(false)
const searched = ref(false)
const selectedCode = ref('')
const selectedLabel = ref('')
const startDate = ref(dayjs().subtract(1, 'year').format('YYYY-MM-DD'))
const endDate = ref(dayjs().format('YYYY-MM-DD'))
const tickData = ref<TickData[]>([])

// 表格客户端分页（全量数据已加载，前端切页）
const tablePage = ref(1)
const tablePageSize = ref(50)

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
  const payload = res?.data !== undefined ? res.data : res
  const items = Array.isArray(payload) ? payload : (payload?.data ?? payload?.items ?? [])
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
  const payload = res?.data !== undefined ? res.data : res
  const items = Array.isArray(payload) ? payload : (payload?.data ?? payload?.items ?? [])
  const total = res?.meta?.total ?? res?.total ?? items.length ?? 0
  return { items, total }
}

/** 加载全量 tick（大批次供图表聚合 + 表格客户端分页） */
const CHART_PAGE_SIZE = 10000

async function loadData() {
  if (!selectedCode.value) return
  loading.value = true
  searched.value = true
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
  } catch {
    tickData.value = []
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
  chart = echarts.init(chartContainer.value, 'dark')
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
    return ratio >= 0.5 ? 'rgba(82,196,26,0.6)' : 'rgba(245,34,45,0.6)'
  })

  chart.setOption({
    backgroundColor: '#1a1a2e',
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
        const color = chg >= 0 ? '#52c41a' : '#f5222d'
        return `<div style="font-size:12px">
          <div style="margin-bottom:4px;color:#8a8a9a">${b.time}</div>
          <div>开 <strong>${b.open.toFixed(2)}</strong> 高 <strong>${b.high.toFixed(2)}</strong></div>
          <div>低 <strong>${b.low.toFixed(2)}</strong> 收 <strong>${b.close.toFixed(2)}</strong></div>
          <div style="color:${color}">涨跌 ${chg >= 0 ? '+' : ''}${chg.toFixed(2)} (${chgPct}%)</div>
          <div>量 ${formatVolume(b.volume)} | ${b.count} 笔</div>
          <div>买 ${b.buyCount} 卖 ${b.sellCount}</div>
        </div>`
      },
    },
    legend: { data: ['K线', '成交量'], top: 4, textStyle: { color: '#8a8a9a' } },
    grid: [
      { left: 60, right: 30, top: 40, height: '52%' },
      { left: 60, right: 30, top: '72%', height: '18%' },
    ],
    xAxis: [
      { type: 'category', data: times, gridIndex: 0, axisLabel: { color: '#8a8a9a', fontSize: 10 }, axisLine: { lineStyle: { color: '#3a3a4e' } }, splitLine: { show: false } },
      { type: 'category', data: times, gridIndex: 1, axisLabel: { show: false }, axisLine: { lineStyle: { color: '#3a3a4e' } }, splitLine: { show: false } },
    ],
    yAxis: [
      { type: 'value', scale: true, gridIndex: 0, axisLabel: { color: '#8a8a9a', fontSize: 10 }, splitLine: { lineStyle: { color: '#2a2a3e' } } },
      { type: 'value', gridIndex: 1, axisLabel: { color: '#8a8a9a', fontSize: 10 }, splitLine: { lineStyle: { color: '#2a2a3e' } } },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], top: '93%', height: 16, borderColor: '#3a3a4e', fillerColor: 'rgba(24,144,255,0.15)', handleStyle: { color: '#1890ff' }, textStyle: { color: '#8a8a9a' } },
    ],
    series: [
      {
        name: 'K线', type: 'candlestick', data: ohlc,
        xAxisIndex: 0, yAxisIndex: 0,
        itemStyle: {
          color: '#52c41a', color0: '#f5222d',
          borderColor: '#52c41a', borderColor0: '#f5222d',
        },
      },
      {
        name: '成交量', type: 'bar', data: volumes,
        xAxisIndex: 1, yAxisIndex: 1,
        itemStyle: {
          color: (params: any) => volColors[params.dataIndex] || 'rgba(138,138,154,0.4)',
        },
      },
    ],
  }, true)
}

// 桶大小变化时刷新图表（数据不变，只需重新聚合渲染）
watch(bucketSize, () => { nextTick(() => updateChart()) })

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
.page-container { padding: 0; background: transparent; }
.page-container :deep(.card) { overflow: visible; }

.page-header { margin-bottom: 24px; }

.page-title {
  font-size: 24px; font-weight: 600; color: #ffffff;
  display: flex; align-items: center; gap: 12px;
}

.back-btn {
  background: none; border: 1px solid #2a2a3e; color: #8a8a9a;
  font-size: 16px; padding: 4px 10px; border-radius: 4px; cursor: pointer; transition: all 0.2s;
}
.back-btn:hover { border-color: #1890ff; color: #1890ff; }

.control-input {
  padding: 7px 12px; background: #2a2a3e; border: 1px solid #3a3a4e;
  border-radius: 4px; color: #fff; font-size: 13px; width: 140px;
}
.control-input:focus { outline: none; border-color: #1890ff; }

.btn-query {
  display: inline-flex; align-items: center; padding: 7px 16px;
  background: #1890ff; border: none; border-radius: 4px; color: #fff;
  font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.btn-query:hover:not(:disabled) { background: #40a9ff; }
.btn-query:disabled { opacity: 0.5; cursor: not-allowed; }

.chart-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; flex-wrap: wrap; gap: 8px;
}

.card-title { font-size: 16px; font-weight: 600; color: #ffffff; margin: 0 0 16px 0; }

.stats-inline { display: flex; gap: 16px; font-size: 13px; color: #8a8a9a; }
.stats-inline strong { color: #ffffff; }
.stat-item { white-space: nowrap; }

.bucket-selector { display: flex; gap: 4px; }
.bucket-btn {
  padding: 4px 10px; background: #2a2a3e; border: 1px solid #3a3a4e;
  border-radius: 4px; color: #8a8a9a; font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.bucket-btn:hover { border-color: #1890ff; color: #1890ff; }
.bucket-btn.active { background: #1890ff; border-color: #1890ff; color: #fff; }

.chart-wrapper { position: relative; }
.chart-container { width: 100%; height: 420px; }

.empty-state {
  padding: 40px 16px; text-align: center; color: #6a6a7a;
  font-size: 13px; border-top: 1px solid #2a2a3e;
}

.text-up { color: #52c41a !important; }
.text-down { color: #f5222d !important; }
.text-neutral { color: #8a8a9a; }

.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-orange { background: rgba(250,173,20,0.15); color: #faad14; }
.tag-blue { background: rgba(24,144,255,0.15); color: #1890ff; }
</style>
