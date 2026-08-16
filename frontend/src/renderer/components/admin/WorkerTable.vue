<template>
  <div
    v-if="loading"
    class="loading-container"
  >
    <div class="spinner" />
  </div>
  <div
    v-else-if="workers.length > 0"
    class="table-wrapper"
  >
    <table class="data-table">
      <thead>
        <tr>
          <th>{{ idHeader }}</th>
          <th>类型</th>
          <th>状态</th>
          <th>详情</th>
          <th>最后心跳</th>
        </tr>
      </thead>
      <tbody>
        <template
          v-for="record in workers"
          :key="`${record.type}-${record.id}`"
        >
          <tr @contextmenu="emit('rowContextmenu', $event, record)">
            <td class="monospace cell-id">
              <button
                v-if="expandable && record.type === 'backtest_worker'"
                class="expand-btn"
                :class="{ expanded: expandedIds.has(record.id) }"
                title="活跃任务"
                @click="toggleExpand(record)"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
              </button>
              <span>{{ record.id }}</span>
            </td>
            <td>
              <span
                class="tag"
                :class="workerTypeTagClass(record.type)"
              >
                {{ workerTypeLabel(record.type) }}
              </span>
            </td>
            <td :class="staleCellClass(record.last_heartbeat)">
              <StatusTag
                type="worker"
                :status="record.status"
              />
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
            <td
              class="monospace"
              :class="staleCellClass(record.last_heartbeat)"
            >
              {{ formatRelativeTime(record.last_heartbeat) }}
            </td>
          </tr>
          <tr
            v-if="expandable && record.type === 'backtest_worker' && expandedIds.has(record.id)"
            class="expand-row"
          >
            <td colspan="5">
              <div
                v-if="expandLoading.has(record.id)"
                class="expand-hint"
              >
                加载中…
              </div>
              <div
                v-else-if="expandError.has(record.id)"
                class="expand-hint expand-error"
              >
                加载失败，点击箭头重试
              </div>
              <div
                v-else-if="(expandedTasks[record.id] || []).length === 0"
                class="expand-hint"
              >
                无活跃任务
              </div>
              <table
                v-else
                class="mini-table"
              >
                <thead>
                  <tr><th>任务</th><th>状态</th><th>进度</th><th>Portfolio</th></tr>
                </thead>
                <tbody>
                  <tr
                    v-for="t in expandedTasks[record.id]"
                    :key="t.task_id"
                  >
                    <td class="monospace">
                      {{ t.name || t.task_id }}
                    </td>
                    <td>
                      <StatusTag
                        type="backtest"
                        :status="t.status"
                      />
                    </td>
                    <td>
                      <div class="progress-bar">
                        <div
                          class="progress-fill"
                          :style="{ width: `${t.progress}%` }"
                        />
                      </div>
                      <span class="progress-num">{{ t.progress }}%</span>
                    </td>
                    <td class="monospace">
                      {{ t.portfolio_id || '-' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
  </div>
  <EmptyState
    v-else
    :description="emptyText"
  />
</template>

<script setup lang="ts">
/**
 * Worker/组件 5 列表(ID/类型/状态/详情/最后心跳)
 *
 * 自 WorkerManagement 与 SystemStatus 逐字重复的两份表格合并。
 * 任务下钻(expandable)仅 Worker 管理页启用,展开态组件自持——
 * 自动刷新只重传列表 props,不刷新已展开任务(收起再展开即重新拉取)。
 * 心跳 stale 预警两档(>30s 警告 / >60s 异常),随 heartbeatTick 重渲染。
 */
import { ref } from 'vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { formatRelativeTime, heartbeatStaleLevel } from '@/utils/format'
import { systemApi } from '@/api'
import type { WorkerInfo, WorkerTaskInfo } from '@/api'
import { message as toast } from '@/utils/toast'
import { workerTypeTagClass, workerTypeLabel } from '@/constants/statusConfig'

const props = withDefaults(defineProps<{
  workers: WorkerInfo[]
  loading?: boolean
  /** backtest_worker 行任务下钻(展开箭头+mini 表) */
  expandable?: boolean
  /** ID 列表头(管理页=Worker ID,状态页=组件 ID) */
  idHeader?: string
  emptyText?: string
  /** 相对时间重渲染 tick(传 store lastUpdate,自动刷新时跳动);仅作响应依赖,值不使用 */
  heartbeatTick?: number | string | null
}>(), {
  loading: false,
  expandable: false,
  idHeader: 'Worker ID',
  emptyText: '暂无 Worker',
  heartbeatTick: null,
})

const emit = defineEmits<{
  (e: 'rowContextmenu', event: MouseEvent, record: WorkerInfo): void
}>()

// 心跳 stale 分级:>30s 警告 / >60s 异常。渲染期读取 heartbeatTick 建立
// 响应依赖(store 每次刷新跳动),相对时间随之重渲染
const staleCellClass = (hb: string) => {
  void props.heartbeatTick
  const level = heartbeatStaleLevel(hb)
  if (level === 2) return 'stale-2'
  if (level === 1) return 'stale-1'
  return ''
}

/** 任务下钻状态:自动刷新只重传列表 props,不刷新已展开任务(收起再展开即重新拉取) */
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
</script>

<style scoped>
/* 密度覆盖:紧凑 12px(公共基线见 styles/tables.less) */
.data-table th,
.data-table td {
  padding: 10px 12px;
  font-size: 12px;
}

.table-wrapper {
  padding: 20px;
  overflow-x: clip;
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
/* loading/spinner 走全局 styles/spinners.less */
</style>
