<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">因子分层</h1>
      <p class="page-description">将股票按因子值分组，验证因子的选股效果。理想因子各组收益应单调递减，多空收益越高越好。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>分层配置</h3>
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
            <label class="form-label">分层数</label>
            <input v-model.number="config.nGroups" type="number" min="3" max="10" class="form-input" />
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
        <h3>分层结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">多空收益</div>
              <div class="stat-value" :class="result.long_short_return >= 0 ? 'stat-danger' : 'stat-success'">
                {{ ((result.long_short_return || 0) * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最佳组</div>
              <div class="stat-value">{{ result.best_group || '-' }}</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">最佳组收益</div>
              <div class="stat-value" :class="result.best_group_return >= 0 ? 'stat-danger' : 'stat-success'">
                {{ ((result.best_group_return || 0) * 100).toFixed(2) }}%
              </div>
            </div>
          </div>

          <div v-if="result.groups && result.groups.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>组别</th>
                  <th>收益</th>
                  <th>股票数</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.groups" :key="`group-${i}`">
                  <td>{{ record.layer }}</td>
                  <td>
                    <span :class="record.return_mean >= 0 ? 'text-danger' : 'text-success'">
                      {{ ((record.return_mean || 0) * 100).toFixed(2) }}%
                    </span>
                  </td>
                  <td>{{ record.count }}</td>
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
const config = reactive({ backtestId: '', nGroups: 5 })

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
    // TODO: 调用 API 进行因子分层分析
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

.stat-danger {
  color: #f5222d;
}

.text-success {
  color: #52c41a;
}

.text-danger {
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
