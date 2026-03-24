<template>
  <div class="position-chart">
    <div class="chart-header">
      <div class="header-left">
        <h4>持仓分析</h4>
        <div class="radio-group">
          <button class="radio-button" :class="{ active: chartType === 'pie' }" @click="chartType = 'pie'">
            饼图
          </button>
          <button class="radio-button" :class="{ active: chartType === 'bar' }" @click="chartType = 'bar'">
            柱状图
          </button>
        </div>
      </div>
      <div class="header-right">
        <select v-model="dateField" class="form-select">
          <option value="amount">按市值</option>
          <option value="count">按数量</option>
        </select>
      </div>
    </div>
    <div ref="chartRef" class="chart-content"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts/core'

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
    updateChart()
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
    data: barData.value.map(p => p.name),
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

// 监听变化
watch([chartType, dateField, () => props.positions], () => {
  updateChart()
}, { deep: true })

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
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.chart-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.radio-group {
  display: flex;
  gap: 8px;
}

.radio-button {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #8a8a9a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-button:hover {
  border-color: #1890ff;
}

.radio-button.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #ffffff;
}

.form-select {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
}

.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.chart-content {
  height: 400px;
}
</style>
