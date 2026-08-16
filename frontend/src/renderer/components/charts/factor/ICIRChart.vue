<template>
  <div class="icir-chart">
    <div
      ref="chartRef"
      class="chart-container"
      :style="{ height: height }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { createChart, type IChartApi, type LineData } from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

interface ICData {
  date: string
  ic: number
  rankIc?: number
}

interface Props {
  icData: ICData[]
  height?: string
  showRankIC?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  height: '350px',
  showRankIC: true
})

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let icSeries: any = null
let rankIcSeries: any = null

const icLineData = computed<LineData[]>(() => {
  return props.icData.map(d => ({
    time: new Date(d.date).getTime() / 1000 as any,
    value: d.ic,
  }))
})

const rankIcLineData = computed<LineData[]>(() => {
  return props.icData.map(d => ({
    time: new Date(d.date).getTime() / 1000 as any,
    value: d.rankIc ?? 0,
  }))
})

const initChart = () => {
  if (!chartRef.value) return

  chart = createChart(chartRef.value, {
    width: chartRef.value.clientWidth,
    height: parseInt(props.height),
    layout: {
      background: { color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
    timeScale: {
      timeVisible: true,
    },
  })

  // IC系列(主线)
  icSeries = chart.addLineSeries({
    color: cssColor('--primary'),
    lineWidth: 2,
    title: 'IC',
  })
  icSeries.setData(icLineData.value)

  // Rank IC系列(次线,warning 色保持区分)
  if (props.showRankIC) {
    rankIcSeries = chart.addLineSeries({
      color: cssColor('--warning-fg'),
      lineWidth: 2,
      title: 'RankIC',
    })
    rankIcSeries.setData(rankIcLineData.value)
  }
}

// 主题切换重绘:canvas 不认 CSS var,须重读 token 调 applyOptions(ADR-045)。
const applyChartTheme = () => {
  if (!chart) return
  chart.applyOptions({
    layout: {
      background: { color: cssColor('--card') },
      textColor: cssColor('--muted-foreground'),
    },
    grid: {
      vertLines: { color: cssColor('--border') },
      horzLines: { color: cssColor('--border') },
    },
  })
  icSeries?.applyOptions({ color: cssColor('--primary') })
  rankIcSeries?.applyOptions({ color: cssColor('--warning-fg') })
}
watch(theme, applyChartTheme)

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
    chart = null
  }
})

watch([icLineData, rankIcLineData], () => {
  if (icSeries) icSeries.setData(icLineData.value)
  if (rankIcSeries) rankIcSeries.setData(rankIcLineData.value)
}, { deep: true })
</script>

<style scoped>
.icir-chart {
  min-height: 250px;
}

.chart-container {
  width: 100%;
}
</style>
