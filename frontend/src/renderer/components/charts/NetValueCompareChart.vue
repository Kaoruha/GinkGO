<template>
  <div class="compare-chart-wrap">
    <div v-if="series.length > 0" class="compare-legend">
      <span v-for="s in legend" :key="s.name" class="legend-item" :title="s.name">
        <span class="legend-dot" :style="{ background: s.color }"></span>
        <span class="legend-name">{{ s.name }}</span>
        <span class="legend-val">{{ s.latest }}</span>
      </span>
    </div>
    <div ref="chartContainer" class="tv-chart-container"></div>
  </div>
</template>

<script setup lang="ts">
/**
 * 多回测净值叠加对比图（组合概览用）。
 * NetValueChart 是单策略+基准双线；同组合多回测横向对比需要任意条线 +
 * 图例，故独立组件。色板取主题 token，5 条封顶（最新优先，调用方裁剪）。
 */
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, IChartApi, ISeriesApi, LineData, ColorType } from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

export interface CompareSeries {
  name: string
  data: LineData[]
}

interface Props {
  series?: CompareSeries[]
  height?: number
}

const props = withDefaults(defineProps<Props>(), {
  series: () => [],
  height: 280,
})

const PALETTE = ['--primary', '--success-fg', '--warning', '--error-fg', '--chart-accent']
const FALLBACK_5TH = '#8b5cf6'

const { theme } = useChartTheme()
const chartContainer = ref<HTMLElement | null>(null)
let chart: IChartApi | null = null
let lineSeries: ISeriesApi<'Line'>[] = []

const seriesColor = (i: number) => {
  const token = PALETTE[i]
  const c = token === '--chart-accent' ? FALLBACK_5TH : cssColor(token)
  return c || FALLBACK_5TH
}

// 图例用：末值（净值），去重排序后取最后
const legendSeries = () =>
  props.series.map((s, i) => {
    const sorted = [...s.data].sort((a, b) => (a.time > b.time ? 1 : -1))
    const last = sorted[sorted.length - 1]
    return { name: s.name, color: seriesColor(i), latest: last ? last.value.toFixed(4) : '--' }
  })
const legend = ref(legendSeries())

const dedupSorted = (d: LineData[]) =>
  [...new Map(d.map((item: any) => [item.time, item])).values()].sort((a: any, b: any) => (a.time > b.time ? 1 : -1))

const renderSeries = () => {
  if (!chart) return
  lineSeries.forEach(s => { try { chart?.removeSeries(s) } catch { /* already removed */ } })
  lineSeries = []
  props.series.forEach((s, i) => {
    if (!s.data.length) return
    const line = chart!.addLineSeries({ color: seriesColor(i), lineWidth: i === 0 ? 2 : 1 })
    try { line.setData(dedupSorted(s.data)) } catch (e) { console.warn('NetValueCompareChart: set data failed', e) }
    lineSeries.push(line)
  })
  chart.timeScale().fitContent()
  legend.value = legendSeries()
}

const initChart = () => {
  if (!chartContainer.value) return
  chart = createChart(chartContainer.value, {
    width: chartContainer.value.clientWidth,
    height: props.height,
    layout: {
      background: { type: ColorType.Solid, color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    rightPriceScale: { borderColor: cssColor('--border') },
    timeScale: { borderColor: cssColor('--border'), timeVisible: false },
  })
  renderSeries()
}

// 主题切换重绘（canvas 不认 CSS var，ADR-045）
watch(theme, () => {
  if (!chart) return
  chart.applyOptions({
    layout: {
      background: { type: ColorType.Solid, color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    rightPriceScale: { borderColor: cssColor('--border') },
    timeScale: { borderColor: cssColor('--border') },
  })
  renderSeries()
})

watch(() => props.series, renderSeries, { deep: true })

const handleResize = () => {
  if (chart && chartContainer.value) chart.applyOptions({ width: chartContainer.value.clientWidth })
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) { chart.remove(); chart = null }
})
</script>

<style scoped>
.compare-chart-wrap { position: relative; width: 100%; }

.tv-chart-container { width: 100%; min-height: 250px; }

.compare-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  padding: 4px 2px 8px;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  max-width: 260px;
}
.legend-dot { width: 10px; height: 3px; border-radius: 2px; flex-shrink: 0; }
.legend-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: hsl(var(--foreground));
}
.legend-val { font-family: monospace; font-variant-numeric: tabular-nums; }
</style>
