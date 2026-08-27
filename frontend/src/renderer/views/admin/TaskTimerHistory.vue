<template>
  <PageLayout>
    <template #title>
      定时任务
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatCard
        title="总执行次数"
        :value="summary.total"
      />
      <StatCard
        title="成功"
        :value="summary.success"
        :color="summary.success > 0 ? 'positive' : 'neutral'"
      />
      <StatCard
        title="失败"
        :value="summary.failed"
        :color="summary.failed > 0 ? 'negative' : 'positive'"
      />
      <StatCard
        title="执行中"
        :value="summary.triggered"
      />
    </div>

    <!-- 已注册任务 -->
    <div
      v-if="tasks.length > 0"
      class="card"
    >
      <div class="card-header">
        <h3>已注册任务</h3>
      </div>
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
            <tr
              v-for="t in tasks"
              :key="t.name"
            >
              <td>{{ t.name }}</td>
              <td><span class="tag tag-blue">{{ t.command }}</span></td>
              <td class="mono">
                {{ t.cron }}
              </td>
              <td>
                <StatusTag
                  type="enable"
                  :status="t.enabled ? 'active' : 'disabled'"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 执行历史:筛选行 + ProTable(服务端分页) -->
    <div class="history-section">
      <div class="history-header">
        <h3>执行历史</h3>
        <div class="filter-bar">
          <select
            v-model="filterJobName"
            class="control-input"
            @change="loadExecutions"
          >
            <option value="">
              全部任务
            </option>
            <option
              v-for="t in tasks"
              :key="t.name"
              :value="t.name"
            >
              {{ t.name }}
            </option>
          </select>
          <select
            v-model="filterStatus"
            class="control-input"
            @change="loadExecutions"
          >
            <option value="">
              全部状态
            </option>
            <option value="triggered">
              执行中
            </option>
            <option value="success">
              成功
            </option>
            <option value="failed">
              失败
            </option>
          </select>
        </div>
      </div>

      <ProTable
        v-if="executions.length > 0"
        :columns="execColumns"
        :data-source="executions"
        row-key="uuid"
        flow
        server-pagination
        :total="pagination.total"
        :page="pagination.current"
        :page-size="pagination.pageSize"
        :page-sizes="[pagination.pageSize]"
        :context-menu="execMenu"
        @update:page="goPage"
      >
        <template #command="{ record }">
          <span class="tag tag-blue">{{ record.command }}</span>
        </template>
        <template #status="{ record }">
          <StatusTag
            type="execution"
            :status="record.status"
          />
        </template>
        <template #triggered_at="{ record }">
          <span class="mono">{{ formatDate(record.triggered_at) }}</span>
        </template>
        <template #duration_ms="{ record }">
          <span class="mono">{{ record.duration_ms > 0 ? record.duration_ms + 'ms' : '-' }}</span>
        </template>
        <template #cron_expr="{ record }">
          <span class="mono">{{ record.cron_expr || '-' }}</span>
        </template>
      </ProTable>
      <!-- 加载失败:区别于空态,提供重试 -->
      <div
        v-else-if="!loading && loadError"
        class="card"
      >
        <EmptyState
          title="加载失败"
          :description="loadError"
          action-text="重试"
          :on-action="loadExecutions"
        />
      </div>
      <div
        v-else-if="!loading"
        class="card"
      >
        <EmptyState description="暂无执行记录" />
      </div>
    </div>

    <div
      v-if="loading"
      class="loading-overlay"
    >
      <div class="spinner" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ProTable from '@/components/common/ProTable.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { taskTimerApi } from '@/api/modules/taskTimer'
import type { TaskTimerExecution, TaskTimerJob, ExecutionSummary } from '@/api/modules/taskTimer'
import { message as toast } from '@/utils/toast'
import type { MenuItem } from '@/composables/useContextMenu'
import { formatDate } from '@/utils/format'

const execColumns = [
  { title: '任务名称', dataIndex: 'job_name' },
  { title: '命令', dataIndex: 'command' },
  { title: '状态', dataIndex: 'status' },
  { title: '触发时间', dataIndex: 'triggered_at' },
  { title: '耗时', dataIndex: 'duration_ms' },
  { title: 'Cron', dataIndex: 'cron_expr' },
]

/** 执行记录行右键菜单(本页无行操作,给复制类) */
const execMenu = (record: TaskTimerExecution): MenuItem[] => [
  { label: '复制任务名', action: () => { navigator.clipboard.writeText(record.job_name); toast.success('已复制') } },
  { label: '复制命令', action: () => { navigator.clipboard.writeText(record.command); toast.success('已复制') } },
]

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
    // 拦截器契约:数组+meta 响应已转 {items,total};res?.data 二次解包=静默空数据
    executions.value = res?.items ?? []
    pagination.value.total = res?.total ?? 0
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

/* 密度覆盖:紧凑 padding + 表头加重 + 正文 13px(公共基线见 styles/tables.less) */
.data-table th,
.data-table td {
  padding: 10px 12px;
}

.data-table th {
  font-weight: 600;
}

.data-table td {
  font-size: 13px;
}

/* 统计卡片:StatCard + 全局 .stats-grid;卡片间距由 .page-layout-body gap 统一提供 */
.card { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); }
.card-header { padding: 12px 16px; font-size: 14px; font-weight: 600; color: hsl(var(--foreground)); border-bottom: 1px solid hsl(var(--border)); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.table-wrapper { overflow-x: clip; }
.mono { font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

.filter-bar { display: flex; gap: 8px; }
.control-input { padding: 6px 12px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 13px; }
.control-input:focus { outline: none; border-color: hsl(var(--primary)); }

/* 执行历史区:筛选行在 ProTable 卡片外,与卡内表头解耦 */
.history-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.history-header h3 { font-size: 14px; font-weight: 600; color: hsl(var(--foreground)); margin: 0; }

.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid hsl(var(--border)); border-top-color: hsl(var(--primary)); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) { .stats-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
