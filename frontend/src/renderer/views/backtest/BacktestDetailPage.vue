<template>
  <PageLayout>
    <template #title>
      <PageTitle
        :title="pageTitle"
        back-to="/backtests"
        back-label="回测中心"
      />
    </template>
    <template #meta>
      <template v-if="currentTask">
        <span
          class="tag"
          :class="statusTagClass(currentTask.status)"
        >{{ statusLabel(currentTask.status) }}</span>
        <span
          class="task-uuid"
          :title="`${currentTask.uuid}（点击复制）`"
          @click="copyUuid"
        >{{ currentTask.uuid.slice(0, 8) }}</span>
        <router-link
          v-if="currentTask.portfolio_id"
          :to="`/portfolios/${currentTask.portfolio_id}`"
          class="portfolio-link"
        >
          组合：{{ portfolioLabel }}
        </router-link>
      </template>
    </template>
    <template #actions>
      <div
        v-if="currentTask"
        class="detail-actions"
      >
        <button
          v-if="canStartByState(currentTask.status)"
          class="btn-primary"
          @click="handleReRun"
        >
          重新运行
        </button>
        <button
          v-if="canStopByState(currentTask.status)"
          class="btn-danger"
          @click="handleStop"
        >
          停止
        </button>
        <button
          v-if="currentTask.status !== 'running'"
          class="btn-danger-outline"
          @click="handleDelete"
        >
          删除
        </button>
      </div>
    </template>

    <!-- 详情内容 -->
    <div
      v-if="detailLoading"
      class="loading-center"
    >
      <div class="spinner" />
    </div>

    <div
      v-else-if="currentTask"
      class="detail-content"
    >
      <!-- 回测区间 + 配置摘要(可折叠):config 来自任务 config_snapshot,口径对齐依据) -->
      <div
        v-if="currentTask.backtest_start_date || currentTask.backtest_end_date"
        class="date-range-bar"
      >
        <span class="date-range-label">回测区间</span>
        <span class="date-range-value">{{ formatShortDate(currentTask.backtest_start_date) }} ~ {{ formatShortDate(currentTask.backtest_end_date) }}</span>
        <button
          v-if="configItems.length"
          class="config-toggle"
          @click="showConfig = !showConfig"
        >
          回测配置 {{ showConfig ? '▲' : '▼' }}
        </button>
      </div>
      <div
        v-if="showConfig && configItems.length"
        class="config-summary"
      >
        <div
          v-for="item in configItems"
          :key="item.label"
          class="config-cell"
        >
          <span class="config-label">{{ item.label }}</span>
          <span class="config-val">{{ item.value }}</span>
        </div>
      </div>

      <!-- 进度 -->
      <div
        v-if="currentTask.status === 'running' || currentTask.status === 'pending'"
        class="card"
      >
        <div class="progress-section">
          <span>{{ currentTask.current_stage || '处理中' }}</span>
          <span>{{ (currentTask.progress || 0).toFixed(1) }}%</span>
        </div>
        <div class="progress-bar-lg">
          <div
            class="progress-fill active"
            :style="{ width: (currentTask.progress || 0) + '%' }"
          />
        </div>
      </div>

      <!-- 详情 tab(L2,状态进 URL query: ?tab=) -->
      <TabsNav
        v-model="activeDetailTab"
        size="small"
        :items="detailTabs"
        class="bt-subtabs"
      />

      <!-- 概览 -->
      <div
        v-if="activeDetailTab === 'overview'"
        class="tab-panel"
      >
        <!-- 净值曲线 -->
        <div class="card">
          <h4>净值曲线</h4>
          <NetValueChart
            v-if="netValueData.length > 0"
            :data="netValueData"
            :benchmark-data="benchmarkData"
            :height="300"
          />
          <p
            v-else
            class="empty-hint"
          >
            暂无净值数据
          </p>
        </div>

        <!-- 指标(hover 出口径说明;'—'=分析器未产出该指标,与真实 0 区分) -->
        <div class="metrics-grid">
          <div
            v-for="m in metrics"
            :key="m.label"
            class="metric-card"
            :class="{ 'metric-empty': m.empty }"
            :title="m.hint"
          >
            <div class="metric-label">
              {{ m.label }}
            </div>
            <div
              class="metric-value"
              :style="m.color ? { color: m.color } : undefined"
            >
              {{ m.value }}
            </div>
          </div>
        </div>

        <!-- 执行统计 -->
        <div class="card">
          <h4>执行统计</h4>
          <div class="exec-stats">
            <span>订单 <strong>{{ currentTask.total_orders || 0 }}</strong></span>
            <span>信号 <strong>{{ currentTask.total_signals || 0 }}</strong></span>
            <span>持仓 <strong>{{ currentTask.total_positions || 0 }}</strong></span>
            <span>事件 <strong>{{ currentTask.total_events || 0 }}</strong></span>
          </div>
        </div>

        <!-- 分析器 -->
        <div
          v-if="analyzers.length > 0"
          class="card"
        >
          <h4>分析器</h4>
          <table class="data-table">
            <thead><tr><th>名称</th><th>最新值</th><th>记录数</th><th>变化</th></tr></thead>
            <tbody>
              <tr
                v-for="a in analyzers"
                :key="a.name"
              >
                <td>
                  <span class="tag tag-blue">{{ a.name }}</span>
                  <!-- 中文名注册名不可读,描述由后端 analyzer 元数据带出 -->
                  <div
                    v-if="a.description"
                    class="analyzer-desc"
                  >
                    {{ a.description }}
                  </div>
                </td>
                <td :style="{ color: getAnalyzerColor(a.name, a.latest_value) }">
                  {{ fmtAnalyzer(a.name, a.latest_value) }}
                </td>
                <td>{{ a.stats?.count || 0 }}</td>
                <td :style="{ color: (a.stats?.change || 0) >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
                  {{ (a.stats?.change || 0) >= 0 ? '↑' : '↓' }} {{ fmtAnalyzer(a.name, Math.abs(a.stats?.change || 0)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 错误 -->
        <div
          v-if="currentTask.error_message"
          class="card card-error"
        >
          <h4>错误信息</h4>
          <pre>{{ currentTask.error_message }}</pre>
        </div>
      </div>

      <!-- 分析器详情 -->
      <div
        v-if="activeDetailTab === 'analyzers'"
        class="tab-panel"
      >
        <div class="card">
          <div
            v-if="analyzerLoading"
            class="loading-center"
          >
            <div class="spinner spinner-sm" />
          </div>
          <template v-else-if="analyzerStats">
            <NetValueChart
              v-if="analyzerChartData.length > 0"
              :data="analyzerChartData"
              :height="250"
            />
            <div class="analyzer-header">
              <select
                v-model="selectedAnalyzer"
                class="form-select"
                @change="loadAnalyzerData"
              >
                <option
                  v-for="a in analyzers"
                  :key="a.name"
                  :value="a.name"
                >
                  {{ a.name }}
                </option>
              </select>
              <!-- 选中项描述由后端 analyzer 元数据带出,帮助理解指标含义 -->
              <span
                v-if="selectedAnalyzerDescription"
                class="analyzer-desc-inline"
              >{{ selectedAnalyzerDescription }}</span>
            </div>
            <div class="stats-row">
              <span>Count: {{ analyzerStats.count }}</span>
              <span>Min: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.min) }}</span>
              <span>Max: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.max) }}</span>
              <span>Avg: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.avg) }}</span>
              <span>Change: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.change) }}</span>
            </div>
            <table
              v-if="analyzerTimeseries.length > 0"
              class="data-table"
            >
              <thead><tr><th>时间</th><th>值</th></tr></thead>
              <tbody>
                <tr
                  v-for="(row, i) in analyzerTimeseries.slice(-50)"
                  :key="i"
                >
                  <td>{{ row.time }}</td>
                  <td :style="{ color: getAnalyzerColor(selectedAnalyzer, row.value) }">
                    {{ fmtAnalyzer(selectedAnalyzer, row.value) }}
                  </td>
                </tr>
              </tbody>
            </table>
            <p
              v-else
              class="empty-hint"
            >
              暂无时序数据
            </p>
          </template>
          <p
            v-else
            class="empty-hint"
          >
            请选择分析器
          </p>
        </div>
      </div>

      <!-- 交易记录 -->
      <div
        v-if="activeDetailTab === 'trades'"
        class="tab-panel"
      >
        <TradesTab
          ref="tradesTabRef"
          :task-uuid="backtestId"
        />
      </div>

      <!-- 日志 -->
      <div
        v-if="activeDetailTab === 'logs'"
        class="tab-panel"
      >
        <LogsTab
          :task-uuid="backtestId"
          :default-range="logDateRange"
        />
      </div>
    </div>

    <!-- 任务不存在 -->
    <EmptyState
      v-else
      description="回测任务不存在"
      action-text="返回列表"
      :on-action="goBack"
    />
    <ConfirmDialog
      v-model:open="confirmOpen"
      :title="confirmTitle"
      :description="confirmDesc"
      danger
      @confirm="onConfirm"
    />
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { backtestApi, portfolioApi } from '@/api'
import type { BacktestTask, AnalyzerInfo } from '@/api'
import { useBacktestStore } from '@/stores'
import { useBacktestStatus } from '@/composables'
import { useWebSocket, useServerEvents, usePolling } from '@/composables'
import { canStartByState, canStopByState } from '@/constants/backtest'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'
import { message } from '@/utils/toast'
import { copyText } from '@/utils/clipboard'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import PageLayout from '@/components/common/PageLayout.vue'
import PageTitle from '@/components/common/PageTitle.vue'
import TabsNav from '@/components/common/TabsNav.vue'
import { formatMoney } from '@/utils/format'
import LogsTab from '@/components/backtest/LogsTab.vue'
import TradesTab from '@/components/backtest/TradesTab.vue'
import {
  formatShortDate, fmtAnalyzer, getAnalyzerColor,
} from '@/composables/useBacktestFormatters'

const route = useRoute()
const router = useRouter()
const backtestStore = useBacktestStore()
const { getTagClass: statusTagClass, getLabel: statusLabel } = useBacktestStatus()

// 防止组件卸载后异步操作继续执行
let disposed = false

const backtestId = computed(() => route.params.uuid as string || '')
const pageTitle = computed(() => currentTask.value?.name || currentTask.value?.uuid?.substring(0, 8) || '回测详情')
// 头部组合链接文案:名称+短id;名称未到位(接口未返回且补拉未回/失败)时退回纯短id
const portfolioLabel = computed(() => {
  const t = currentTask.value
  if (!t?.portfolio_id) return ''
  const id8 = t.portfolio_id.slice(0, 8)
  return t.portfolio_name ? `${t.portfolio_name}（${id8}）` : id8
})

// 回测配置摘要:详情接口 config 字段即 config_snapshot 解析体(初始资金/费率/滑点/频率
// 等),此前页面无处展示,指标无法对口径。ATTITUDE_TYPES: 1=悲观 2=乐观 3=随机。
const showConfig = ref(false)
const ATTITUDE_LABELS: Record<number, string> = { 1: '悲观（不利价成交）', 2: '乐观（有利价成交）', 3: '随机' }
const configItems = computed<{ label: string; value: string }[]>(() => {
  const c: any = (currentTask.value as any)?.config
  if (!c || typeof c !== 'object') return []
  const items: { label: string; value: string }[] = []
  if (c.initial_cash != null) items.push({ label: '初始资金', value: formatMoney(Number(c.initial_cash)) })
  if (c.frequency) items.push({ label: '数据频率', value: String(c.frequency) })
  if (c.commission_rate != null) items.push({ label: '佣金率', value: String(c.commission_rate) })
  if (c.commission_min != null) items.push({ label: '最低佣金', value: String(c.commission_min) })
  if (c.slippage_rate != null) items.push({ label: '滑点率', value: String(c.slippage_rate) })
  if (c.broker_attitude != null) items.push({ label: '成交模型', value: ATTITUDE_LABELS[Number(c.broker_attitude)] || String(c.broker_attitude) })
  if (c.fill_price_policy && c.fill_price_policy !== 'attitude') items.push({ label: '成交价策略', value: String(c.fill_price_policy) })
  if (c.max_position_ratio != null) items.push({ label: '最大仓位比', value: String(c.max_position_ratio) })
  if (c.stop_loss_ratio != null) items.push({ label: '止损比', value: String(c.stop_loss_ratio) })
  if (c.take_profit_ratio != null) items.push({ label: '止盈比', value: String(c.take_profit_ratio) })
  if (c.engine_name) items.push({ label: '引擎', value: String(c.engine_name) })
  return items
})
const copyUuid = async () => {
  const id = currentTask.value?.uuid
  if (!id) return
  // http 局域网部署 clipboard API 不可用,copyText 内含 execCommand 降级
  if (await copyText(id)) message.success('已复制完整 ID')
  else message.info(`ID: ${id}`)
}

// ========== 详情状态 ==========
const currentTask = ref<BacktestTask | null>(null)
const detailLoading = ref(false)
const analyzers = ref<AnalyzerInfo[]>([])
const netValueData = ref<LineData[]>([])
const benchmarkData = ref<LineData[]>([])

// 详情 L2 tab:状态进 URL query(?tab=),可深链/刷新保持/后退自然
const DETAIL_TABS = ['overview', 'analyzers', 'trades', 'logs'] as const
const activeDetailTab = computed<string>({
  get: () => DETAIL_TABS.includes(route.query.tab as any) ? String(route.query.tab) : 'overview',
  set: (v) => router.replace({ query: { ...route.query, tab: v } }),
})

// Analyzer value extraction
const analyzerValue = (name: string): number | null => {
  const a = analyzers.value.find(a => a.name === name)
  return a?.latest_value ?? null
}

const tradeWinRate = computed(() => analyzerValue('trade_win_rate'))
const dailyWinRate = computed(() => analyzerValue('win_rate'))
const profitFactor = computed(() => analyzerValue('profit_factor'))
const avgWinLoss = computed(() => analyzerValue('avg_win_loss_ratio'))
const maxConsLosses = computed(() => analyzerValue('max_consecutive_losses'))
const avgHoldPeriod = computed(() => analyzerValue('avg_holding_period'))
// immediate: 深链直达 ?tab=logs 时 watch 也须 fire(onMounted 不调 loadLogs)
const detailTabs = [
  { key: 'overview', label: '概览' },
  { key: 'analyzers', label: '分析器' },
  { key: 'trades', label: '交易记录' },
  { key: 'logs', label: '日志' },
]

// 日志默认筛选区间(回测起止,截 YYYY-MM-DD——date input 不收带时间的 ISO 串)
const logDateRange = computed(() => {
  const t = currentTask.value
  return {
    start: t?.backtest_start_date ? String(t.backtest_start_date).substring(0, 10) : '',
    end: t?.backtest_end_date ? String(t.backtest_end_date).substring(0, 10) : '',
  }
})

// 分析器详情
const selectedAnalyzer = ref('')
// 选中分析器的一句话描述(后端 analyzer 元数据带出,缺省为空不显示)
const selectedAnalyzerDescription = computed(() =>
  analyzers.value.find(a => a.name === selectedAnalyzer.value)?.description || '')
const analyzerLoading = ref(false)
const analyzerStats = ref<any>(null)
const analyzerTimeseries = ref<any[]>([])
const analyzerChartData = computed<LineData[]>(() =>
  analyzerTimeseries.value.map((r: any) => ({ time: String(r.time).substring(0, 10), value: Number(r.value) }))
)

// 交易记录 tab 组件引用(终态刷新时调 reload 重拉三表)
const tradesTabRef = ref<InstanceType<typeof TradesTab> | null>(null)

// ========== 详情方法 ==========
// silent=true 时不切 detailLoading(不闪 spinner),用于运行中节流刷新
const loadDetail = async (silent = false) => {
  if (!backtestId.value || disposed) return
  if (!silent) detailLoading.value = true
  try {
    const task = await backtestApi.get(backtestId.value)
    if (disposed) return
    const prevName = currentTask.value?.portfolio_name
    const fresh = task

    // 静默刷新沿用已补拉过的组合名,省一次 /portfolios/{id} 往返(限流敏感期少占配额)
    if (silent && prevName && !fresh.portfolio_name) fresh.portfolio_name = prevName
    currentTask.value = fresh
    // 详情接口不带 portfolio_name(仅列表联查有),缺省时补拉组合名,头部展示"名称+短id"
    // skipErrorToast:组合已删是预期降级(保留短 id 展示),不该全局弹 toast——
    // 且 loadDetail 会被多路径触发(进页/WS 重连补齐/轮询终态),不 opt-out 会连环弹
    if (currentTask.value?.portfolio_id && !currentTask.value.portfolio_name) {
      try {
        const p: any = await portfolioApi.get(currentTask.value.portfolio_id, { skipErrorToast: true })
        if (!disposed && p?.name) currentTask.value.portfolio_name = p.name
      } catch { /* 组合可能已删,保留 id 展示 */ }
    }
    // net value
    try {
      const nv = await backtestApi.getNetValue(backtestId.value)
      if (disposed) return
      netValueData.value = (nv?.strategy || []).map((i: any) => ({ time: String(i.time).substring(0, 10), value: i.value }))
      benchmarkData.value = (nv?.benchmark || []).map((i: any) => ({ time: String(i.time).substring(0, 10), value: i.value }))
    } catch { /* net value may not exist */ }
    // analyzers
    try {
      const ar = await backtestApi.getAnalyzers(backtestId.value)
      if (disposed) return
      analyzers.value = ar?.analyzers || []
      if (analyzers.value.length > 0) {
        selectedAnalyzer.value = analyzers.value[0].name
        loadAnalyzerData()
      }
    } catch { /* analyzers may not exist */ }
    // trades(组件挂载时自治加载;此处仅终态/静默刷新场景补拉)
    tradesTabRef.value?.reload()
  } catch (e) {
    console.error('Failed to load detail:', e)
    // silent 刷新失败(如限流 429)保留旧数据续命,不清空页面——清空会让 WS 就地
    // 更新失配、页面假死;仅首次显式加载失败才回退空态
    if (!disposed && !silent) currentTask.value = null
  } finally {
    if (!disposed && !silent) detailLoading.value = false
  }
}

const loadAnalyzerData = async () => {
  if (!backtestId.value || !selectedAnalyzer.value) return
  analyzerLoading.value = true
  try {
    const res = await backtestApi.getAnalyzerData(backtestId.value, selectedAnalyzer.value)
    // request.ts 拦截器已拆包: res = {data:[...], stats}（AnalyzerTimeseriesResponse）
    analyzerStats.value = res?.stats ?? null
    analyzerTimeseries.value = res?.data || []
  } catch {
    analyzerStats.value = null
    analyzerTimeseries.value = []
  } finally {
    analyzerLoading.value = false
  }
}

const handleReRun = () => {
  if (!currentTask.value) return
  openConfirm('确认重新运行', '将重新调度并运行此回测任务，运行结果会被新的一次覆盖。', doReRun)
}

const doReRun = async () => {
  if (!currentTask.value) return
  try {
    const result = await backtestStore.startTask(currentTask.value.uuid)
    console.log('重新运行结果:', result) // 调试日志
    message.success('已重新启动回测')

    if (result?.task_id) {
      // 重新运行后，等待一小段时间让任务状态更新，然后重新加载
      await new Promise(resolve => setTimeout(resolve, 1000))

      // 如果返回的 task_id 与当前页面不同，跳转到新任务
      if (result.task_id !== backtestId.value) {
        console.log('跳转到新任务:', result.task_id) // 调试日志
        router.push(`/backtests/${result.task_id}`)
      } else {
        // 相同任务ID，重新加载详情
        console.log('重新加载当前任务详情') // 调试日志
        await loadDetail()
      }
    } else {
      // 没有返回 task_id，直接重新加载
      await loadDetail()
    }
  } catch (e: any) {
    console.error('重新运行失败:', e) // 调试日志
    message.error(e.response?.data?.detail || '重新运行失败')
  }
}

// WebSocket 订阅:薄事件信封(ADR-046)直接 patch 本地 currentTask。
// 旧路径经 store 往返(tasks 里碰巧有同 id 任务才生效,重跑后常失灵),
// 新路径 entity+id 精确定位,信封 status 已是 REST 同款小写枚举
const TERMINAL_EVENTS = ['backtest.completed', 'backtest.failed', 'backtest.stopped']

function setupWebSocketSubscription() {
  if (unsubscribe) {
    unsubscribe()
    unsubscribe = null
  }

  unsubscribe = on('*', (e) => {
    const t = currentTask.value
    if (!t || e.entity !== 'backtest_task' || e.id !== t.uuid) return

    if (e.data?.progress != null) t.progress = e.data.progress
    if (e.status && e.event !== 'backtest.progress') t.status = e.status as typeof t.status

    // 终态:静默补一次全量(指标/图表/交易记录落定)
    if (TERMINAL_EVENTS.includes(e.event)) {
      loadDetail(true)
      return
    }
    // 运行中:节流 10s 静默刷新图表/统计,兼顾"数据不只在结束后刷新"与不闪屏
    const now = Date.now()
    if (now - lastRunRefresh > 10000) {
      lastRunRefresh = now
      loadDetail(true)
    }
  })
}

// 统一危险操作确认(停止/删除回测)— 替代原生 confirm(),站点风格一致、Electron 下不弹原生框
const confirmOpen = ref(false)
const confirmTitle = ref('')
const confirmDesc = ref('')
const confirmAction = ref<(() => Promise<void> | void) | null>(null)
const openConfirm = (title: string, desc: string, action: () => Promise<void> | void) => {
  confirmTitle.value = title
  confirmDesc.value = desc
  confirmAction.value = action
  confirmOpen.value = true
}
const onConfirm = async () => {
  confirmOpen.value = false
  const fn = confirmAction.value
  confirmAction.value = null
  await fn?.()
}

const handleStop = () => {
  if (!currentTask.value?.uuid) return
  openConfirm('确认停止', '确定要停止此回测？', async () => {
    try {
      await backtestStore.stopTask(currentTask.value!.uuid)
      message.success('已停止')
      loadDetail()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '停止失败')
    }
  })
}

const handleDelete = () => {
  if (!currentTask.value?.uuid) return
  openConfirm('确认删除', '删除后不可恢复，确定要删除？', async () => {
    try {
      await backtestStore.deleteTask(currentTask.value!.uuid)
      message.success('已删除')
      goBack()
    } catch (e: any) {
      message.error(e.response?.data?.detail || '删除失败')
    }
  })
}

const goBack = () => {
  router.push('/backtests')
}

const pnlColor = computed(() => {
  const v = currentTask.value?.total_pnl ?? 0
  return v >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))'
})

// 声明式指标卡片:label/value/color 数据驱动。hint=hover 口径说明(盈亏比 vs 平均
// 盈亏比易混);empty=分析器未产出('—' 灰显,与真实 0 区分,如胜率 0.0%)
const metrics = computed<{ label: string; value: string; color?: string; hint?: string; empty?: boolean }[]>(() => {
  const t = currentTask.value
  const ar = t?.annual_return ?? 0
  const md = t?.max_drawdown ?? 0
  const twr = tradeWinRate.value
  const dwr = dailyWinRate.value
  const pf = profitFactor.value
  const awl = avgWinLoss.value
  const mcl = maxConsLosses.value
  const ahp = avgHoldPeriod.value
  const pos = 'hsl(var(--success))'
  const neg = 'hsl(var(--error))'
  return [
    { label: '最终资产', value: formatMoney(t?.final_portfolio_value ?? 0), hint: '回测结束时组合总资产（现金+持仓市值）' },
    { label: '总盈亏', value: formatMoney(t?.total_pnl ?? 0), color: pnlColor.value, hint: '最终资产 − 初始资金（含手续费）' },
    { label: '年化收益', value: `${(ar * 100).toFixed(2)}%`, color: ar >= 0 ? pos : neg, hint: '按回测区间折算的年化收益率' },
    { label: '夏普比率', value: (t?.sharpe_ratio ?? 0).toFixed(2), hint: '风险调整后收益（超额收益/波动率）' },
    { label: '最大回撤', value: `${(md * 100).toFixed(2)}%`, color: md <= 0.1 ? pos : neg, hint: '净值自峰值的最大回落幅度' },
    { label: '交易胜率', value: twr !== null ? `${(twr * 100).toFixed(1)}%` : '—', color: twr !== null ? (twr >= 0.5 ? pos : neg) : '', empty: twr === null, hint: '按平仓交易笔数统计（trade_win_rate）' },
    { label: '日胜率', value: dwr !== null ? `${(dwr * 100).toFixed(1)}%` : '—', color: dwr !== null ? (dwr >= 0.5 ? pos : neg) : '', empty: dwr === null, hint: '按交易日统计（win_rate）' },
    { label: '盈亏比', value: pf !== null ? pf.toFixed(2) : '—', color: pf !== null ? (pf >= 1 ? pos : neg) : '', empty: pf === null, hint: '利润因子：总盈利/总亏损（profit_factor）' },
    { label: '平均盈亏比', value: awl !== null ? awl.toFixed(2) : '—', color: awl !== null ? (awl >= 1 ? pos : neg) : '', empty: awl === null, hint: '平均每笔盈利/平均每笔亏损（avg_win_loss_ratio）' },
    { label: '最大连续亏损', value: mcl !== null ? `${Math.round(mcl)} 笔` : '—', color: mcl !== null && mcl > 5 ? neg : '', empty: mcl === null, hint: '连续亏损笔数峰值（max_consecutive_losses）' },
    { label: '平均持仓', value: ahp !== null ? `${ahp.toFixed(1)} 天` : '—', empty: ahp === null, hint: '平均每笔持仓天数（avg_holding_period）' },
  ]
})

// ========== WebSocket ==========
const { isConnected } = useWebSocket()
const { on } = useServerEvents()
let unsubscribe: (() => void) | null = null
// 运行中节流静默刷新的时间戳(进度事件 2s 一条,详情全量刷新节流到 10s)
let lastRunRefresh = 0

// ========== 运行态轮询(断线兜底) ==========
// WS 推送是主路径;断线窗口内 5s 轮询顶上(轻量,拉任务本体不走 loadDetail 全家桶),
// 终态时停轮询并补一次全量刷新让指标/图表/交易记录落定
const ACTIVE_STATES = ['created', 'pending', 'running']
const TERMINAL_STATES = ['completed', 'failed', 'stopped']
const pollTaskStatus = async () => {
  if (!backtestId.value || disposed) return stopProgressPolling()
  const s = currentTask.value?.status
  if (!s || !ACTIVE_STATES.includes(s)) return stopProgressPolling()
  try {
    const task = await backtestApi.get(backtestId.value)
    if (disposed) return
    const prev = currentTask.value
    const fresh = task
    // 沿用已补拉过的组合名(详情接口不返回 portfolio_name)
    if (prev?.portfolio_name && !fresh.portfolio_name) fresh.portfolio_name = prev.portfolio_name
    currentTask.value = fresh
    if (TERMINAL_STATES.includes(fresh.status)) {
      stopProgressPolling()
      loadDetail(true)
    }
  } catch { /* 单次失败(如限流 429)静默保留旧值,下轮重试 */ }
}
const { start: startProgressPolling, stop: stopProgressPolling } = usePolling(pollTaskStatus, 5000)
// 轮询反转(ADR-046 设计):连线时 WS 事件是主路径,停轮询并补齐一次断线窗口;
// 断线且任务活跃才轮询。前提是 isConnected 真实——新版 useWebSocket 的
// 65s watchdog(半开检测)+无限退避重连保证断线终会翻转 isConnected,
// 旧 bundle(3 次重试耗尽/无 watchdog)不满足该前提,须刷新页面载入
watch(isConnected, (connected) => {
  if (connected) {
    stopProgressPolling()
    if (backtestId.value) loadDetail(true)
  } else {
    const s = currentTask.value?.status
    if (s && ACTIVE_STATES.includes(s)) startProgressPolling()
    else stopProgressPolling()
  }
}, { immediate: true })
// 重跑等场景终态→活跃翻转时,断线下重启兜底轮询(连线时上方 watch 已处理)
watch(() => currentTask.value?.status, (s) => {
  if (s && ACTIVE_STATES.includes(s) && !isConnected.value) startProgressPolling()
  else stopProgressPolling()
})

onMounted(() => {
  loadDetail()

  setupWebSocketSubscription()
})

watch(backtestId, (newVal) => {
  if (newVal) loadDetail()
})

onUnmounted(() => {
  disposed = true
  backtestStore.clearCurrentTask()
  if (unsubscribe) unsubscribe()
})
</script>

<style scoped>
.detail-content {
  flex: 1;
  overflow-y: auto;
  /* 窄窗口下宽表(持仓7列/订单7列)应可滚动而非被裁切 */
  overflow-x: auto;
}

.detail-actions { display: flex; gap: 8px; }

.task-uuid {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-family: monospace;
  user-select: all;
}

.portfolio-link {
  font-size: 12px;
  color: hsl(var(--primary));
}

/* Date range bar */
.date-range-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  margin-bottom: 12px;
}
.date-range-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}
.date-range-value {
  font-size: 13px;
  color: hsl(var(--foreground));
  font-family: monospace;
}

/* 回测配置摘要(折叠展开区) */
.config-toggle {
  margin-left: auto;
  background: none;
  border: none;
  color: hsl(var(--primary));
  font-size: 12px;
  cursor: pointer;
  padding: 2px 6px;
}
.config-toggle:hover { text-decoration: underline; }

.config-summary {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 8px 16px;
  padding: 10px 14px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-top: none;
  border-radius: 0 0 var(--radius) var(--radius);
  margin-bottom: 12px;
}
.config-cell { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.config-label { font-size: 11px; color: hsl(var(--muted-foreground)); }
.config-val {
  font-size: 13px;
  color: hsl(var(--foreground));
  font-family: monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 指标卡空态(分析器未产出,与真实 0 区分) */
.metric-empty, .metric-empty .metric-value { color: hsl(var(--muted-foreground) / 0.7); }

/* 血缘跳转目标行高亮 */
.row-highlight {
  animation: row-flash 2.5s ease-out;
}
@keyframes row-flash {
  0%, 60% { background: hsl(var(--primary) / 0.18); }
  100% { background: transparent; }
}


/* Progress section */
.progress-section {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.progress-bar-lg {
  height: 6px;
  background: hsl(var(--border));
  border-radius: var(--radius-sm);
  overflow: hidden;
  margin-top: 8px;
}

.progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  border-radius: var(--radius-sm);
  transition: width 0.3s;
}

.progress-fill.active {
  background: linear-gradient(90deg, hsl(var(--primary)), hsl(var(--primary)));
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* 详情内嵌 tab(L2/L3) */
.bt-subtabs { margin-bottom: 16px; }

.tab-panel { flex: 1; }

/* Tags */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}

.text-red { color: hsl(var(--error)); }

/* Metrics grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 12px;
}

.metric-label { font-size: 11px; color: hsl(var(--muted-foreground)); margin-bottom: 4px; }
.metric-value { font-size: 18px; font-weight: 600; color: hsl(var(--foreground)); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }

/* Card */
.card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 14px;
  margin-bottom: 12px;
}

.card h4 {
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0 0 10px 0;
}

.card-error pre {
  color: hsl(var(--error));
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
}

.card-error { border-color: hsl(var(--error) / 0.3); }

/* Exec stats */
.exec-stats {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.exec-stats strong { color: hsl(var(--foreground)); }

/* Stats row */
.stats-row {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-bottom: 12px;
  flex-wrap: wrap;
}

/* Analyzer header */
.analyzer-header { margin-bottom: 12px; }
/* 分析器描述:概览表格名称下方小字 + 详情页 select 旁行内说明 */
.analyzer-desc {
  margin-top: 4px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  line-height: 1.4;
}
.analyzer-desc-inline {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.form-select {
  width: 100%; padding: 8px 12px;
  background: hsl(var(--card)); border: 1px solid hsl(var(--border));
  border-radius: var(--radius); color: hsl(var(--foreground)); font-size: 14px;
  appearance: auto;
}

.form-input {
  width: 100%;
  padding: 7px 10px;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
}

.form-input:focus, .form-select:focus { border-color: hsl(var(--primary)); outline: none; }

.btn-danger {
  padding: 6px 14px;
  background: hsl(var(--error));
  border: none;
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
}

.btn-danger-outline {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid hsl(var(--error));
  border-radius: var(--radius-sm);
  color: hsl(var(--error));
  font-size: 13px;
  cursor: pointer;
}

/* Data table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--card));
  text-align: left;
  padding: 6px 8px;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
  border-bottom: 1px solid hsl(var(--border));
}

.data-table td {
  padding: 6px 8px;
  color: hsl(var(--foreground));
  border-bottom: 1px solid hsl(var(--foreground) / 0.03);
}

.data-table tr:hover td { background: hsl(var(--foreground) / 0.02); }

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

.spinner-sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin { to { transform: rotate(360deg); } }
.empty-hint {
  /* muted-foreground 已是次级色,不再叠 opacity 双重压暗(light 下对比不足) */
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}



/* Responsive */
@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
