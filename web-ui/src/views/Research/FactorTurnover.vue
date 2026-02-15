<template>
  <div class="factor-turnover">
    <a-card title="因子换手率分析">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择因子</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="选择因子">
            <a-select
              v-model:value="selectedFactor"
              placeholder="选择要分析的因子"
              style="width: 100%"
            >
              <a-select-option v-for="f in factors" :key="f.name" :value="f.name">
                {{ f.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="基准指数">
            <a-select v-model:value="benchmarkIndex" style="width: 150px">
              <a-select-option :value="0">沪深300</a-select-option>
              <a-select-option :value="1">中证500</a-select-option>
              <a-select-option :value="2">中证800</a-select-option>
              <a-select-option :value="3">中证1000</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="8">
          <a-form-item label="再平衡频率（天）">
            <a-input-number
              v-model:value="rebalanceFreq"
              :min="1"
              :max="60"
              style="width: 100%"
            />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="分析周期">
            <a-range-picker v-model:value="dateRange" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="换手率计算方式">
            <a-radio-group v-model:value="calcMethod">
              <a-radio value="count">计数法</a-radio>
              <a-radio value="amount">金额法</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="analyzing" @click="startAnalysis">
            开始分析
          </a-button>
          <a-button @click="resetConfig">重置</a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="results" title="换手率统计" class="mt-4">
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-statistic title="平均换手率" :value="avgTurnover.toFixed(2)" suffix="%" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="最大换手率" :value="maxTurnover.toFixed(2)" suffix="%" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="最小换手率" :value="minTurnover.toFixed(2)" suffix="%" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="换手率标准差" :value="stdTurnover.toFixed(2)" />
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="chart-section mt-4">
        <h4>换手率时序图</h4>
        <div ref="turnoverChartRef" class="chart-container" style="height: 300px"></div>
      </div>

      <!-- Custom -->
      <div class="distribution-section mt-4">
        <h4>换手率分布直方图</h4>
        <div ref="distributionRef" class="chart-container" style="height: 300px"></div>
      </div>

      <!-- Custom -->
      <a-table
        :columns="columns"
        :data-source="detailData"
        :pagination="{ pageSize: 20 }"
        size="small"
        :scroll="{ y: 400 }"
      >
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'

const router = useRouter()

// 监听结果变化，自动渲染图表
watch(() => results.value.length, async (newLen) => {
  if (newLen > 0) {
    await nextTick()
    renderTurnoverChart()
    renderDistribution()
  }
})

// 因子列表（模拟）
const factors = ref([
  { name: 'momentum', label: '动量因子' },
  { name: 'reversal', label: '反转因子' },
  { name: 'volatility', label: '波动率因子' },
])

const selectedFactor = ref('')
const benchmarkIndex = ref(0)
const rebalanceFreq = ref(5)
const dateRange = ref<any[]>([])
const calcMethod = ref('count')
const analyzing = ref(false)

// 结果
const results = ref<any[]>([])
const avgTurnover = ref(0)
const maxTurnover = ref(0)
const minTurnover = ref(0)
const stdTurnover = ref(0)

const turnoverChartRef = ref<HTMLDivElement>()
const distributionRef = ref<HTMLDivElement>()

// 表格列
const columns = [
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: '组合市值', dataIndex: 'portfolio_value', width: 120 },
  { title: '换出金额', dataIndex: 'turnover_amount', width: 120 },
  { title: '换入金额', dataIndex: 'turnover_in', width: 120 },
  { title: '换手率%', dataIndex: 'turnover_rate', width: 100 }
]

const detailData = computed(() => {
  // TODO: 获取详细数据
  return results.value.map((r, i) => ({
    date: r.date,
    portfolio_value: (1000000 + Math.random() * 50000).toFixed(0),
    turnover_amount: (Math.random() * 50000).toFixed(0),
    turnover_in: (Math.random() * 45000).toFixed(0),
    turnover_rate: (Math.random() * 80 + 10).toFixed(2)
  }))
})

// 开始分析
const startAnalysis = async () => {
  if (!selectedFactor.value) {
    message.warning('请先选择因子')
    return
  }

  analyzing.value = true

  try {
    // TODO: 调用换手率分析API
    await simulateAnalysis()

    message.success('换手率分析完成')
  } catch (e) {
    message.error('分析失败')
  } finally {
    analyzing.value = false
  }
}

// 模拟分析过程
const simulateAnalysis = async () => {
  const n = 100 // 模拟交易日数

  for (let i = 0; i < n; i++) {
    await new Promise(resolve => setTimeout(resolve, 20))

    // 模拟换手率数据
    const turnover = Math.random() * 0.6 + 0.1  // 10%-70%

    results.value.push({
      date: `2024-${String(i + 1).padStart(2, '0')}`,
      turnover_rate: turnover
    })

    avgTurnover.value = results.value.reduce((a, b) => a + b, 0) / results.value.length
    maxTurnover.value = Math.max(...results.value.map(r => r.turnover_rate))
    minTurnover.value = Math.min(...results.value.map(r => r.turnover_rate))
    stdTurnover.value = 0 // 简化计算
  }

  renderTurnoverChart()
  renderDistribution()
}

// 渲染换手率时序图
const renderTurnoverChart = () => {
  if (!turnoverChartRef.value) return

  const chart = echarts.init(turnoverChartRef.value, {
    height: 300,
    width: turnoverChartRef.value.clientWidth
  })

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: results.value.map(r => r.date)
    },
    yAxis: {
      type: 'value',
      name: '换手率(%)',
      min: 0,
      max: Math.max(...results.value.map(r => r.turnover_rate)) * 1.2
    },
    series: [{
      type: 'line',
      data: results.value.map(r => r.turnover_rate),
      smooth: true
    }]
  })
}

// 渲染分布直方图
const renderDistribution = () => {
  if (!distributionRef.value) return

  const chart = echarts.init(distributionRef.value, {
    height: 300,
    width: distributionRef.value.clientWidth
  })

  const bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 5.0]
  const data = bins.map(bin => {
    const count = results.value.filter(r => r.turnover_rate < bin).length
    return `${bin * 10}-${(bin + 1) * 10}%: ${count}`
  })

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: bins,
      axisLabel: {
        formatter: (v) => v
      }
    },
    yAxis: {
      type: 'value',
      name: '次数'
    },
    series: [{
      type: 'bar',
      data: bins.map(bin => {
        value: results.value.filter(r => {
          const lower = bin * 0.1
          const upper = (bin + 1) * 0.1
          return r.turnover_rate >= lower && r.turnover_rate < upper
        }).length
      })
    }]
  })
}

const resetConfig = () => {
  results.value = []
  avgTurnover.value = 0
  maxTurnover.value = 0
}
</script>

<style scoped>
.factor-turnover {
  padding: 16px;
}

.chart-section {
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
}
</style>
