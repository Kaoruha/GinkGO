<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">定时任务</h1>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">总执行次数</div>
        <div class="stat-value">{{ summary.total }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">成功</div>
        <div class="stat-value" style="color: #52c41a">{{ summary.success }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">失败</div>
        <div class="stat-value" style="color: #f5222d">{{ summary.failed }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">执行中</div>
        <div class="stat-value" style="color: #1890ff">{{ summary.triggered }}</div>
      </div>
    </div>

    <!-- 已注册任务 -->
    <div class="card" v-if="tasks.length > 0">
      <div class="card-header"><h3>已注册任务</h3></div>
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>任务名称</th>
              <th>命令</th>
              <th>Cron</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in tasks" :key="t.name">
              <td>{{ t.name }}</td>
              <td><span class="tag tag-blue">{{ t.command }}</span></td>
              <td class="mono">{{ t.cron }}</td>
              <td>
                <span class="tag" :class="t.enabled ? 'tag-green' : 'tag-gray'">
                  {{ t.enabled ? '启用' : '禁用' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 执行历史 -->
    <div class="card">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center;">
        <h3>执行历史</h3>
        <div class="filter-bar">
          <select v-model="filterJobName" class="control-input" @change="loadExecutions">
            <option value="">全部任务</option>
            <option v-for="t in tasks" :key="t.name" :value="t.name">{{ t.name }}</option>
          </select>
          <select v-model="filterStatus" class="control-input" @change="loadExecutions">
            <option value="">全部状态</option>
            <option value="triggered">执行中</option>
            <option value="success">成功</option>
            <option value="failed">失败</option>
          </select>
        </div>
      </div>

      <div class="table-wrapper">
        <table class="data-table" v-if="executions.length > 0">
          <thead>
            <tr>
              <th>任务名称</th>
              <th>命令</th>
              <th>状态</th>
              <th>触发时间</th>
              <th>耗时</th>
              <th>Cron</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in executions" :key="e.uuid">
              <td>{{ e.job_name }}</td>
              <td><span class="tag tag-blue">{{ e.command }}</span></td>
              <td>
                <span class="tag" :class="statusClass(e.status)">{{ statusText(e.status) }}</span>
              </td>
              <td class="mono">{{ formatTime(e.triggered_at) }}</td>
              <td class="mono">{{ e.duration_ms > 0 ? e.duration_ms + 'ms' : '-' }}</td>
              <td class="mono">{{ e.cron_expr || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else-if="!loading" class="empty-state">暂无执行记录</div>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="pagination.total > 0">
        <span class="pagination-info">
          共 {{ pagination.total }} 条，第 {{ pagination.current }} / {{ totalPages }} 页
        </span>
        <div class="pagination-controls">
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(1)">«</button>
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(pagination.current - 1)">‹</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(pagination.current + 1)">›</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(totalPages)">»</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay"><div class="spinner"></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { taskTimerApi } from '@/api/modules/taskTimer'
import type { TaskTimerExecution, TaskTimerJob, ExecutionSummary } from '@/api/modules/taskTimer'
import dayjs from 'dayjs'

const loading = ref(false)
const tasks = ref<TaskTimerJob[]>([])
const executions = ref<TaskTimerExecution[]>([])
const summary = ref<ExecutionSummary>({ total: 0, success: 0, failed: 0, triggered: 0, by_job: {} })
const filterJobName = ref('')
const filterStatus = ref('')
const pagination = ref({ current: 1, pageSize: 20, total: 0 })
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize)))

function statusClass(s: string) {
  return { triggered: 'tag-blue', success: 'tag-green', failed: 'tag-red' }[s] || 'tag-gray'
}
function statusText(s: string) {
  return { triggered: '执行中', success: '成功', failed: '失败' }[s] || s
}
function formatTime(t: string | null) {
  if (!t) return '-'
  return dayjs(t).format('YYYY-MM-DD HH:mm:ss')
}

async function loadSummary() {
  try {
    const res: any = await taskTimerApi.getSummary()
    const data = res?.data ?? res
    summary.value = data || { total: 0, success: 0, failed: 0, triggered: 0, by_job: {} }
  } catch { /* ignore */ }
}

async function loadJobs() {
  try {
    const res: any = await taskTimerApi.getJobs()
    const data = res?.data ?? res
    tasks.value = data?.tasks || []
  } catch { /* ignore */ }
}

async function loadExecutions() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    }
    if (filterJobName.value) params.job_name = filterJobName.value
    if (filterStatus.value) params.status = filterStatus.value

    const res: any = await taskTimerApi.getExecutions(params)
    const data = res?.data ?? []
    executions.value = Array.isArray(data) ? data : []
    pagination.value.total = res?.meta?.total || 0
  } catch {
    executions.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  pagination.value.current = p
  loadExecutions()
}

onMounted(() => {
  loadSummary()
  loadJobs()
  loadExecutions()
})
</script>

<style scoped>
.page-container { position: relative; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-title { margin: 0; font-size: 20px; font-weight: 600; color: #fff; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 16px; }
.stat-label { font-size: 12px; color: #8a8a9a; margin-bottom: 4px; }
.stat-value { font-size: 24px; font-weight: 600; color: #fff; }

.card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; overflow: hidden; margin-bottom: 16px; }
.card-header { padding: 12px 16px; font-size: 14px; font-weight: 600; color: #fff; border-bottom: 1px solid #2a2a3e; }
.table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { padding: 10px 12px; text-align: left; color: #fff; background: #2a2a3e; font-weight: 600; white-space: nowrap; }
.data-table td { padding: 10px 12px; color: #fff; border-bottom: 1px solid #2a2a3e; }
.data-table tbody tr:hover { background: #22223a; }
.mono { font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-blue { background: rgba(24,144,255,0.15); color: #69c0ff; }
.tag-green { background: rgba(82,196,26,0.15); color: #95de64; }
.tag-red { background: rgba(245,34,45,0.15); color: #ff7875; }
.tag-gray { background: rgba(255,255,255,0.08); color: #8a8a9a; }

.filter-bar { display: flex; gap: 8px; }
.control-input { padding: 6px 12px; background: #2a2a3e; border: 1px solid #3a3a4e; border-radius: 4px; color: #fff; font-size: 13px; }
.control-input:focus { outline: none; border-color: #1890ff; }

.empty-state { padding: 40px; text-align: center; color: #8a8a9a; }
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid #2a2a3e; }
.pagination-info { font-size: 13px; color: #8a8a9a; }
.pagination-controls { display: flex; gap: 4px; }
.pg-btn { min-width: 28px; height: 28px; padding: 0 6px; background: #2a2a3e; border: 1px solid #3a3a4e; border-radius: 4px; color: #fff; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.pg-btn:hover:not(:disabled) { background: #3a3a4e; border-color: #1890ff; }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid #2a2a3e; border-top-color: #1890ff; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
