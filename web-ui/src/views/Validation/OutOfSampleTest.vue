<template>
  <div class="oos-test">
    <div class="card">
      <div class="card-header">
        <h4>样本外测试</h4>
        <button class="btn-secondary" @click="$router.push('/portfolio')">选择策略</button>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">验证方法</label>
            <select v-model="validationMethod" class="form-select">
              <option value="walk_forward">走步验证</option>
              <option value="rolling_window">滚动窗口</option>
              <option value="cross_validation">交叉验证</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">策略</label>
            <select v-model="selectedStrategy" class="form-select">
              <option value="">选择策略</option>
              <option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }}
              </option>
            </select>
          </div>
        </div>

        <!-- 走步验证配置 -->
        <div v-if="validationMethod === 'walk_forward'" class="config-section">
          <h4>走步验证配置</h4>
          <div class="config-grid">
            <div class="form-group">
              <label class="form-label">训练期长度（天）</label>
              <input v-model.number="walkForwardConfig.trainSize" type="number" :min="30" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">测试期长度（天）</label>
              <input v-model.number="walkForwardConfig.testSize" type="number" :min="10" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">步长（天）</label>
              <input v-model.number="walkForwardConfig.stepSize" type="number" :min="1" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">最小训练样本</label>
              <input v-model.number="walkForwardConfig.minTrainSamples" type="number" :min="50" class="form-input" />
            </div>
          </div>
        </div>

        <!-- 滚动窗口配置 -->
        <div v-if="validationMethod === 'rolling_window'" class="config-section">
          <h4>滚动窗口配置</h4>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">窗口大小: {{ rollingConfig.windowSize }}</label>
              <input v-model.number="rollingConfig.windowSize" type="range" :min="50" :max="500" class="slider-input" />
              <div class="slider-marks">
                <span>50</span>
                <span>252</span>
                <span>500</span>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">最小数据点</label>
              <input v-model.number="rollingConfig.minDataPoints" type="number" :min="20" class="form-input" />
            </div>
          </div>
        </div>

        <!-- 交叉验证配置 -->
        <div v-if="validationMethod === 'cross_validation'" class="config-section">
          <h4>交叉验证配置</h4>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">折数（K-Fold）</label>
              <select v-model="cvConfig.nFolds" class="form-select">
                <option :value="3">3折</option>
                <option :value="5">5折</option>
                <option :value="10">10折</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">数据范围</label>
              <div class="date-range-inputs">
                <input v-model="startDate" type="date" class="form-input" />
                <input v-model="endDate" type="date" class="form-input" />
              </div>
            </div>
          </div>
        </div>

        <div class="divider">参数设置</div>
        <div class="params-display">
          <div v-for="p in fixedParams" :key="p.name" class="param-item">
            <span class="param-label">{{ p.label }}</span>
            <span class="param-value">{{ formatParamValue(p.value) }}</span>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-primary" :disabled="testing" @click="startTest">
            {{ testing ? '测试中...' : '开始测试' }}
          </button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
        </div>
      </div>
    </div>

    <!-- 测试进度卡片 -->
    <div v-if="testing" class="card mt-4">
      <div class="card-header">
        <h4>测试进度</h4>
      </div>
      <div class="card-body">
        <div class="progress-bar">
          <div
            class="progress-fill"
            :class="getProgressStatus()"
            :style="{ width: testProgress + '%' }"
          ></div>
        </div>
        <div class="progress-info">
          <div class="stat-item">
            <span class="stat-label">当前窗口</span>
            <span class="stat-value">{{ currentWindow }} / {{ totalWindows }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">已完成</span>
            <span class="stat-value">{{ completedWindows }} 个窗口</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 测试结果卡片 -->
    <div v-if="results && results.length > 0" class="card mt-4">
      <div class="card-header">
        <h4>测试结果</h4>
        <div class="header-actions">
          <button class="btn-secondary" @click="exportReport">导出报告</button>
          <button class="btn-secondary" @click="plotResults">图表对比</button>
        </div>
      </div>
      <div class="card-body">
        <div class="alert" :class="`alert-${overfitStatus.type}`">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <span>{{ overfitStatus.message }}</span>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <h5>训练集统计</h5>
            <div class="stat-row">
              <span class="stat-label">平均收益</span>
              <span class="stat-value">{{ (summary.trainAvgReturn * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">夏普比率</span>
              <span class="stat-value">{{ summary.trainSharpe.toFixed(2) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">最大回撤</span>
              <span class="stat-value">{{ (summary.trainMaxDD * 100).toFixed(2) }}%</span>
            </div>
          </div>
          <div class="stat-card">
            <h5>测试集统计</h5>
            <div class="stat-row">
              <span class="stat-label">平均收益</span>
              <span class="stat-value">{{ (summary.valAvgReturn * 100).toFixed(2) }}%</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">夏普比率</span>
              <span class="stat-value">{{ summary.valSharpe.toFixed(2) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">最大回撤</span>
              <span class="stat-value">{{ (summary.valMaxDD * 100).toFixed(2) }}%</span>
            </div>
          </div>
        </div>

        <div class="stat-card">
          <h5>泛化能力分析</h5>
          <div class="degradation-grid">
            <div class="degradation-item">
              <span class="stat-label">性能退化</span>
              <span class="stat-value" :style="{ color: getDegradationColor(summary.performanceDegradation) }">
                {{ summary.performanceDegradation.toFixed(2) }}%
              </span>
            </div>
            <div class="degradation-item">
              <span class="stat-label">稳定性得分</span>
              <span class="stat-value" :style="{ color: getStabilityColor(summary.stabilityScore) }">
                {{ summary.stabilityScore.toFixed(2) }}
              </span>
            </div>
          </div>
          <div class="progress-bar mt-3">
            <div
              class="progress-fill"
              :style="{ width: (summary.stabilityScore * 20) + '%', backgroundColor: getStabilityColor(summary.stabilityScore) }"
            ></div>
          </div>
        </div>

        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>窗口</th>
                <th>训练期</th>
                <th>测试期</th>
                <th>训练收益%</th>
                <th>测试收益%</th>
                <th>收益差%</th>
                <th>过拟合</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in results" :key="record.window">
                <td>{{ record.window }}</td>
                <td>{{ record.train_period }}</td>
                <td>{{ record.val_period }}</td>
                <td :style="{ color: record.train_return >= 0 ? '#52c41a' : '#f5222d' }">
                  {{ (record.train_return * 100).toFixed(2) }}%
                </td>
                <td :style="{ color: record.val_return >= 0 ? '#52c41a' : '#f5222d' }">
                  {{ (record.val_return * 100).toFixed(2) }}%
                </td>
                <td>{{ record.return_diff }}</td>
                <td>
                  <span class="tag" :class="record.overfit ? 'tag-red' : 'tag-green'">
                    {{ record.overfit ? '是' : '否' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import dayjs from 'dayjs'

const router = useRouter()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 策略列表（模拟）
const strategies = ref([
  { uuid: 's1', name: '双均线策略' },
  { uuid: 's2', name: '动量轮动' },
])

const selectedStrategy = ref('')
const validationMethod = ref('walk_forward')
const startDate = ref('')
const endDate = ref('')

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
const fixedParams = ref<any[]>([
  { name: 'short_period', label: '短期均线', value: 5 },
  { name: 'long_period', label: '长期均线', value: 20 },
  { name: 'stop_loss', label: '止损比例', value: 0.05 },
])

// 测试状态
const testing = ref(false)
const testProgress = ref(0)
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

// 获取进度状态
const getProgressStatus = () => {
  if (testProgress.value >= 100) return 'progress-success'
  if (testProgress.value > 0) return 'progress-active'
  return ''
}

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
    showToast('请先选择策略', 'warning')
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

    showToast('测试完成')
  } catch {
    showToast('测试失败', 'error')
  } finally {
    testing.value = false
  }
}

// 走步验证
const runWalkForward = async () => {
  const { trainSize, testSize, stepSize } = walkForwardConfig.value

  // 计算窗口数
  const dataLength = 600
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
    trainSharpe: 0,
    trainMaxDD: Math.min(...trainReturns),
    valAvgReturn: valReturns.reduce((a, b) => a + b, 0) / valReturns.length,
    valSharpe: 0,
    valMaxDD: Math.min(...valReturns),
    performanceDegradation: ((valReturns.reduce((a, b) => a + b, 0) / valReturns.length) - (trainReturns.reduce((a, b) => a + b, 0) / trainReturns.length)) * 100,
    stabilityScore: 75
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
    showToast('没有可导出的结果', 'warning')
    return
  }
  showToast('导出验证报告...')
}

// 图表对比
const plotResults = () => {
  showToast('打开结果对比图表')
}
</script>

<style scoped>
.oos-test {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.btn-primary {
  padding: 10px 20px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
}

.form-input,
.form-select {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.config-section {
  background: #2a2a3e;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.config-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px 0;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

/* Slider */
.slider-input {
  -webkit-appearance: none;
  width: 100%;
  height: 6px;
  background: #3a3a4e;
  border-radius: 3px;
  outline: none;
}

.slider-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  background: #1890ff;
  border-radius: 50%;
  cursor: pointer;
}

.slider-input::-moz-range-thumb {
  width: 16px;
  height: 16px;
  background: #1890ff;
  border-radius: 50%;
  cursor: pointer;
  border: none;
}

.slider-marks {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #8a8a9a;
  margin-top: 4px;
}

.date-range-inputs {
  display: flex;
  gap: 8px;
}

.date-range-inputs .form-input {
  flex: 1;
}

.divider {
  display: flex;
  align-items: center;
  color: #8a8a9a;
  font-size: 14px;
  font-weight: 500;
  margin: 20px 0 16px;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #2a2a3e;
}

.divider::before {
  margin-right: 16px;
}

.divider::after {
  margin-left: 16px;
}

.params-display {
  background: #2a2a3e;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #3a3a4e;
}

.param-item:last-child {
  border-bottom: none;
}

.param-label {
  color: #8a8a9a;
  font-size: 13px;
}

.param-value {
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

/* Progress */
.progress-bar {
  height: 8px;
  background: #2a2a3e;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 0.3s ease;
}

.progress-fill.progress-active {
  background: #1890ff;
  animation: progress-pulse 1.5s ease-in-out infinite;
}

.progress-fill.progress-success {
  background: #52c41a;
}

@keyframes progress-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.progress-info {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

/* Alert */
.alert {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.alert-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid #52c41a;
  color: #52c41a;
}

.alert-warning {
  background: rgba(250, 173, 20, 0.1);
  border: 1px solid #faad14;
  color: #faad14;
}

.alert-error {
  background: rgba(245, 34, 45, 0.1);
  border: 1px solid #f5222d;
  color: #f5222d;
}

.alert-info {
  background: rgba(24, 144, 255, 0.1);
  border: 1px solid #1890ff;
  color: #1890ff;
}

.alert svg {
  flex-shrink: 0;
}

/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.stat-card h5 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #3a3a4e;
}

.stat-row:last-child {
  border-bottom: none;
}

.degradation-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.degradation-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Table */
.table-wrapper {
  overflow-x: auto;
  margin-top: 16px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tr:hover {
  background: #2a2a3e;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.mt-3 {
  margin-top: 12px;
}

.mt-4 {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .config-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .progress-info {
    flex-direction: column;
    gap: 16px;
  }
}
</style>
