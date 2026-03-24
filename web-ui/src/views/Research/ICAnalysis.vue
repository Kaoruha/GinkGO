<template>
  <div class="ic-analysis">
    <div class="card">
      <div class="card-header">
        <h4>因子IC分析</h4>
        <div class="header-actions">
          <select v-model="selectedFactor" class="form-select">
            <option value="">选择因子</option>
            <option v-for="f in factors" :key="f" :value="f">{{ f }}</option>
          </select>
          <div class="date-range">
            <input v-model="startDate" type="date" class="form-input" />
            <input v-model="endDate" type="date" class="form-input" />
          </div>
          <button class="btn-primary" @click="runAnalysis">分析</button>
        </div>
      </div>

      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ icStats.mean.toFixed(3) }}</span>
            <span class="stat-label">IC均值</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ icStats.std.toFixed(3) }}</span>
            <span class="stat-label">IC标准差</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ icStats.icir.toFixed(3) }}</span>
            <span class="stat-label">ICIR</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ icStats.tStat.toFixed(3) }}</span>
            <span class="stat-label">t统计量</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ icStats.posRatio.toFixed(1) }}%</span>
            <span class="stat-label">正IC占比</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ icStats.absMean.toFixed(3) }}</span>
            <span class="stat-label">绝对IC均值</span>
          </div>
        </div>

        <div class="chart-section">
          <h4>IC时序图</h4>
          <ICIRChart :ic-data="icData" height="300px" />
        </div>

        <div class="chart-section">
          <h4>IC分布</h4>
          <div ref="histRef" class="histogram-chart"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ICIRChart } from '@/components/charts/factor'
import { analyzeIC } from '@/api/modules/research'
import type { ICDataPoint } from '@/api/modules/research'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const factors = ref(['momentum', 'reversal', 'volatility', 'liquidity'])
const selectedFactor = ref('')
const startDate = ref('')
const endDate = ref('')
const histRef = ref<HTMLDivElement>()
const loading = ref(false)

const icStats = ref({
  mean: 0,
  std: 0,
  icir: 0,
  tStat: 0,
  posRatio: 0,
  absMean: 0
})

const icData = ref<ICDataPoint[]>([])

const runAnalysis = async () => {
  if (!selectedFactor.value) {
    showToast('请选择因子', 'error')
    return
  }

  loading.value = true
  try {
    const res = await analyzeIC({
      factor_name: selectedFactor.value,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      periods: [1, 5, 10, 20]
    })

    icData.value = res.data?.timeseries || []
    icStats.value = res.data?.statistics || icStats.value
    showToast('IC分析完成')
  } catch (e) {
    showToast('IC分析失败', 'error')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ic-analysis {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  flex-wrap: wrap;
  gap: 16px;
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

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.form-select,
.form-input {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.date-range {
  display: flex;
  gap: 8px;
}

.btn-primary {
  padding: 6px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 8px;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #8a8a9a;
}

.chart-section {
  margin-top: 24px;
}

.chart-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.histogram-chart {
  height: 250px;
  background: #2a2a3e;
  border-radius: 8px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .date-range {
    flex-direction: column;
  }
}
</style>
