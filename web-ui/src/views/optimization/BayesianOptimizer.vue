<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">贝叶斯优化</h1>
      <p class="page-description">基于概率模型的智能搜索，利用已有结果推断下一组参数。计算效率最高。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>优化配置</h3>
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
            <label class="form-label">迭代次数</label>
            <input v-model.number="config.nIterations" type="number" min="10" max="200" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">初始点数</label>
            <input v-model.number="config.nInitial" type="number" min="3" max="20" class="form-input" />
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runOptimization">
              {{ loading ? '优化中...' : '开始优化' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>优化结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">总迭代</div>
              <div class="stat-value">{{ result.total_iterations }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最佳收益</div>
              <div class="stat-value" :class="result.best_value >= 0 ? 'stat-danger' : 'stat-success'">
                {{ (result.best_value * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最优参数</div>
              <div class="stat-value stat-small">{{ result.best_params }}</div>
            </div>
          </div>

          <div v-if="result.history && result.history.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>迭代</th>
                  <th>参数</th>
                  <th>目标值</th>
                  <th>不确定性</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.history" :key="`iter-${i}`">
                  <td>{{ record.iteration }}</td>
                  <td>{{ record.params }}</td>
                  <td>{{ record.score?.toFixed(4) || '-' }}</td>
                  <td>{{ record.uncertainty?.toFixed(4) || '-' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>请配置参数并开始优化</p>
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
const config = reactive({ strategyId: '', nIterations: 50, nInitial: 5 })

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
    // TODO: 调用 API 进行贝叶斯优化
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

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
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
  flex-wrap: wrap;
  align-items: flex-end;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  word-break: break-all;
}

.stat-small {
  font-size: 14px;
}

.stat-success {
  color: #52c41a;
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
