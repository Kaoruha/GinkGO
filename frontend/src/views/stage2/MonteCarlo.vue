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
              <option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">{{ bt.task_id }}</option>
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

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
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
