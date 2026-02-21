<template>
  <div class="analyzer-panel">
    <!-- 分析器选择器 -->
    <div class="analyzer-selector">
      <span class="label">选择分析器：</span>
      <a-select
        v-model:value="selectedAnalyzer"
        style="width: 240px"
        placeholder="请选择分析器"
        @change="onAnalyzerChange"
      >
        <a-select-option v-for="a in analyzers" :key="a.name" :value="a.name">
          {{ a.name }}
          <span class="analyzer-count">({{ a.record_count }}条)</span>
        </a-select-option>
      </a-select>
    </div>

    <!-- 图表区域 -->
    <a-card v-if="selectedAnalyzer" title="时序图表" style="margin-bottom: 16px">
      <a-spin :spinning="chartLoading">
        <NetValueChart
          v-if="chartData.length > 0"
          :data="chartData"
          :height="300"
          :show-benchmark="false"
        />
        <a-empty v-else description="暂无数据" />
      </a-spin>
    </a-card>

    <!-- 统计信息 -->
    <a-card v-if="stats" title="统计信息" style="margin-bottom: 16px">
      <a-row :gutter="16">
        <a-col :span="4">
          <a-statistic title="记录数" :value="stats.count" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="最小值" :value="stats.min" :precision="4" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="最大值" :value="stats.max" :precision="4" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="平均值" :value="stats.avg" :precision="4" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="首值" :value="stats.first" :precision="4" />
        </a-col>
        <a-col :span="4">
          <a-statistic
            title="末值"
            :value="stats.latest"
            :precision="4"
            :value-style="{ color: stats.change >= 0 ? '#52c41a' : '#f5222d' }"
          />
        </a-col>
      </a-row>
      <a-row :gutter="16" style="margin-top: 16px">
        <a-col :span="8">
          <a-statistic
            title="变化量"
            :value="stats.change"
            :precision="4"
            :value-style="{ color: stats.change >= 0 ? '#52c41a' : '#f5222d' }"
          >
            <template #suffix>
              <span v-if="stats.change >= 0">↑</span>
              <span v-else>↓</span>
            </template>
          </a-statistic>
        </a-col>
      </a-row>
    </a-card>

    <!-- 数据表格 -->
    <a-card v-if="tableData.length > 0" title="数据记录">
      <a-table
        :columns="columns"
        :data-source="tableData"
        :pagination="{ pageSize: 20 }"
        size="small"
        row-key="time"
      />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'
import { backtestApi, type AnalyzerInfo } from '@/api/modules/backtest'

interface Props {
  taskId: string
  portfolioId: string
  analyzers: AnalyzerInfo[]
}

const props = defineProps<Props>()

const selectedAnalyzer = ref<string>('')
const chartLoading = ref(false)
const chartData = ref<LineData[]>([])
const tableData = ref<Array<{ time: string; value: number }>>([])
const stats = ref<{
  count: number
  min: number
  max: number
  avg: number
  latest: number | null
  first: number | null
  change: number
} | null>(null)

const columns = [
  { title: '时间', dataIndex: 'time', width: 150 },
  { title: '值', dataIndex: 'value', width: 150 },
]

const onAnalyzerChange = async (name: string) => {
  if (!name || !props.taskId) return

  chartLoading.value = true
  try {
    const result = await backtestApi.getAnalyzerData(props.taskId, name)

    // 处理图表数据
    chartData.value = result.data
      .filter((d: any) => d.value !== null)
      .map((d: any) => ({
        time: d.time,
        value: d.value
      }))

    // 处理表格数据
    tableData.value = result.data

    // 设置统计信息
    stats.value = result.stats
  } catch (e) {
    console.error('Failed to load analyzer data:', e)
    message.error('加载分析器数据失败')
  } finally {
    chartLoading.value = false
  }
}

// 监听 analyzers 变化，自动选择第一个
watch(() => props.analyzers, (newAnalyzers) => {
  if (newAnalyzers.length > 0 && !selectedAnalyzer.value) {
    // 优先选择 net_value
    const netValue = newAnalyzers.find(a => a.name === 'net_value')
    selectedAnalyzer.value = netValue?.name || newAnalyzers[0].name
    onAnalyzerChange(selectedAnalyzer.value)
  }
}, { immediate: true })
</script>

<style scoped>
.analyzer-panel {
  padding: 0;
}

.analyzer-selector {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
}

.analyzer-selector .label {
  font-weight: 500;
  margin-right: 8px;
}

.analyzer-count {
  color: #999;
  font-size: 12px;
  margin-left: 4px;
}
</style>
