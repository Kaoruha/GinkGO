<template>
  <div class="icir-chart">
    <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { createChart, type IChartApi, type LineData } from 'lightweight-charts'

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
      background: { color: '#ffffff' },
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#e1e1e1' },
      horzLines: { color: '#e1e1e1' },
    },
    timeScale: {
      timeVisible: true,
    },
  })

  // IC系列
  icSeries = chart.addLineSeries({
    color: '#2196F3',
    lineWidth: 2,
    title: 'IC',
  })
  icSeries.setData(icLineData.value)

  // Rank IC系列
  if (props.showRankIC) {
    rankIcSeries = chart.addLineSeries({
      color: '#FF9800',
      lineWidth: 2,
      title: 'RankIC',
    })
    rankIcSeries.setData(rankIcLineData.value)
  }
}

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
