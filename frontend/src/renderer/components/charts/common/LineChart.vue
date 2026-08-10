<template>
  <div ref="chartRef" class="line-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type LineData } from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

interface Props {
  data: LineData[]
  width?: string
  height?: string
  color?: string
  lineWidth?: number
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '400px',
  color: '',
  lineWidth: 2,
  title: ''
})

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let lineSeries: any = null

// 颜色解析:prop 优先,缺省回退 token(ADR-045)。
const resolveColor = () => props.color || cssColor('--primary')

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
      secondsVisible: false,
    },
  })

  lineSeries = chart.addLineSeries({
    color: resolveColor(),
    lineWidth: props.lineWidth as any,
    title: props.title,
  })

  lineSeries.setData(props.data)
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
  lineSeries?.applyOptions({ color: resolveColor() })
}
watch(theme, applyChartTheme)

const updateChart = () => {
  if (!lineSeries) return
  lineSeries.setData(props.data)
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

watch(() => props.data, updateChart, { deep: true })

defineExpose({
  getInstance: () => chart,
  getSeries: () => lineSeries,
  update: (newData: LineData) => lineSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.line-chart {
  min-height: 200px;
}
</style>
