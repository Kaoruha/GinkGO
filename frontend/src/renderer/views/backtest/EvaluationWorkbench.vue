<template>
  <PageLayout>
    <template #title>
      评估
    </template>
    <template #description>
      输入一个组合，定位它在「回测可信 → 回测有效 → 模拟一致 → 实盘就绪」四级漏斗中的位置。阈值来自后端
      gate 单一事实源，报告实时计算不落库。
    </template>

    <!-- 输入区: 组合 + 回测任务 + 对比序列 -->
    <div class="card">
      <div class="card-body filter-bar">
        <div class="form-group grow">
          <label class="form-label">组合</label>
          <select
            v-model="portfolioId"
            class="form-select"
            data-testid="eval-portfolio-select"
          >
            <option value="">
              选择组合
            </option>
            <option
              v-for="p in portfolios"
              :key="p.uuid"
              :value="p.uuid"
            >
              {{ p.name }}（{{ p.uuid.slice(0, 8) }}）
            </option>
          </select>
        </div>
        <div class="form-group grow">
          <label class="form-label">回测任务（基准）</label>
          <select
            v-model="taskId"
            class="form-select"
            data-testid="eval-task-select"
            :disabled="!tasks.length"
          >
            <option value="">
              最近完成
            </option>
            <option
              v-for="t in tasks"
              :key="t.uuid"
              :value="t.uuid"
            >
              {{ t.name || t.uuid.slice(0, 8) }}（{{ t.uuid.slice(0, 8) }}）
            </option>
          </select>
        </div>
        <div class="form-group">
          <button
            class="btn-primary"
            data-testid="eval-run-btn"
            :disabled="!portfolioId || loadingFunnel"
            @click="runFunnel"
          >
            {{ loadingFunnel ? '评估中…' : '一键评估' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 漏斗报告 -->
    <div
      v-if="funnelError"
      class="card"
    >
      <div class="card-body">
        <EmptyState
          title="评估失败"
          :description="funnelError"
          action-text="重试"
          :on-action="runFunnel"
        />
      </div>
    </div>

    <!-- 漏斗图: 绝对定位悬浮常驻, Teleport 到 body 脱离 .m-page 的 transform containing block -->
    <Teleport to="body">
      <div
        v-if="report"
        class="funnel-float"
        role="complementary"
        aria-label="评估漏斗概览"
        data-testid="eval-funnel-float"
      >
        <button
          v-if="vizCollapsed"
          class="viz-fab"
          data-testid="eval-viz-fab"
          title="展开评估漏斗"
          @click="vizCollapsed = false"
        >
          漏斗
        </button>
        <template v-else>
          <div class="viz-head">
            <span class="viz-title">评估漏斗 · {{ report.level_reached }}</span>
            <button
              class="viz-toggle"
              data-testid="eval-viz-collapse"
              title="收起"
              @click="vizCollapsed = true"
            >
              收起
            </button>
          </div>
          <div
            class="funnel-viz"
            data-testid="eval-funnel-viz"
          >
            <div
              v-for="(lv, i) in LEVELS"
              :key="lv.key"
              class="funnel-layer"
              :data-testid="`eval-layer-${lv.key}`"
              role="button"
              :title="`查看 ${lv.key} ${lv.name} 明细`"
              @click="scrollToLevel(lv.key)"
            >
              <div
                class="layer-bar"
                :class="`layer-${levelStates[lv.key]}`"
                :style="clipStyle(i)"
              >
                <span class="layer-key">{{ lv.key }}</span>
                <span class="layer-name">{{ lv.name }}</span>
                <span class="layer-count">{{ levelSummaries[lv.key].pass }}/{{ levelSummaries[lv.key].total }}</span>
              </div>
            </div>
            <div class="viz-legend">
              <span class="lg lg-pass">通过</span>
              <span class="lg lg-fail">未过</span>
              <span class="lg lg-pending">样本不足/依赖未就绪</span>
            </div>
          </div>
        </template>
      </div>
    </Teleport>

    <template v-if="report">
      <!-- 未过项行动列表 (可操作) -->
      <div
        v-if="actions.length"
        class="card action-card"
      >
        <div class="card-header">
          <h3>行动列表</h3>
        </div>
        <div class="card-body">
          <div
            v-for="a in actions"
            :key="a.id"
            class="action-row"
          >
            <span :class="['action-badge', a.status === 'FAIL' ? 'fail' : 'muted']">{{ a.status === 'FAIL' ? '未过' : '待样本' }}</span>
            <span class="action-name">{{ a.name }}</span>
            <span class="action-detail">{{ a.detail }}</span>
            <span class="action-remediation">{{ a.remediation }}</span>
          </div>
        </div>
      </div>

      <!-- gate 详情: 按级分组指标卡 (可观测, 漏斗层点击跳转目标) -->
      <div
        v-for="lv in LEVELS"
        :id="`gate-group-${lv.key}`"
        :key="lv.key"
        class="level-group"
      >
        <div class="level-title">
          <span class="level-key">{{ lv.key }}</span>{{ lv.name }}
          <span :class="['level-state', stepClass(lv.key)]">{{ stepLabel(lv.key) }}</span>
        </div>
        <div class="gate-grid">
          <div
            v-for="g in gatesOf(lv.key)"
            :key="g.id"
            class="gate-card"
            :data-testid="`eval-gate-${g.id}`"
          >
            <div class="gate-head">
              <span class="gate-name">{{ g.name }}</span>
              <span :class="['status-pill', statusClass(g.status)]">{{ statusLabel(g.status) }}</span>
            </div>
            <div class="gate-metric">
              <span class="gate-value">{{ fmtValue(g) }}</span>
              <span class="gate-threshold">
                阈值 {{ g.direction === 'lte' ? '≤' : '≥' }} {{ g.threshold }}{{ g.unit || '' }}
              </span>
            </div>
            <div
              v-if="g.detail"
              class="gate-detail"
            >
              {{ g.detail }}
            </div>
          </div>
        </div>
      </div>
    </template>

    <div
      v-else-if="!funnelError"
      class="card"
    >
      <div class="card-body">
        <EmptyState
          title="选择组合开始评估"
          description="选择组合后点击「评估」，系统将逐 gate 报告 PASS / FAIL / 样本不足 / BLOCKED。"
        />
      </div>
    </div>

    <!-- 数据预检 (G0) -->
    <div class="card section-card">
      <div class="card-header">
        <h3>数据预检（G0 质量项）</h3>
      </div>
      <div class="card-body">
        <div class="filter-bar">
          <div class="form-group">
            <label class="form-label">开始日期</label>
            <input
              v-model="pfStart"
              type="date"
              class="form-input"
              data-testid="pf-start"
            >
          </div>
          <div class="form-group">
            <label class="form-label">结束日期</label>
            <input
              v-model="pfEnd"
              type="date"
              class="form-input"
              data-testid="pf-end"
            >
          </div>
          <div class="form-group">
            <button
              class="btn-primary"
              data-testid="pf-run-btn"
              :disabled="!portfolioId || !pfStart || !pfEnd || loadingPf"
              @click="runPreflight"
            >
              {{ loadingPf ? '检查中…' : '预检' }}
            </button>
          </div>
        </div>

        <div
          v-if="pfError"
          class="error-text"
          data-testid="pf-error"
        >
          {{ pfError }}
        </div>

        <template v-if="preflight">
          <div
            class="pf-verdict"
            :class="preflight.ok ? 'good' : 'bad'"
            data-testid="pf-verdict"
          >
            {{ preflight.ok ? '✓ 无阻断性问题，可回测' : '✗ 存在阻断性问题，先修数据再回测' }}
          </div>
          <div
            v-for="n in preflight.notes || []"
            :key="n"
            class="note-line"
          >
            · {{ n }}
          </div>

          <table
            v-if="preflight.codes.length"
            class="pf-table"
          >
            <thead>
              <tr>
                <th>Code</th>
                <th>Bar 数</th>
                <th>缺口率</th>
                <th>缺失日</th>
                <th>因子回跳</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="c in preflight.codes"
                :key="c"
              >
                <td>{{ c }}</td>
                <td>{{ preflight.coverage[c] ?? '-' }}</td>
                <td>{{ preflight.quality[c]?.gap_pct ?? '-' }}%</td>
                <td>{{ preflight.quality[c]?.missing_days ?? '-' }}</td>
                <td>{{ preflight.quality[c]?.factor_reversals ?? '-' }}</td>
              </tr>
            </tbody>
          </table>

          <div
            v-for="i in preflight.issues"
            :key="`${i.code}-${i.kind}`"
            class="action-row"
          >
            <span :class="['action-badge', i.severity === 'blocker' ? 'fail' : 'muted']">
              {{ i.severity === 'blocker' ? '阻断' : '提示' }}
            </span>
            <span class="action-name">{{ i.code }}</span>
            <span class="action-detail">{{ i.detail }}</span>
            <span class="action-remediation">{{ i.remediation }}</span>
          </div>
        </template>
      </div>
    </div>

    <!-- 一致性 (G2) -->
    <div class="card section-card">
      <div class="card-header">
        <h3>模拟一致性（G2 五项）</h3>
      </div>
      <div class="card-body">
        <div class="filter-bar">
          <div class="form-group grow">
            <label class="form-label">基准序列（回测）</label>
            <input
              v-model="parityBaseline"
              class="form-input"
              placeholder="回测 task ID"
              data-testid="parity-baseline"
            >
          </div>
          <div class="form-group grow">
            <label class="form-label">对比序列（模拟盘/另一次回测）</label>
            <input
              v-model="parityCandidate"
              class="form-input"
              placeholder="task ID"
              data-testid="parity-candidate"
            >
          </div>
          <div class="form-group">
            <button
              class="btn-primary"
              data-testid="parity-run-btn"
              :disabled="!parityBaseline || !parityCandidate || !portfolioId || loadingParity"
              @click="runParity"
            >
              {{ loadingParity ? '计算中…' : '对比' }}
            </button>
          </div>
        </div>

        <div
          v-if="parityError"
          class="error-text"
          data-testid="parity-error"
        >
          {{ parityError }}
        </div>

        <template v-if="parity">
          <div class="parity-grid">
            <div
              v-for="m in parityMetrics"
              :key="m.label"
              class="parity-item"
            >
              <span class="parity-label">{{ m.label }}</span>
              <span :class="['parity-value', m.ok === null ? 'muted' : m.ok ? 'good' : 'bad']">
                {{ m.display }}
              </span>
            </div>
          </div>
          <div
            v-for="n in parity.notes || []"
            :key="n"
            class="note-line"
          >
            · {{ n }}
          </div>
        </template>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { portfolioApi, type Portfolio } from '@/api/modules/portfolio'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'
import {
  evaluationApi,
  type FunnelReport,
  type GateResult,
  type GateStatus,
  type ParityReport,
  type PreflightReport,
} from '@/api/modules/evaluation'

defineOptions({ name: 'EvaluationWorkbench' })

const route = useRoute()

const LEVELS = [
  { key: 'G0', name: '回测可信' },
  { key: 'G1', name: '回测有效' },
  { key: 'G2', name: '模拟一致' },
  { key: 'G3', name: '实盘就绪' },
] as const

// ---------- 输入态 ----------
const portfolios = ref<Portfolio[]>([])
const tasks = ref<BacktestTask[]>([])
const portfolioId = ref('')
const taskId = ref('')

// ---------- 漏斗 ----------
const report = ref<FunnelReport | null>(null)
const loadingFunnel = ref(false)
const funnelError = ref('')
const vizCollapsed = ref(false) // 悬浮漏斗折叠态

// ---------- 一致性 ----------
const parityBaseline = ref('')
const parityCandidate = ref('')
const parity = ref<ParityReport | null>(null)
const loadingParity = ref(false)
const parityError = ref('')

// ---------- 预检 ----------
const pfStart = ref('2025-05-07')
const pfEnd = ref('2026-05-07')
const preflight = ref<PreflightReport | null>(null)
const loadingPf = ref(false)
const pfError = ref('')

// ---------- 加载 ----------
// 深链预填: /backtests/evaluation?portfolio=<pid>&task=<tid> (详情页「去评估」跳入即自动评估)
let pendingQueryTask = ''
onMounted(async () => {
  const q = route.query
  if (typeof q.task === 'string') pendingQueryTask = q.task
  if (typeof q.portfolio === 'string') portfolioId.value = q.portfolio
  try {
    // portfolio 端点 page 为 0 基 (Dashboard 同惯例; page:1 会跳过第一页)
    const res = await portfolioApi.list({ page: 0, page_size: 100 })
    portfolios.value = res.items ?? []
  } catch (e) {
    funnelError.value = `组合列表加载失败: ${(e as Error).message}`
  }
})

watch(portfolioId, async (pid) => {
  report.value = null
  parity.value = null
  preflight.value = null
  taskId.value = ''
  tasks.value = []
  if (!pid) return
  try {
    const res = await backtestApi.list({ portfolio_id: pid, page: 1, page_size: 50 })
    tasks.value = res.items ?? []
  } catch {
    tasks.value = [] // 任务列表拉不到不阻塞漏斗评估(可用「最近完成」兜底)
  }
  // 深链带 task: 列表到位后选中并自动评估 (一次性; 不校验列表成员——funnel 只认 id, 深链的 task 未必在首页 50 条里)
  if (pendingQueryTask) {
    taskId.value = pendingQueryTask
    pendingQueryTask = ''
    await nextTick()
    runFunnel()
  }
})

// 选中任务 → 预检窗口自动对齐该任务回测区间 (一键评估时数据同口径)
watch(taskId, (tid) => {
  const t = tasks.value.find((x) => x.uuid === tid)
  if (t?.backtest_start_date) pfStart.value = t.backtest_start_date.slice(0, 10)
  if (t?.backtest_end_date) pfEnd.value = t.backtest_end_date.slice(0, 10)
})

// ---------- 漏斗 ----------
/** 一键评估: 漏斗+预检并行, parity 两栏齐时自动带上; 各区仍可单独重跑 */
async function runFunnel() {
  if (!portfolioId.value) return
  loadingFunnel.value = true
  funnelError.value = ''
  const funnelJob = evaluationApi
    .getFunnel({
      portfolio_id: portfolioId.value,
      task_id: taskId.value || undefined,
    })
    .then((r) => {
      report.value = r
      // 一致性基准默认 = 当前任务
      if (!parityBaseline.value && r.task_id) parityBaseline.value = r.task_id
    })
    .catch((e) => {
      report.value = null
      funnelError.value = (e as Error).message || '评估失败'
    })
  await Promise.allSettled([funnelJob, runPreflight()])
  // parity 基准可能在 funnel 结果里才填上, 放到之后判断
  if (parityBaseline.value && parityCandidate.value) await runParity()
  loadingFunnel.value = false
}

const levelStates = computed(() => {
  // 每级状态: blocker FAIL → fail; 有 FAIL 且 PASS 混合 → fail;
  // 全 INSUFFICIENT/BLOCKED → pending; 全 PASS → pass (G3 kill switch 等 BLOCKED 视为 pending)
  const states: Record<string, 'pass' | 'fail' | 'pending'> = {}
  let reached = true
  for (const lv of LEVELS) {
    const gates = gatesOf(lv.key)
    const failed = gates.filter((g) => g.status === 'FAIL')
    const blocked = gates.filter((g) => g.status === 'BLOCKED' || g.status === 'INSUFFICIENT_DATA')
    if (failed.length) states[lv.key] = 'fail'
    else if (gates.length && blocked.length === gates.length) states[lv.key] = 'pending'
    else states[lv.key] = 'pass'
    if (states[lv.key] !== 'pass') reached = false
    else if (!reached) states[lv.key] = 'pending' // 前级未过,后级通过也只算待定
  }
  return states
})

function gatesOf(level: string): GateResult[] {
  return report.value?.gates.filter((g) => g.level === level) ?? []
}

function stepClass(key: string) {
  return `step-${levelStates.value[key]}`
}

function stepLabel(key: string) {
  const s = levelStates.value[key]
  return s === 'pass' ? '已通过' : s === 'fail' ? '未通过' : '待样本'
}

// 每级 gate 计数 + 未过名单 (漏斗层上直出)
const levelSummaries = computed(() => {
  const out: Record<string, { pass: number; total: number; fails: string[] }> = {}
  for (const lv of LEVELS) {
    const gates = gatesOf(lv.key)
    out[lv.key] = {
      pass: gates.filter((g) => g.status === 'PASS').length,
      total: gates.length,
      fails: gates.filter((g) => g.status === 'FAIL').map((g) => g.name),
    }
  }
  return out
})

/** 漏斗梯形: 层 i 顶宽 100-i*7%, 底宽再收 7%, 相邻层衔接成连续收窄 */
function clipStyle(i: number) {
  const tl = i * 7
  const tr = 100 - i * 7
  const bl = (i + 1) * 7
  const br = 100 - (i + 1) * 7
  return { clipPath: `polygon(${tl}% 0, ${tr}% 0, ${br}% 100%, ${bl}% 100%)` }
}

function scrollToLevel(key: string) {
  document.getElementById(`gate-group-${key}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// 行动列表: 未过/样本不足/依赖未就绪的 gate → 修复建议 (对齐后端 failed_blockers 语义)
const actions = computed(() =>
  report.value?.gates
    .filter((g) => g.status === 'FAIL' || g.status === 'INSUFFICIENT_DATA' || g.status === 'BLOCKED')
    .map((g) => ({
      id: g.id,
      status: g.status,
      name: `${g.level} ${g.name}`,
      detail: g.detail || (g.value === null ? '' : `当前值 ${g.value}`),
      remediation: g.remediation || '',
    })) ?? [],
)

function fmtValue(g: GateResult) {
  if (g.value === null || g.value === undefined) return '—'
  const v = Number(g.value)
  if (Math.abs(v) >= 100) return v.toFixed(0)
  return Number(v.toFixed(4)).toString()
}

function statusClass(s: GateStatus) {
  return {
    PASS: 'pass',
    FAIL: 'fail',
    INSUFFICIENT_DATA: 'insufficient',
    BLOCKED: 'blocked',
  }[s]
}

function statusLabel(s: GateStatus) {
  return {
    PASS: '通过',
    FAIL: '未过',
    INSUFFICIENT_DATA: '样本不足',
    BLOCKED: '依赖未就绪',
  }[s]
}

// ---------- 一致性 ----------
const PARITY_GATES: Array<{ label: string; key: keyof ParityReport; fmt: (v: number) => string }> = [
  { label: '重叠交易日', key: 'overlap_days', fmt: (v) => `${v} 天` },
  { label: '日收益相关性', key: 'daily_return_corr', fmt: (v) => v.toFixed(4) },
  { label: '带宽比', key: 'band_ratio', fmt: (v) => `${v.toFixed(2)}×` },
  { label: '换手偏差', key: 'turnover_deviation_pct', fmt: (v) => `${v.toFixed(1)}%` },
  { label: '回撤形态相关性', key: 'drawdown_shape_corr', fmt: (v) => v.toFixed(4) },
]

const parityMetrics = computed(() => {
  if (!parity.value) return []
  return PARITY_GATES.map(({ label, key, fmt }) => {
    const raw = parity.value?.[key] as number | null
    return {
      label,
      display: raw === null || raw === undefined ? '不可算' : fmt(raw),
      ok: raw === null || raw === undefined ? null : true,
    }
  })
})

async function runParity() {
  loadingParity.value = true
  parityError.value = ''
  try {
    parity.value = await evaluationApi.getParity({
      portfolio_id: portfolioId.value,
      baseline_task_id: parityBaseline.value.trim(),
      candidate_task_id: parityCandidate.value.trim(),
    })
  } catch (e) {
    parity.value = null
    parityError.value = (e as Error).message || '对比失败'
  } finally {
    loadingParity.value = false
  }
}

// ---------- 预检 ----------
async function runPreflight() {
  loadingPf.value = true
  pfError.value = ''
  try {
    preflight.value = await evaluationApi.runPreflight({
      portfolio_id: portfolioId.value,
      start: pfStart.value,
      end: pfEnd.value,
    })
  } catch (e) {
    preflight.value = null
    pfError.value = (e as Error).message || '预检失败'
  } finally {
    loadingPf.value = false
  }
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.grow {
  flex: 1;
  min-width: 220px;
}

/* ---------- 漏斗图 (悬浮常驻) ---------- */
.funnel-float {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 30; /* 弹窗层级之下, 内容之上 */
  width: 264px;
  padding: 10px 12px 8px;
  /* 半透明 + 毛玻璃: 下方被遮卡片隐约可见, 降低遮挡感 */
  background: hsl(var(--card) / 0.88);
  backdrop-filter: blur(4px);
  border: 1px solid hsl(var(--border));
  border-radius: 10px;
  box-shadow: 0 8px 24px hsl(var(--foreground) / 0.14);
}

.viz-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.viz-title {
  font-size: 12px;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.viz-toggle {
  flex-shrink: 0;
  font-size: 12px;
  padding: 1px 8px;
  border-radius: 6px;
  border: 1px solid hsl(var(--border));
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}

.viz-toggle:hover {
  background: hsl(var(--muted) / 0.5);
}

.viz-fab {
  width: 100%;
  height: 36px;
  border: none;
  border-radius: 8px;
  background: hsl(var(--primary) / 0.9);
  color: hsl(var(--primary-foreground));
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.viz-fab:hover {
  filter: brightness(1.08);
}

.funnel-viz {
  margin-bottom: 0;
}

.funnel-layer {
  position: relative;
  cursor: pointer;
  padding: 2px 0; /* 层间距, 视觉连续 */
}

.layer-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 32px;
  transition: filter 0.15s;
}

.funnel-layer:hover .layer-bar {
  filter: brightness(1.08);
}

.layer-key {
  font-weight: 700;
  font-size: 13px;
}

.layer-name {
  font-size: 12px;
}

.layer-count {
  font-size: 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  padding: 0 7px;
  border-radius: 999px;
  background: hsl(var(--card) / 0.45);
}

/* 层色 = 级状态 (与图例对应) */
.layer-pass {
  background: hsl(var(--success) / 0.75);
  color: hsl(var(--success-foreground, 0 0% 100%));
}

.layer-fail {
  background: hsl(var(--destructive) / 0.78);
  color: hsl(var(--destructive-foreground, 0 0% 100%));
}

.layer-pending {
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
}

/* 图例 */
.viz-legend {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  flex-wrap: wrap;
}

.lg {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.lg::before {
  content: '';
  width: 10px;
  height: 10px;
  border-radius: 2px;
  display: inline-block;
}

.lg-pass::before {
  background: hsl(var(--success) / 0.75);
}

.lg-fail::before {
  background: hsl(var(--destructive) / 0.78);
}

.lg-pending::before {
  background: hsl(var(--muted));
}

/* 窄屏: 悬浮卡收窄避让内容 */
@media (max-width: 768px) {
  .funnel-float {
    right: 12px;
    bottom: 12px;
    width: 200px;
  }

  .layer-name {
    display: none; /* 窄卡只留层级键 + 计数 */
  }
}

@media (prefers-reduced-motion: reduce) {
  .funnel-layer:hover .layer-bar {
    filter: none;
  }
}

/* ---------- gate 分组 ---------- */
.level-group {
  margin-bottom: 16px;
}

.level-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.level-key {
  background: hsl(var(--muted));
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.level-state {
  margin-left: auto;
  font-size: 12px;
  font-weight: 400;
  color: hsl(var(--muted-foreground));
}

.level-state.step-pass {
  color: hsl(var(--success));
}

.level-state.step-fail {
  color: hsl(var(--destructive));
}

.gate-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.gate-card {
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 10px 12px;
  background: hsl(var(--card));
}

.gate-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.gate-name {
  font-size: 13px;
  color: hsl(var(--foreground));
}

.gate-metric {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 6px;
}

.gate-value {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.gate-threshold {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.gate-detail {
  margin-top: 4px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* ---------- 状态徽章 ---------- */
.status-pill {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.status-pill.pass {
  background: hsl(var(--success) / 0.15);
  color: hsl(var(--success));
}

.status-pill.fail {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.status-pill.insufficient {
  background: hsl(var(--warning) / 0.15);
  color: hsl(var(--warning));
}

.status-pill.blocked {
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
}

/* ---------- 行动列表 ---------- */
.action-card {
  margin-bottom: 16px;
}

.action-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 6px 0;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
  font-size: 13px;
  flex-wrap: wrap;
}

.action-row:last-child {
  border-bottom: none;
}

.action-badge {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.action-badge.fail {
  background: hsl(var(--destructive) / 0.12);
  color: hsl(var(--destructive));
}

.action-badge.muted {
  background: hsl(var(--muted));
  color: hsl(var(--muted-foreground));
}

.action-name {
  font-weight: 600;
  min-width: 180px;
}

.action-detail {
  color: hsl(var(--muted-foreground));
}

.action-remediation {
  margin-left: auto;
  color: hsl(var(--primary));
}

/* ---------- 一致性 / 预检 ---------- */
.section-card {
  margin-bottom: 16px;
}

.parity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
  margin-top: 12px;
}

.parity-item {
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.parity-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.parity-value {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.parity-value.good {
  color: hsl(var(--success));
}

.parity-value.bad {
  color: hsl(var(--destructive));
}

.muted {
  color: hsl(var(--muted-foreground));
}

.note-line {
  margin-top: 6px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.error-text {
  margin-top: 8px;
  font-size: 13px;
  color: hsl(var(--destructive));
}

.pf-verdict {
  margin-top: 10px;
  font-size: 14px;
  font-weight: 600;
  padding: 8px 12px;
  border-radius: var(--radius);
}

.pf-verdict.good {
  background: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.pf-verdict.bad {
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.pf-table {
  width: 100%;
  margin-top: 10px;
  border-collapse: collapse;
  font-size: 13px;
}

.pf-table th,
.pf-table td {
  text-align: left;
  padding: 6px 10px;
  border-bottom: 1px solid hsl(var(--border) / 0.5);
}

.pf-table th {
  color: hsl(var(--muted-foreground));
  font-weight: 500;
}

@media (max-width: 768px) {
  .stepper {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
