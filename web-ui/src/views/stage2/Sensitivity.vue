<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        敏感性分析
      </h1>
      <p class="page-description">评估策略对参数变化的敏感程度。敏感性低说明参数选择更稳健，不易过拟合。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>分析配置</h3>
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
            <label class="form-label">分析参数</label>
            <input v-model="config.paramName" type="text" placeholder="如: max_position" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">参数值</label>
            <input v-model="config.paramValues" type="text" placeholder="0.1,0.2,0.3,0.4" class="form-input" />
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
        <h3>分析结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result" class="stats-grid-three">
          <div class="stat-card">
            <div class="stat-label">敏感性分数</div>
            <div class="stat-value">{{ result.sensitivity_score }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最优参数值</div>
            <div class="stat-value">{{ result.optimal_value }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">最优收益</div>
            <div class="stat-value">{{ (result.optimal_return * 100).toFixed(2) }}%</div>
          </div>
        </div>

        <div v-if="result.data_points && result.data_points.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>参数值</th>
                <th>收益率</th>
                <th>夏普比率</th>
                <th>最大回撤</th>
                <th>标记</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(record, i) in result.data_points" :key="`point-${i}`">
                <td>{{ record.param_value }}</td>
                <td>
                  <span :style="{ color: record.return >= 0 ? '#cf1322' : '#3f8600' }">
                    {{ (record.return * 100).toFixed(2) }}%
                  </span>
                </td>
                <td>{{ record.sharpe_ratio?.toFixed(2) || '-' }}</td>
                <td>{{ record.max_drawdown?.toFixed(2) || '-' }}</td>
                <td>
                  <span v-if="record.is_optimal" class="tag tag-green">最优</span>
                </td>
              </tr>
            </tbody>
          </table>
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

const config = reactive({ backtestId: '', paramName: '', paramValues: '' })

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    console.warn('请选择回测任务')
    return
  }
  if (!config.paramName) {
    console.warn('请输入参数名称')
    return
  }
  if (!config.paramValues.trim()) {
    console.warn('请输入参数值列表')
    return
  }

  loading.value = true
  try {
    // TODO: 调用 API 进行敏感性分析
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

.stats-grid-three {
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

  .stats-grid-three {
    grid-template-columns: 1fr;
  }
}
</style>
