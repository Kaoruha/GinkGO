<template>
  <div class="backtest-tab">
    <!-- ========== 列表视图 ========== -->
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <SegmentedControl
          :model-value="filterStatus"
          :options="statusOptions"
          @update:model-value="setFilter"
        />
        <div class="search-box">
          <input
            v-model="searchKeyword"
            type="search"
            placeholder="搜索任务..."
            class="search-input"
            @keyup.enter="loadList()"
          />
        </div>
      </div>
      <button class="btn-primary" @click="showCreateModal = true">新建回测</button>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="loading-center"><div class="spinner"></div></div>

    <!-- 空状态 -->
    <EmptyState v-else-if="tasks.length === 0" description="暂无回测任务" action-text="创建第一个回测" :on-action="() => showCreateModal = true" />

    <!-- 任务卡片列表 -->
    <div v-else class="task-list">
      <div
        v-for="task in tasks"
        :key="task.uuid"
        class="task-card"
        @click="viewDetail(task.uuid)"
      >
        <div class="task-card-main">
          <div class="task-name">
            {{ task.name || '(未命名)' }}
            <span class="task-uuid" :title="task.uuid">{{ task.uuid.slice(0, 8) }}</span>
            <!-- PnL 主锚点:9 项指标平铺无主次,收益数字提级放大,其余降为次级 -->
            <span class="pnl-anchor" :style="{ color: getPnLColor(task.total_pnl) }" title="总盈亏（最终资产 − 初始资金）">
              {{ task.total_pnl > 0 ? '+' : '' }}{{ formatDecimal(task.total_pnl) }}
            </span>
          </div>
          <div v-if="task.backtest_start_date" class="task-date-range">{{ formatShortDate(task.backtest_start_date) }} ~ {{ formatShortDate(task.backtest_end_date) }}</div>
          <div class="task-meta">
            <span class="tag" :class="statusTagClass(task.status)">{{ statusLabel(task.status) }}</span>
            <span v-if="task.status === 'running' || task.status === 'pending'" class="progress-info">
              <div class="progress-bar-sm"><div class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></div></div>
              <span class="progress-text">{{ (task.progress || 0).toFixed(0) }}%</span>
            </span>
            <span class="meta-item" :style="{ color: getSharpeColor(task.sharpe_ratio) }">Sharpe {{ formatDecimal(task.sharpe_ratio) }}</span>
            <span class="meta-item" :style="{ color: getDrawdownColor(task.max_drawdown) }">回撤 {{ formatPercent(task.max_drawdown) }}</span>
            <span class="meta-item">年化 {{ formatPercent(task.annual_return) }}</span>
            <span class="meta-item">胜率 {{ formatPercent(task.win_rate) }}</span>
            <span class="meta-item">{{ task.total_orders || 0 }} 单</span>
            <span class="meta-item">{{ task.total_signals || 0 }} 信号</span>
          </div>
        </div>
        <div class="task-card-right">
          <span class="task-date">{{ formatShortDate(task.created_at) }}</span>
          <div class="task-actions" @click.stop>
            <button v-if="canStartByState(task.status)" class="link-btn" @click="handleStart(task)">启动</button>
            <button v-if="canStopByState(task.status)" class="link-btn link-danger" @click="handleStop(task)">停止</button>
            <button v-if="canCancelByState(task.status)" class="link-btn" @click="handleCancel(task)">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="tasks.length > 0" class="pagination">
      <button class="btn-sm" :disabled="page === 0" @click="page--; loadList()">上一页</button>
      <span class="page-info">{{ page * size + 1 }}-{{ Math.min((page + 1) * size, total) }} / {{ total }}</span>
      <button class="btn-sm" :disabled="(page + 1) * size >= total" @click="page++; loadList()">下一页</button>
    </div>

    <!-- 创建模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="showCreateModal = false">
      <div class="modal-box">
        <div class="modal-header">
          <h3>新建回测</h3>
          <button class="btn-close" @click="showCreateModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-item">
            <label>任务名称</label>
            <input v-model="createForm.name" type="text" placeholder="例如：沪深300回测" class="form-input" />
          </div>
          <div class="form-row">
            <div class="form-item">
              <label>开始日期</label>
              <div class="date-field" @click="startPickerOpen = !startPickerOpen">
                <span :class="{ placeholder: !createForm.start_date }">{{ createForm.start_date || '选择日期' }}</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                <div v-if="startPickerOpen" class="picker-panel" @click.stop>
                  <div class="picker-header">
                    <button type="button" class="picker-nav" @click="startPickerMonth--">‹</button>
                    <span class="picker-title">{{ startPickerYear }}年{{ startPickerMonth + 1 }}月</span>
                    <button type="button" class="picker-nav" @click="startPickerMonth++">›</button>
                  </div>
                  <div class="picker-weekdays">
                    <span v-for="d in ['一','二','三','四','五','六','日']" :key="d" class="picker-wd">{{ d }}</span>
                  </div>
                  <div class="picker-days">
                    <button
                      v-for="(day, i) in startPickerDays"
                      :key="i"
                      type="button"
                      class="picker-day"
                      :class="{
                        empty: !day,
                        selected: day && createForm.start_date === formatPickerDay(day, startPickerYear, startPickerMonth),
                        today: day && isToday(day, startPickerYear, startPickerMonth)
                      }"
                      :disabled="!day"
                      @click="if (day) { createForm.start_date = formatPickerDay(day, startPickerYear, startPickerMonth); startPickerOpen = false }"
                    >{{ day || '' }}</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="form-item">
              <label>结束日期</label>
              <div class="date-field" @click="endPickerOpen = !endPickerOpen">
                <span :class="{ placeholder: !createForm.end_date }">{{ createForm.end_date || '选择日期' }}</span>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                <div v-if="endPickerOpen" class="picker-panel" @click.stop>
                  <div class="picker-header">
                    <button type="button" class="picker-nav" @click="endPickerMonth--">‹</button>
                    <span class="picker-title">{{ endPickerYear }}年{{ endPickerMonth + 1 }}月</span>
                    <button type="button" class="picker-nav" @click="endPickerMonth++">›</button>
                  </div>
                  <div class="picker-weekdays">
                    <span v-for="d in ['一','二','三','四','五','六','日']" :key="d" class="picker-wd">{{ d }}</span>
                  </div>
                  <div class="picker-days">
                    <button
                      v-for="(day, i) in endPickerDays"
                      :key="i"
                      type="button"
                      class="picker-day"
                      :class="{
                        empty: !day,
                        selected: day && createForm.end_date === formatPickerDay(day, endPickerYear, endPickerMonth),
                        today: day && isToday(day, endPickerYear, endPickerMonth)
                      }"
                      :disabled="!day"
                      @click="if (day) { createForm.end_date = formatPickerDay(day, endPickerYear, endPickerMonth); endPickerOpen = false }"
                    >{{ day || '' }}</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="form-item">
            <label>初始资金</label>
            <input :value="formatCash(createForm.initial_cash)" type="text" inputmode="numeric" class="form-input" placeholder="1,000,000" @input="onCashInput($event)" @blur="onCashBlur" />
          </div>
          <!-- 高级设置:费率/滑点/频率等成本与口径参数。留空=后端默认(占位符注明),
               不显式传值避免覆盖快照默认;频率与 CLI 对齐(#5386) -->
          <div class="form-item advanced">
            <button type="button" class="advanced-toggle" @click="advancedOpen = !advancedOpen">
              高级设置（费率/滑点/频率）{{ advancedOpen ? '▲' : '▼' }}
            </button>
            <div v-if="advancedOpen" class="advanced-body">
              <div class="form-row">
                <div class="form-item">
                  <label>佣金率</label>
                  <input v-model="createForm.commission_rate" type="text" class="form-input" placeholder="0.0003" />
                </div>
                <div class="form-item">
                  <label>滑点率</label>
                  <input v-model="createForm.slippage_rate" type="text" class="form-input" placeholder="0.0001" />
                </div>
              </div>
              <div class="form-row">
                <div class="form-item">
                  <label>最低佣金（元）</label>
                  <input v-model="createForm.commission_min" type="text" class="form-input" placeholder="5" />
                </div>
                <div class="form-item">
                  <label>数据频率</label>
                  <select v-model="createForm.frequency" class="form-select">
                    <option value="">日频（默认）</option>
                    <option value="1MIN">1 分钟</option>
                    <option value="5MIN">5 分钟</option>
                    <option value="15MIN">15 分钟</option>
                    <option value="30MIN">30 分钟</option>
                    <option value="60MIN">60 分钟</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="showCreateModal = false">取消</button>
          <button class="btn-primary" :disabled="creating" @click="handleCreate">
            {{ creating ? '创建中...' : '创建并启动' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { backtestApi } from '@/api'
import type { BacktestTask } from '@/api'
import { useBacktestStore } from '@/stores'
import { useBacktestStatus } from '@/composables'
import { useServerEvents } from '@/composables'
import { canStartByState, canStopByState, canCancelByState, BACKTEST_DEFAULT_RANGE_MONTHS } from '@/constants/backtest'
import { message } from '@/utils/toast'
import { formatPercent } from '@/utils/format'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import {
  formatShortDate, formatDecimal, getPnLColor, getSharpeColor, getDrawdownColor,
} from '@/composables/useBacktestFormatters'

const route = useRoute()
const router = useRouter()
const backtestStore = useBacktestStore()
const { getTagClass: statusTagClass, getLabel: statusLabel } = useBacktestStatus()

// 防止组件卸载后异步操作继续执行
let disposed = false

// ========== 路由参数 ==========
const portfolioId = computed(() => route.params.id as string)

// ========== 列表状态 ==========
const tasks = ref<BacktestTask[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(0)
const size = ref(20)
const filterStatus = ref('')
const searchKeyword = ref('')

const statusOptions = [
  { key: '', label: '全部' },
  { key: 'running', label: '进行中' },
  { key: 'completed', label: '已完成' },
  { key: 'stopped', label: '已停止' },
  { key: 'failed', label: '失败' },
  { key: 'pending', label: '排队中' },
]

// ========== 创建状态 ==========
const showCreateModal = ref(false)
const creating = ref(false)

watch(showCreateModal, (open) => {
  if (open && !createForm.value.start_date) {
    const { start, end } = defaultDateRange()
    createForm.value.start_date = start
    createForm.value.end_date = end
    startPickerYear.value = new Date(start).getFullYear()
    startPickerMonth.value = new Date(start).getMonth()
  }
})
const defaultDateRange = () => {
  const today = new Date()
  const past = new Date(today)
  past.setMonth(past.getMonth() - BACKTEST_DEFAULT_RANGE_MONTHS)
  const fmt = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  return { start: fmt(past), end: fmt(today) }
}
const createForm = ref({
  name: '', start_date: '', end_date: '', initial_cash: 1000000,
  // 高级参数:空串=不传(走后端默认),填了才进 engine_config
  commission_rate: '', slippage_rate: '', commission_min: '', frequency: '',
})
const advancedOpen = ref(false)

/** 字符串→number|undefined;非法输入返回 NaN 供调用方拦截 */
const parseNum = (s: string) => (s.trim() === '' ? undefined : parseFloat(s))

function formatCash(val: number | string) {
  const n = typeof val === 'string' ? parseInt(val.replace(/,/g, ''), 10) : val
  if (isNaN(n)) return ''
  return n.toLocaleString('en-US')
}

function onCashInput(e: Event) {
  const raw = (e.target as HTMLInputElement).value.replace(/,/g, '')
  const n = parseInt(raw, 10)
  createForm.value.initial_cash = isNaN(n) ? 0 : n
}

function onCashBlur() {
  // Re-format on blur in case partial input
}

// Date picker state
const startPickerOpen = ref(false)
const endPickerOpen = ref(false)
const now = new Date()
const startPickerYear = ref(now.getFullYear())
const startPickerMonth = ref(now.getMonth())
const endPickerYear = ref(now.getFullYear())
const endPickerMonth = ref(now.getMonth())

watch(startPickerMonth, (v) => {
  if (v < 0) { startPickerMonth.value = 11; startPickerYear.value-- }
  if (v > 11) { startPickerMonth.value = 0; startPickerYear.value++ }
})
watch(endPickerMonth, (v) => {
  if (v < 0) { endPickerMonth.value = 11; endPickerYear.value-- }
  if (v > 11) { endPickerMonth.value = 0; endPickerYear.value++ }
})

function getDaysInMonth(year: number, month: number): (number | null)[] {
  const firstDay = new Date(year, month, 1).getDay()
  const offset = firstDay === 0 ? 6 : firstDay - 1 // Monday=0
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = []
  for (let i = 0; i < offset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length < 42) cells.push(null)
  return cells
}

const startPickerDays = computed(() => getDaysInMonth(startPickerYear.value, startPickerMonth.value))
const endPickerDays = computed(() => getDaysInMonth(endPickerYear.value, endPickerMonth.value))

const formatPickerDay = (day: number, year?: number, month?: number) => {
  const y = year ?? startPickerYear.value
  const mo = month ?? startPickerMonth.value
  const m = String(mo + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const isToday = (day: number, year?: number, month?: number) => {
  const t = new Date()
  const y = year ?? startPickerYear.value
  const mo = month ?? startPickerMonth.value
  return day === t.getDate() && mo === t.getMonth() && y === t.getFullYear()
}

// ========== 列表方法 ==========
const loadList = async (opts?: { silent?: boolean }) => {
  if (disposed) return
  if (!opts?.silent) loading.value = true
  try {
    const params: any = { page: page.value + 1, page_size: size.value, portfolio_id: portfolioId.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchKeyword.value) params.keyword = searchKeyword.value
    const res = await backtestApi.list(params)
    if (disposed) return
    tasks.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    // 静默失败会让列表伪装成"暂无回测",须提示(轮询 silent 刷新不弹,避免刷屏)
    console.error('Failed to load backtests:', e)
    if (!opts?.silent) message.error('回测列表加载失败，请稍后重试')
  } finally {
    if (!disposed && !opts?.silent) loading.value = false
  }
}

const setFilter = (val: string) => {
  filterStatus.value = val
  page.value = 0
  loadList()
}

// 详情已独立为 /backtests/:uuid 页面(BacktestDetailPage)
const viewDetail = (uuid: string) => {
  router.push(`/backtests/${uuid}`)
}

const handleStart = async (task: BacktestTask) => {
  try {
    let params: any = {}
    if (task.config_snapshot) {
      const config = typeof task.config_snapshot === 'string' ? JSON.parse(task.config_snapshot) : task.config_snapshot
      params = { start_date: config.start_date, end_date: config.end_date }
    }
    await backtestApi.start(task.uuid, params)
    message.success('任务已启动')
    loadList()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '启动失败')
  }
}

const handleStop = async (task: BacktestTask) => {
  try {
    await backtestStore.stopTask(task.uuid)
    message.success('任务已停止')
    loadList()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '停止失败')
  }
}

const handleCancel = async (task: BacktestTask) => {
  try {
    await backtestStore.cancelTask(task.uuid)
    message.success('任务已取消')
    loadList()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '取消失败')
  }
}

const handleCreate = async () => {
  if (!createForm.value.name) {
    message.warning('请输入任务名称')
    return
  }
  if (!createForm.value.start_date || !createForm.value.end_date) {
    message.warning('请选择日期范围')
    return
  }
  // 高级参数校验:填了但非法须当场报,静默丢弃会让用户以为配置生效
  const advFields: [keyof typeof createForm.value, string][] = [
    ['commission_rate', '佣金率'], ['slippage_rate', '滑点率'], ['commission_min', '最低佣金'],
  ]
  const advNums: Record<string, number | undefined> = {}
  for (const [key, label] of advFields) {
    const v = parseNum(String(createForm.value[key]))
    if (Number.isNaN(v)) { message.warning(`${label}须为数字`); return }
    advNums[key] = v
  }
  creating.value = true
  try {
    const task = await backtestStore.createTask({
      name: createForm.value.name,
      portfolio_uuids: [portfolioId.value],
      engine_config: {
        start_date: createForm.value.start_date,
        end_date: createForm.value.end_date,
        initial_cash: createForm.value.initial_cash || undefined,
        commission_rate: advNums.commission_rate,
        slippage_rate: advNums.slippage_rate,
        commission_min: advNums.commission_min,
        frequency: createForm.value.frequency || undefined,
      },
    })
    if (task?.uuid) {
      await backtestStore.startTask(task.uuid)
    }
    message.success('回测任务已创建并启动')
    showCreateModal.value = false
    const { start, end } = defaultDateRange()
    createForm.value = { name: '', start_date: start, end_date: end, initial_cash: 1000000, commission_rate: '', slippage_rate: '', commission_min: '', frequency: '' }
    loadList()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

// ========== WebSocket ==========
// 薄事件 → 按 key trailing 合并刷新(多任务事件风暴塌缩成一次列表拉取,ADR-046)
const { on, onReconnect, scheduleRefetch } = useServerEvents()
let unsubscribe: (() => void) | null = null
const refetchList = () => scheduleRefetch('backtest-tab-list', () => loadList({ silent: true }))

onMounted(() => {
  loadList()
  if (route.query.action === 'create') {
    showCreateModal.value = true
    router.replace({ query: {} })
  }

  const offs = [
    on('*', (e) => {
      if (e.entity !== 'backtest_task') return
      refetchList()
    }),
    // 重连补齐:断线窗口内丢失的事件靠幂等全量拉取兜底
    onReconnect(refetchList),
  ]
  unsubscribe = () => offs.forEach(off => off())
})

onUnmounted(() => {
  disposed = true
  if (unsubscribe) unsubscribe()
})
</script>

<style scoped>
.backtest-tab {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.search-input {
  padding: 5px 10px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
  width: 160px;
}

.search-input:focus { border-color: hsl(var(--primary)); outline: none; }

/* Buttons */

.btn-secondary {
  padding: 6px 14px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
}

.btn-sm {
  padding: 4px 10px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
  cursor: pointer;
}

.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-close { background: none; border: none; color: hsl(var(--muted-foreground)); font-size: 18px; cursor: pointer; }
.btn-close:hover { color: hsl(var(--foreground)); }

/* Link button */
.link-btn {
  background: none;
  border: none;
  color: hsl(var(--primary));
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
}

.link-btn:hover { color: hsl(var(--primary)); }
.link-btn.link-danger { color: hsl(var(--error)); }
.link-btn.link-danger:hover { color: hsl(var(--error)); }

/* Task list */
.task-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  cursor: pointer;
  transition: all 0.2s;
}

.task-card:hover { border-color: hsl(var(--secondary)); background: hsl(var(--card)); }

.task-card-main { flex: 1; min-width: 0; }

.task-name {
  font-size: 14px;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-uuid {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-family: monospace;
  margin-left: 6px;
  user-select: all;
}

/* PnL 主锚点:随任务名行右对齐放大,收益一眼可辨 */
.pnl-anchor {
  float: right;
  font-size: 17px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  margin-left: 12px;
}

/* 高级设置折叠区 */
.advanced { margin-bottom: 4px; }
.advanced-toggle {
  background: none;
  border: none;
  color: hsl(var(--primary));
  font-size: 12px;
  cursor: pointer;
  padding: 4px 0;
}
.advanced-toggle:hover { text-decoration: underline; }
.advanced-body { padding-top: 8px; }

.task-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item { font-size: 12px; color: hsl(var(--muted-foreground)); }
.task-date-range {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-top: 2px;
  margin-bottom: 4px;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
}

.task-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 16px;
}

.task-date { font-size: 11px; color: hsl(var(--muted-foreground)); }

.task-actions { display: flex; gap: 4px; }

/* Progress bar small */
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

/* Tags */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

.tag-processing { background: hsl(var(--primary) / 0.15); color: hsl(var(--primary)); }

.text-green { color: hsl(var(--success)); }
.text-red { color: hsl(var(--error)); }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
  flex-shrink: 0;
}

.page-info { font-size: 12px; color: hsl(var(--muted-foreground)); }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  overflow: visible;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.modal-header h3 { margin: 0; color: hsl(var(--foreground)); font-size: 16px; }

.modal-body { padding: 20px; overflow: visible; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid hsl(var(--border));
}

/* Form */
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 12px; color: hsl(var(--muted-foreground)); margin-bottom: 4px; }

.form-input, .form-select {
  width: 100%;
  padding: 7px 10px;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
}

.form-input:focus, .form-select:focus { border-color: hsl(var(--primary)); outline: none; }

.form-row { display: flex; gap: 12px; }
.form-row .form-item { flex: 1; }

/* Loading */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
/* Date field */
.date-field {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: hsl(var(--foreground));
}

.date-field .placeholder { color: hsl(var(--muted-foreground)); }
.date-field svg { color: hsl(var(--muted-foreground)); flex-shrink: 0; }

/* Picker panel */
.picker-panel {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 10px;
  z-index: 1100;
  box-shadow: var(--shadow-lg);
  width: 252px;
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.picker-title {
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.picker-nav {
  background: none;
  border: none;
  color: hsl(var(--muted-foreground));
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.picker-nav:hover { color: hsl(var(--foreground)); background: hsl(var(--border)); }

.picker-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  margin-bottom: 4px;
}

.picker-wd {
  text-align: center;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
  height: 24px;
  line-height: 24px;
}

.picker-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.picker-day {
  width: 32px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: none;
  cursor: pointer;
  margin: 1px auto;
}

.picker-day:hover:not(:disabled) { background: hsl(var(--border)); color: hsl(var(--foreground)); }
.picker-day:disabled { visibility: hidden; }
.picker-day.selected { background: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }
.picker-day.today { font-weight: 700; color: hsl(var(--primary)); }
.picker-day.today.selected { color: hsl(var(--primary-foreground)); }

/* Responsive */
@media (max-width: 768px) {
  .toolbar { flex-wrap: wrap; }
}
</style>
