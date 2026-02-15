<template>
  <div class="monte-carlo">
    <a-card title="蒙特卡洛模拟">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择策略</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="选择策略">
            <a-select v-model:value="selectedStrategy" placeholder="选择策略">
              <a-select-option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="分析目标">
            <a-select v-model:value="analyzeTarget">
              <a-select-option value="total_return">总收益分布</a-select-option>
              <a-select-option value="sharpe">夏普比率分布</a-select-option>
              <a-select-option value="drawdown">回撤分布</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-divider>策略参数</a-divider>
      <div class="params-display">
        <a-descriptions bordered :column="1" size="small">
          <a-descriptions-item v-for="p in fixedParams" :key="p.name" :label="p.label">
            {{ p.value }}
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- Custom -->
      <a-divider>蒙特卡洛配置</a-divider>
      <a-row :gutter="16" class="mb-4">
        <a-col :span="8">
          <a-form-item label="历史收益率数据">
            <a-select v-model:value="returnDataSource" placeholder="选择数据来源">
              <a-select-option value="backtest">使用回测收益</a-select-option>
              <a-select-option value="manual">手动输入</a-select-option>
              <a-select-option value="historical">历史市场数据</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="模拟次数">
            <a-input-number v-model:value="nSimulations" :min="100" :max="100000" :step="100" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="置信水平">
            <a-select v-model:value="confidenceLevel">
              <a-select-option :value="0.9">90%</a-select-option>
              <a-select-option :value="0.95">95%</a-select-option>
              <a-select-option :value="0.99">99%</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="随机种子">
            <a-input-number v-model:value="randomSeed" :min="0" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div v-if="returnDataSource === 'manual'" class="mb-4">
        <a-form-item label="历史收益率（每行一个，用逗号或空格分隔）">
          <a-textarea
            v-model:value="manualReturns"
            :rows="5"
            placeholder="例如: 0.02, -0.01, 0.03, 0.015, ..."
          />
        </a-form-item>
      </div>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="simulating" @click="startSimulation">
            开始模拟
          </a-button>
          <a-button @click="resetConfig">重置</a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="simulating" title="模拟进度" class="mt-4">
      <a-progress :percent="progress" :status="progressStatus" />
      <div class="progress-detail mt-3">
        <a-statistic title="已完成" :value="completedSimulations" suffix="/ {{ nSimulations }}" />
        <a-statistic title="预计剩余" :value="estimatedTime" suffix="秒" class="ml-4" />
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="results" title="蒙特卡洛模拟结果" class="mt-4">
      <template #extra>
        <a-space>
          <a-button @click="exportResults">导出数据</a-button>
          <a-button @click="generateReport">生成报告</a-button>
        </a-space>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-statistic title="模拟次数" :value="results.n_simulations" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="平均收益" :value="results.mean.toFixed(4)" suffix="%" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="标准差" :value="results.std.toFixed(4)" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="夏普比率" :value="results.sharpe.toFixed(2)" />
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-divider>百分位数分布</a-divider>
      <div class="percentile-section">
        <a-table
          :columns="percentileColumns"
          :data-source="percentileData"
          :pagination="false"
          size="small"
          bordered
        >
          <template #bodyCell="{ column, record }">
            <span v-if="column.dataIndex === 'probability'" style="color: #666">
              {{ record.probability }}
            </span>
          </template>
        </a-table>
      </div>

      <!-- Custom -->
      <a-divider>风险度量</a-divider>
      <a-row :gutter="16">
        <a-col :span="8">
          <a-card title="VaR (Value at Risk)" size="small">
            <a-statistic
              :title="`VaR ${(confidenceLevel * 100)}%`"
              :value="results.var.toFixed(2)"
              suffix="%"
              :precision="2"
            />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card title="CVaR (Conditional VaR)" size="small">
            <a-statistic
              :title="`CVaR ${(confidenceLevel * 100)}%`"
              :value="results.cvar.toFixed(2)"
              suffix="%"
              :precision="2"
            />
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card title="最大回撤期望" size="small">
            <a-statistic
              title="期望"
              :value="results.max_drawdown.toFixed(2)"
              suffix="%"
              :precision="2"
            />
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="charts-section mt-4">
        <a-row :gutter="16">
          <a-col :span="12">
            <h4>收益分布直方图</h4>
            <div ref="histogramRef" class="chart-container" style="height: 300px"></div>
          </a-col>
          <a-col :span="12">
            <h4>累计分布函数</h4>
            <div ref="ecdfRef" class="chart-container" style="height: 300px"></div>
          </a-col>
        </a-row>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import { monteCarloSimulation } from '@/api/modules/validation'

const router = useRouter()

// 策略列表（模拟）
const strategies = ref([
  { uuid: 's1', name: '双均线策略' },
  { uuid: 's2', name: '动量轮动' },
])

// 配置
const selectedStrategy = ref('')
const analyzeTarget = ref('total_return')
const returnDataSource = ref('backtest')
const nSimulations = ref(10000)
const confidenceLevel = ref(0.95)
const randomSeed = ref(42)

// 参数配置
const fixedParams = ref<any[]>([])

// 手动输入
const manualReturns = ref('')

// 模拟状态
const simulating = ref(false)
const progress = ref(0)
const progressStatus = ref<'normal' | 'active' | 'success'>('normal')
const completedSimulations = ref(0)
const estimatedTime = ref(0)

// 结果
const results = ref<any>(null)
const histogramRef = ref<HTMLDivElement>()
const ecdfRef = ref<HTMLDivElement>()

// 百分位数据
const percentileData = computed(() => {
  if (!results.value) return []

  const conf = confidenceLevel.value
  const percentiles = [
    { percentile: 0, probability: '最低值', value: results.value.distribution.percentiles.p0 },
    { percentile: 5, probability: '5%', value: results.value.distribution.percentiles.p5 },
    { percentile: 10, probability: '10%', value: results.value.distribution.percentiles.p10 },
    { percentile: 25, probability: '25%', value: results.value.distribution.percentiles.p25 },
    { percentile: 50, probability: '50%', value: results.value.distribution.percentiles.p50 },
    { percentile: 75, probability: '75%', value: results.value.distribution.percentiles.p75 },
    { percentile: 90, probability: '90%', value: results.value.distribution.percentiles.p90 },
    { percentile: 95, probability: '95%', value: results.value.distribution.percentiles.p95 },
  ]

  return percentiles
})

const percentileColumns = [
  { title: '置信度', dataIndex: 'percentile', width: 100 },
  { title: '概率', dataIndex: 'probability', width: 100 },
  { title: '收益', dataIndex: 'value', width: 120 },
  { title: '累计概率', dataIndex: 'cumulative', width: 120 }
]

// 根据策略加载参数
const loadParameters = async () => {
  if (!selectedStrategy.value) return

  // 模拟：加载参数
  fixedParams.value = [
    { name: 'short_period', label: '短期周期', value: 5 },
    { name: 'long_period', label: '长期周期', value: 20 },
    { name: 'stop_loss', label: '止损比例', value: 0.05 }
  ]
}

// 开始模拟
const startSimulation = async () => {
  if (!selectedStrategy.value) {
    message.warning('请先选择策略')
    return
  }

  if (returnDataSource.value === 'manual' && !manualReturns.value) {
    message.warning('请输入历史收益率数据')
    return
  }

  simulating.value = true
  progress.value = 0
  completedSimulations.value = 0

  try {
    // TODO: 调用API进行蒙特卡洛模拟
    await simulateMonteCarlo()

    message.success('蒙特卡洛模拟完成')
  } catch (e) {
    message.error('模拟失败')
  } finally {
    simulating.value = false
  }
}

// 模拟蒙特卡洛过程
const simulateMonteCarlo = async () => {
  const n = nSimulations.value
  const batchSize = 100
  const batches = Math.ceil(n / batchSize)

  // 解析历史收益
  let baseReturns: number[] = []
  if (returnDataSource.value === 'manual') {
    baseReturns = manualReturns.value.split(/[\s,]+/).map(s => parseFloat(s.trim()))
  } else if (returnDataSource.value === 'backtest') {
    // TODO: 从回测结果获取收益序列
    baseReturns = Array.from({ length: 252 }, () => Math.random() * 0.3 - 0.05)
  }

  for (let batch = 0; batch < batches; batch++) {
    const batchResults = []
    for (let i = 0; i < batchSize && (batch * batchSize + i) < n; i++) {
      // 随机重采样
      const sampleIndex = Math.floor(Math.random() * baseReturns.length)
      const baseReturn = baseReturns[sampleIndex]

      // 组合历史收益
      const periodLength = 252 // 一年交易日
      const startIndex = Math.floor(Math.random() * (baseReturns.length - periodLength))
      const sampleReturns = baseReturns.slice(startIndex, startIndex + periodLength)

      // 计算组合收益
      let totalReturn = 1
      for (const r of sampleReturns) {
        totalReturn *= (1 + r)
      }
      const annualReturn = (Math.pow(totalReturn, 252 / periodLength) - 1) * 100

      batchResults.push(annualReturn)

      completedSimulations.value = batch * batchSize + i + 1
      progress.value = Math.floor((completedSimulations.value / n) * 100)

      await new Promise(resolve => setTimeout(resolve, 1))
    }

    // 计算统计结果
    calculateStatistics(batchResults)
  }
}

// 计算统计结果
const calculateStatistics = (data: number[]) => {
  if (data.length === 0) return

  // 基础统计
  const mean = data.reduce((a, b) => a + b, 0) / data.length
  const variance = data.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / data.length
  const std = Math.sqrt(variance)
  const sharpe = mean / std * Math.sqrt(252)

  // 计算百分位数
  const sorted = [...data].sort((a, b) => a - b)
  const percentiles = {
    p0: sorted[0],
    p5: sorted[Math.floor(sorted.length * 0.05)],
    p10: sorted[Math.floor(sorted.length * 0.10)],
    p25: sorted[Math.floor(sorted.length * 0.25)],
    p50: sorted[Math.floor(sorted.length * 0.50)],
    p75: sorted[Math.floor(sorted.length * 0.75)],
    p90: sorted[Math.floor(sorted.length * 0.90)],
    p95: sorted[Math.floor(sorted.length * 0.95)],
    p100: sorted[sorted.length - 1]
  }

  // 计算分布
  const distribution: Record<number, number> = {}
  const binCount = 50
  const binSize = (Math.max(...data) - Math.min(...data)) / binCount

  for (let i = 0; i < binCount; i++) {
    const binMin = Math.min(...data) + i * binSize
    const binMax = binMin + binSize
    const count = data.filter(v => v >= binMin && v < binMax).length
    distribution[i] = count
  }

  results.value = {
    n_simulations: data.length,
    mean,
    std,
    sharpe,
    percentiles,
    distribution,
    // 风险度量
    var: variance,
    cvar: data.filter(v => v < percentiles.p5).reduce((a, b) => a + b, 0) / data.length,
    max_drawdown: percentiles.p0
  }

  // 渲染图表
  renderHistogram()
  renderECDF()
}

// 渲染直方图
const renderHistogram = () => {
  if (!histogramRef.value || !results.value) return

  const chart = echarts.init(histogramRef.value, {
    height: 300,
    width: histogramRef.value.clientWidth
  })

  const data = Object.entries(results.value.distribution).map(([k, v]) => [parseFloat(k), v])

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `收益: ${params.mark[0].toFixed(2)}%<br/>次数: ${params.mark[1]}`
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d[0].toFixed(2) + '%')
    },
    yAxis: {
      type: 'value',
      name: '次数'
    },
    series: [{
      type: 'bar',
      data: data.map(d => d[1]),
      itemStyle: {
        color: '#2196F3'
      }
    }]
  })
}

// 渲染累计分布函数
const renderECDF = () => {
  if (!ecdfRef.value || !results.value) return

  const chart = echarts.init(ecdfRef.value, {
    height: 300,
    width: ecdfRef.value.clientWidth
  })

  const sorted = [...Object.entries(results.value.distribution)]
    .sort((a, b) => parseFloat(a[0]) - parseFloat(b[0]))

  // 计算累计分布
  let cumulative = 0
  const total = sorted.reduce((sum, [, count]) => sum + count, 0)
  const ecdfData = sorted.map(([k, v], i) => {
    cumulative += v
    return [parseFloat(k), cumulative / total]
  })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `收益: ${params.mark[0].toFixed(2)}%<br/>累计: ${(params.mark[1] * 100).toFixed(1)}%`
    },
    xAxis: {
      type: 'value',
      name: '收益',
      min: 'dataMin',
      max: 'dataMax'
    },
    yAxis: {
      type: 'value',
      name: '累计概率',
      max: 1,
      axisLabel: {
        formatter: (v) => (v * 100).toFixed(0) + '%'
      }
    },
    series: [{
      type: 'line',
      data: ecdfData,
      smooth: true,
      areaStyle: {
        color: '#2196F3',
        opacity: 0.3
      },
      lineStyle: { color: '#2196F3' }
    }]
  })
}

// 重置配置
const resetConfig = () => {
  results.value = null
  progress.value = 0
  manualReturns.value = ''
}

// 导出结果
const exportResults = () => {
  if (!results.value) {
    message.warning('没有可导出的结果')
    return
  }
  message.info('导出蒙特卡洛模拟数据...')
}

// 生成报告
const generateReport = () => {
  if (!results.value) {
    message.warning('请先运行模拟')
    return
  }
  message.info('生成蒙特卡洛分析报告...')
}

// 加载参数
onMounted(() => {
  loadParameters()
})
</script>

<style scoped>
.monte-carlo {
  padding: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.params-display {
  background: #fafafa;
  padding: 16px;
  border-radius: 8px;
}

.action-buttons {
  text-align: center;
  margin-top: 24px;
}

.progress-detail {
  display: flex;
  justify-content: center;
}

.ml-4 {
  margin-left: 16px;
}

.percentile-section {
  margin-top: 16px;
}

.charts-section h4 {
  margin-bottom: 12px;
}

.chart-container {
  width: 100%;
}
</style>
