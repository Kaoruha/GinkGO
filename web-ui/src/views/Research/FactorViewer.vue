<template>
  <div class="factor-viewer">
    <div class="card">
      <div class="card-header">
        <h3>因子查看器</h3>
        <div class="header-actions">
          <select v-model="selectedFactor" class="form-select">
            <option value="">选择因子</option>
            <option v-for="f in factors" :key="f.name" :value="f.name">
              {{ f.label }}
            </option>
          </select>
          <button class="btn-primary" @click="loadFactorData">加载</button>
        </div>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">均值</div>
            <div class="stat-value">{{ stats.mean }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">标准差</div>
            <div class="stat-value">{{ stats.std }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">偏度</div>
            <div class="stat-value">{{ stats.skew }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">峰度</div>
            <div class="stat-value">{{ stats.kurt }}</div>
          </div>
        </div>

        <div class="chart-section">
          <h4>因子分布</h4>
          <div ref="distRef" class="distribution-chart"></div>
        </div>

        <div v-if="factorData.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>股票代码</th>
                <th>因子值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in factorData" :key="`data-${i}`">
                <td>{{ d.date }}</td>
                <td>{{ d.code }}</td>
                <td>{{ d.value }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as echarts from 'echarts'
import { getFactorList, queryFactorData } from '@/api/modules/research'
import type { FactorList, FactorValue } from '@/api/modules/research'

const factors = ref<FactorList[]>([])
const selectedFactor = ref('')
const factorData = ref<FactorValue[]>([])
const distRef = ref<HTMLDivElement>()

const stats = computed(() => {
  if (factorData.value.length === 0) return { mean: '-', std: '-', skew: '-', kurt: '-' }
  const values = factorData.value.map(d => d.value)
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length
  const std = Math.sqrt(variance)
  return { mean: mean.toFixed(4), std: std.toFixed(4), skew: '-', kurt: '-' }
})

// 加载因子列表
const loadFactors = async () => {
  try {
    const res = await getFactorList()
    factors.value = res.data || []
  } catch (e) {
    console.error('加载因子列表失败')
  }
}

// 加载因子数据
const loadFactorData = async () => {
  if (!selectedFactor.value) {
    console.warn('请先选择因子')
    return
  }
  try {
    const res = await queryFactorData({
      factor_name: selectedFactor.value,
      limit: 100
    })
    factorData.value = res.data || []
  } catch (e) {
    console.error('加载因子数据失败')
  }
}

onMounted(() => {
  loadFactors()
})
</script>

<style scoped>
.factor-viewer {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.card-body {
  padding: 20px;
}

.form-select {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-select:focus {
  outline: none;
  border-color: #1890ff;
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

.chart-section {
  margin-top: 24px;
  margin-bottom: 20px;
}

.chart-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.distribution-chart {
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
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .header-actions {
    width: 100%;
  }

  .form-select {
    flex: 1;
  }
}
</style>
