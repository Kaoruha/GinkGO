<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        蒙特卡洛模拟
      </h1>
      <p class="page-description">基于历史收益统计特征随机模拟，评估策略风险分布和极端损失概率。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>模拟配置</h3>
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
            <label class="form-label">模拟次数</label>
            <input v-model.number="config.nSimulations" type="number" min="1000" max="100000" step="1000" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">置信水平</label>
            <select v-model.number="config.confidenceLevel" class="form-select">
              <option :value="0.9">90%</option>
              <option :value="0.95">95%</option>
              <option :value="0.99">99%</option>
            </select>
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runSimulation">
              {{ loading ? '模拟中...' : '开始模拟' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <template v-if="result">
      <!-- 主要统计 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">VaR</div>
          <div class="stat-value stat-danger">{{ (result.var * 100).toFixed(2) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">CVaR</div>
          <div class="stat-value stat-danger">{{ (result.cvar * 100).toFixed(2) }}%</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">期望收益</div>
          <div class="stat-value" :class="result.expected_return >= 0 ? 'stat-danger' : 'stat-success'">
            {{ (result.expected_return * 100).toFixed(2) }}%
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-label">损失概率</div>
          <div class="stat-value">{{ (result.loss_probability * 100).toFixed(2) }}%</div>
        </div>
      </div>

      <!-- 收益分布统计 -->
      <div class="card">
        <div class="card-header">
          <h3>收益分布统计</h3>
        </div>
        <div class="card-body">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">最大收益</div>
              <div class="stat-value stat-danger">{{ (result.max_return * 100).toFixed(2) }}%</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最小收益</div>
              <div class="stat-value stat-success">{{ (result.min_return * 100).toFixed(2) }}%</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">标准差</div>
              <div class="stat-value">{{ (result.std_dev * 100).toFixed(2) }}%</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">偏度</div>
              <div class="stat-value">{{ result.skewness?.toFixed(2) || '-' }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 空状态 -->
    <div v-else class="card">
      <div class="card-body">
        <div class="empty-state">
          <p>请配置参数并开始模拟</p>
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
  nSimulations: 10000,
  confidenceLevel: 0.95,
})

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runSimulation = async () => {
  if (!config.backtestId) {
    console.warn('请选择回测任务')
    return
  }

  loading.value = true
  try {
    // TODO: 调用 API 进行蒙特卡洛模拟
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('模拟完成')
  } catch {
    console.error('模拟失败')
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
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-description {
  margin: 0;
  color: #8a8a9a;
  font-size: 14px;
}

.tag {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
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
  min-width: 150px;
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
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
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

.stat-success {
  color: #52c41a;
}

.stat-danger {
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

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
