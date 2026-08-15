<template>
  <PageLayout>
    <template #title>
      Worker 管理
    </template>
    <template #actions>
      <label class="switch-label">
        <input type="checkbox" v-model="autoRefreshModel" @change="toggleAutoRefresh" class="switch-input" />
        <span class="switch-slider"></span>
        <span class="switch-text">自动刷新</span>
      </label>
      <button class="btn-secondary" @click="refreshData">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
          <path d="M3 3v5h5"></path>
          <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
          <path d="M16 21h5v-5"></path>
        </svg>
        刷新
      </button>
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatCard title="总 Worker" :value="filteredWorkers.length" />
      <StatCard title="运行中" :value="runningCount" :color="runningCount > 0 ? 'positive' : 'neutral'" />
      <StatCard title="已停止" :value="stoppedCount" color="neutral" />
      <StatCard title="异常" :value="errorCount" :color="errorCount > 0 ? 'negative' : 'positive'" />
    </div>

    <!-- Worker 列表 -->
    <div class="card">
      <div class="card-header">
        <h3>Worker 列表</h3>
        <select v-model="typeFilter" class="filter-select">
          <option value="">全部类型</option>
          <option value="data_worker">数据 Worker</option>
          <option value="backtest_worker">回测 Worker</option>
          <option value="execution_node">执行节点</option>
          <option value="scheduler">调度器</option>
          <option value="task_timer">定时器</option>
        </select>
      </div>
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else-if="filteredWorkers.length > 0" class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Worker ID</th>
              <th>类型</th>
              <th>状态</th>
              <th>详情</th>
              <th>最后心跳</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="record in filteredWorkers" :key="`${record.type}-${record.id}`">
            <tr @contextmenu="openWorkerMenu($event)">
              <td class="monospace cell-id">
                <button
                  v-if="record.type === 'backtest_worker'"
                  class="expand-btn"
                  :class="{ expanded: expandedIds.has(record.id) }"
                  @click="toggleExpand(record)"
                  title="活跃任务"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                </button>
                <span>{{ record.id }}</span>
              </td>
              <td>
                <span class="tag" :class="`tag-${getTypeColorClass(record.type)}`">
                  {{ getTypeText(record.type) }}
                </span>
              </td>
              <td :class="staleCellClass(record.last_heartbeat)">
                <StatusTag type="worker" :status="record.status" />
              </td>
              <td class="detail-text">
                <template v-if="record.type === 'backtest_worker'">
                  任务: {{ record.task_count || 0 }}/{{ record.max_tasks || 5 }}
                </template>
                <template v-else-if="record.type === 'execution_node'">
                  Portfolio: {{ record.portfolio_count || 0 }}
                </template>
                <template v-else-if="record.type === 'scheduler'">
                  运行: {{ record.running_tasks || 0 }} / 待处理: {{ record.pending_tasks || 0 }}
                </template>
                <template v-else-if="record.type === 'task_timer'">
                  定时任务: {{ record.jobs_count || 0 }}
                </template>
                <template v-else>
                  已处理: {{ record.task_count || 0 }}
                </template>
              </td>
              <td class="monospace" :class="staleCellClass(record.last_heartbeat)">
                {{ formatRelativeTime(record.last_heartbeat) }}
              </td>
            </tr>
            <tr v-if="record.type === 'backtest_worker' && expandedIds.has(record.id)" class="expand-row">
              <td colspan="5">
                <div v-if="expandLoading.has(record.id)" class="expand-hint">加载中…</div>
                <div v-else-if="expandError.has(record.id)" class="expand-hint expand-error">加载失败，点击箭头重试</div>
                <div v-else-if="(expandedTasks[record.id] || []).length === 0" class="expand-hint">无活跃任务</div>
                <table v-else class="mini-table">
                  <thead>
                    <tr><th>任务</th><th>状态</th><th>进度</th><th>Portfolio</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="t in expandedTasks[record.id]" :key="t.task_id">
                      <td class="monospace">{{ t.name || t.task_id }}</td>
                      <td>
                        <StatusTag type="backtest" :status="t.status" />
                      </td>
                      <td>
                        <div class="progress-bar">
                          <div class="progress-fill" :style="{ width: `${t.progress}%` }"></div>
                        </div>
                        <span class="progress-num">{{ t.progress }}%</span>
                      </td>
                      <td class="monospace">{{ t.portfolio_id || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
      <EmptyState v-else description="暂无 Worker" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { formatRelativeTime, heartbeatStaleLevel } from '@/utils/format'
import { useSystemStore } from '@/stores'
import { systemApi } from '@/api'
import type { WorkerInfo, WorkerTaskInfo } from '@/api'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'

/** 行右键菜单(纯监控:仅刷新) */
const { open: openCtxMenu } = useContextMenu()
const openWorkerMenu = (e: MouseEvent) => {
  openCtxMenu(e, [
    { label: '刷新', action: refreshData },
  ])
}

const systemStore = useSystemStore()
const autoRefreshModel = ref(false)
const typeFilter = ref('')

const loading = computed(() => systemStore.loading)
const workers = computed(() => systemStore.workers)

const filteredWorkers = computed(() => {
  if (!typeFilter.value) return workers.value
  return workers.value.filter(w => w.type === typeFilter.value)
})

const runningCount = computed(() => filteredWorkers.value.filter(w => w.status === 'running' || w.status === 'active').length)
const stoppedCount = computed(() => filteredWorkers.value.filter(w => w.status === 'stopped' || w.status === 'idle').length)
const errorCount = computed(() => filteredWorkers.value.filter(w => w.status === 'error' || w.status === 'stale').length)

/** 相对时间重渲染 tick：随 store 每次刷新变化（自动刷新 5s 一跳） */
const heartbeatTick = computed(() => systemStore.lastUpdate)

const staleCellClass = (hb: string) => {
  heartbeatTick.value // 渲染期读取，建立响应依赖
  const level = heartbeatStaleLevel(hb)
  if (level === 2) return 'stale-2'
  if (level === 1) return 'stale-1'
  return ''
}

/** 任务下钻状态：自动刷新只重拉列表，不刷新已展开任务（收起再展开即重新拉取） */
const expandedIds = ref(new Set<string>())
const expandedTasks = ref<Record<string, WorkerTaskInfo[]>>({})
const expandLoading = ref(new Set<string>())
const expandError = ref(new Set<string>())

const toggleExpand = async (worker: WorkerInfo) => {
  const id = worker.id
  const next = new Set(expandedIds.value)
  if (next.has(id)) {
    // 收起：丢弃缓存，重展开时重新拉最新
    next.delete(id)
    expandedIds.value = next
    const { [id]: _drop, ...rest } = expandedTasks.value
    expandedTasks.value = rest
    return
  }
  next.add(id)
  expandedIds.value = next
  if (expandLoading.value.has(id)) return
  const loading = new Set(expandLoading.value)
  loading.add(id)
  expandLoading.value = loading
  const errs = new Set(expandError.value)
  errs.delete(id)
  expandError.value = errs
  try {
    const resp = await systemApi.getWorkerTasks(id)
    expandedTasks.value = { ...expandedTasks.value, [id]: resp.tasks || [] }
  } catch {
    const e = new Set(expandError.value)
    e.add(id)
    expandError.value = e
    toast.error('任务加载失败')
  } finally {
    const l = new Set(expandLoading.value)
    l.delete(id)
    expandLoading.value = l
  }
}

const getTypeColorClass = (type: string) => {
  const colors: Record<string, string> = { data_worker: 'purple', backtest_worker: 'blue', execution_node: 'green', scheduler: 'orange', task_timer: 'magenta' }
  return colors[type] || 'gray'
}

const getTypeText = (type: string) => {
  const texts: Record<string, string> = { data_worker: '数据Worker', backtest_worker: '回测Worker', execution_node: '执行节点', scheduler: '调度器', task_timer: '定时器' }
  return texts[type] || type
}

const refreshData = () => {
  systemStore.fetchWorkers()
}

const toggleAutoRefresh = () => {
  if (autoRefreshModel.value) {
    systemStore.enableAutoRefresh(5000)
  } else {
    systemStore.disableAutoRefresh()
  }
}

onMounted(() => {
  refreshData()
})

onUnmounted(() => {
  systemStore.disableAutoRefresh()
})
</script>

<style scoped>
/* 开关 */
.switch-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.switch-input {
  position: relative;
  width: 40px;
  height: 20px;
  appearance: none;
  background: hsl(var(--secondary));
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
  transition: background 0.3s;
}

.switch-input::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: hsl(var(--card));
  border-radius: 50%;
  transition: transform 0.3s;
}

.switch-input:checked {
  background: hsl(var(--primary));
}

.switch-input:checked::after {
  transform: translateX(20px);
}

.switch-text {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

/* 统计卡片:StatCard + 全局 .stats-grid/.stat-card(间距需页内补) */
.stats-grid {
  margin-bottom: 16px;
}

/* 筛选下拉 */
.filter-select {
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  color: hsl(var(--foreground));
  font-size: 13px;
}

/* 标签 */

/* 表格 */
.table-wrapper {
  padding: 20px;
  overflow-x: clip;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid hsl(var(--border));
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--border));
  color: hsl(var(--foreground));
  font-weight: 500;
  font-size: 12px;
  white-space: nowrap;
}

.data-table td {
  color: hsl(var(--foreground));
  font-size: 12px;
}

.monospace {
  font-family: monospace;
  font-size: 11px;
}

.detail-text {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 心跳 stale 预警 */
.stale-1 { color: hsl(var(--warning)); }
.stale-2 { color: hsl(var(--error)); font-weight: 600; }
.stale-1 :deep(.status-tag) { color: hsl(var(--warning)); }
.stale-2 :deep(.status-tag) { color: hsl(var(--error)); }

/* 下钻展开 */
.cell-id { display: flex; align-items: center; gap: 6px; }

.expand-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: transform 0.2s, color 0.2s;
}

.expand-btn:hover { color: hsl(var(--foreground)); }
.expand-btn.expanded { transform: rotate(90deg); }

.expand-row > td { padding: 8px 12px 16px 40px; background: hsl(var(--secondary) / 0.3); }

.expand-hint { font-size: 12px; color: hsl(var(--muted-foreground)); padding: 4px 0; }
.expand-error { color: hsl(var(--error)); }

.mini-table { width: 100%; border-collapse: collapse; }
.mini-table th,
.mini-table td { padding: 6px 10px; text-align: left; border-bottom: 1px solid hsl(var(--border)); font-size: 12px; }
.mini-table th { color: hsl(var(--muted-foreground)); font-weight: 500; white-space: nowrap; }

.progress-bar {
  display: inline-block;
  width: 100px;
  height: 6px;
  border-radius: 3px;
  background: hsl(var(--secondary));
  overflow: hidden;
  vertical-align: middle;
}

.progress-fill {
  height: 100%;
  border-radius: 3px;
  background: hsl(var(--primary));
  transition: width 0.3s;
}

.progress-num { margin-left: 8px; font-size: 11px; color: hsl(var(--muted-foreground)); }

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
