<template>
  <div class="monte-carlo">
    <div class="page-header">
      <h1 class="page-title">蒙特卡洛模拟</h1>
      <button class="btn-secondary" @click="$router.push('/portfolio')">选择策略</button>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>模拟配置</h3>
      </div>
      <div class="card-body">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">选择策略</label>
            <select v-model="selectedStrategy" class="form-select">
              <option value="">选择策略</option>
              <option v-for="s in strategies" :key="s.uuid" :value="s.uuid">{{ s.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分析目标</label>
            <select v-model="analyzeTarget" class="form-select">
              <option value="total_return">总收益分布</option>
              <option value="sharpe">夏普比率分布</option>
              <option value="drawdown">回撤分布</option>
            </select>
          </div>
        </div>

        <div class="section-divider">
          <h4>策略参数</h4>
        </div>

        <div class="params-display" v-if="fixedParams.length > 0">
          <div class="param-item" v-for="p in fixedParams" :key="p.name">
            <span class="param-label">{{ p.label }}:</span>
            <span class="param-value">{{ p.value }}</span>
          </div>
        </div>

        <div class="section-divider">
          <h4>蒙特卡洛配置</h4>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">历史收益率数据</label>
            <select v-model="returnDataSource" class="form-select">
              <option value="backtest">使用回测收益</option>
              <option value="manual">手动输入</option>
              <option value="historical">历史市场数据</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">模拟次数</label>
            <input v-model.number="nSimulations" type="number" min="100" max="100000" step="100" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">置信水平</label>
            <select v-model.number="confidenceLevel" class="form-select">
              <option :value="0.9">90%</option>
              <option :value="0.95">95%</option>
              <option :value="0.99">99%</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">随机种子</label>
            <input v-model.number="randomSeed" type="number" min="0" class="form-input" />
          </div>
        </div>

        <div v-if="returnDataSource === 'manual'" class="form-group" style="margin-top: 16px;">
          <label class="form-label">历史收益率（每行一个，用逗号或空格分隔）</label>
          <textarea v-model="manualReturns" rows="5" class="form-textarea" placeholder="例如: 0.02, -0.01, 0.03, 0.015, ..."></textarea>
        </div>

        <div class="action-buttons">
          <button class="btn-primary" :disabled="simulating" @click="startSimulation">
            {{ simulating ? '模拟中...' : '开始模拟' }}
          </button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
        </div>
      </div>
    </div>

    <!-- 进度卡片 -->
    <div v-if="simulating" class="card">
      <div class="card-header">
        <h3>模拟进度</h3>
      </div>
      <div class="card-body">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progress + '%' }"></div>
        </div>
        <div class="progress-detail">
          <div class="progress-stat">
            <span class="stat-label">已完成</span>
            <span class="stat-value">{{ completedSimulations }} / {{ nSimulations }}</span>
          </div>
          <div class="progress-stat">
            <span class="stat-label">预计剩余</span>
            <span class="stat-value">{{ estimatedTime }} 秒</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div v-if="results" class="card">
      <div class="card-header">
        <h3>蒙特卡洛模拟结果</h3>
        <div class="card-actions">
          <button class="btn-secondary" @click="exportResults">导出数据</button>
          <button class="btn-secondary" @click="generateReport">生成报告</button>
        </div>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">模拟次数</div>
            <div class="stat-value">{{ results.n_simulations }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">平均收益</div>
            <div class="stat-value">{{ results.mean.toFixed(4) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">标准差</div>
            <div class="stat-value">{{ results.std.toFixed(4) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">夏普比率</div>
            <div class="stat-value">{{ results.sharpe.toFixed(2) }}</div>
          </div>
        </div>

        <div class="section-divider">
          <h4>百分位数分布</h4>
        </div>

        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>置信度</th>
                <th>概率</th>
                <th>收益</th>
                <th>累计概率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in percentileData" :key="record.percentile">
                <td>{{ record.percentile }}%</td>
                <td style="color: #8a8a9a">{{ record.probability }}</td>
                <td>{{ record.value?.toFixed(2) }}%</td>
                <td>{{ record.cumulative ? (record.cumulative * 100).toFixed(1) + '%' : '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="section-divider">
          <h4>风险度量</h4>
        </div>

        <div class="risk-stats">
          <div class="risk-card">
            <div class="risk-title">VaR (Value at Risk)</div>
            <div class="risk-value">VaR {{ (confidenceLevel * 100) }}%</div>
            <div class="risk-number">{{ results.var.toFixed(2) }}%</div>
          </div>
          <div class="risk-card">
            <div class="risk-title">CVaR (Conditional VaR)</div>
            <div class="risk-value">CVaR {{ (confidenceLevel * 100) }}%</div>
            <div class="risk-number">{{ results.cvar.toFixed(2) }}%</div>
          </div>
          <div class="risk-card">
            <div class="risk-title">最大回撤期望</div>
            <div class="risk-value">期望</div>
            <div class="risk-number">{{ results.max_drawdown.toFixed(2) }}%</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

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
const completedSimulations = ref(0)
const estimatedTime = ref(0)

// 结果
const results = ref<any>(null)

// 百分位数据
const percentileData = computed(() => {
  if (!results.value) return []

  return [
    { percentile: 0, probability: '最低值', value: results.value.percentiles?.p0, cumulative: null },
    { percentile: 5, probability: '5%', value: results.value.percentiles?.p5, cumulative: 0.05 },
    { percentile: 10, probability: '10%', value: results.value.percentiles?.p10, cumulative: 0.10 },
    { percentile: 25, probability: '25%', value: results.value.percentiles?.p25, cumulative: 0.25 },
    { percentile: 50, probability: '50%', value: results.value.percentiles?.p50, cumulative: 0.50 },
    { percentile: 75, probability: '75%', value: results.value.percentiles?.p75, cumulative: 0.75 },
    { percentile: 90, probability: '90%', value: results.value.percentiles?.p90, cumulative: 0.90 },
    { percentile: 95, probability: '95%', value: results.value.percentiles?.p95, cumulative: 0.95 },
  ]
})

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
    console.warn('请先选择策略')
    return
  }

  if (returnDataSource.value === 'manual' && !manualReturns.value) {
    console.warn('请输入历史收益率数据')
    return
  }

  simulating.value = true
  progress.value = 0
  completedSimulations.value = 0

  try {
    // TODO: 调用API进行蒙特卡洛模拟
    await simulateMonteCarlo()
    console.log('蒙特卡洛模拟完成')
  } catch (e) {
    console.error('模拟失败')
  } finally {
    simulating.value = false
  }
}

// 模拟蒙特卡洛过程
const simulateMonteCarlo = async () => {
  const n = Math.min(nSimulations.value, 1000) // 限制模拟次数用于演示
  const batchSize = 100
  const batches = Math.ceil(n / batchSize)

  // 模拟结果
  const simulationResults = []
  for (let batch = 0; batch < batches; batch++) {
    for (let i = 0; i < batchSize && (batch * batchSize + i) < n; i++) {
      const annualReturn = Math.random() * 60 - 20 // -20% 到 40%
      simulationResults.push(annualReturn)

      completedSimulations.value = batch * batchSize + i + 1
      progress.value = Math.floor((completedSimulations.value / n) * 100)
      estimatedTime.value = Math.ceil((n - completedSimulations.value) / 10)

      await new Promise(resolve => setTimeout(resolve, 1))
    }
  }

  // 计算统计结果
  calculateStatistics(simulationResults)
}

// 计算统计结果
const calculateStatistics = (data: number[]) => {
  if (data.length === 0) return

  const mean = data.reduce((a, b) => a + b, 0) / data.length
  const variance = data.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / data.length
  const std = Math.sqrt(variance)
  const sharpe = mean / std * Math.sqrt(252)

  // 计算百分位数
  const sorted = [...data].sort((a, b) => a - b)

  results.value = {
    n_simulations: data.length,
    mean,
    std,
    sharpe,
    percentiles: {
      p0: sorted[0],
      p5: sorted[Math.floor(sorted.length * 0.05)],
      p10: sorted[Math.floor(sorted.length * 0.10)],
      p25: sorted[Math.floor(sorted.length * 0.25)],
      p50: sorted[Math.floor(sorted.length * 0.50)],
      p75: sorted[Math.floor(sorted.length * 0.75)],
      p90: sorted[Math.floor(sorted.length * 0.90)],
      p95: sorted[Math.floor(sorted.length * 0.95)],
    },
    var: sorted[Math.floor(sorted.length * (1 - confidenceLevel.value))],
    cvar: sorted.filter(v => v < sorted[Math.floor(sorted.length * 0.05)]).reduce((a, b) => a + b, 0) / data.length,
    max_drawdown: sorted[0]
  }
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
    console.warn('没有可导出的结果')
    return
  }
  console.log('导出蒙特卡洛模拟数据...')
}

// 生成报告
const generateReport = () => {
  if (!results.value) {
    console.warn('请先运行模拟')
    return
  }
  console.log('生成蒙特卡洛分析报告...')
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

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #ffffff;
}

.card-actions {
  display: flex;
  gap: 8px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.section-divider {
  margin: 20px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2a3e;
}

.section-divider h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
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
  font-size: 14px;
}

.param-value {
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 24px;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.progress-bar {
  height: 24px;
  background: #2a2a3e;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #1890ff, #52c41a);
  transition: width 0.3s ease;
}

.progress-detail {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.progress-stat {
  text-align: center;
}

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

.risk-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.risk-card {
  background: #2a2a3e;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.risk-title {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.risk-value {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.risk-number {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .risk-stats {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
