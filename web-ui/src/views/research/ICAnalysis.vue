<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">IC 分析</h1>
      <p class="page-description">评估因子对未来收益的预测能力。IC均值>0.05为强因子，ICIR>0.5为优秀因子。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>因子配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select v-model="config.backtestId" class="form-select">
              <option value="">选择回测任务</option>
              <option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">收益周期</label>
            <select v-model.number="config.returnPeriod" class="form-select">
              <option :value="1">1日</option>
              <option :value="5">5日</option>
              <option :value="10">10日</option>
              <option :value="20">20日</option>
            </select>
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
        <h3>IC 统计结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">IC 均值</div>
              <div class="stat-value">{{ result.ic_mean?.toFixed(4) || '-' }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">IC 标准差</div>
              <div class="stat-value">{{ result.ic_std?.toFixed(4) || '-' }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">ICIR</div>
              <div class="stat-value">{{ result.icir?.toFixed(4) || '-' }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">IC > 0 比例</div>
              <div class="stat-value">{{ ((result.ic_positive_ratio || 0) * 100).toFixed(2) }}%</div>
            </div>
          </div>

          <div v-if="result.ic_series && result.ic_series.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>IC</th>
                  <th>Rank IC</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.ic_series" :key="`ic-${i}`">
                  <td>{{ record.date }}</td>
                  <td>{{ record.ic?.toFixed(4) || '-' }}</td>
                  <td>{{ record.rank_ic?.toFixed(4) || '-' }}</td>
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

const config = reactive({
  backtestId: '',
  returnPeriod: 5,
})

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
    // TODO: 调用 API 进行 IC 分析
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('分析完成')
  } catch {
    console.error('分析失败')
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
