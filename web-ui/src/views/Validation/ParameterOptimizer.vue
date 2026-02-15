<template>
  <div class="parameter-optimizer">
    <a-card title="参数优化">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择策略</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="选择策略">
            <a-select v-model:value="selectedStrategy" placeholder="选择要优化的策略">
              <a-select-option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }} - {{ s.strategy_type }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="优化目标">
            <a-select v-model:value="optimizeTarget">
              <a-select-option value="sharpe">夏普比率</a-select-option>
              <a-select-option value="total_return">总收益</a-select-option>
              <a-select-option value="max_drawdown">最大回撤</a-select-option>
              <a-select-option value="calmar">卡玛比率</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-divider>参数范围配置</a-divider>
      <div class="params-config">
        <a-row :gutter="16" v-for="(param, index) in parameters" :key="param.name" class="mb-3">
          <a-col :span="6">
            <a-form-item :label="`${param.label} 最小值`">
              <a-input-number v-model:value="param.min" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item :label="`${param.label} 最大值`">
              <a-input-number v-model:value="param.max" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="步长">
              <a-input-number v-model:value="param.step" :min="0.001" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="类型">
              <a-select v-model:value="param.type">
                <a-select-option value="int">整数</a-select-option>
                <a-select-option value="float">浮点数</a-select-option>
                <a-select-option value="categorical">分类</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
      </div>

      <!-- Custom -->
      <a-divider>优化方法</a-divider>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="优化算法">
            <a-select v-model:value="optimizeMethod">
              <a-select-option value="grid">网格搜索</a-select-option>
              <a-select-option value="genetic">遗传算法</a-select-option>
              <a-select-option value="bayesian">贝叶斯优化</a-select-option>
              <a-select-option value="random">随机搜索</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="最大迭代次数">
            <a-input-number v-model:value="maxIterations" :min="10" :max="1000" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="6">
          <a-form-item label="并行任务数">
            <a-input-number v-model:value="nJobs" :min="1" :max="10" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="训练数据范围">
            <a-range-picker v-model:value="trainDateRange" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="验证数据范围">
            <a-range-picker v-model:value="valDateRange" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="optimizing" @click="startOptimization">
            开始优化
          </a-button>
          <a-button @click="resetConfig">重置</a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="optimizing" title="优化进度" class="mt-4">
      <a-progress :percent="progress" :status="progressStatus">
        <template #format="percent">
          <span>{{ percent }}%</span>
          <span class="ml-2">{{ progressText }}</span>
        </template>
      </a-progress>
      <div class="progress-detail mt-3">
        <a-statistic title="已完成" :value="completedIterations" suffix="/ {{ maxIterations }}" />
        <a-statistic title="最优目标值" :value="bestObjectiveValue.toFixed(4)" class="ml-4" />
        <a-statistic title="剩余时间" :value="estimatedTime" class="ml-4" />
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="results && results.length > 0" title="优化结果" class="mt-4">
      <template #extra>
        <a-button @click="exportResults">导出结果</a-button>
      </template>

      <!-- Custom -->
      <a-alert type="success" show-icon class="mb-4">
        <template #message>
          <div>最优参数组合</div>
          <div class="mt-2">
            <span style="font-size: 16px; font-weight: 600;">
              {{ optimizeTarget.toUpperCase() }} = {{ bestObjectiveValue.toFixed(4) }}
            </span>
          </div>
        </template>
      </a-alert>

      <a-table :columns="resultColumns" :data-source="results" :pagination="{ pageSize: 20 }" size="small">
        <template #bodyCell="{ column, record }">
          <a-tag v-if="column.dataIndex === 'rank'" :color="getRankColor(record.rank)">
            #{{ record.rank }}
          </a-tag>
          <span v-else-if="column.dataIndex === 'objective_value'" :style="{ color: getValueColor(record.objective_value) }">
            {{ record.objective_value.toFixed(4) }}
          </span>
        </template>
      </a-table>

      <!-- Custom -->
      <div class="heatmap-section mt-4">
        <h4>参数空间热力图</h4>
        <div ref="heatmapRef" class="heatmap-container" style="height: 400px"></div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import dayjs from 'dayjs'

const router = useRouter()

// 策略列表（模拟数据）
const strategies = ref([
  { uuid: 's1', name: '双均线策略', strategy_type: 'SMA_CROSS' },
  { uuid: 's2', name: '动量轮动', strategy_type: 'MOMENTUM' },
  { uuid: 's3', name: 'RSI策略', strategy_type: 'RSI' },
])

// 优化配置
const selectedStrategy = ref('')
const optimizeTarget = ref('sharpe')
const optimizeMethod = ref('grid')
const maxIterations = ref(100)
const nJobs = ref(4)
const trainDateRange = ref<any[]>([])
const valDateRange = ref<any[]>([])

// 参数配置（根据策略动态生成）
const parameters = ref<any[]>([])

// 优化状态
const optimizing = ref(false)
const progress = ref(0)
const progressStatus = ref<'normal' | 'active' | 'success' | 'exception'>('normal')
const progressText = ref('')
const completedIterations = ref(0)
const bestObjectiveValue = ref(0)
const estimatedTime = ref('0分钟')

// 优化结果
const results = ref<any[]>([])
const heatmapRef = ref<HTMLDivElement>()

// 结果表格列
const resultColumns = [
  { title: '排名', dataIndex: 'rank', width: 80, fixed: 'left' },
  { title: '参数组合', dataIndex: 'params_str', width: 300 },
  { title: '训练集' + optimizeTarget.value.toUpperCase(), dataIndex: 'train_value', width: 120 },
  { title: '验证集' + optimizeTarget.value.toUpperCase(), dataIndex: 'val_value', width: 120 },
  { title: '过拟合检测', dataIndex: 'overfit', width: 100 },
]

// 计算属性
const bestResult = computed(() => {
  return results.value.length > 0 ? results.value[0] : null
})

// 根据策略更新参数配置
const updateParameters = () => {
  if (!selectedStrategy.value) return

  // 模拟：不同策略有不同参数
  const paramMap: Record<string, any[]> = {
    'SMA_CROSS': [
      { name: 'short_period', label: '短期周期', min: 5, max: 60, step: 1, type: 'int' },
      { name: 'long_period', label: '长期周期', min: 20, max: 200, step: 1, type: 'int' },
      { name: 'stop_loss', label: '止损比例', min: 0.01, max: 0.2, step: 0.01, type: 'float' },
    ],
    'MOMENTUM': [
      { name: 'lookback', label: '回看期', min: 5, max: 60, step: 1, type: 'int' },
      { name: 'hold_period', label: '持有期', min: 1, max: 30, step: 1, type: 'int' },
      { name: 'percentile', label: '分位数', min: 0.1, max: 0.9, step: 0.05, type: 'float' },
    ],
    'RSI': [
      { name: 'period', label: 'RSI周期', min: 5, max: 30, step: 1, type: 'int' },
      { name: 'overbought', label: '超买线', min: 70, max: 90, step: 1, type: 'int' },
      { name: 'oversold', label: '超卖线', min: 10, max: 30, step: 1, type: 'int' },
    ],
  }

  parameters.value = paramMap[selectedStrategy.value] || []
}

// 开始优化
const startOptimization = async () => {
  if (!selectedStrategy.value) {
    message.warning('请先选择策略')
    return
  }

  optimizing.value = true
  progress.value = 0
  completedIterations.value = 0
  results.value = []

  try {
    // TODO: 调用后端优化API
    // const res = await optimizeParameters({ ... })
    await simulateOptimization()
    message.success('优化完成')
    renderHeatmap()
  } catch (e) {
    message.error('优化失败')
  } finally {
    optimizing.value = false
  }
}

// 模拟优化过程
const simulateOptimization = async () => {
  const total = maxIterations.value
  for (let i = 0; i < total; i++) {
    await new Promise(resolve => setTimeout(resolve, 100))
    completedIterations.value = i + 1
    progress.value = Math.floor(((i + 1) / total) * 100)
    progressText.value = `运行中 ${i + 1}/${total}`

    // 模拟生成结果
    const objValue = Math.random() * 2 - 0.5
    const result = {
      rank: results.value.length + 1,
      params_str: generateParamsString(),
      train_value: objValue,
      val_value: objValue - Math.random() * 0.2,
      overfit: Math.abs(Math.random() * 0.2) < 0.05 ? '正常' : '警告',
      objective_value: objValue - Math.random() * 0.1
    }
    results.value.push(result)

    if (objValue > bestObjectiveValue.value) {
      bestObjectiveValue.value = objValue
    }

    estimatedTime.value = Math.ceil((total - i - 1) * 0.1) + '分钟'
  }
  progressStatus.value = 'success'
  progressText.value = '优化完成'

  // 排序结果
  results.value.sort((a, b) => b.objective_value - a.objective_value)
}

// 生成参数字符串
const generateParamsString = () => {
  const params: string[] = []
  parameters.value.forEach(p => {
    const value = p.type === 'float'
      ? (p.min + Math.random() * (p.max - p.min)).toFixed(2)
      : Math.floor(p.min + Math.random() * (p.max - p.min))
    params.push(`${p.name}=${value}`)
  })
  return params.join(', ')
}

// 渲染热力图
const renderHeatmap = () => {
  if (!heatmapRef.value || results.value.length === 0) return

  const chart = echarts.init(heatmapRef.value, {
    height: 400,
    width: heatmapRef.value.clientWidth
  })

  // 取前20个结果
  const topResults = results.value.slice(0, 20)

  chart.setOption({
    tooltip: {
      position: 'top',
      formatter: (params: any) => {
        return `${params.mark}[0].params_str}<br/>目标值: ${params.mark}[0].data.toFixed(4)}`
      }
    },
    grid: {
      height: '50%',
      top: '10%'
    },
    xAxis: {
      type: 'category',
      data: topResults.map(r => `#${r.rank}`),
      axisLabel: { rotate: 45 }
    },
    yAxis: {
      type: 'category',
      data: topResults.map(r => `#${r.rank}`),
      position: 'right'
    },
    visualMap: {
      min: Math.min(...topResults.map(r => r.objective_value)),
      max: Math.max(...topResults.map(r => r.objective_value)),
      calculable: true,
      orient: 'horizontal',
      inRange: { color: '#313695' },
      outOfRange: { color: '#eee' }
    },
    series: [{
      type: 'heatmap',
      data: topResults.map((r, i) => ({
        value: [i, i],
        objective_value: r.objective_value
      })),
      label: {
        show: false
      }
    }]
  })
}

// 获取排名颜色
const getRankColor = (rank: number) => {
  if (rank === 1) return 'gold'
  if (rank === 2) return 'silver'
  if (rank === 3) return '#cd7f32'
  return 'default'
}

// 获取数值颜色
const getValueColor = (value: number) => {
  return value >= 0 ? '#52c41a' : '#f5222d'
}

// 重置配置
const resetConfig = () => {
  selectedStrategy.value = ''
  parameters.value = []
  results.value = []
  progress.value = 0
  bestObjectiveValue.value = 0
}

// 导出结果
const exportResults = () => {
  if (results.value.length === 0) {
    message.warning('没有可导出的结果')
    return
  }

  // TODO: 实现CSV导出
  message.info('导出优化结果...')
}

// 监听策略选择
import { watch } from 'vue'
watch(selectedStrategy, updateParameters)

onMounted(() => {
  updateParameters()
})
</script>

<style scoped>
.parameter-optimizer {
  padding: 16px;
}

.mb-3 {
  margin-bottom: 16px;
}

.mb-4 {
  margin-bottom: 24px;
}

.mt-2 {
  margin-top: 8px;
}

.mt-3 {
  margin-top: 12px;
}

.mt-4 {
  margin-top: 16px;
}

.ml-2 {
  margin-left: 8px;
}

.ml-4 {
  margin-left: 16px;
}

.params-config {
  background: #fafafa;
  padding: 16px;
  border-radius: 8px;
}

.action-buttons {
  margin-top: 24px;
  text-align: center;
}

.progress-detail {
  display: flex;
  justify-content: space-around;
}

.heatmap-section h4 {
  margin-bottom: 12px;
}

.heatmap-container {
  width: 100%;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
}
</style>
