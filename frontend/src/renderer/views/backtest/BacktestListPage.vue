<template>
  <ListPage
    title="回测中心"
    :columns="columns"
    :data-source="tasks"
    :loading="loading && tasks.length === 0"
    :error-text="listError"
    row-key="uuid"
    :searchable="false"
    :creatable="false"
    :infinite-scroll="true"
    clickable
    :context-menu="rowMenu"
    @sort="onSort"
    @row-click="goDetail"
    @retry="resetAndFetch"
  >
    <template #filters>
      <SegmentedControl
        :model-value="statusFilter"
        :options="statusOptions"
        @update:model-value="(v) => { statusFilter = v; resetAndFetch() }"
      />
    </template>

    <template #name="{ record }">
      <router-link
        :to="`/backtests/${record.uuid}`"
        class="task-link"
        @click.stop
      >
        {{ record.name || record.uuid?.slice(0, 8) }}
      </router-link>
    </template>

    <template #portfolio_name="{ record }">
      <router-link
        v-if="record.portfolio_id"
        :to="`/portfolios/${record.portfolio_id}`"
        class="portfolio-link"
        @click.stop
      >
        {{ record.portfolio_name || record.portfolio_id?.slice(0, 8) }}
      </router-link>
      <span v-else class="val-muted">-</span>
    </template>

    <template #status="{ record }">
      <div class="status-cell">
        <StatusTag :status="record.status" type="backtest" />
        <!-- 进行中/排队中显示实时进度条(WS 就地更新,参照 BacktestTab) -->
        <span v-if="record.status === 'running' || record.status === 'pending'" class="progress-info">
          <div class="progress-bar-sm"><div class="progress-fill" :style="{ width: (record.progress || 0) + '%' }"></div></div>
          <span class="progress-text">{{ (record.progress || 0).toFixed(0) }}%</span>
        </span>
      </div>
    </template>

    <template #sparkline="{ record }">
      <Sparkline v-if="sparklines[record.uuid]?.length >= 2" :points="sparklines[record.uuid]" :width="110" :height="30" />
      <span v-else class="val-muted">-</span>
    </template>

    <template #annual_return="{ record }">
      <span :class="Number(record.annual_return) >= 0 ? 'val-green' : 'val-red'">
        {{ formatPercent(record.annual_return) }}
      </span>
    </template>

    <template #sharpe_ratio="{ record }">
      <span :class="Number(record.sharpe_ratio) >= 0 ? 'val-green' : 'val-red'">
        {{ formatDecimal(record.sharpe_ratio) }}
      </span>
    </template>

    <template #max_drawdown="{ record }">
      <span class="val-red">{{ formatPercent(record.max_drawdown) }}</span>
    </template>

    <template #win_rate="{ record }">
      {{ formatPercent(record.win_rate) }}
    </template>

    <template #total_signals="{ record }">
      <span class="val-muted">{{ record.total_signals ?? '-' }}</span>
      <span class="val-divider">/</span>
      <span class="val-muted">{{ record.total_orders ?? '-' }}</span>
    </template>

    <template #update_at="{ record }">
      <span class="val-muted" :title="formatTime(record.update_at || record.created_at)">{{ formatRelativeTime(record.update_at || record.created_at) }}</span>
    </template>

    <!-- 无限滚动触发器 -->
    <template #afterTable>
      <div v-if="tasks.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
        <div v-if="loadingMore" class="spinner spinner-small"></div>
        <div v-else-if="!hasMore" class="no-more">没有更多了</div>
        <div v-else class="load-more-sentinel"></div>
      </div>
    </template>
  </ListPage>

  <!-- 删除确认 -->
  <ConfirmDialog
    v-model:open="deleteConfirmOpen"
    :title="`删除回测「${deletingTask?.name || deletingTask?.uuid?.slice(0, 8) || ''}」?`"
    description="回测记录与结果数据将被删除,此操作不可恢复。"
    danger
    confirm-text="删除"
    :loading="deleting"
    @confirm="doDelete"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import ListPage from '@/components/common/ListPage.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import Sparkline from '@/components/charts/Sparkline.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { backtestApi } from '@/api/modules/backtest'
import request from '@/api/request'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { useWebSocket, useServerEvents } from '@/composables'
import { formatDecimal } from '@/composables/useBacktestFormatters'
import { formatPercent, formatRelativeTime } from '@/utils/format'
import type { MenuItem } from '@/composables/useContextMenu'
import { message } from '@/utils/toast'

const router = useRouter()

// ========== WebSocket 实时进度 ==========
const { isConnected } = useWebSocket()
const { on, onReconnect } = useServerEvents()
let unsubscribe: (() => void) | null = null
let pollTimer: number | null = null

const tasks = ref<any[]>([])
// 净值缩略图:task uuid → 降采样净值序列(批量端点一次拉全页)
const sparklines = ref<Record<string, number[]>>({})
const loadSparklines = async (rows: any[]) => {
  const completed = rows.filter(t => t.status === 'completed').map(t => t.uuid)
  if (!completed.length) return
  try {
    const res = await request.get('/api/v1/backtests/netvalue-sparklines', {
      params: { task_ids: completed.join(',') },
      skipErrorToast: true,
    } as any)
    sparklines.value = ((res as any).data || res) as Record<string, number[]>
  } catch { sparklines.value = {} }
}
const loading = ref(false)
// 列表加载失败(后端 5xx/网络断):须与"暂无数据"空态区分,提供重试
const listError = ref('')
const loadingMore = ref(false)
const total = ref(0)
const currentPage = ref(0)
const pageSize = 20
const statusFilter = ref('')

const statusOptions = [
  { key: '', label: '全部状态' },
  { key: 'completed', label: '已完成' },
  { key: 'running', label: '进行中' },
  { key: 'pending', label: '排队中' },
  { key: 'failed', label: '失败' },
  { key: 'stopped', label: '已停止' },
  { key: 'created', label: '待调度' },
]
const sortBy = ref('update_at')
const sortOrder = ref<'asc' | 'desc'>('desc')

const hasMore = computed(() => tasks.value.length < total.value)

const columns = [
  { title: '任务名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '组合', dataIndex: 'portfolio_name', key: 'portfolio_name', width: 150 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 160 },
  { title: '净值', key: 'sparkline', width: 130, dataIndex: 'sparkline' } as any,
  { title: '收益率', dataIndex: 'annual_return', key: 'annual_return', width: 100, sortable: true },
  { title: '夏普', dataIndex: 'sharpe_ratio', key: 'sharpe_ratio', width: 80, sortable: true },
  { title: '最大回撤', dataIndex: 'max_drawdown', key: 'max_drawdown', width: 100, sortable: true },
  { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', width: 80, sortable: true },
  { title: '信号/订单', dataIndex: 'total_signals', key: 'total_signals', width: 100 },
  { title: '最近更新', dataIndex: 'update_at', key: 'update_at', width: 110, sortable: true },
]

const formatTime = (t: string) => {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

function goDetail(record: any) {
  router.push(`/backtests/${record.uuid}`)
}

const stopTask = async (record: any) => {
  try {
    await backtestApi.stop(record.uuid)
    message.success('已发送停止指令')
    fetchTasks(false)
  } catch (e: any) {
    message.error(e?.response?.data?.message || e?.message || '停止失败')
  }
}

/** 行右键菜单:详情/复制ID/删除,运行中或排队中可停止 */
const deleteConfirmOpen = ref(false)
const deletingTask = ref<any>(null)
const deleting = ref(false)

const doDelete = async () => {
  if (!deletingTask.value) return
  deleting.value = true
  try {
    await backtestApi.delete(deletingTask.value.uuid)
    message.success('删除成功')
    deleteConfirmOpen.value = false
    resetAndFetch()
  } catch (e: any) {
    message.error(e?.response?.data?.message || '删除失败')
  } finally {
    deleting.value = false
  }
}

const rowMenu = (record: any): MenuItem[] => {
  const running = record.status === 'running' || record.status === 'pending' || record.status === 'created'
  return [
    { label: '详情', action: () => goDetail(record) },
    {
      label: '复制ID',
      action: () => {
        navigator.clipboard.writeText(record.uuid)
        message.success('ID 已复制')
      },
    },
    ...(running ? [{ label: '停止', danger: true, action: () => stopTask(record) }] : []),
    { divider: true },
    { label: '删除', danger: true, action: () => { deletingTask.value = record; deleteConfirmOpen.value = true } },
  ]
}

function onSort(field: string, order: 'asc' | 'desc') {
  sortBy.value = field
  sortOrder.value = order
  resetAndFetch()
}

async function resetAndFetch() {
  currentPage.value = 0
  tasks.value = []
  total.value = 0
  // 断开旧 observer，首次 fetch 完成后重建
  if (observer) { observer.disconnect(); observer = null }
  await fetchTasks(false)
  nextTick(() => setupObserver())
}

async function fetchTasks(append: boolean) {
  if (append) {
    if (!hasMore.value || loading.value || loadingMore.value) return
    loadingMore.value = true
    currentPage.value += 1
  } else {
    loading.value = true
    currentPage.value = 1
  }

  try {
    const params: any = { page: currentPage.value, page_size: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    if (sortBy.value) {
      params.sort_by = sortBy.value
      params.sort_order = sortOrder.value
    }
    const res: any = await backtestApi.list(params)
    const newData = res?.items || []
    if (append) {
      tasks.value.push(...newData)
      loadSparklines(tasks.value)  // 净值缩略图(仅 completed,批量一次)
    } else {
      tasks.value = newData
      loadSparklines(tasks.value)
    }
    total.value = res?.total || 0
    if (!append) listError.value = ''
  } catch (e: any) {
    // 静默清空会让后端故障伪装成"暂无数据",必须显式报错
    if (!append) {
      const st = e?.response?.status
          listError.value = st ? `回测列表加载失败（HTTP ${st}）` : '回测列表加载失败，请检查网络后重试'
      tasks.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => fetchTasks(true)

// IntersectionObserver — 只建一次，靠 loadingMore/hasMore 守卫防重入
const loadMoreTrigger = ref<HTMLElement>()
let observer: IntersectionObserver | null = null

const setupObserver = () => {
  if (!loadMoreTrigger.value || observer) return
  const scrollableContainer = document.querySelector('.list-content')
  if (!scrollableContainer) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loading.value && !loadingMore.value) {
        loadMore()
      }
    },
    { root: scrollableContainer as Element, rootMargin: '200px', threshold: 0.1 }
  )
  observer.observe(loadMoreTrigger.value)
}

onMounted(async () => {
  await fetchTasks(false)
  nextTick(() => setupObserver())

  // WS 薄事件就地更新行内 progress/status(无限滚动 append 模式,全量替换会丢已加载页)。
  // 信封 status 已是 REST 同款小写枚举,直接赋值(旧路径 data.type 会写入大写态名)
  const offs = [
    on('*', (e) => {
      if (e.entity !== 'backtest_task') return
      const hit = tasks.value.find(t => t.uuid === e.id)
      if (!hit) return
      if (e.data?.progress != null) hit.progress = e.data.progress
      if (e.status && e.event !== 'backtest.progress') hit.status = e.status
      // 终态后补一次静默刷新(拉取指标/信号数字;已有数据时 loading prop 为 false,视觉静默)
      if (['backtest.completed', 'backtest.failed', 'backtest.stopped'].includes(e.event)
        && currentPage.value === 1 && !loadingMore.value) {
        fetchTasks(false)
      }
    }),
    // 重连补齐:断线窗口内丢失的事件靠幂等全量拉取兜底(ADR-046 无全局 seq)
    onReconnect(() => {
      if (!loading.value) fetchTasks(false)
    }),
  ]
  unsubscribe = () => offs.forEach(off => off())

  // WS 断连时降级 5s 轮询,重连后恢复推送
  watch(isConnected, (connected) => {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    if (!connected) pollTimer = window.setInterval(() => fetchTasks(false), 5000)
  }, { immediate: true })
})

onUnmounted(() => {
  if (observer) observer.disconnect()
  if (unsubscribe) unsubscribe()
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
})
</script>

<style scoped>
.task-link {
  color: hsl(var(--primary));
  font-weight: 500;
  text-decoration: none;
}
.task-link:hover { text-decoration: underline; }

.portfolio-link {
  color: hsl(var(--muted-foreground));
  text-decoration: none;
  font-size: 12px;
}
.portfolio-link:hover { color: hsl(var(--primary)); }

.val-green { color: hsl(var(--success-fg)); font-weight: 500; }
.val-red { color: hsl(var(--error)); font-weight: 500; }
.val-muted { color: hsl(var(--muted-foreground)); }
/* 分隔符此前用 --secondary(light 下 L≈92%)几乎不可见,改 muted-foreground */
.val-divider { color: hsl(var(--muted-foreground)); margin: 0 2px; }

.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.no-more {
  color: hsl(var(--muted-foreground));
  font-size: 12px;
}

.load-more-sentinel {
  height: 1px;
}

/* 状态列:标签+实时进度条并排 */
.status-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-info { display: flex; align-items: center; gap: 8px; }

.progress-bar-sm {
  width: 60px;
  height: 4px;
  background: hsl(var(--border));
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-text { font-size: 11px; color: hsl(var(--muted-foreground)); }

.progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  border-radius: var(--radius-sm);
  transition: width 0.3s;
}
</style>
