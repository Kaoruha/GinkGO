<template>
  <div class="factor-turnover">
    <div class="card">
      <div class="card-header">
        <h3>因子换手率分析</h3>
        <button class="btn-secondary" @click="$router.push('/portfolio')">选择因子</button>
      </div>
      <div class="card-body">
        <!-- 配置区域 -->
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">选择因子</label>
            <select v-model="selectedFactor" class="form-select">
              <option value="">选择要分析的因子</option>
              <option v-for="f in factors" :key="f.name" :value="f.name">
                {{ f.label }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">基准指数</label>
            <select v-model="benchmarkIndex" class="form-select">
              <option :value="0">沪深300</option>
              <option :value="1">中证500</option>
              <option :value="2">中证800</option>
              <option :value="3">中证1000</option>
            </select>
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">再平衡频率（天）</label>
            <input v-model.number="rebalanceFreq" type="number" min="1" max="60" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">分析周期</label>
            <input v-model="dateRangeText" type="text" placeholder="选择日期范围" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">换手率计算方式</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="calcMethod" value="count" />
                计数法
              </label>
              <label class="radio-label">
                <input type="radio" v-model="calcMethod" value="amount" />
                金额法
              </label>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button class="btn-primary" :disabled="analyzing" @click="startAnalysis">
            {{ analyzing ? '分析中...' : '开始分析' }}
          </button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div v-if="results.length > 0" class="card">
      <div class="card-header">
        <h3>换手率统计</h3>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">平均换手率</div>
            <div class="stat-value">{{ avgTurnover.toFixed(2) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最大换手率</div>
            <div class="stat-value">{{ maxTurnover.toFixed(2) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最小换手率</div>
            <div class="stat-value">{{ minTurnover.toFixed(2) }}%</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">换手率标准差</div>
            <div class="stat-value">{{ stdTurnover.toFixed(2) }}</div>
          </div>
        </div>

        <div class="chart-section">
          <h4>换手率时序图</h4>
          <div ref="turnoverChartRef" class="chart-container"></div>
        </div>

        <div class="distribution-section">
          <h4>换手率分布直方图</h4>
          <div ref="distributionRef" class="chart-container"></div>
        </div>

        <div v-if="detailData.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>组合市值</th>
                <th>换出金额</th>
                <th>换入金额</th>
                <th>换手率%</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(record, i) in detailData" :key="`detail-${i}`">
                <td>{{ record.date }}</td>
                <td>{{ record.portfolio_value }}</td>
                <td>{{ record.turnover_amount }}</td>
                <td>{{ record.turnover_in }}</td>
                <td>{{ record.turnover_rate }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
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
const dateRangeText = ref('')
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

const detailData = computed(() => {
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
    console.warn('请先选择因子')
    return
  }

  analyzing.value = true

  try {
    await simulateAnalysis()
    console.log('换手率分析完成')
  } catch (e) {
    console.error('分析失败')
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

    avgTurnover.value = results.value.reduce((a, b) => a + b.turnover_rate, 0) / results.value.length
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

  const chart = echarts.init(turnoverChartRef.value)

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

  const chart = echarts.init(distributionRef.value)

  const bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 5.0]

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: bins
    },
    yAxis: {
      type: 'value',
      name: '次数'
    },
    series: [{
      type: 'bar',
      data: bins.map(bin => {
        const value = results.value.filter(r => {
          const lower = bin * 0.1
          const upper = (bin + 1) * 0.1
          return r.turnover_rate >= lower && r.turnover_rate < upper
        }).length
        return value
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

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 200px;
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
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.radio-group {
  display: flex;
  gap: 16px;
  align-items: center;
  height: 100%;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.btn-primary {
  padding: 8px 16px;
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: #2a2a3e;
  border-radius: 6px;
  padding: 16px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.chart-section,
.distribution-section {
  margin-bottom: 20px;
}

.chart-section h4,
.distribution-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.table-wrapper {
  overflow-x: auto;
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

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
