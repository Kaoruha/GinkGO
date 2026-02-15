<template>
  <div class="oos-test">
    <a-card title="样本外测试">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择策略</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="验证方法">
            <a-select v-model:value="validationMethod">
              <a-select-option value="walk_forward">走步验证</a-select-option>
              <a-select-option value="rolling_window">滚动窗口</a-select-option>
              <a-select-option value="cross_validation">交叉验证</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="策略">
            <a-select v-model:value="selectedStrategy" placeholder="选择策略">
              <a-select-option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div v-if="validationMethod === 'walk_forward'" class="config-section">
        <h4>走步验证配置</h4>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="训练期长度（天）">
              <a-input-number v-model:value="walkForwardConfig.trainSize" :min="30" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="测试期长度（天）">
              <a-input-number v-model:value="walkForwardConfig.testSize" :min="10" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="步长（天）">
              <a-input-number v-model:value="walkForwardConfig.stepSize" :min="1" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="最小训练样本">
              <a-input-number v-model:value="walkForwardConfig.minTrainSamples" :min="50" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </div>

      <!-- Custom -->
      <div v-if="validationMethod === 'rolling_window'" class="config-section">
        <h4>滚动窗口配置</h4>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="窗口大小">
              <a-slider v-model:value="rollingConfig.windowSize" :min="50" :max="500" :marks="{ 100: '100', 252: '252', 500: '500' }" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="最小数据点">
              <a-input-number v-model:value="rollingConfig.minDataPoints" :min="20" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </div>

      <!-- Custom -->
      <div v-if="validationMethod === 'cross_validation'" class="config-section">
        <h4>交叉验证配置</h4>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="折数（K-Fold）">
              <a-select v-model:value="cvConfig.nFolds">
                <a-select-option :value="3">3折</a-select-option>
                <a-select-option :value="5">5折</a-select-option>
                <a-select-option :value="10">10折</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="数据范围">
              <a-range-picker v-model:value="dateRange" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </div>

      <!-- Custom -->
      <a-divider>参数设置</a-divider>
      <div class="params-display">
        <a-descriptions bordered :column="1">
          <a-descriptions-item v-for="p in fixedParams" :key="p.name" :label="p.label">
            {{ formatParamValue(p.value) }}
          </a-descriptions-item>
        </a-descriptions>
      </div>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="testing" @click="startTest">
            开始测试
          </a-button>
          <a-button @click="resetConfig">重置</a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="testing" title="测试进度" class="mt-4">
      <a-progress :percent="testProgress" :status="testStatus" />
      <div class="progress-info mt-3">
        <a-statistic title="当前窗口" :value="currentWindow" suffix="/ {{ totalWindows }}" />
        <a-statistic title="已完成" :value="completedWindows" suffix="个窗口" class="ml-4" />
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="results" title="测试结果" class="mt-4">
      <template #extra>
        <a-space>
          <a-button @click="exportReport">导出报告</a-button>
          <a-button @click="plotResults">图表对比</a-button>
        </a-space>
      </template>

      <!-- Custom -->
      <a-alert
        :type="overfitStatus.type"
        :message="overfitStatus.message"
        show-icon
        class="mb-4"
      />

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-card title="训练集统计" size="small">
            <a-statistic title="平均收益" :value="summary.trainAvgReturn" suffix="%" :precision="2" />
            <a-statistic title="夏普比率" :value="summary.trainSharpe" :precision="2" class="mt-2" />
            <a-statistic title="最大回撤" :value="summary.trainMaxDD" suffix="%" :precision="2" class="mt-2" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="测试集统计" size="small">
            <a-statistic title="平均收益" :value="summary.valAvgReturn" suffix="%" :precision="2" />
            <a-statistic title="夏普比率" :value="summary.valSharpe" :precision="2" class="mt-2" />
            <a-statistic title="最大回撤" :value="summary.valMaxDD" suffix="%" :precision="2" class="mt-2" />
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-card title="泛化能力分析" size="small" class="mb-4">
        <div class="degradation-info">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-statistic
                title="性能退化"
                :value="summary.performanceDegradation"
                suffix="%"
                :value-style="{ color: getDegradationColor(summary.performanceDegradation) }"
                :precision="2"
              />
            </a-col>
            <a-col :span="12">
              <a-statistic
                title="稳定性得分"
                :value="summary.stabilityScore"
                :precision="2"
                :value-style="{ color: getStabilityColor(summary.stabilityScore) }"
              />
            </a-col>
          </a-row>
          <div class="mt-3">
            <a-progress
              :percent="summary.stabilityScore * 20"
              :stroke-color="getStabilityColor(summary.stabilityScore)"
            />
          </div>
        </div>
      </a-card>

      <!-- Custom -->
      <a-table
        :columns="resultColumns"
        :data-source="results"
        :pagination="{ pageSize: 20 }"
        :scroll="{ y: 400 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <span v-if="column.dataIndex === 'train_return'" :style="{ color: record.train_return >= 0 ? '#52c41a' : '#f5222d' }">
            {{ (record.train_return * 100).toFixed(2) }}%
          </span>
          <span v-if="column.dataIndex === 'val_return'" :style="{ color: record.val_return >= 0 ? '#52c41a' : '#f5222d' }">
            {{ (record.val_return * 100).toFixed(2) }}%
          </span>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import { outOfSampleTest } from '@/api/modules/validation'
import dayjs from 'dayjs'

const router = useRouter()

// 策略列表（模拟）
const strategies = ref([
  { uuid: 's1', name: '双均线策略' },
  { uuid: 's2', name: '动量轮动' },
])

const selectedStrategy = ref('')
const validationMethod = ref('walk_forward')
const dateRange = ref<any[]>([])

// 走步验证配置
const walkForwardConfig = ref({
  trainSize: 252,
  testSize: 63,
  stepSize: 21,
  minTrainSamples: 100
})

// 滚动窗口配置
const rollingConfig = ref({
  windowSize: 252,
  minDataPoints: 50
})

// 交叉验证配置
const cvConfig = ref({
  nFolds: 5
})

// 固定参数（根据策略获取）
const fixedParams = ref<any[]>([])

// 测试状态
const testing = ref(false)
const testProgress = ref(0)
const testStatus = ref<'normal' | 'active' | 'success'>('normal')
const currentWindow = ref(0)
const totalWindows = ref(0)
const completedWindows = ref(0)

// 测试结果
const results = ref<any[]>([])

// 统计摘要
const summary = ref({
  trainAvgReturn: 0,
  trainSharpe: 0,
  trainMaxDD: 0,
  valAvgReturn: 0,
  valSharpe: 0,
  valMaxDD: 0,
  performanceDegradation: 0,
  stabilityScore: 0
})

// 结果表格列
const resultColumns = [
  { title: '窗口', dataIndex: 'window', width: 80, fixed: 'left' },
  { title: '训练期', dataIndex: 'train_period', width: 150 },
  { title: '测试期', dataIndex: 'val_period', width: 150 },
  { title: '训练收益%', dataIndex: 'train_return', width: 100 },
  { title: '测试收益%', dataIndex: 'val_return', width: 100 },
  { title: '收益差%', dataIndex: 'return_diff', width: 100 },
  { title: '过拟合', dataIndex: 'overfit', width: 80 }
]

// 过拟合状态
const overfitStatus = computed(() => {
  const deg = summary.value.performanceDegradation
  if (deg < -10) {
    return { type: 'error', message: '⚠️ 严重过拟合：测试性能严重退化' }
  } else if (deg < -5) {
    return { type: 'warning', message: '⚠️ 轻度过拟合：测试性能有所下降' }
  } else if (deg < 0) {
    return { type: 'info', message: 'ℹ️ 正常性能衰减' }
  } else {
    return { type: 'success', message: '✅ 泛化能力良好：测试性能接近或优于训练集' }
  }
})

// 获取退化颜色
const getDegradationColor = (value: number) => {
  if (value < -10) return '#f5222d'
  if (value < -5) return '#faad14'
  if (value < 0) return '#52c41a'
  return '#13ce66'
}

// 获取稳定性颜色
const getStabilityColor = (value: number) => {
  if (value >= 80) return '#52c41a'
  if (value >= 60) return '#1890ff'
  if (value >= 40) return '#faad14'
  return '#f5222d'
}

// 格式化参数值
const formatParamValue = (value: any) => {
  if (typeof value === 'number') return value.toFixed(4)
  return value
}

// 开始测试
const startTest = async () => {
  if (!selectedStrategy.value) {
    message.warning('请先选择策略')
    return
  }

  testing.value = true
  testProgress.value = 0
  results.value = []

  try {
    if (validationMethod.value === 'walk_forward') {
      await runWalkForward()
    } else if (validationMethod.value === 'cross_validation') {
      await runCrossValidation()
    } else {
      await runRollingWindow()
    }

    message.success('测试完成')
  } catch (e) {
    message.error('测试失败')
  } finally {
    testing.value = false
  }
}

// 走步验证
const runWalkForward = async () => {
  const { trainSize, testSize, stepSize } = walkForwardConfig.value

  // 计算窗口数
  const dataLength = dateRange.value[1] ? dayjs(dateRange.value[1]).diff(dayjs(dateRange.value[0]), 'day') : 600
  totalWindows.value = Math.floor((dataLength - trainSize) / stepSize)

  // 模拟运行
  for (let i = 0; i < totalWindows.value; i++) {
    const trainStart = i * stepSize
    const trainEnd = trainStart + trainSize
    const valStart = trainEnd
    const valEnd = valStart + testSize

    completedWindows.value = i + 1
    currentWindow.value = i + 1
    testProgress.value = Math.floor(((i + 1) / totalWindows.value) * 100)

    // 模拟结果
    const trainReturn = Math.random() * 0.3 - 0.05
    const valReturn = trainReturn - Math.random() * 0.15

    results.value.push({
      window: i + 1,
      train_period: `${dayjs().add(trainStart, 'day').format('YYYY-MM-DD')} ~ ${dayjs().add(trainEnd, 'day').format('YYYY-MM-DD')}`,
      val_period: `${dayjs().add(valStart, 'day').format('YYYY-MM-DD')} ~ ${dayjs().add(valEnd, 'day').format('YYYY-MM-DD')}`,
      train_return: trainReturn,
      val_return: valReturn,
      return_diff: ((valReturn - trainReturn) * 100).toFixed(2),
      overfit: valReturn < trainReturn - 0.05
    })

    await new Promise(resolve => setTimeout(resolve, 100))
  }

  // 计算统计
  calculateSummary()
}

// 交叉验证
const runCrossValidation = async () => {
  // 模拟K折验证
  totalWindows.value = cvConfig.value.nFolds

  for (let i = 0; i < cvConfig.value.nFolds; i++) {
    const trainReturn = Math.random() * 0.3 - 0.05
    const valReturn = trainReturn - Math.random() * 0.1

    completedWindows.value = i + 1
    currentWindow.value = i + 1
    testProgress.value = Math.floor(((i + 1) / cvConfig.value.nFolds) * 100)

    results.value.push({
      window: `Fold ${i + 1}`,
      train_period: `训练集 ${i + 1}`,
      val_period: `验证集 ${i + 1}`,
      train_return: trainReturn,
      val_return: valReturn,
      return_diff: ((valReturn - trainReturn) * 100).toFixed(2),
      overfit: valReturn < trainReturn - 0.05
    })

    await new Promise(resolve => setTimeout(resolve, 300))
  }

  calculateSummary()
}

// 滚动窗口
const runRollingWindow = async () => {
  const windows = Math.floor(500 / rollingConfig.value.windowSize)
  totalWindows.value = windows

  for (let i = 0; i < windows; i++) {
    const trainReturn = Math.random() * 0.25 - 0.03
    const valReturn = trainReturn - Math.random() * 0.08

    completedWindows.value = i + 1
    currentWindow.value = i + 1
    testProgress.value = Math.floor(((i + 1) / windows) * 100)

    results.value.push({
      window: i + 1,
      train_period: `窗口 ${i + 1}`,
      val_period: `测试 ${i + 1}`,
      train_return: trainReturn,
      val_return: valReturn,
      return_diff: ((valReturn - trainReturn) * 100).toFixed(2),
      overfit: valReturn < trainReturn - 0.03
    })

    await new Promise(resolve => setTimeout(resolve, 200))
  }

  calculateSummary()
}

// 计算统计摘要
const calculateSummary = () => {
  const trainReturns = results.value.map(r => r.train_return)
  const valReturns = results.value.map(r => r.val_return)

  summary.value = {
    trainAvgReturn: trainReturns.reduce((a, b) => a + b, 0) / trainReturns.length,
    trainSharpe: 0, // 简化计算
    trainMaxDD: Math.min(...trainReturns),
    valAvgReturn: valReturns.reduce((a, b) => a + b, 0) / valReturns.length,
    valSharpe: 0,
    valMaxDD: Math.min(...valReturns),
    performanceDegradation: ((valReturns.reduce((a, b) => a + b, 0) / valReturns.length) - (trainReturns.reduce((a, b) => a + b, 0) / trainReturns.length)) * 100,
    stabilityScore: 75 // 模拟值
  }
}

// 重置配置
const resetConfig = () => {
  results.value = []
  testProgress.value = 0
  summary.value = {
    trainAvgReturn: 0,
    trainSharpe: 0,
    trainMaxDD: 0,
    valAvgReturn: 0,
    valSharpe: 0,
    valMaxDD: 0,
    performanceDegradation: 0,
    stabilityScore: 0
  }
}

// 导出报告
const exportReport = () => {
  if (results.value.length === 0) {
    message.warning('没有可导出的结果')
    return
  }
  message.info('导出验证报告...')
}

// 图表对比
const plotResults = () => {
  message.info('打开结果对比图表')
}
</script>

<style scoped>
.oos-test {
  padding: 16px;
}

.mb-4 {
  margin-bottom: 16px;
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

.ml-4 {
  margin-left: 16px;
}

.config-section {
  background: #fafafa;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.config-section h4 {
  margin-bottom: 12px;
  color: #333;
}

.params-display {
  background: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
}

.action-buttons {
  text-align: center;
  margin-top: 24px;
}

.progress-info {
  display: flex;
  justify-content: center;
}

.degradation-info {
  padding: 16px;
}
</style>
