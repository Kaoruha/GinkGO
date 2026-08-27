<template>
  <PageLayout>
    <template #title>
      概览
    </template>
    <template #meta>
      <span
        v-if="lastUpdated"
        class="updated-at"
      >更新于 {{ lastUpdated }}</span>
    </template>
    <template #actions>
      <div class="quick-actions">
        <button
          class="btn btn-secondary"
          @click="$router.push('/data/sync')"
        >
          数据同步
        </button>
        <button
          class="btn btn-secondary"
          @click="$router.push('/portfolios')"
        >
          创建组合
        </button>
        <button
          class="btn btn-secondary"
          :disabled="loading"
          @click="fetchDashboardData"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            :class="{ 'spin': loading }"
          >
            <path d="M21 12a9 9 0 1 1-2.64-6.36" />
            <polyline points="21 3 21 9 15 9" />
          </svg>
          刷新
        </button>
      </div>
    </template>

    <div class="page-content">
      <!-- 系统状态卡片(配置数组见 script statCards) -->
      <div
        class="stats-grid m-stagger"
        data-testid="stats-grid"
      >
        <div
          v-for="card in statCards"
          :key="card.key"
          class="stat-card"
          :data-testid="card.testid"
        >
          <div class="stat-icon">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              v-html="STAT_ICONS[card.key]"
            />
          </div>
          <div class="stat-content">
            <div class="stat-label">
              {{ card.label }}
            </div>
            <div class="stat-value">
              <template v-if="card.value !== null">
                {{ card.value }} <span
                  v-if="card.suffix"
                  class="stat-suffix"
                >{{ card.suffix }}</span>
              </template>
              <template v-else>
                --
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 4阶段概览(配置数组见 script stageCards) -->
      <div
        class="stages-grid"
        data-testid="stages-grid"
      >
        <div
          v-for="card in stageCards"
          :key="card.key"
          :class="['stage-card', card.cls]"
          :data-testid="card.testid"
          @click="$router.push(card.to)"
        >
          <div class="stage-header">
            <h3>{{ card.title }}</h3>
          </div>
          <div class="stage-stats">
            <div
              v-for="s in card.stats"
              :key="s.label"
              class="stage-stat"
            >
              <span class="stat-label">{{ s.label }}</span>
              <span
                class="stat-number"
                :class="{ 'is-running': s.running }"
              >{{ s.value }}</span>
            </div>
          </div>
          <span
            class="stage-link"
            :data-testid="card.linkTestid"
          >{{ card.link }}</span>
        </div>
      </div>

      <!-- 数据面板:收益对比 + 最近回测 -->
      <div
        class="panels-grid"
        data-testid="panels-grid"
      >
        <div
          class="panel-card"
          data-testid="panel-returns"
        >
          <div class="panel-header">
            <h3>组合年化收益对比</h3>
            <button
              class="list-link"
              @click="$router.push('/portfolio')"
            >
              管理组合 →
            </button>
          </div>
          <p
            v-if="loading"
            class="loading-text"
          >
            加载中...
          </p>
          <template v-else-if="portfolios.length > 0">
            <div
              v-for="p in portfolios.slice(0, 6)"
              :key="p.uuid"
              class="return-row"
              @click="$router.push(`/portfolio/${p.uuid}`)"
            >
              <span
                class="return-name"
                :title="p.name"
              >{{ p.name }}</span>
              <div class="return-track">
                <div
                  class="return-bar"
                  :class="barClass(p.annual_return)"
                  :style="{ width: barWidth(p.annual_return) + '%' }"
                />
              </div>
              <span
                class="return-val"
                :class="returnClass(p.annual_return)"
              >{{ fmtPercent(p.annual_return) }}</span>
            </div>
          </template>
          <EmptyState
            v-else
            description="暂无组合数据"
          />
        </div>

        <div
          class="panel-card"
          data-testid="panel-recent-backtests"
        >
          <div class="panel-header">
            <h3>最近回测</h3>
            <button
              class="list-link"
              @click="$router.push('/backtests')"
            >
              全部 →
            </button>
          </div>
          <!-- 健康度:近100条状态分布,失败>0 红显 -->
          <div
            v-if="btHealth.total > 0"
            class="bt-health"
            title="近100条回测状态统计"
          >
            <span class="bh-item"><span class="bh-dot bh-ok" />完成 {{ btHealth.completed }}</span>
            <span
              class="bh-item"
              :class="{ 'bh-err-text': btHealth.failed > 0 }"
            ><span class="bh-dot bh-err" />失败 {{ btHealth.failed }}</span>
            <span class="bh-item"><span class="bh-dot bh-run" />进行中 {{ btHealth.active }}</span>
            <span class="bh-scope">共{{ btHealth.total }}条</span>
          </div>
          <p
            v-if="loading"
            class="loading-text"
          >
            加载中...
          </p>
          <template v-else-if="recentBacktests.length > 0">
            <div
              v-for="t in recentBacktests"
              :key="t.uuid"
              class="recent-row"
              @click="$router.push(`/backtests/${t.uuid}`)"
            >
              <span
                class="recent-name"
                :title="t.name"
              >{{ t.name || t.uuid.substring(0, 8) }}</span>
              <span
                class="tag"
                :class="btTagClass(t.status)"
              >{{ btStatusLabel(t.status) }}</span>
              <span
                v-if="t.status === 'running'"
                class="recent-prog"
              >{{ (t.progress || 0).toFixed(0) }}%</span>
              <span
                class="recent-pnl"
                :style="{ color: getPnLColor(t.total_pnl) }"
              >{{ formatDecimal(t.total_pnl) }}</span>
              <span
                class="recent-date"
                :title="t.update_at || t.created_at"
              >{{ formatRelativeTime(t.update_at || t.created_at) }}</span>
            </div>
          </template>
          <EmptyState
            v-else
            description="暂无回测任务"
            action-text="去创建 →"
            :on-action="() => $router.push('/backtests')"
          />
        </div>
      </div>

      <!-- 数据新鲜度:四类数据最近一次同步状态 -->
      <div
        class="freshness-card"
        data-testid="panel-data-freshness"
        @click="$router.push('/data')"
      >
        <div class="freshness-header">
          <h3>数据新鲜度</h3>
          <button class="list-link">
            数据管理 →
          </button>
        </div>
        <p
          v-if="loading"
          class="loading-text"
        >
          加载中...
        </p>
        <div
          v-else
          class="freshness-grid"
        >
          <div
            v-for="f in freshnessRows"
            :key="f.type"
            class="freshness-cell"
          >
            <span
              class="freshness-dot"
              :class="`dot-${f.level}`"
            />
            <div class="freshness-info">
              <span class="freshness-type">{{ f.label }}</span>
              <span
                class="freshness-time"
                :title="f.rawTime"
              >{{ f.time }}</span>
            </div>
            <span
              class="freshness-status"
              :class="`st-${f.level}`"
            >{{ f.statusLabel }}</span>
          </div>
        </div>
      </div>

      <!-- Portfolio 列表 -->
      <div
        v-if="portfolios.length > 0"
        class="portfolio-list-card"
      >
        <div class="list-header">
          <h3>Portfolio 列表</h3>
          <button
            class="list-link"
            @click="$router.push('/portfolio')"
          >
            查看全部 →
          </button>
        </div>
        <div class="portfolio-table">
          <div class="table-row table-header-row">
            <span class="col-name">名称</span>
            <span class="col-mode">模式</span>
            <span class="col-state">状态</span>
            <span class="col-num">年化收益</span>
            <span class="col-num">最大回撤</span>
          </div>
          <div
            v-for="p in portfolios.slice(0, 8)"
            :key="p.uuid"
            class="table-row"
            @click="$router.push(`/portfolio/${p.uuid}`)"
          >
            <span class="col-name">{{ p.name }}</span>
            <span class="col-mode"><span
              class="tag"
              :class="modeTagClass(p.mode)"
            >{{ modeLabel(p.mode) }}</span></span>
            <span class="col-state">
              <span
                class="badge"
                :class="stateClass(p.state)"
              >{{ stateLabel(p.state) }}</span>
            </span>
            <span
              class="col-num"
              :class="returnClass(p.annual_return)"
            >{{ fmtPercent(p.annual_return) }}</span>
            <span class="col-num">{{ fmtPercent(p.max_drawdown) }}</span>
          </div>
        </div>
      </div>
      <div
        v-else
        class="activity-card"
      >
        <h3>Portfolio 列表</h3>
        <p
          v-if="loading"
          class="loading-text"
        >
          加载中...
        </p>
        <EmptyState
          v-else
          description="暂无 Portfolio"
          action-text="创建一个 →"
          :on-action="() => $router.push('/portfolio')"
        />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { portfolioApi, backtestApi, dataApi } from '@/api'
import type { Portfolio, BacktestTask } from '@/api'
import { useBacktestStatus } from '@/composables'
import { formatDecimal, getPnLColor } from '@/composables/useBacktestFormatters'
import { formatNumber, formatRelativeTime } from '@/utils/format'

interface Stats {
  total: number
  running: number
  avgNetValue: number
  totalAssets: number
}

const stats = ref<Stats>({ total: 0, running: 0, avgNetValue: 1, totalAssets: 0 })
const portfolios = ref<Portfolio[]>([])
// 近100条回测:健康度统计用全量,面板展示取前5
const btTasks = ref<BacktestTask[]>([])
const recentBacktests = computed(() => btTasks.value.slice(0, 5))
const syncRecords = ref<any[]>([])
const loading = ref(true)
const lastUpdated = ref('')
let pollTimer: ReturnType<typeof setInterval> | null = null

// 回测状态 tag/标签复用回测域既有映射(小写六态)
const { getTagClass: btTagClass, getLabel: btStatusLabel } = useBacktestStatus()

const countByMode = (mode: string, runningOnly = false) =>
  portfolios.value.filter(p =>
    String(p.mode) === mode && (!runningOnly || String(p.state) === 'RUNNING')
  ).length

const backtestCount = computed(() => countByMode('BACKTEST'))
const backtestRunning = computed(() => countByMode('BACKTEST', true))
const paperCount = computed(() => countByMode('PAPER'))
const paperRunning = computed(() => countByMode('PAPER', true))
const liveCount = computed(() => countByMode('LIVE'))
const liveRunning = computed(() => countByMode('LIVE', true))

// 顶部 4 张统计卡图标(SVG innerHTML,配置数组 v-for 渲染;图标原样自旧模板迁入)
const STAT_ICONS: Record<string, string> = {
  portfolio: '<circle cx="12" cy="12" r="10" /><polygon points="10,8 16,12 10,16" />',
  total: '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z" /><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65" /><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65" />',
  assets: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1" /><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4" />',
  netValue: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17" /><polyline points="16 7 22 7 22 13" />',
}

// 统计卡展示配置:value=null 显示 --(加载中/实盘资产为 0 与原条件一致)
const statCards = computed(() => [
  { key: 'portfolio', testid: 'stat-portfolio', label: '运行中 Portfolio', value: loading.value ? null : `${stats.value.running}`, suffix: '个' },
  { key: 'total', testid: 'stat-backtest', label: 'Portfolio 总数', value: loading.value ? null : `${stats.value.total}`, suffix: '个' },
  { key: 'assets', testid: 'stat-worker', label: '实盘资产', value: loading.value || stats.value.totalAssets <= 0 ? null : formatNumber(stats.value.totalAssets), suffix: '元' },
  { key: 'netValue', testid: 'stat-system', label: '平均净值', value: loading.value ? null : stats.value.avgNetValue.toFixed(4), suffix: '' },
])

// 4 阶段卡展示配置:验证域无统计数据,占位 -- 与原模板一致
const stageCards = computed(() => [
  {
    key: 'backtest', cls: 'stage-1', testid: 'stage-backtest', title: '回测', to: '/backtest',
    linkTestid: 'stage-link-backtest', link: '进入回测 →',
    stats: [
      { label: '回测组合', value: `${backtestCount.value}`, running: false },
      { label: '运行中', value: `${backtestRunning.value}`, running: backtestRunning.value > 0 },
    ],
  },
  {
    key: 'validation', cls: 'stage-2', testid: 'stage-validation', title: '验证', to: '/validation/walkforward',
    linkTestid: 'stage-link-validation', link: '进入验证 →',
    stats: [
      { label: '验证组合', value: '--', running: false },
      { label: '通过验证', value: '--', running: false },
    ],
  },
  {
    key: 'paper', cls: 'stage-3', testid: 'stage-paper', title: '模拟', to: '/paper',
    linkTestid: 'stage-link-paper', link: '进入模拟 →',
    stats: [
      { label: '模拟组合', value: `${paperCount.value}`, running: false },
      { label: '运行中', value: `${paperRunning.value}`, running: paperRunning.value > 0 },
    ],
  },
  {
    key: 'live', cls: 'stage-4', testid: 'stage-live', title: '实盘', to: '/live',
    linkTestid: 'stage-link-live', link: '进入实盘 →',
    stats: [
      { label: '实盘组合', value: `${liveCount.value}`, running: false },
      { label: '运行中', value: `${liveRunning.value}`, running: liveRunning.value > 0 },
    ],
  },
])

// 回测健康度:近100条状态分布(running+pending+created 计为进行中)
const btHealth = computed(() => {
  const c = { completed: 0, failed: 0, active: 0, total: btTasks.value.length }
  for (const t of btTasks.value) {
    if (t.status === 'completed') c.completed++
    else if (t.status === 'failed') c.failed++
    else if (t.status === 'running' || t.status === 'pending' || t.status === 'created') c.active++
  }
  return c
})

// 数据新鲜度:四类数据各自最近一次同步记录(status: running/success/partial/failed)
const SYNC_TYPES = [
  { type: 'stockinfo', label: '股票信息' },
  { type: 'bars', label: 'K线数据' },
  { type: 'ticks', label: 'Tick数据' },
  { type: 'adjustfactor', label: '复权因子' },
] as const
const SYNC_STATUS: Record<string, { label: string; level: string }> = {
  success: { label: '成功', level: 'ok' },
  partial: { label: '部分', level: 'warn' },
  failed: { label: '失败', level: 'err' },
  running: { label: '同步中', level: 'run' },
}
const freshnessRows = computed(() =>
  SYNC_TYPES.map(({ type, label }) => {
    const rec = syncRecords.value.find(r => r.sync_type === type)
    if (!rec) return { type, label, time: '暂无记录', rawTime: '', statusLabel: '—', level: 'none' }
    const st = SYNC_STATUS[rec.status] ?? { label: rec.status, level: 'none' }
    const raw = rec.completed_at || rec.started_at
    return {
      type, label, rawTime: raw || '',
      time: raw ? formatRelativeTime(raw) : '暂无记录',
      statusLabel: st.label, level: st.level,
    }
  })
)

async function fetchDashboardData() {
  loading.value = true
  try {
    const [statsResult, listResult, btResult, syncResult] = await Promise.allSettled([
      portfolioApi.getStats(),
      portfolioApi.list({ page: 0, page_size: 10 }),
      backtestApi.list({ page: 1, page_size: 100, sort_by: 'update_at', sort_order: 'desc' }),
      dataApi.getSyncHistory({ page: 1, page_size: 50 }),
    ])

    if (statsResult.status === 'fulfilled' && statsResult.value) {
      const d = statsResult.value
      stats.value = {
        total: d.total || 0,
        running: d.running || 0,
        avgNetValue: d.avg_net_value ?? 1,
        totalAssets: d.total_assets || 0,
      }
    }

    if (listResult.status === 'fulfilled' && listResult.value?.items) {
      portfolios.value = listResult.value.items
    }

    if (btResult.status === 'fulfilled' && btResult.value?.items) {
      btTasks.value = btResult.value.items
    }

    if (syncResult.status === 'fulfilled') {
      const raw: any = syncResult.value
      syncRecords.value = raw?.items ?? (Array.isArray(raw) ? raw : [])
    }

    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } finally {
    loading.value = false
  }
}

function stateLabel(state: string | number): string {
  const map: Record<string, string> = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    STOPPED: '已停止',
    COMPLETED: '已完成',
    ERROR: '异常',
    INITIALIZED: '已初始化',
  }
  return map[String(state)] ?? String(state)
}

function stateClass(state: string | number): string {
  const map: Record<string, string> = {
    RUNNING: 'badge-running',
    PAUSED: 'badge-paused',
    STOPPED: 'badge-stopped',
    COMPLETED: 'badge-completed',
    ERROR: 'badge-error',
    INITIALIZED: 'badge-stopped',
  }
  return map[String(state)] ?? ''
}

// 百分比格式化:null/undefined 显示 --;回撤为正值原样,收益保留符号
function fmtPercent(v: number | null | undefined): string {
  if (v === null || v === undefined || isNaN(v)) return '--'
  return `${(v * 100).toFixed(2)}%`
}

// 涨绿跌红(ADR-045 西式),文字走 *-fg token 双主题可读
function returnClass(v: number | null | undefined): string {
  if (v === null || v === undefined || isNaN(v) || v === 0) return ''
  return v > 0 ? 'num-positive' : 'num-negative'
}

// 收益对比条:中心基线发散,宽度按展示集内 |收益| 最大值归一(半轨=50%)
const DISPLAYED = 6
const maxAbsReturn = computed(() =>
  Math.max(
    ...portfolios.value.slice(0, DISPLAYED).map(p => Math.abs(Number(p.annual_return) || 0)),
    0.0001
  )
)
function barClass(v: number | null | undefined): string {
  if (v === null || v === undefined || isNaN(v) || v === 0) return ''
  return v > 0 ? 'bar-pos' : 'bar-neg'
}
function barWidth(v: number | null | undefined): number {
  const n = Number(v)
  if (v === null || v === undefined || isNaN(n) || n === 0) return 0
  return Math.min(50, (Math.abs(n) / maxAbsReturn.value) * 50)
}

function modeLabel(mode: string | number): string {
  const map: Record<string, string> = {
    BACKTEST: '回测',
    PAPER: '模拟',
    LIVE: '实盘',
  }
  return map[String(mode)] ?? String(mode)
}

function modeTagClass(mode: string | number): string {
  const map: Record<string, string> = {
    BACKTEST: 'tag-gray',
    PAPER: 'tag-cyan',
    LIVE: 'tag-green',
  }
  return map[String(mode)] ?? 'tag-gray'
}

// 有运行中组合/回测时 30s 轮询;页面隐藏(document.hidden)时跳过本轮
const hasRunning = computed(() =>
  portfolios.value.some(p => String(p.state) === 'RUNNING') ||
  btTasks.value.some(t => t.status === 'running' || t.status === 'pending')
)

function setupPolling() {
  pollTimer = setInterval(() => {
    if (document.hidden || !hasRunning.value) return
    fetchDashboardData()
  }, 30_000)
}

onMounted(() => {
  fetchDashboardData()
  setupPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.page-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片网格 */

/* 图标位基础走全局 cards.less(2026-08-19 收口);灰阶基调 muted-fg on muted 双主题可读(ADR-045) */

.stat-content {
  flex: 1;
}

.stat-suffix {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
  font-weight: 400;
}

/* 阶段卡片网格 */
.stages-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stage-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s;
  cursor: pointer;
}

.stage-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stage-card.stage-1 {
  border-top: 3px solid hsl(var(--primary));
}

.stage-card.stage-2 {
  border-top: 3px solid hsl(var(--success));
}

.stage-card.stage-3 {
  border-top: 3px solid hsl(var(--warning));
}

.stage-card.stage-4 {
  border-top: 3px solid hsl(var(--error));
}

.stage-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0 0 16px 0;
}

.stage-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stage-stat .stat-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.stage-stat .stat-number {
  font-size: 18px;
  font-weight: 600;
  color: hsl(var(--foreground));
  font-variant-numeric: tabular-nums;
  /* 登录页输入框同款 JetBrains Mono(与 .stat-value 同口径,cards.less) */
  font-family: 'JetBrains Mono', 'PingFang SC', 'Microsoft YaHei', monospace;
}

/* 运行中 >0 用文字专用 success-fg(双主题可读) */
.stage-stat .stat-number.is-running {
  color: hsl(var(--success-fg));
}

.stage-link {
  display: inline-block;
  padding: 8px 0 0;
  background: transparent;
  border: none;
  color: hsl(var(--primary));
  font-size: 14px;
  text-align: left;
  transition: color 0.2s;
}

.stage-link:hover {
  color: hsl(var(--primary));
  text-decoration: underline;
}

/* 活动卡片 */
.activity-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 20px;
}

.activity-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0 0 16px 0;
}

.activity-card .loading-text {
  color: hsl(var(--muted-foreground));
  margin: 0;
}

/* 头部快捷操作:入口跳转 + 刷新 */
.quick-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 最近回测面板顶部健康度行 */
.bt-health {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-bottom: 10px;
  margin-bottom: 6px;
  border-bottom: 1px solid hsl(var(--border));
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.bh-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-variant-numeric: tabular-nums;
}

.bh-item.bh-err-text {
  color: hsl(var(--error-fg));
  font-weight: 500;
}

.bh-scope {
  margin-left: auto;
  font-size: 11px;
}

.bh-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.bh-ok { background: hsl(var(--success-fg)); }
.bh-err { background: hsl(var(--error-fg)); }
.bh-run { background: hsl(var(--primary)); }

/* 数据新鲜度横条卡:四类数据最近同步状态 */
.freshness-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.freshness-card:hover {
  box-shadow: var(--shadow-md);
}

.freshness-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.freshness-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.freshness-card .loading-text {
  color: hsl(var(--muted-foreground));
  margin: 0;
  padding: 12px 0;
  text-align: center;
}

.freshness-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.freshness-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  padding: 10px 12px;
  background: hsl(var(--muted) / 0.4);
  border-radius: var(--radius-md);
}

.freshness-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 状态色点:ok 绿/warn 橙/err 红/run 蓝/none 灰 */
.freshness-dot.dot-ok { background: hsl(var(--success-fg)); }
.freshness-dot.dot-warn { background: hsl(var(--warning)); }
.freshness-dot.dot-err { background: hsl(var(--error-fg)); }
.freshness-dot.dot-run { background: hsl(var(--primary)); }
.freshness-dot.dot-none { background: hsl(var(--muted-foreground)); }

.freshness-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.freshness-type {
  font-size: 13px;
  color: hsl(var(--foreground));
}

.freshness-time {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.freshness-status {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
}

.freshness-status.st-ok { color: hsl(var(--success-fg)); }
.freshness-status.st-warn { color: hsl(var(--warning)); }
.freshness-status.st-err { color: hsl(var(--error-fg)); }
.freshness-status.st-run { color: hsl(var(--primary)); }
.freshness-status.st-none { color: hsl(var(--muted-foreground)); }

/* 数据面板:收益对比 + 最近回测 */
.panels-grid {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
  align-items: stretch;
}

.panel-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 20px;
  min-width: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.panel-card .loading-text {
  color: hsl(var(--muted-foreground));
  margin: 0;
  padding: 16px 0;
  text-align: center;
}

/* 收益对比:中心基线发散条,正值向右/负值向左,数值端圆角 */
.return-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 0;
  border-bottom: 1px solid hsl(var(--border));
  cursor: pointer;
}

.return-row:last-child {
  border-bottom: none;
}

.return-row:hover .return-name {
  color: hsl(var(--primary));
}

.return-name {
  flex: 0 0 128px;
  font-size: 13px;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.return-track {
  position: relative;
  flex: 1;
  height: 8px;
}

.return-track::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -3px;
  bottom: -3px;
  width: 1px;
  background: hsl(var(--border));
}

.return-bar {
  position: absolute;
  top: 0;
  bottom: 0;
  min-width: 2px;
}

.return-bar.bar-pos {
  left: 50%;
  border-radius: 0 3px 3px 0;
  background: hsl(var(--success-fg));
}

.return-bar.bar-neg {
  right: 50%;
  border-radius: 3px 0 0 3px;
  background: hsl(var(--error-fg));
}

.return-val {
  flex: 0 0 72px;
  text-align: right;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: hsl(var(--foreground));
}

/* 最近回测 */
.recent-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid hsl(var(--border));
  cursor: pointer;
}

.recent-row:last-child {
  border-bottom: none;
}

.recent-row:hover .recent-name {
  color: hsl(var(--primary));
}

.recent-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recent-prog {
  font-size: 11px;
  color: hsl(var(--success-fg));
  font-variant-numeric: tabular-nums;
}

.recent-pnl {
  flex: 0 0 72px;
  text-align: right;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.recent-date {
  flex: 0 0 72px;
  text-align: right;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

/* Portfolio 列表 */
.portfolio-list-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.list-link {
  background: transparent;
  border: none;
  color: hsl(var(--primary));
  font-size: 14px;
  cursor: pointer;
}

.list-link:hover {
  text-decoration: underline;
}

.portfolio-table {
  display: flex;
  flex-direction: column;
}

.table-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid hsl(var(--border));
  cursor: pointer;
  transition: background 0.15s;
}

.table-row:hover {
  background: hsl(var(--muted) / 0.5);
}

.table-row:last-child {
  border-bottom: none;
}

.table-header-row {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--card));
  cursor: default;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-header-row:hover {
  background: transparent;
}

.col-name {
  flex: 2;
  color: hsl(var(--foreground));
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-mode {
  flex: 1;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}

.col-state {
  flex: 1;
}

.col-num {
  flex: 1;
  text-align: right;
  color: hsl(var(--foreground));
  font-size: 14px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.num-positive {
  color: hsl(var(--success-fg));
}

.num-negative {
  color: hsl(var(--error-fg));
}

/* 头部:更新时间 + 刷新按钮 */
.updated-at {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  font-variant-numeric: tabular-nums;
}

.spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Status badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}

.badge-running {
  background: hsl(var(--success) / 0.15);
  color: hsl(var(--success));
}

.badge-paused {
  background: hsl(var(--warning) / 0.15);
  color: hsl(var(--warning));
}

.badge-stopped {
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--muted-foreground));
}

.badge-completed {
  background: hsl(var(--primary) / 0.15);
  color: hsl(var(--primary));
}

.badge-error {
  background: hsl(var(--error) / 0.15);
  color: hsl(var(--error-fg));
}

/* Responsive */
@media (max-width: 900px) {
  .panels-grid {
    grid-template-columns: 1fr;
  }

  .freshness-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .return-name {
    flex-basis: 96px;
  }
}
</style>
