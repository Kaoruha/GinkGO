<template>
  <div ref="chartRef" class="trend-chart" :style="{ height: `${height}px` }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { useApiError } from '@/composables/useApiError'

/**
 * 趋势图表组件
 * 基于 ECharts 的可复用图表封装
 */

interface Props {
  data: Array<{ name: string; value: number[] }>
  height?: number
  smooth?: boolean
  area?: boolean
  showZoom?: boolean
  showLegend?: boolean
  title?: string
  color?: string
}

const props = withDefaults(defineProps<Props>(), {
  height: 300,
  smooth: true,
  area: true,
  showZoom: true,
  showLegend: true
  color: '#1890ff'
})

const chartRef = ref<echarts.ECharts>()
let chartInstance: echarts.ECharts | null = null

const { handleError } = useApiError()

// 初始化图表
const initChart = () => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value, {
      height: props.height,
      renderer: 'canvas'
    })
  }

  // 响应式调整
  window.addEventListener('resize', () => {
    chartInstance?.resize()
  })
}

// 销毁图表
const disposeChart = () => {
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  window.removeEventListener('resize', () => {})
}

// 更新图表
const updateChart = () => {
  if (!chartInstance || !props.data.length) return

  const dates = props.data.map(item => item.name)
  const values = props.data.map(item => item.value)

  const option: echarts.EChartOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      backgroundColor: 'rgba(255, 255, 255, 0.1)'
      }
    },
    legend: {
      show: props.showLegend,
      data: dates
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '3%'
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: {
        lineStyle: { color: '#E0E6F' }
      },
      axisLabel: {
        color: '#8C8C8'
      },
      axisTick: {
        color: '#8C8C8'
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        lineStyle: { color: '#E0E6F' }
      },
      axisLabel: {
        color: '#8C8C8'
      },
      splitLine: {
        lineStyle: { color: '#E0E6F' }
      },
      axisTick: {
        color: '#8C8C8'
      }
    },
    series: values.map((item, index) => ({
      name: item.name,
      type: 'line',
      smooth: props.smooth,
      symbol: 'none',
      areaStyle: {
        color: props.color
      opacity: props.area ? 0.3 : 0
      },
      lineStyle: {
        color: props.color,
        width: 2
      },
      data: item.value
    }))
  }

  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  disposeChart()
})

watch(
  () => [props.data, props.height, props.smooth, props.area],
  () => updateChart,
  { deep: true }
)

defineExpose({
  chartRef,
  updateChart
})
</script>

<style scoped>
.trend-chart {
  width: 100%;
}
</style>
