<template>
  <div class="factor-comparison">
    <div class="card">
      <div class="card-header">
        <h4>因子对比</h4>
        <div class="header-actions">
          <div class="multi-select">
            <label v-for="f in allFactors" :key="f" class="checkbox-label">
              <input v-model="selectedFactors" type="checkbox" :value="f" />
              {{ f }}
            </label>
          </div>
          <div class="date-range">
            <input v-model="startDate" type="date" class="form-input" />
            <input v-model="endDate" type="date" class="form-input" />
          </div>
          <button class="btn-primary" @click="compare">对比</button>
        </div>
      </div>

      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>因子</th>
                <th>IC均值</th>
                <th>ICIR</th>
                <th>t统计量</th>
                <th>正IC占比</th>
                <th>综合评分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in comparisonData" :key="record.factor">
                <td>{{ record.factor }}</td>
                <td :class="{ 'best-value': record.isBest }">{{ record.icMean }}</td>
                <td :class="{ 'best-value': record.isBest }">{{ record.icir }}</td>
                <td :class="{ 'best-value': record.isBest }">{{ record.tStat }}</td>
                <td :class="{ 'best-value': record.isBest }">{{ record.posRatio }}</td>
                <td :class="{ 'best-value': record.isBest }">{{ record.score }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="chart-section">
          <h4>IC对比</h4>
          <ICIRChart :ic-data="icChartData" height="280px" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ICIRChart } from '@/components/charts/factor'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const allFactors = ref(['momentum', 'reversal', 'volatility', 'liquidity', 'size', 'value'])
const selectedFactors = ref<string[]>([])
const startDate = ref('')
const endDate = ref('')

const comparisonData = ref<any[]>([])
const icChartData = ref<any[]>([])

const compare = async () => {
  if (selectedFactors.value.length < 2) {
    showToast('请至少选择2个因子', 'error')
    return
  }
  // TODO: 调用因子对比API
  showToast('进行因子对比...')
}
</script>

<style scoped>
.factor-comparison {
  padding: 16px;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 300px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #1890ff;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.date-range {
  display: flex;
  gap: 8px;
}

.table-wrapper {
  overflow-x: auto;
  margin-bottom: 24px;
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

.best-value {
  color: #52c41a;
  font-weight: 600;
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

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .multi-select {
    max-width: none;
  }

  .date-range {
    flex-direction: column;
  }
}
</style>
