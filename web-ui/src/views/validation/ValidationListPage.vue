<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">策略验证</h1>
      <p class="page-description">基于回测结果的策略有效性验证</p>
    </div>

    <!-- Tab 切换 -->
    <div class="card">
      <div class="card-header">
        <div class="tab-bar">
          <button
            v-for="m in methods"
            :key="m.key"
            class="tab-btn"
            :class="{ active: activeMethod === m.key }"
            @click="activeMethod = m.key"
          >{{ m.label }}</button>
        </div>
      </div>
      <div class="card-body">
        <!-- 参数区 -->
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select v-model="config.taskId" class="form-select">
              <option value="">选择已完成回测</option>
              <option v-for="t in backtestList" :key="t.uuid" :value="t.uuid">
                {{ t.name || t.uuid?.slice(0, 8) }} ({{ t.status }})
              </option>
            </select>
          </div>
          <div class="form-group" v-if="activeMethod === 'monte_carlo'">
            <label class="form-label">模拟次数</label>
            <input v-model.number="mcSims" type="number" class="form-input" min="1000" step="1000" />
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="!config.taskId || running" @click="runValidation">
              {{ running ? '计算中...' : '开始验证' }}
            </button>
          </div>
        </div>

        <!-- 结果区 -->
        <div v-if="newResult" class="result-section">
          <!-- 分段稳定性 -->
          <template v-if="activeMethod === 'segment_stability'">
            <h4 class="result-title">分段稳定性结果</h4>
            <div class="stats-grid">
              <div class="stat-card" v-for="w in newResult.windows" :key="w.n_segments">
                <div class="stat-value">{{ w.n_segments }} 段</div>
                <div class="stat-label">稳定性评分</div>
                <div class="stat-value" :class="w.stability_score >= 0.7 ? 'text-green' : w.stability_score >= 0.4 ? 'text-yellow' : 'text-red'">
                  {{ (w.stability_score * 100).toFixed(1) }}%
                </div>
              </div>
            </div>
          </template>
          <!-- 蒙特卡洛 -->
          <template v-if="activeMethod === 'monte_carlo'">
            <h4 class="result-title">蒙特卡洛模拟结果</h4>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-label">VaR 95%</div>
                <div class="stat-value text-red">{{ (newResult.statistics.var_95 * 100).toFixed(2) }}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">VaR 99%</div>
                <div class="stat-value text-red">{{ (newResult.statistics.var_99 * 100).toFixed(2) }}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">期望损失 (ES)</div>
                <div class="stat-value text-red">{{ (newResult.statistics.expected_shortfall * 100).toFixed(2) }}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">均值收益</div>
                <div class="stat-value">{{ (newResult.statistics.mean_return * 100).toFixed(2) }}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">收益标准差</div>
                <div class="stat-value">{{ (newResult.statistics.std_return * 100).toFixed(2) }}%</div>
              </div>
              <div class="stat-card">
                <div class="stat-label">P50 收益</div>
                <div class="stat-value">{{ (newResult.percentiles.p50 * 100).toFixed(2) }}%</div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 历史记录 -->
    <div class="card">
      <div class="card-header">
        <h3>验证记录</h3>
        <div class="tab-bar compact">
          <button
            class="tab-btn sm"
            :class="{ active: methodFilter === '' }"
            @click="methodFilter = ''"
          >全部</button>
          <button
            v-for="m in methods"
            :key="m.key"
            class="tab-btn sm"
            :class="{ active: methodFilter === m.key }"
            @click="methodFilter = m.key"
          >{{ m.label }}</button>
        </div>
      </div>
      <div class="card-body">
        <table v-if="records.length" class="data-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>方法</th>
              <th>任务</th>
              <th>评分</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.uuid">
              <td>{{ formatTime(r.create_at) }}</td>
              <td>{{ methodLabel(r.method) }}</td>
              <td style="font-family: monospace; font-size: 12px; color: #8a8a9a;">{{ r.task_id?.slice(0, 8) }}</td>
              <td>{{ r.score != null ? (r.score * 100).toFixed(1) + '%' : '-' }}</td>
              <td>{{ r.status === 1 ? '完成' : r.status === 0 ? '运行中' : '失败' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="empty-state">暂无验证记录</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { validationApi } from '@/api/modules/validation'
import { backtestApi } from '@/api/modules/backtest'

const methods = [
  { key: 'segment_stability', label: '分段稳定性' },
  { key: 'monte_carlo', label: '蒙特卡洛' },
]

const backtestList = ref<any[]>([])
const records = ref<any[]>([])
const newResult = ref<any>(null)
const running = ref(false)
const activeMethod = ref('segment_stability')
const methodFilter = ref('')
const mcSims = ref(10000)

const config = reactive({
  taskId: '',
})

const methodLabel = (m: string) => {
  return methods.find(x => x.key === m)?.label || m
}

const formatTime = (t: string) => {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

const fetchBacktestList = async () => {
  try {
    const res = await backtestApi.list({ page: 1, size: 100, status: 'completed' })
    backtestList.value = res.data || []
  } catch { /* ignore */ }
}

const fetchRecords = async () => {
  try {
    const params: any = { page: 1, page_size: 50 }
    if (methodFilter.value) params.method = methodFilter.value
    const res = await validationApi.listResults(params)
    records.value = res.data || []
  } catch { /* ignore */ }
}

const runValidation = async () => {
  if (!config.taskId) return
  running.value = true
  newResult.value = null
  try {
    const task = backtestList.value.find(t => t.uuid === config.taskId)
    const portfolioId = task?.portfolio_id || ''
    let res: any
    if (activeMethod.value === 'segment_stability') {
      res = await validationApi.segmentStability({
        task_id: config.taskId,
        portfolio_id: portfolioId,
      })
    } else if (activeMethod.value === 'monte_carlo') {
      res = await validationApi.monteCarlo({
        backtest_id: config.taskId,
        n_simulations: mcSims.value,
      })
    }
    newResult.value = res
    fetchRecords()
  } catch (e: any) {
    alert('验证失败: ' + (e.message || e))
  } finally {
    running.value = false
  }
}

watch(methodFilter, () => fetchRecords())

onMounted(() => {
  fetchBacktestList()
  fetchRecords()
})
</script>

<style scoped>
.tab-bar {
  display: flex;
  gap: 4px;
}
.tab-bar.compact { gap: 2px; }

.tab-btn {
  padding: 8px 20px;
  background: transparent;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  color: #8a8a9a;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.tab-btn:hover { color: #fff; border-color: #3a3a4e; }
.tab-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}
.tab-btn.sm {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 4px;
}

.result-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #2a2a3e;
}
.result-title {
  margin: 0 0 12px;
  color: #fff;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.stat-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}
.stat-value { font-size: 18px; font-weight: 600; color: #fff; }
.stat-label { font-size: 12px; color: #8a8a9a; margin-top: 4px; }

.text-green { color: #22c55e; }
.text-red { color: #ef4444; }
.text-yellow { color: #eab308; }
</style>
