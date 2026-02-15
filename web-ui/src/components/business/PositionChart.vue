<template>
  <div class="position-chart">
    <div class="chart-header">
      <div class="header-left">
        <h4>持仓分析</h4>
        <a-radio-group v-model:value="chartType" size="small" style="margin-right: 16px">
          <a-radio-button value="pie">饼图</a-radio-button>
          <a-radio-button value="bar">柱状图</a-radio-button>
        </a-radio-group>
      </div>
      <div class="header-right">
        <a-select v-model:value="dateField" size="small" style="width: 150px">
          <a-select-option value="amount">按市值</a-select-option>
          <a-select-option value="count">按数量</a-select-option>
        </a-select>
      </div>
    </div>
    <div ref="chartRef" class="chart-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import * as echarts from 'echarts/core'
import dayjs from 'dayjs'

/**
 * 持仓图表组件
 * 展示持仓分析（饼图、柱状图）
 */

interface Position {
  code: string
  name: string
  amount: number
  currentPrice: number
  marketValue: number
}

const props = defineProps<{
  positions: Position[]
}>()

const chartType = ref('bar')
const dateField = ref('amount')

// 饼图数据
const pieData = computed(() => {
  return props.positions.map(p => ({
    name: p.name,
    value: p.amount
  }))
})

// 柱状图数据
const barData = computed(() => {
  if (dateField.value === 'amount') {
    return props.positions.slice(0, 10).map(p => ({
      name: p.code,
      value: p.amount
    }))
  }
  return props.positions.slice(0, 10)
})

const chartRef = ref()
let chartInstance: echarts.ECharts | null = null

// 初始化图表
const initChart = () => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value, {
      height: 400,
      renderer: 'canvas'
    })
  }
}

// 销毁图表
const disposeChart = () => {
  chartInstance?.dispose()
  chartInstance = null
}

// 更新图表
const updateChart = () => {
  if (!chartInstance) return

  const option = chartType.value === 'pie' ? getPieOption() : getBarOption()
  chartInstance.setOption(option)
}

const getPieOption = () => ({
  tooltip: {
    trigger: 'item',
    formatter: (value: any) => {
      const position = props.positions[props.positions.indexOf(value as any)]
      return `${position.name}\n${(value as number).toFixed(2)}`
    }
  },
  series: [{
    type: 'pie',
    data: pieData.value,
    radius: '70%'
  }]
})

const getBarOption = () => ({
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'shadow'
    }
  },
  xAxis: {
    type: 'category',
    data: barData.value.map(p => p.name)
    axisLabel: {
      interval: 0
    }
  },
  yAxis: {
    type: 'value',
    axisLabel: {
      formatter: (value: any) => `¥${(value as number).toFixed(2)}`
    }
  },
  series: [{
    type: 'bar',
    data: barData.value,
    itemStyle: {
      color: '#1890ff'
    }
  }]
})

onMounted(() => {
  initChart()
})

onUnmounted(() => {
  disposeChart()
})
</script>

<style scoped>
.position-chart {
  height: 480px;
  background: white;
  border-radius: 8px;
  padding: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-content {
  height: 400px;
}
</style>
