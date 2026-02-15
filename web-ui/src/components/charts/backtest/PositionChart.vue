<template>
  <div class="position-chart">
    <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi } from 'lightweight-charts'

interface PositionData {
  code: string
  time: number
  value: number
  color?: string
}

interface Props {
  positionData: PositionData[]
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px'
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
const seriesMap = new Map<string, any>()

// 预定义颜色池
const colorPool = [
  '#2196F3', '#4CAF50', '#FF9800', '#9C27B0',
  '#F44336', '#00BCD4', '#FFEB3B', '#795548'
]

const getColor = (index: number) => colorPool[index % colorPool.length]

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
}

const updateChart = () => {
  if (!chart) return

  // 清除旧的series
  seriesMap.forEach(series => chart?.removeSeries(series))
  seriesMap.clear()

  // 按代码分组
  const grouped = new Map<string, Array<{ time: number; value: number }>>()
  props.positionData.forEach(d => {
    if (!grouped.has(d.code)) {
      grouped.set(d.code, [])
    }
    grouped.get(d.code)!.push({ time: d.time, value: d.value })
  })

  // 为每个代码创建area series
  let index = 0
  grouped.forEach((data, code) => {
    const series = chart!.addAreaSeries({
      lineColor: props.positionData.find(d => d.code === code)?.color || getColor(index),
      topColor: `${getColor(index)}40`,
      bottomColor: `${getColor(index)}00`,
      title: code,
    })
    series.setData(data)
    seriesMap.set(code, series)
    index++
  })
}

onMounted(() => {
  initChart()
  updateChart()
})

onUnmounted(() => {
  if (chart) {
    chart.remove()
    chart = null
  }
})

watch(() => props.positionData, updateChart, { deep: true })
</script>

<style scoped>
.position-chart {
  min-height: 200px;
}

.chart-container {
  width: 100%;
}
</style>
