<template>
  <div class="page-container">
    <div class="page-header-section">
      <h1 class="page-title">因子正交化</h1>
      <p class="page-description">消除多因子之间的相关性，避免信息重复。正交化后因子相互独立，组合效果更好。</p>
    </div>

    <div class="card config-card">
      <div class="card-header">
        <h4>正交化配置</h4>
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
            <label class="form-label">正交化方法</label>
            <select v-model="config.method" class="form-select">
              <option value="gram_schmidt">Gram-Schmidt</option>
              <option value="pca">PCA</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">&nbsp;</label>
            <button class="btn-primary" :disabled="loading" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="card result-card">
      <div class="card-header">
        <h4>相关性矩阵对比</h4>
      </div>
      <div class="card-body">
        <div v-if="result" class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ result.original_avg_corr?.toFixed(4) || '-' }}</span>
            <span class="stat-label">原始平均相关系数</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ result.orthogonal_avg_corr?.toFixed(4) || '-' }}</span>
            <span class="stat-label">正交后平均相关系数</span>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <circle cx="8.5" cy="8.5" r="1.5"></circle>
            <path d="M21 15l-5-5L5 21"></path>
          </svg>
          <p>请先选择回测任务并开始分析</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 简化的API调用（实际项目中需要导入真实的API）
const backtestApi: any = {
  list: async (params: any) => ({ data: [] })
}
const researchApi: any = {
  orthogonalize: async (params: any) => ({ data: null })
}

interface FactorOrthogonalizeResult {
  original_avg_corr: number
  orthogonal_avg_corr: number
}

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorOrthogonalizeResult | null>(null)
const config = reactive({ backtestId: '', method: 'gram_schmidt' as 'gram_schmidt' | 'pca' | 'residual' })

const fetchBacktestList = async () => {
  try {
    backtestList.value = (await backtestApi.list({ size: 20 })).data || []
  } catch {
    // 静默失败
  }
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    showToast('请选择回测任务', 'warning')
    return
  }

  loading.value = true
  try {
    result.value = await researchApi.orthogonalize({
      backtest_id: config.backtestId,
      factors: [],
      method: config.method
    })
    showToast('完成')
  } catch {
    showToast('失败', 'error')
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
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header-section {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.page-description {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 16px;
}

.config-card {
  margin-bottom: 16px;
}

.result-card {
  margin-bottom: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
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
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: flex-end;
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

.form-select {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  min-width: 150px;
  cursor: pointer;
}

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
  white-space: nowrap;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .form-select,
  .btn-primary {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
