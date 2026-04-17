<template>
  <div class="parameter-optimizer">
    <div class="card">
      <div class="card-header">
        <h4>参数优化</h4>
        <button class="btn-secondary" @click="$router.push('/portfolio')">选择策略</button>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">选择策略</label>
            <select v-model="selectedStrategy" class="form-select">
              <option value="">选择要优化的策略</option>
              <option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }} - {{ s.strategy_type }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">优化目标</label>
            <select v-model="optimizeTarget" class="form-select">
              <option value="sharpe">夏普比率</option>
              <option value="total_return">总收益</option>
              <option value="max_drawdown">最大回撤</option>
              <option value="calmar">卡玛比率</option>
            </select>
          </div>
        </div>

        <div class="divider">参数范围配置</div>
        <div class="params-config">
          <div v-for="(param, index) in parameters" :key="param.name" class="param-row">
            <div class="form-group">
              <label class="form-label">{{ param.label }} 最小值</label>
              <input v-model.number="param.min" type="number" step="any" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">{{ param.label }} 最大值</label>
              <input v-model.number="param.max" type="number" step="any" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">步长</label>
              <input v-model.number="param.step" type="number" :min="0.001" step="any" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">类型</label>
              <select v-model="param.type" class="form-select">
                <option value="int">整数</option>
                <option value="float">浮点数</option>
                <option value="categorical">分类</option>
              </select>
            </div>
          </div>
        </div>

        <div class="divider">优化方法</div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">优化算法</label>
            <select v-model="optimizeMethod" class="form-select">
              <option value="grid">网格搜索</option>
              <option value="genetic">遗传算法</option>
              <option value="bayesian">贝叶斯优化</option>
              <option value="random">随机搜索</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">最大迭代次数</label>
            <input v-model.number="maxIterations" type="number" :min="10" :max="1000" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">并行任务数</label>
            <input v-model.number="nJobs" type="number" :min="1" :max="10" class="form-input" />
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">训练数据范围</label>
            <div class="date-range-inputs">
              <input v-model="trainStartDate" type="date" class="form-input" />
              <input v-model="trainEndDate" type="date" class="form-input" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">验证数据范围</label>
            <div class="date-range-inputs">
              <input v-model="valStartDate" type="date" class="form-input" />
              <input v-model="valEndDate" type="date" class="form-input" />
            </div>
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-primary" :disabled="optimizing" @click="startOptimization">
            {{ optimizing ? '优化中...' : '开始优化' }}
          </button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
        </div>
      </div>
    </div>

    <!-- 优化进度卡片 -->
    <div v-if="optimizing" class="card mt-4">
      <div class="card-header">
        <h4>优化进度</h4>
      </div>
      <div class="card-body">
        <div class="progress-wrapper">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :class="getProgressStatus()"
              :style="{ width: progress + '%' }"
            ></div>
          </div>
          <div class="progress-text">
            <span>{{ progress }}%</span>
            <span class="ml-2">{{ progressText }}</span>
          </div>
        </div>
        <div class="progress-detail">
          <div class="stat-item">
            <span class="stat-label">已完成</span>
            <span class="stat-value">{{ completedIterations }} / {{ maxIterations }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">最优目标值</span>
            <span class="stat-value">{{ bestObjectiveValue.toFixed(4) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">剩余时间</span>
            <span class="stat-value">{{ estimatedTime }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 优化结果卡片 -->
    <div v-if="results && results.length > 0" class="card mt-4">
      <div class="card-header">
        <h4>优化结果</h4>
        <button class="btn-secondary" @click="exportResults">导出结果</button>
      </div>
      <div class="card-body">
        <div class="alert alert-success">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <div class="alert-content">
            <div class="alert-title">最优参数组合</div>
            <div class="best-value">{{ optimizeTarget.toUpperCase() }} = {{ bestObjectiveValue.toFixed(4) }}</div>
          </div>
        </div>

        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>参数组合</th>
                <th>训练集{{ optimizeTarget.toUpperCase() }}</th>
                <th>验证集{{ optimizeTarget.toUpperCase() }}</th>
                <th>过拟合检测</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in results" :key="record.rank">
                <td>
                  <span class="tag" :class="getRankClass(record.rank)">
                    #{{ record.rank }}
                  </span>
                </td>
                <td>{{ record.params_str }}</td>
                <td>{{ record.train_value?.toFixed(4) }}</td>
                <td>{{ record.val_value?.toFixed(4) }}</td>
                <td>
                  <span class="tag" :class="record.overfit === '正常' ? 'tag-green' : 'tag-orange'">
                    {{ record.overfit }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="heatmap-section">
          <h4>参数空间热力图</h4>
          <div ref="heatmapRef" class="heatmap-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'

const router = useRouter()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

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
const trainStartDate = ref('')
const trainEndDate = ref('')
const valStartDate = ref('')
const valEndDate = ref('')

// 参数配置（根据策略动态生成）
const parameters = ref<any[]>([])

// 优化状态
const optimizing = ref(false)
const progress = ref(0)
const progressText = ref('')
const completedIterations = ref(0)
const bestObjectiveValue = ref(0)
const estimatedTime = ref('0分钟')

// 优化结果
const results = ref<any[]>([])
const heatmapRef = ref<HTMLDivElement>()

// 计算属性
const bestResult = computed(() => {
  return results.value.length > 0 ? results.value[0] : null
})

// 获取进度状态
const getProgressStatus = () => {
  if (progress.value >= 100) return 'progress-success'
  if (progress.value > 0) return 'progress-active'
  return ''
}

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

  // 通过策略名称获取参数
  const strategy = strategies.value.find(s => s.uuid === selectedStrategy.value)
  if (strategy) {
    parameters.value = paramMap[strategy.strategy_type] || []
  }
}

// 开始优化
const startOptimization = async () => {
  if (!selectedStrategy.value) {
    showToast('请先选择策略', 'warning')
    return
  }

  optimizing.value = true
  progress.value = 0
  completedIterations.value = 0
  results.value = []

  try {
    await simulateOptimization()
    showToast('优化完成')
    renderHeatmap()
  } catch {
    showToast('优化失败', 'error')
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
        return `${params.data[2]}<br/>目标值: ${(params.data[2] || 0).toFixed(4)}`
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
      inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8'] },
    },
    series: [{
      type: 'heatmap',
      data: topResults.map((r, i) => [i, i, r.objective_value]),
      label: {
        show: false
      }
    }]
  })
}

// 获取排名颜色类
const getRankClass = (rank: number) => {
  if (rank === 1) return 'tag-gold'
  if (rank === 2) return 'tag-silver'
  if (rank === 3) return 'tag-bronze'
  return 'tag-gray'
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
    showToast('没有可导出的结果', 'warning')
    return
  }
  showToast('导出优化结果...')
}

// 监听策略选择
watch(selectedStrategy, updateParameters)

onMounted(() => {
  updateParameters()
})
</script>

<style scoped>
.parameter-optimizer {
  padding: 16px;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
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

.params-config {
  background: #2a2a3e;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.param-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

/* 进度条 */
.progress-wrapper {
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: #2a2a3e;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
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

.progress-text {
  display: flex;
  align-items: center;
  font-size: 14px;
  color: #ffffff;
}

.ml-2 {
  margin-left: 8px;
}

.progress-detail {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* Alert */
.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.alert-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid #52c41a;
}

.alert svg {
  flex-shrink: 0;
  color: #52c41a;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 4px;
}

.best-value {
  font-size: 16px;
  font-weight: 600;
  color: #52c41a;
}

/* 表格 */
.table-wrapper {
  overflow-x: auto;
  margin-bottom: 20px;
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

.tag-silver {
  background: rgba(192, 192, 192, 0.2);
  color: #c0c0c0;
}

.tag-bronze {
  background: rgba(205, 127, 50, 0.2);
  color: #cd7f32;
}

/* 热力图 */
.heatmap-section {
  margin-top: 20px;
}

.heatmap-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px 0;
}

.heatmap-container {
  width: 100%;
  height: 400px;
  background: #2a2a3e;
  border-radius: 8px;
}

.mt-4 {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .param-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .progress-detail {
    flex-direction: column;
    gap: 16px;
  }
}
</style>
