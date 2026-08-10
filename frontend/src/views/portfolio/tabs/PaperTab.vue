<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { portfolioApi } from '@/api/modules/portfolio'
import StatCard from '@/components/common/StatCard.vue'
import { RefreshCw, Settings } from 'lucide-vue-next'
import * as echarts from 'echarts'

const route = useRoute()
const portfolioId = route.params.id as string

// ── 指标定义 ──────────────────────────────
interface MetricDef {
  key: string
  label: string
  type: 'number' | 'percent' | 'money' | 'decimal'
  decimals?: number
}

const ALL_METRICS: MetricDef[] = [
  { key: 'net_value', label: '净值', type: 'decimal', decimals: 4 },
  { key: 'annual_return', label: '年化收益', type: 'percent', decimals: 2 },
  { key: 'max_drawdown', label: '最大回撤', type: 'percent', decimals: 2 },
  { key: 'sharpe_ratio', label: '夏普比率', type: 'decimal', decimals: 2 },
  { key: 'sortino_ratio', label: '索提诺', type: 'decimal', decimals: 2 },
  { key: 'calmar_ratio', label: '卡玛比率', type: 'decimal', decimals: 2 },
  { key: 'win_rate', label: '胜率', type: 'percent', decimals: 2 },
  { key: 'signal_count', label: '信号数', type: 'number' },
  { key: 'total_pnl', label: '总盈亏', type: 'money', decimals: 2 },
  { key: 'total_trades', label: '交易次数', type: 'number' },
  { key: 'profit_factor', label: '盈亏比', type: 'decimal', decimals: 2 },
  { key: 'volatility', label: '波动率', type: 'percent', decimals: 2 },
]

const DEFAULT_METRICS = ['net_value', 'annual_return', 'max_drawdown', 'sharpe_ratio']
const MAX_METRICS = 8
const STORAGE_KEY = `paper-metrics-${portfolioId}`

// ── 指标配置（localStorage） ──────────────
const selectedKeys = ref<string[]>([...DEFAULT_METRICS])
const showConfig = ref(false)

const loadConfig = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      if (Array.isArray(parsed) && parsed.length > 0) {
        selectedKeys.value = parsed
          .filter((k: string) => ALL_METRICS.some(m => m.key === k))
          .slice(0, MAX_METRICS)
        return
      }
    }
  } catch { /* ignore */ }
  selectedKeys.value = [...DEFAULT_METRICS]
}

const saveConfig = () => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(selectedKeys.value))
}

const toggleMetric = (key: string) => {
  const idx = selectedKeys.value.indexOf(key)
  if (idx >= 0) {
    selectedKeys.value.splice(idx, 1)
  } else if (selectedKeys.value.length < MAX_METRICS) {
    selectedKeys.value.push(key)
  }
  saveConfig()
}

const visibleMetrics = computed(() =>
  selectedKeys.value
    .map(k => ALL_METRICS.find(m => m.key === k)!)
    .filter(Boolean)
)

// ── 数据加载 ──────────────────────────────
const loading = ref(false)
const metrics = ref<Record<string, number | null>>({})
const netValueSeries = ref<{ time: string; value: number }[]>([])
const events = ref<any[]>([])
const eventsTotal = ref(0)

const loadData = async () => {
  loading.value = true
  try {
    const [analyticsRes, eventsRes] = await Promise.all([
      portfolioApi.getAnalytics(portfolioId).catch(() => null),
      portfolioApi.listEvents(portfolioId, { limit: 50 }).catch(() => null),
    ])
    if (analyticsRes) {
      const a = analyticsRes as any
      metrics.value = a.metrics || {}
      netValueSeries.value = a.net_value_series || []
    }
    if (eventsRes) {
      const e = eventsRes as any
      events.value = e.data || []
      eventsTotal.value = e.total || 0
    }
  } catch (e) {
    console.error('加载监控数据失败:', e)
  } finally {
    loading.value = false
  }
}

// ── ECharts 净值曲线 ──────────────────────
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let resizeObs: ResizeObserver | null = null

const initChart = () => {
  if (!chartRef.value) return
  if (chart) { chart.dispose(); chart = null }
  chart = echarts.init(chartRef.value, 'dark')
  resizeObs?.disconnect()
  resizeObs = new ResizeObserver(() => chart?.resize())
  resizeObs.observe(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chart) return
  const data = netValueSeries.value
  if (!data.length) {
    chart.setOption({
      backgroundColor: '#1a1a2e',
      title: { text: '暂无净值数据', left: 'center', top: 'center', textStyle: { color: '#8a8a9a', fontSize: 14 } },
    })
    return
  }
  chart.setOption({
    backgroundColor: '#1a1a2e',
    animation: true,
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26,26,46,0.95)',
      borderColor: '#2a2a3e',
      textStyle: { color: '#ccc', fontSize: 12 },
    },
    grid: { left: 60, right: 16, top: 16, bottom: 28 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.time),
      axisLine: { lineStyle: { color: '#2a2a3e' } },
      axisLabel: { color: '#8a8a9a', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#2a2a3e', type: 'dashed' } },
      axisLabel: { color: '#8a8a9a', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: data.map(d => d.value),
      smooth: true,
      showSymbol: false,
      lineStyle: { color: '#3b82f6', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59,130,246,0.25)' },
          { offset: 1, color: 'rgba(59,130,246,0.02)' },
        ]),
      },
    }],
  })
}

watch(netValueSeries, () => nextTick(updateChart))

// ── 事件类型样式 ──────────────────────────
const EVENT_STYLES: Record<string, { icon: string; color: string; label: string }> = {
  SIGNALGENERATION: { icon: '📡', color: '#3b82f6', label: '信号' },
  ORDERSUBMITTED: { icon: '📋', color: '#eab308', label: '下单' },
  ORDERFILLED: { icon: '✅', color: '#10b981', label: '成交' },
  ORDERPARTIALLYFILLED: { icon: '✅', color: '#10b981', label: '部分成交' },
  ORDERREJECTED: { icon: '❌', color: '#ef4444', label: '拒绝' },
  ORDERCANCELACK: { icon: '⏹', color: '#6b7280', label: '取消' },
  ORDEREXPIRED: { icon: '⏰', color: '#6b7280', label: '过期' },
  RISKBREACH: { icon: '⚠️', color: '#f97316', label: '风控' },
}

const getEventStyle = (type: string) =>
  EVENT_STYLES[type] || { icon: '📌', color: '#8a8a9a', label: type }

const formatEventDesc = (e: any): string => {
  const parts: string[] = []
  if (e.symbol) parts.push(e.symbol)
  if (e.direction) {
    const d = e.direction
    parts.push(d === 'LONG' || d === 'BUY' ? '买' : d === 'SHORT' || d === 'SELL' ? '卖' : d)
  }
  if (e.signal_reason) parts.push(e.signal_reason)
  if (e.transaction_price) parts.push(`@${e.transaction_price}`)
  if (e.transaction_volume) parts.push(`×${e.transaction_volume}`)
  if (e.reject_reason) parts.push(e.reject_reason)
  if (e.risk_reason) parts.push(e.risk_reason)
  if (e.message && parts.length === 0) return (e.message as string).slice(0, 80)
  return parts.join(' ') || '-'
}

const formatTime = (ts: string | null): string => {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    if (isNaN(d.getTime())) return ts.slice(0, 19)
    const mm = String(d.getMonth() + 1).padStart(2, '0')
    const dd = String(d.getDate()).padStart(2, '0')
    const hh = String(d.getHours()).padStart(2, '0')
    const mi = String(d.getMinutes()).padStart(2, '0')
    const ss = String(d.getSeconds()).padStart(2, '0')
    return `${mm}-${dd} ${hh}:${mi}:${ss}`
  } catch {
    return ts.slice(0, 16)
  }
}

// ── 点击外部关闭配置面板 ──────────────────
const configWrapperRef = ref<HTMLDivElement>()
const onDocClick = (ev: MouseEvent) => {
  if (showConfig.value && configWrapperRef.value && !configWrapperRef.value.contains(ev.target as Node)) {
    showConfig.value = false
  }
}

// ── 生命周期 ──────────────────────────────
onMounted(() => {
  loadConfig()
  loadData()
  nextTick(initChart)
  document.addEventListener('click', onDocClick)
})

onUnmounted(() => {
  chart?.dispose()
  chart = null
  resizeObs?.disconnect()
  resizeObs = null
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <div class="paper-tab">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <RefreshCw class="w-5 h-5 animate-spin" />
      <span>加载中...</span>
    </div>

    <template v-else>
      <!-- ═══ 指标卡区域 ═══ -->
      <div class="section">
        <div class="section-header">
          <h3>绩效指标</h3>
          <div class="header-actions">
            <button class="btn-ghost" @click="loadData"><RefreshCw class="w-3.5 h-3.5" /></button>
            <div ref="configWrapperRef" class="config-wrapper">
              <button class="btn-ghost" @click.stop="showConfig = !showConfig">
                <Settings class="w-3.5 h-3.5" />
              </button>
              <Transition name="dropdown">
                <div v-if="showConfig" class="config-dropdown" @click.stop>
                  <div class="config-title">选择指标 ({{ selectedKeys.length }}/{{ MAX_METRICS }})</div>
                  <label v-for="m in ALL_METRICS" :key="m.key" class="config-item">
                    <input
                      type="checkbox"
                      :checked="selectedKeys.includes(m.key)"
                      :disabled="!selectedKeys.includes(m.key) && selectedKeys.length >= MAX_METRICS"
                      @change="toggleMetric(m.key)"
                    />
                    <span>{{ m.label }}</span>
                  </label>
                </div>
              </Transition>
            </div>
          </div>
        </div>
        <div class="metrics-grid">
          <StatCard
            v-for="m in visibleMetrics"
            :key="m.key"
            :title="m.label"
            :value="metrics[m.key]"
            :type="m.type"
            :decimals="m.decimals || 2"
            color="auto"
          />
        </div>
      </div>

      <!-- ═══ 净值曲线 ═══ -->
      <div class="section">
        <div class="section-header">
          <h3>净值曲线</h3>
        </div>
        <div ref="chartRef" class="chart-container"></div>
      </div>

      <!-- ═══ 事件时间线 ═══ -->
      <div class="section">
        <div class="section-header">
          <h3>事件时间线</h3>
          <span v-if="eventsTotal > 0" class="events-count">共 {{ eventsTotal }} 条</span>
        </div>
        <div v-if="events.length === 0" class="empty-hint">暂无事件</div>
        <div v-else class="event-list">
          <div v-for="(e, i) in events" :key="i" class="event-item">
            <span class="event-icon">{{ getEventStyle(e.event_type).icon }}</span>
            <span
              class="event-badge"
              :style="{
                background: getEventStyle(e.event_type).color + '18',
                color: getEventStyle(e.event_type).color,
              }"
            >
              {{ getEventStyle(e.event_type).label }}
            </span>
            <span class="event-time">{{ formatTime(e.timestamp) }}</span>
            <span class="event-desc">{{ formatEventDesc(e) }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.paper-tab {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 加载 */
.loading-state {
  display: flex; align-items: center; gap: 8px;
  padding: 32px 0; color: rgba(255,255,255,0.5);
}

/* 通用 section */
.section {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  padding: 14px 16px;
}
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}
.section-header h3 {
  margin: 0; font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.85);
}
.header-actions { display: flex; gap: 4px; }

/* 按钮 */
.btn-ghost {
  background: none; border: none; color: rgba(255,255,255,0.4);
  cursor: pointer; padding: 4px; display: flex; align-items: center;
}
.btn-ghost:hover { color: rgba(255,255,255,0.7); }

/* 指标卡网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

/* 配置下拉 */
.config-wrapper { position: relative; }
.config-dropdown {
  position: absolute; right: 0; top: 100%; z-index: 50;
  background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 8px;
  padding: 10px 12px; min-width: 180px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.config-title {
  font-size: 12px; color: #8a8a9a; margin-bottom: 8px;
  padding-bottom: 6px; border-bottom: 1px solid #2a2a3e;
}
.config-item {
  display: flex; align-items: center; gap: 8px;
  padding: 4px 0; font-size: 13px; color: rgba(255,255,255,0.8);
  cursor: pointer;
}
.config-item:hover { color: #fff; }
.config-item input[type="checkbox"] {
  accent-color: #3b82f6; width: 14px; height: 14px; cursor: pointer;
}
.config-item input:disabled { opacity: 0.35; }

/* 下拉动画 */
.dropdown-enter-active, .dropdown-leave-active { transition: all 0.15s ease; }
.dropdown-enter-from, .dropdown-leave-to {
  opacity: 0; transform: translateY(-4px);
}

/* 图表 */
.chart-container {
  width: 100%; height: 220px;
}

/* 事件时间线 */
.events-count {
  font-size: 12px; color: #8a8a9a;
}
.empty-hint {
  color: rgba(255,255,255,0.35); font-size: 13px;
  padding: 20px 0; text-align: center;
}
.event-list {
  display: flex; flex-direction: column; gap: 0;
  max-height: 400px; overflow-y: auto;
}
.event-list::-webkit-scrollbar { width: 4px; }
.event-list::-webkit-scrollbar-thumb { background: #2a2a3e; border-radius: 2px; }

.event-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 4px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  font-size: 13px;
}
.event-item:last-child { border-bottom: none; }
.event-icon { font-size: 14px; flex-shrink: 0; width: 20px; text-align: center; }
.event-badge {
  flex-shrink: 0; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600; white-space: nowrap;
}
.event-time {
  flex-shrink: 0; font-size: 12px; color: #8a8a9a;
  font-family: monospace; min-width: 110px;
}
.event-desc {
  color: rgba(255,255,255,0.8);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
