<template>
  <div ref="chartRef" class="area-chart" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { createChart, type IChartApi, type AreaData } from 'lightweight-charts'
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

interface Props {
  data: AreaData[]
  width?: string
  height?: string
  lineColor?: string
  topColor?: string
  bottomColor?: string
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  width: '100%',
  height: '400px',
  lineColor: '',
  topColor: '',
  bottomColor: '',
  title: ''
})

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
let areaSeries: any = null

// 颜色解析:prop 优先,缺省回退 token(ADR-045)。
const resolveColors = () => ({
  lineColor: props.lineColor || cssColor('--primary'),
  topColor: props.topColor || cssColor('--primary', 0.4),
  bottomColor: props.bottomColor || cssColor('--primary', 0.0),
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
  })

  const c = resolveColors()
  areaSeries = chart.addAreaSeries({
    lineColor: c.lineColor,
    topColor: c.topColor,
    bottomColor: c.bottomColor,
    title: props.title,
  })

  areaSeries.setData(props.data)
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
  const c = resolveColors()
  areaSeries?.applyOptions({
    lineColor: c.lineColor,
    topColor: c.topColor,
    bottomColor: c.bottomColor,
  })
}
watch(theme, applyChartTheme)

const updateChart = () => {
  if (!areaSeries) return
  areaSeries.setData(props.data)
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
  getSeries: () => areaSeries,
  update: (newData: AreaData) => areaSeries?.update(newData),
  resize: () => chart?.applyOptions({ width: chartRef.value?.clientWidth }),
})
</script>

<style scoped>
.area-chart {
  min-height: 200px;
}
</style>
