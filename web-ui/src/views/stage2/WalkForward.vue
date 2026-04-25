<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        走步验证
      </h1>
      <p class="page-description">时间序列交叉验证，评估策略样本外表现。退化程度大说明过拟合风险高。</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>验证配置</h3>
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
            <label class="form-label">折数</label>
            <input v-model.number="config.nFolds" type="number" min="2" max="10" class="form-input" style="width: 80px" />
          </div>
          <div class="form-group">
            <label class="form-label">训练期比例: {{ config.trainRatio }}</label>
            <input v-model.number="config.trainRatio" type="range" min="0.5" max="0.9" step="0.1" class="form-slider" />
          </div>
          <div class="form-group">
            <label class="form-label">窗口类型</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="config.windowType" value="expanding" />
                <span>扩展窗口</span>
              </label>
              <label class="radio-label">
                <input type="radio" v-model="config.windowType" value="rolling" />
                <span>滚动窗口</span>
              </label>
            </div>
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runValidation">
              {{ loading ? '验证中...' : '开始验证' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>验证结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">平均训练收益</div>
              <div class="stat-value" :class="{ 'stat-danger': result.avg_train_return >= 0, 'stat-success': result.avg_train_return < 0 }">
                {{ (result.avg_train_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">平均测试收益</div>
              <div class="stat-value" :class="{ 'stat-danger': result.avg_test_return >= 0, 'stat-success': result.avg_test_return < 0 }">
                {{ (result.avg_test_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">退化程度</div>
              <div class="stat-value" :class="{ 'stat-danger': result.degradation >= 0, 'stat-success': result.degradation < 0 }">
                {{ (result.degradation * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">稳定性评分</div>
              <div class="stat-value">{{ result.stability_score?.toFixed(2) || '-' }}</div>
            </div>
          </div>

          <div v-if="result.folds && result.folds.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Fold</th>
                  <th>训练开始</th>
                  <th>训练结束</th>
                  <th>测试开始</th>
                  <th>测试结束</th>
                  <th>训练收益</th>
                  <th>测试收益</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(record, i) in result.folds" :key="`fold-${i}`">
                  <td>{{ record.fold }}</td>
                  <td>{{ record.train_start }}</td>
                  <td>{{ record.train_end }}</td>
                  <td>{{ record.test_start }}</td>
                  <td>{{ record.test_end }}</td>
                  <td>
                    <span :class="record.train_return >= 0 ? 'text-danger' : 'text-success'">
                      {{ (record.train_return * 100).toFixed(2) }}%
                    </span>
                  </td>
                  <td>
                    <span :class="record.test_return >= 0 ? 'text-danger' : 'text-success'">
                      {{ (record.test_return * 100).toFixed(2) }}%
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>请配置参数并开始验证</p>
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
  nFolds: 5,
  trainRatio: 0.7,
  windowType: 'expanding' as 'expanding' | 'rolling',
})

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runValidation = async () => {
  if (!config.backtestId) {
    console.warn('请选择回测任务')
    return
  }

  loading.value = true
  try {
    // TODO: 调用 API 进行走步验证
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('验证完成')
  } catch {
    console.error('验证失败')
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

.form-slider {
  width: 150px;
  accent-color: #1890ff;
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
}

.radio-label input[type="radio"] {
  accent-color: #1890ff;
  cursor: pointer;
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
