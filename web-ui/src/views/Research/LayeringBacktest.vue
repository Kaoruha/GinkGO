<template>
  <div class="layering-backtest">
    <div class="card">
      <div class="card-header">
        <h3>因子分层回测</h3>
        <div class="header-actions">
          <select v-model="selectedFactor" class="form-select">
            <option value="">选择因子</option>
            <option v-for="f in factors" :key="f" :value="f">{{ f }}</option>
          </select>
          <select v-model="layerCount" class="form-select">
            <option :value="3">3层</option>
            <option :value="5">5层</option>
            <option :value="10">10层</option>
          </select>
          <input v-model="dateRangeText" type="text" placeholder="选择日期范围" class="form-input" />
          <button class="btn-primary" @click="runBacktest">开始回测</button>
        </div>
      </div>
      <div class="card-body">
        <div v-if="layerReturns.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th v-for="i in layerCount" :key="`group-${i}`">第{{ i }}组</th>
                <th>多空</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(record, idx) in layerReturns" :key="`return-${idx}`">
                <td>{{ record.date }}</td>
                <td v-for="i in layerCount" :key="`val-${idx}-${i}`">
                  <span :class="getClassForValue(record[`group${i}`])">
                    {{ formatPercent(record[`group${i}`]) }}
                  </span>
                </td>
                <td>
                  <span :class="getClassForValue(record.longShort)">
                    {{ formatPercent(record.longShort) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state">
          <p>请选择因子并开始回测</p>
        </div>

        <div v-if="layerReturns.length > 0" class="chart-section">
          <h4>各组收益对比</h4>
          <LayeringReturnChart :layer-data="chartData" height="350px" />
        </div>

        <div v-if="layerReturns.length > 0" class="stats-section">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">多空收益</div>
              <div class="stat-value">{{ longShortReturn }}%</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">单调性R²</div>
              <div class="stat-value">{{ monotonicityR2.toFixed(3) }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最大回撤</div>
              <div class="stat-value">{{ maxDrawdown.toFixed(2) }}%</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { LayeringReturnChart } from '@/components/charts/factor'
import { layeringBacktest } from '@/api/modules/research'

const factors = ref(['momentum', 'reversal', 'volatility'])
const selectedFactor = ref('')
const layerCount = ref(5)
const dateRangeText = ref('')
const loading = ref(false)

const layerReturns = ref<any[]>([])

const chartData = computed(() => {
  return layerReturns.value.map(d => {
    const returns: Record<string, number> = {}
    for (let i = 1; i <= layerCount.value; i++) {
      returns[`group${i}`] = d[`group${i}`] || 0
    }
    return {
      date: d.date,
      returns: { ...returns, long_short: d.longShort }
    }
  })
})

const longShortReturn = computed(() => {
  if (layerReturns.value.length === 0) return '0.00'
  const last = layerReturns.value[layerReturns.value.length - 1]
  return ((last.longShort || 0) * 100).toFixed(2)
})

const monotonicityR2 = ref(0)
const maxDrawdown = ref(0)

const formatPercent = (value: number) => {
  return (value * 100).toFixed(2) + '%'
}

const getClassForValue = (value: number) => {
  return value >= 0 ? 'text-danger' : 'text-success'
}

const runBacktest = async () => {
  if (!selectedFactor.value) {
    console.warn('请选择因子')
    return
  }

  loading.value = true
  try {
    const res = await layeringBacktest({
      factor_name: selectedFactor.value,
      n_groups: layerCount.value,
      start_date: undefined,
      end_date: undefined
    })

    // 转换结果为表格数据
    layerReturns.value = (res.data?.results || []).map(r => ({
      date: r.date,
      ...r.returns,
      longShort: r.long_short
    }))

    monotonicityR2.value = res.data?.statistics?.monotonicity_r2 || 0
    maxDrawdown.value = (res.data?.statistics?.max_drawdown || 0) * 100

    console.log('分层回测完成')
  } catch (e) {
    console.error('分层回测失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.layering-backtest {
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
  flex-wrap: wrap;
}

.card-body {
  padding: 20px;
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
  border-right: 1px solid #2a2a3e;
}

.data-table th:last-child,
.data-table td:last-child {
  border-right: none;
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

.text-success {
  color: #52c41a;
}

.text-danger {
  color: #f5222d;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

.chart-section {
  margin: 24px 0;
}

.chart-section h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.stats-section {
  margin-top: 16px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
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

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .form-select,
  .form-input {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
