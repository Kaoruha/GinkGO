<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-orange">Tick</span>
        Tick 数据
      </div>
      <div class="header-controls">
        <select v-model="selectedCode" class="control-select">
          <option value="">选择股票</option>
          <option v-for="opt in stockOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
        </select>
        <input v-model="startDate" type="date" class="control-input" />
        <input v-model="endDate" type="date" class="control-input" />
        <button class="btn-primary" @click="loadData" :disabled="!selectedCode || loading">查询</button>
      </div>
    </div>

    <!-- 散点图 -->
    <div class="card" v-if="tickData.length > 0">
      <div class="card-header-simple">时间-价格散点图</div>
      <div ref="chartContainer" class="chart-wrapper"></div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid" v-if="tickData.length > 0">
      <div class="stat-card-small">
        <div class="stat-value-small">{{ formatNumber(stats.total) }}</div>
        <div class="stat-label-small">数据条数</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ stats.latestPrice }}</div>
        <div class="stat-label-small">最新价</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ formatVolume(stats.totalVolume) }}</div>
        <div class="stat-label-small">总成交量</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small" :class="stats.buyRatio >= 0.5 ? 'text-green' : 'text-red'">
          {{ (stats.buyRatio * 100).toFixed(1) }}%
        </div>
        <div class="stat-label-small">买入占比</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="card">
      <div class="card-header-simple">数据明细</div>
      <div class="table-wrapper">
        <table class="data-table" v-if="tickData.length > 0">
          <thead>
            <tr>
              <th>时间</th>
              <th>代码</th>
              <th>价格</th>
              <th>成交量</th>
              <th>方向</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="tick in paginatedData" :key="tick.uuid">
              <td>{{ formatTime(tick.timestamp) }}</td>
              <td>{{ tick.code }}</td>
              <td class="num">{{ tick.price?.toFixed(2) }}</td>
              <td class="num">{{ tick.volume?.toLocaleString() }}</td>
              <td>
                <span :class="directionClass(tick.direction)">{{ directionLabel(tick.direction) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-else-if="!loading" class="empty-state-small">请输入股票代码并点击查询</div>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="pagination.total > 0">
        <span class="pagination-info">
          共 {{ pagination.total }} 条，第 {{ pagination.current }} / {{ totalPages }} 页
        </span>
        <div class="pagination-controls">
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(1)">«</button>
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(pagination.current - 1)">‹</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(pagination.current + 1)">›</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(totalPages)">»</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay"><div class="spinner"></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { dataApi } from '@/api/modules/data'
import type { TickData } from '@/api/modules/data'
import dayjs from 'dayjs'

const route = useRoute()

const stockOptions = [
  { value: '000001.SZ', label: '000001.SZ 平安银行' },
  { value: '000002.SZ', label: '000002.SZ 万科A' },
  { value: '600519.SH', label: '600519.SH 贵州茅台' },
]

const selectedCode = ref((route.query.code as string) || '')
const startDate = ref(dayjs().subtract(7, 'day').format('YYYY-MM-DD'))
const endDate = ref(dayjs().format('YYYY-MM-DD'))
const loading = ref(false)
const tickData = ref<TickData[]>([])
const totalRecords = ref(0)

const pagination = ref({ current: 1, pageSize: 50, total: 0 })

const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize)))

const paginatedData = computed(() => {
  // 数据已从服务端分页，直接返回
  return tickData.value
})

const stats = computed(() => {
  if (tickData.value.length === 0) return { total: 0, latestPrice: '-', totalVolume: 0, buyRatio: 0 }
  const data = tickData.value
  const latest = data[data.length - 1]
  const totalVol = data.reduce((s, t) => s + (t.volume || 0), 0)
  const buyCount = data.filter(t => t.direction === 1).length
  return {
    total: pagination.value.total,
    latestPrice: latest?.price?.toFixed(2) || '-',
    totalVolume: totalVol,
    buyRatio: data.length > 0 ? buyCount / data.length : 0,
  }
})

const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

function formatNumber(n: number) {
  if (n >= 100000000) return (n / 100000000).toFixed(2) + ' 亿'
  if (n >= 10000) return (n / 10000).toFixed(1) + ' 万'
  return n.toLocaleString()
}

function formatVolume(v: number) {
  if (v >= 100000000) return (v / 100000000).toFixed(2) + ' 亿'
  if (v >= 10000) return (v / 10000).toFixed(1) + ' 万'
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
  if (d === 1) return 'dir-buy'
  if (d === -1) return 'dir-sell'
  return 'dir-neutral'
}

async function loadData() {
  if (!selectedCode.value) return
  loading.value = true
  try {
    const res: any = await dataApi.getTicks({
      code: selectedCode.value,
      start_date: startDate.value,
      end_date: endDate.value,
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    })
    tickData.value = res?.data || []
    pagination.value.total = res?.meta?.total || 0
    totalRecords.value = res?.meta?.total || 0
    nextTick(() => updateChart())
  } catch {
    tickData.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  pagination.value.current = p
  loadData()
}

function updateChart() {
  if (!chartContainer.value || tickData.value.length === 0) return
  if (!chart) {
    chart = echarts.init(chartContainer.value, 'dark')
    window.addEventListener('resize', handleResize)
  }

  // 按方向分组
  const buyData: [number, number, number][] = []
  const sellData: [number, number, number][] = []
  const neutralData: [number, number, number][] = []

  tickData.value.forEach(t => {
    const ts = new Date(t.timestamp).getTime()
    const point: [number, number, number] = [ts, t.price, t.volume || 1]
    if (t.direction === 1) buyData.push(point)
    else if (t.direction === -1) sellData.push(point)
    else neutralData.push(point)
  })

  const maxVol = Math.max(...tickData.value.map(t => t.volume || 1), 1)

  chart.setOption({
    backgroundColor: '#1a1a2e',
    grid: { left: 60, right: 30, top: 30, bottom: 40 },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const d = new Date(params.value[0])
        return `${d.toLocaleString()}<br/>价格: ${params.value[1]?.toFixed(2)}<br/>成交量: ${params.value[2]?.toLocaleString()}<br/>方向: ${params.seriesName}`
      },
    },
    legend: { data: ['买入', '卖出', '中性'], top: 4, textStyle: { color: '#8a8a9a' } },
    xAxis: {
      type: 'time',
      axisLabel: { color: '#8a8a9a', fontSize: 11 },
      splitLine: { lineStyle: { color: '#2a2a3e' } },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: { color: '#8a8a9a', fontSize: 11 },
      splitLine: { lineStyle: { color: '#2a2a3e' } },
    },
    series: [
      {
        name: '买入',
        type: 'scatter',
        data: buyData,
        symbolSize: (val: number[]) => Math.max(3, Math.min(20, (val[2] / maxVol) * 20)),
        itemStyle: { color: '#52c41a', opacity: 0.7 },
      },
      {
        name: '卖出',
        type: 'scatter',
        data: sellData,
        symbolSize: (val: number[]) => Math.max(3, Math.min(20, (val[2] / maxVol) * 20)),
        itemStyle: { color: '#f5222d', opacity: 0.7 },
      },
      {
        name: '中性',
        type: 'scatter',
        data: neutralData,
        symbolSize: (val: number[]) => Math.max(3, Math.min(20, (val[2] / maxVol) * 20)),
        itemStyle: { color: '#8a8a9a', opacity: 0.5 },
      },
    ],
  }, true)
}

function handleResize() {
  chart?.resize()
}

onMounted(() => {
  if (selectedCode.value) loadData()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.page-container { position: relative; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 20px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px; }
.header-controls { display: flex; gap: 10px; align-items: center; }
.control-input { padding: 6px 12px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 4px; color: #fff; font-size: 13px; }
.control-input:focus { outline: none; border-color: #1890ff; }
.control-select { padding: 7px 12px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 4px; color: #fff; font-size: 13px; cursor: pointer; min-width: 160px; }
.control-select:focus { outline: none; border-color: #1890ff; }
.control-input[type="date"] { width: 140px; }

.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-orange { background: rgba(250,173,20,0.15); color: #faad14; }

.btn-primary { display: inline-flex; align-items: center; padding: 7px 16px; background: #1890ff; border: none; border-radius: 4px; color: #fff; font-size: 13px; cursor: pointer; }
.btn-primary:hover { background: #40a9ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Chart */
.card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; margin-bottom: 16px; overflow: hidden; }
.card-header-simple { padding: 12px 16px; font-size: 14px; font-weight: 600; color: #fff; border-bottom: 1px solid #2a2a3e; }
.chart-wrapper { width: 100%; height: 400px; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card-small { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 16px; }
.stat-value-small { font-size: 20px; font-weight: 600; color: #fff; }
.stat-label-small { font-size: 12px; color: #8a8a9a; margin-top: 4px; }
.text-green { color: #52c41a !important; }
.text-red { color: #f5222d !important; }

/* Table */
.table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { padding: 10px 12px; text-align: left; color: #fff; background: #2a2a3e; font-weight: 600; white-space: nowrap; }
.data-table td { padding: 10px 12px; color: #fff; border-bottom: 1px solid #2a2a3e; }
.data-table tbody tr:hover { background: #22223a; }
.data-table .num { font-variant-numeric: tabular-nums; }

.dir-buy { color: #52c41a; font-weight: 500; }
.dir-sell { color: #f5222d; font-weight: 500; }
.dir-neutral { color: #8a8a9a; }

.empty-state-small { padding: 40px; text-align: center; color: #8a8a9a; }

/* Pagination */
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid #2a2a3e; }
.pagination-info { font-size: 13px; color: #8a8a9a; }
.pagination-controls { display: flex; gap: 4px; }
.pg-btn { min-width: 28px; height: 28px; padding: 0 6px; background: #2a2a3e; border: 1px solid #3a3a4e; border-radius: 4px; color: #fff; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.pg-btn:hover:not(:disabled) { background: #3a3a4e; border-color: #1890ff; }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid #2a2a3e; border-top-color: #1890ff; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .header-controls { flex-wrap: wrap; }
}
</style>
