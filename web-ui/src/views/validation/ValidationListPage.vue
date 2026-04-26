<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">策略验证</h1>
      <p class="page-description">基于回测结果的策略有效性验证</p>
    </div>

    <!-- 新建验证 -->
    <div class="card">
      <div class="card-header"><h3>新建验证</h3></div>
      <div class="card-body">
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
          <div class="form-group">
            <label class="form-label">验证方法</label>
            <select v-model="config.method" class="form-select">
              <option value="segment_stability">分段稳定性</option>
              <option value="monte_carlo">蒙特卡洛</option>
            </select>
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="!config.taskId || running" @click="runValidation">
              {{ running ? '计算中...' : '开始验证' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 验证结果 -->
    <div v-if="newResult" class="card">
      <div class="card-header"><h3>验证结果</h3></div>
      <div class="card-body">
        <div v-if="config.method === 'segment_stability'" class="stats-grid">
          <div class="stat-card" v-for="w in newResult.windows" :key="w.n_segments">
            <div class="stat-value">{{ w.n_segments }} 段</div>
            <div class="stat-label">稳定性评分</div>
            <div class="stat-value" :class="w.stability_score >= 0.7 ? 'text-green' : w.stability_score >= 0.4 ? 'text-yellow' : 'text-red'">
              {{ (w.stability_score * 100).toFixed(1) }}%
            </div>
          </div>
        </div>
        <div v-else-if="config.method === 'monte_carlo'" class="stats-grid">
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
      </div>
    </div>

    <!-- 历史记录 -->
    <div class="card">
      <div class="card-header">
        <h3>验证记录</h3>
        <select v-model="methodFilter" class="form-select" style="width: auto;">
          <option value="">全部方法</option>
          <option value="segment_stability">分段稳定性</option>
          <option value="monte_carlo">蒙特卡洛</option>
        </select>
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

const backtestList = ref<any[]>([])
const records = ref<any[]>([])
const newResult = ref<any>(null)
const running = ref(false)
const methodFilter = ref('')

const config = reactive({
  taskId: '',
  method: 'segment_stability',
})

const methodLabel = (m: string) => {
  const map: Record<string, string> = {
    segment_stability: '分段稳定性',
    monte_carlo: '蒙特卡洛',
  }
  return map[m] || m
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
    if (config.method === 'segment_stability') {
      res = await validationApi.segmentStability({
        task_id: config.taskId,
        portfolio_id: portfolioId,
      })
    } else if (config.method === 'monte_carlo') {
      res = await validationApi.monteCarlo({
        backtest_id: config.taskId,
        n_simulations: 10000,
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
.text-green { color: #22c55e; }
.text-red { color: #ef4444; }
.text-yellow { color: #eab308; }
</style>
