<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-green">验证</span>
        分段稳定性
      </h1>
      <p class="page-description">将回测区间等分为多段，对比各段表现是否一致</p>
    </div>

    <div class="card">
      <div class="card-header"><h3>分析配置</h3></div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select class="form-select" v-model="config.taskId">
              <option value="">请选择任务</option>
              <option v-for="t in backtestList" :key="t.uuid" :value="t.uuid">
                {{ t.name || t.uuid?.slice(0, 8) }} ({{ t.status }})
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分段数</label>
            <input class="form-input" v-model="segmentsInput" placeholder="2, 4, 8" />
          </div>
          <div class="form-group" style="align-self: flex-end;">
            <button class="btn-primary" :disabled="loading || !config.taskId" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <template v-if="result">
      <div class="stats-grid">
        <div class="stat-card" v-for="w in result.windows" :key="w.n_segments">
          <div class="stat-value">{{ w.n_segments }} 段</div>
          <div class="stat-label">稳定性评分</div>
          <div class="stat-value" :class="scoreClass(w.stability_score)">
            {{ (w.stability_score * 100).toFixed(1) }}%
          </div>
        </div>
      </div>

      <div class="card" v-for="w in result.windows" :key="'detail-' + w.n_segments">
        <div class="card-header">
          <h3>{{ w.n_segments }} 段分析</h3>
          <span :class="scoreClass(w.stability_score)">评分 {{ (w.stability_score * 100).toFixed(1) }}%</span>
        </div>
        <div class="card-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>段</th>
                <th>收益</th>
                <th>夏普</th>
                <th>最大回撤</th>
                <th>胜率</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(seg, i) in w.segments" :key="i">
                <td>{{ i + 1 }}</td>
                <td :class="seg.total_return >= 0 ? 'stat-success' : 'stat-danger'">
                  {{ (seg.total_return * 100).toFixed(2) }}%
                </td>
                <td>{{ seg.sharpe.toFixed(2) }}</td>
                <td class="stat-danger">{{ (seg.max_drawdown * 100).toFixed(2) }}%</td>
                <td>{{ (seg.win_rate * 100).toFixed(1) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else-if="!loading" class="card">
      <div class="empty-state">选择回测任务并点击分析</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { validationApi } from '@/api/modules/validation'
import { backtestApi } from '@/api/modules/backtest'

const loading = ref(false)
const result = ref<any>(null)
const backtestList = ref<any[]>([])
const segmentsInput = ref('2, 4, 8')
const config = reactive({
  taskId: '',
  portfolioId: '',
})

const scoreClass = (score: number) => {
  if (score >= 0.7) return 'stat-success'
  if (score >= 0.4) return 'stat-warning'
  return 'stat-danger'
}

const runAnalysis = async () => {
  if (!config.taskId) return
  loading.value = true
  result.value = null
  try {
    const segments = segmentsInput.value.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n))
    const task = backtestList.value.find(t => t.uuid === config.taskId)
    const portfolioId = task?.portfolio_id || config.portfolioId
    const res = await validationApi.segmentStability({
      task_id: config.taskId,
      portfolio_id: portfolioId,
      n_segments: segments.length ? segments : undefined,
    })
    result.value = res.data
  } catch (e: any) {
    alert('分析失败: ' + (e.message || e))
  } finally {
    loading.value = false
  }
}

const fetchBacktestList = async () => {
  try {
    const res = await backtestApi.list({ page: 1, size: 50, status: 'completed' })
    backtestList.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => { fetchBacktestList() })
</script>

<style scoped>
.stat-warning { color: #eab308; }
.stat-success { color: #22c55e; }
.stat-danger { color: #ef4444; }
</style>
