<template>
  <PageLayout>
    <template #title>
      定时任务
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatCard title="总执行次数" :value="summary.total" />
      <StatCard title="成功" :value="summary.success" :color="summary.success > 0 ? 'positive' : 'neutral'" />
      <StatCard title="失败" :value="summary.failed" :color="summary.failed > 0 ? 'negative' : 'positive'" />
      <StatCard title="执行中" :value="summary.triggered" />
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
                <StatusTag type="enable" :status="t.enabled ? 'active' : 'disabled'" />
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
            <tr v-for="e in executions" :key="e.uuid" @contextmenu="openExecMenu($event, e)">
              <td>{{ e.job_name }}</td>
              <td><span class="tag tag-blue">{{ e.command }}</span></td>
              <td>
                <StatusTag type="execution" :status="e.status" />
              </td>
              <td class="mono">{{ formatTime(e.triggered_at) }}</td>
              <td class="mono">{{ e.duration_ms > 0 ? e.duration_ms + 'ms' : '-' }}</td>
              <td class="mono">{{ e.cron_expr || '-' }}</td>
            </tr>
          </tbody>
        </table>
        <!-- 加载失败:区别于空态,提供重试 -->
        <EmptyState
          v-else-if="!loading && loadError"
          title="加载失败"
          :description="loadError"
          action-text="重试"
          :on-action="loadExecutions"
        />
        <EmptyState v-else-if="!loading" description="暂无执行记录" />
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
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { taskTimerApi } from '@/api/modules/taskTimer'
import type { TaskTimerExecution, TaskTimerJob, ExecutionSummary } from '@/api/modules/taskTimer'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import dayjs from 'dayjs'

/** 执行记录行右键菜单(本页无行操作,给复制类) */
const { open: openCtxMenu } = useContextMenu()
const openExecMenu = (e: MouseEvent, record: TaskTimerExecution) => {
  openCtxMenu(e, [
    { label: '复制任务名', action: () => { navigator.clipboard.writeText(record.job_name); toast.success('已复制') } },
    { label: '复制命令', action: () => { navigator.clipboard.writeText(record.command); toast.success('已复制') } },
  ])
}

const loading = ref(false)
const tasks = ref<TaskTimerJob[]>([])
const executions = ref<TaskTimerExecution[]>([])
const summary = ref<ExecutionSummary>({ total: 0, success: 0, failed: 0, triggered: 0, by_job: {} })
const filterJobName = ref('')
const filterStatus = ref('')
// 执行历史加载失败(后端 5xx/网络断):须与"暂无执行记录"空态区分
const loadError = ref('')
const pagination = ref({ current: 1, pageSize: 20, total: 0 })
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize)))

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
  loadError.value = ''
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
  } catch (e: any) {
    executions.value = []
    pagination.value.total = 0
    const st = e?.response?.status
    loadError.value = st ? `执行历史加载失败（HTTP ${st}）` : '执行历史加载失败，请检查网络后重试'
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
/* 统计卡片:StatCard + 全局 .stats-grid(间距需页内补) */
.stats-grid { margin-bottom: 16px; }

.card { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); margin-bottom: 16px; }
.card-header { padding: 12px 16px; font-size: 14px; font-weight: 600; color: hsl(var(--foreground)); border-bottom: 1px solid hsl(var(--border)); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.table-wrapper { overflow-x: clip; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { position: sticky; top: 0; z-index: 1; padding: 10px 12px; text-align: left; color: hsl(var(--foreground)); background: hsl(var(--border)); font-weight: 600; white-space: nowrap; }
.data-table td { padding: 10px 12px; color: hsl(var(--foreground)); border-bottom: 1px solid hsl(var(--border)); }
.data-table tbody tr:hover { background: hsl(var(--secondary)); }
.mono { font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

.filter-bar { display: flex; gap: 8px; }
.control-input { padding: 6px 12px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 13px; }
.control-input:focus { outline: none; border-color: hsl(var(--primary)); }

.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid hsl(var(--border)); }
.pagination-info { font-size: 13px; color: hsl(var(--muted-foreground)); }
.pagination-controls { display: flex; gap: 4px; }
.pg-btn { min-width: 28px; height: 28px; padding: 0 6px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.pg-btn:hover:not(:disabled) { background: hsl(var(--secondary)); border-color: hsl(var(--primary)); }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid hsl(var(--border)); border-top-color: hsl(var(--primary)); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
