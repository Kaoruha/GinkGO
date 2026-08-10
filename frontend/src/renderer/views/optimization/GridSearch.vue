<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">网格搜索</h1>
      <p class="page-description">穷举所有参数组合，保证找到全局最优。适合2-3个参数，计算量较大。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>搜索配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">策略选择</label>
            <select v-model="config.strategyId" class="form-select">
              <option value="">选择策略</option>
              <option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">参数配置 (JSON)</label>
            <input v-model="config.params" type="text" placeholder='{"param1": [1, 2, 3]}' class="form-input" style="width: 300px" />
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runOptimization">
              {{ loading ? '搜索中...' : '开始搜索' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>搜索结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">总组合数</div>
              <div class="stat-value">{{ result.total_combinations }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最佳收益</div>
              <div class="stat-value" :class="result.best_return >= 0 ? 'stat-danger' : 'stat-success'">
                {{ (result.best_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最佳参数</div>
              <div class="stat-value stat-small">{{ result.best_params }}</div>
            </div>
          </div>

          <div v-if="result.top_results && result.top_results.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>排名</th>
                  <th>参数</th>
                  <th>收益</th>
                  <th>夏普比率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.top_results" :key="`result-${i}`">
                  <td>{{ record.rank }}</td>
                  <td>{{ record.params }}</td>
                  <td>{{ (record.total_return * 100).toFixed(2) }}%</td>
                  <td>{{ record.sharpe_ratio?.toFixed(2) || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>请配置参数并开始搜索</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<any>(null)
const config = reactive({ strategyId: '', params: '' })

const fetchStrategyList = async () => {
  // TODO: 调用 API 获取策略列表
  strategyList.value = []
}

const runOptimization = async () => {
  if (!config.strategyId) {
    console.warn('请选择策略')
    return
  }
  loading.value = true
  try {
    // TODO: 调用 API 进行网格搜索
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('完成')
  } catch {
    console.error('失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStrategyList()
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

.stat-small {
  font-size: 14px;
}

.stat-danger {
  color: #f5222d;
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
