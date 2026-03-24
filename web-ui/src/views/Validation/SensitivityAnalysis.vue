<template>
  <div class="sensitivity-analysis-container">
    <div class="page-header">
      <h1 class="page-title">参数敏感性分析</h1>
      <p class="page-subtitle">分析参数变化对策略表现的影响</p>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>分析配置</h3>
      </div>
      <div class="card-body">
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">选择策略</label>
            <select v-model="selectedStrategy" class="form-select">
              <option value="">选择策略</option>
              <option v-for="s in strategies" :key="s.uuid" :value="s.uuid">{{ s.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分析目标</label>
            <select v-model="analyzeTarget" class="form-select">
              <option value="sharpe">夏普比率</option>
              <option value="total_return">总收益</option>
              <option value="max_drawdown">最大回撤</option>
              <option value="win_rate">胜率</option>
            </select>
          </div>
        </div>

        <div class="section-divider">
          <h4>敏感性参数配置</h4>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">要分析的参数</label>
            <select v-model="sensitivityParam.name" class="form-select">
              <option v-for="p in parameterList" :key="p.name" :value="p.name">{{ p.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">最小值</label>
            <input v-model.number="rangeConfig.min" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">最大值</label>
            <input v-model.number="rangeConfig.max" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">步长</label>
            <input v-model.number="rangeConfig.step" type="number" step="0.001" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">测试点数</label>
            <input v-model.number="rangeConfig.points" type="number" min="5" max="100" class="form-input" />
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="analyzing" @click="runAnalysis">
              {{ analyzing ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div v-if="results.length > 0" class="card">
      <div class="card-header">
        <h3>分析结果</h3>
      </div>
      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>参数值</th>
                <th>目标值</th>
                <th>变化率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in results" :key="record.key">
                <td>{{ record.param_value }}</td>
                <td>
                  <span :class="getValueClass(record.target)">{{ record.target?.toFixed(4) }}</span>
                </td>
                <td>{{ record.change }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

const selectedStrategy = ref('')
const analyzeTarget = ref('sharpe')
const analyzing = ref(false)

const strategies = ref<any[]>([
  { uuid: '1', name: '双均线策略' },
  { uuid: '2', name: '动量策略' }
])

const parameterList = ref<any[]>([
  { name: 'short_period', label: '短周期' },
  { name: 'long_period', label: '长周期' },
  { name: 'stop_loss', label: '止损比例' }
])

const sensitivityParam = reactive({
  name: 'short_period',
  baseValue: 10
})

const rangeConfig = reactive({
  min: 5,
  max: 20,
  step: 1,
  points: 10
})

const results = ref<any[]>([])

const getValueClass = (value: number) => {
  if (value > 1) return 'value-up'
  if (value < 0.5) return 'value-down'
  return ''
}

const runAnalysis = async () => {
  if (!selectedStrategy.value) {
    console.warn('请选择策略')
    return
  }

  analyzing.value = true
  try {
    // 模拟分析结果
    results.value = []
    for (let i = rangeConfig.min; i <= rangeConfig.max; i += rangeConfig.step) {
      results.value.push({
        key: i,
        param_value: i,
        target: Math.random() * 2,
        change: (Math.random() * 20 - 10).toFixed(2) + '%'
      })
    }
    console.log('分析完成')
  } catch (error: any) {
    console.error('分析失败:', error)
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.sensitivity-analysis-container {
  padding: 24px;
  background: #0f0f1e;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
  color: #ffffff;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 24px;
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
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

.section-divider {
  margin: 20px 0 16px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #2a2a3e;
}

.section-divider h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
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
  align-self: flex-end;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
