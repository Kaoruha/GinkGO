<template>
  <div class="factor-decay">
    <div class="card">
      <div class="card-header">
        <h4>因子衰减分析</h4>
        <button class="btn-secondary" @click="$router.push('/portfolio')">选择因子</button>
      </div>

      <div class="card-body">
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
            <label class="form-label">最大滞后期</label>
            <input v-model.number="maxLag" type="number" min="1" max="60" class="form-input" />
          </div>
        </div>

        <div class="action-buttons">
          <button class="btn-primary" :disabled="analyzing" @click="startAnalysis">
            {{ analyzing ? '分析中...' : '开始分析' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="decayData.length > 0" class="card mt-4">
      <div class="card-header">
        <h4>衰减曲线</h4>
      </div>
      <div class="card-body">
        <div ref="decayChartRef" class="chart-container"></div>
      </div>
    </div>

    <div v-if="halfLife" class="card mt-4">
      <div class="card-header">
        <h4>半衰期</h4>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ halfLife }}</span>
            <span class="stat-label">半衰期（天）</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ bestLag }}</span>
            <span class="stat-label">最佳滞后期</span>
          </div>
        </div>
      </div>
    </div>

    <div class="card mt-4">
      <div class="card-header">
        <h4>各期IC值</h4>
      </div>
      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>滞后期(天)</th>
                <th>IC</th>
                <th>|IC|</th>
                <th>t统计量</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in lagData" :key="record.lag">
                <td>{{ record.lag }}</td>
                <td :style="{ color: record.ic > 0 ? '#52c41a' : '#f5222d' }">
                  {{ record.ic.toFixed(3) }}
                </td>
                <td>{{ record.abs_ic?.toFixed(3) }}</td>
                <td>{{ record.t_stat?.toFixed(3) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { analyzeDecay } from '@/api/modules/research'

const router = useRouter()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 监听衰减数据变化，自动渲染图表
watch(() => decayData.value.length, async (newLen) => {
  if (newLen > 0) {
    await nextTick()
    renderChart()
  }
})

const factors = ref([
  { name: 'momentum', label: '动量因子' },
  { name: 'reversal', label: '反转因子' },
  { name: 'volatility', label: '波动率因子' },
])

const selectedFactor = ref('')
const maxLag = ref(20)
const analyzing = ref(false)
const decayData = ref<any[]>([])
const halfLife = ref(0)
const bestLag = ref(0)
const decayChartRef = ref<HTMLDivElement>()

// 滞后数据
const lagData = ref<any[]>([])

// 开始分析
const startAnalysis = async () => {
  if (!selectedFactor.value) {
    showToast('请先选择因子', 'error')
    return
  }

  analyzing.value = true
  decayData.value = []
  lagData.value = []

  try {
    // TODO: 调用衰减分析API
    // const res = await analyzeDecay({
    //   factor_name: selectedFactor.value,
    //   max_lag: maxLag.value
    // })

    // 模拟数据
    for (let lag = 1; lag <= maxLag.value; lag++) {
      const ic = Math.random() * 0.15 - 0.08
      const tStat = ic / (0.15 / Math.sqrt(100))

      decayData.value.push({
        lag: lag,
        ic: ic,
        t_stat: tStat
      })

      if (lag <= maxLag.value / 2) {
        halfLife.value = lag
        bestLag.value = lag
      }

      lagData.value.push({
        lag: lag,
        ic: ic,
        abs_ic: Math.abs(ic),
        t_stat: tStat
      })
    }

    // 计算半衰期（IC值降到最大值的一半时的滞后期）
    const maxIC = Math.max(...decayData.value.map(d => d.ic))
    const halfLifeData = decayData.value.find(d => Math.abs(d.ic) < maxIC * 0.5)
    halfLife.value = halfLifeData?.lag || maxLag.value

    // 找到最佳滞后期（IC绝对值最大的滞后期）
    const bestICData = decayData.value.reduce((best, curr) =>
      Math.abs(curr.ic) > Math.abs(best.ic) ? curr : best
    )
    bestLag.value = bestICData.lag

    showToast('衰减分析完成')
  } catch (e) {
    showToast('衰减分析失败', 'error')
  } finally {
    analyzing.value = false
  }
}

// 渲染衰减曲线
const renderChart = () => {
  if (!decayChartRef.value || decayData.value.length === 0) return

  const chart = echarts.init(decayChartRef.value, {
    height: 350,
    width: decayChartRef.value.clientWidth
  })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `滞后期: ${params.mark[0].lag}天<br/>IC: ${params.mark[0].ic.toFixed(3)}<br/>t统计: ${params.mark[1].toFixed(2)}`
    },
    xAxis: {
      type: 'category',
      data: decayData.value.map(d => d.lag),
      name: '滞后期(天)',
      axisLabel: {
        formatter: (v: string) => v + '天'
      }
    },
    yAxis: {
      type: 'value',
      name: 'IC值',
      axisLabel: {
        formatter: (v: string) => parseFloat(v).toFixed(2)
      }
    },
    series: [{
      type: 'line',
      data: decayData.value.map(d => d.ic),
      smooth: true,
      markLine: {
        data: [{ value: 0 }],
        lineStyle: { color: '#8a8a9a', type: 'dashed' }
      }
    }],
    visualMap: {
      min: -0.15,
      max: 0.15,
      calculable: true,
      inRange: { color: '#52c41a' },
      outOfRange: { color: '#f5222d' }
    }
  })
}
</script>

<style scoped>
.factor-decay {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 24px;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
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
  padding: 10px 12px;
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

.action-buttons {
  display: flex;
  justify-content: center;
  padding: 16px 0;
}

.chart-container {
  height: 350px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.stat-card {
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
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
  border: 1px solid #2a2a3e;
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

.mt-4 {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
