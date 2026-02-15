<template>
  <div class="layering-chart">
    <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
    <div class="legend">
      <div v-for="group in groups" :key="group.name" class="legend-item">
        <span class="color-box" :style="{ background: group.color }"></span>
        <span>{{ group.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { createChart, type IChartApi, type LineData } from 'lightweight-charts'

interface LayerData {
  date: string
  returns: Record<string, number>
}

interface Props {
  layerData: LayerData[]
  height?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: '400px'
})

const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
const seriesMap = new Map<string, any>()

const colorPool = ['#d32f2f', '#f57c00', '#fbc02d', '#689f38', '#388e3c']

const groups = computed(() => {
  if (props.layerData.length === 0) return []
  const keys = Object.keys(props.layerData[0].returns).filter(k => k !== 'long_short')
  return keys.map((key, i) => ({
    name: key,
    color: colorPool[i % colorPool.length]
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
  })

  // 为每个分组创建series
  groups.value.forEach((group, index) => {
    const series = chart!.addLineSeries({
      color: group.color,
      lineWidth: 2,
      title: group.name,
    })
    seriesMap.set(group.name, series)
  })

  updateSeriesData()
}

const updateSeriesData = () => {
  if (!chart) return

  // 为每个series设置数据
  groups.value.forEach(group => {
    const series = seriesMap.get(group.name)
    if (!series) return

    const data: LineData[] = props.layerData.map(d => ({
      time: new Date(d.date).getTime() / 1000 as any,
      value: d.returns[group.name] || 0
    }))
    series.setData(data)
  })
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

watch(() => props.layerData, updateSeriesData, { deep: true })
</script>

<style scoped>
.layering-chart {
  min-height: 300px;
}

.chart-container {
  width: 100%;
}

.legend {
  display: flex;
  gap: 16px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.color-box {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}
</style>
