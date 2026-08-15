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
import { useChartTheme, cssColor } from '@/composables/useChartTheme'

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

const { theme } = useChartTheme()
const chartRef = ref<HTMLDivElement>()
let chart: IChartApi | null = null
const seriesMap = new Map<string, any>()

// token 池:主题切换时各组颜色保持区分(ADR-045)。
const tokenPool = ['--primary', '--success-fg', '--warning-fg', '--error-fg', '--muted-foreground']
const colorAt = (i: number) => cssColor(tokenPool[i % tokenPool.length])

const groups = computed(() => {
  // 读 theme 建立响应依赖:主题切换时重算 legend/series 色(ADR-045)。
  void theme.value
  if (props.layerData.length === 0) return []
  const keys = Object.keys(props.layerData[0].returns).filter(k => k !== 'long_short')
  return keys.map((key, i) => ({
    name: key,
    color: colorAt(i),
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
  })

  // 为每个分组创建series
  groups.value.forEach((group) => {
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
  groups.value.forEach((group, i) => {
    seriesMap.get(group.name)?.applyOptions({ color: colorAt(i) })
  })
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
  gap: 8px;
  font-size: 13px;
}

.color-box {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-sm);
}
</style>
