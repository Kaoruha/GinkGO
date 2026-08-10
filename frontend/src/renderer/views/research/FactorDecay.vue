<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">因子衰减</h1>
      <p class="page-description">测量因子信号随时间的有效性衰减。半衰期短需高频调仓，半衰期长可降低换手率。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>衰减分析配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select v-model="config.backtestId" class="form-select">
              <option value="">选择回测任务</option>
              <option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">{{ bt.task_id }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">最大周期</label>
            <input v-model.number="config.maxPeriod" type="number" min="5" max="60" class="form-input" />
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>IC 衰减结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">半衰期</div>
              <div class="stat-value">{{ result.half_life }} 天</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最优调仓周期</div>
              <div class="stat-value">{{ result.optimal_rebalance_freq }} 天</div>
            </div>
          </div>

          <div v-if="result.decay_series && result.decay_series.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>周期</th>
                  <th>IC</th>
                  <th>自相关</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.decay_series" :key="`decay-${i}`">
                  <td>{{ record.lag }}</td>
                  <td>{{ record.ic?.toFixed(4) || '-' }}</td>
                  <td>{{ record.autocorrelation?.toFixed(4) || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>请配置参数并开始分析</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)
const config = reactive({ backtestId: '', maxPeriod: 20 })

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    console.warn('请选择回测任务')
    return
  }
  loading.value = true
  try {
    // TODO: 调用 API 进行衰减分析
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('完成')
  } catch {
    console.error('失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.page-description {
  margin: 0;
  color: #8a8a9a;
  font-size: 14px;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
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

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
