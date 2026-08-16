<template>
  <div>
    <!-- 交易子 tab(L3,状态进 URL query: &trade=) -->
    <TabsNav
      v-model="activeTradeTab"
      size="small"
      :items="tradeSubTabs"
      class="bt-subtabs"
    />

    <!-- 三表(信号/订单/持仓记录)共用的 code 多选筛选 -->
    <CodeFilter
      v-model:selected="selectedCodes"
      :codes="allCodes"
    />

    <!-- 信号 -->
    <div
      v-if="activeTradeTab === 'signals'"
      class="card"
    >
      <div
        v-if="signalsLoading"
        class="loading-center"
      >
        <div class="spinner spinner-sm" />
      </div>
      <table
        v-else-if="filteredSignals.length > 0"
        class="data-table"
      >
        <thead><tr><th>代码</th><th>方向</th><th>权重</th><th>原因</th><th>时间</th></tr></thead>
        <tbody>
          <tr
            v-for="s in filteredSignals"
            :key="s.uuid"
            :data-uuid="s.uuid"
            :class="{ 'row-highlight': highlightUuid === s.uuid }"
          >
            <td>{{ s.code }}</td>
            <td><span :class="directionColor(s.direction)">{{ directionLabel(s.direction) }}</span></td>
            <td>{{ (s.weight * 100).toFixed(1) }}%</td>
            <td>{{ s.reason || '-' }}</td>
            <td>{{ formatShortDate(s.business_timestamp || s.timestamp) }}</td>
          </tr>
        </tbody>
      </table>
      <p
        v-else
        class="empty-hint"
      >
        暂无信号记录
      </p>
    </div>

    <!-- 订单 -->
    <div
      v-if="activeTradeTab === 'orders'"
      class="card"
    >
      <div
        v-if="ordersLoading"
        class="loading-center"
      >
        <div class="spinner spinner-sm" />
      </div>
      <table
        v-else-if="filteredOrders.length > 0"
        class="data-table"
      >
        <thead><tr><th>代码</th><th>方向</th><th>类型</th><th>数量</th><th>成交价</th><th>手续费</th><th>来源信号</th><th>时间</th><th /></tr></thead>
        <tbody>
          <template
            v-for="o in filteredOrders"
            :key="o.uuid"
          >
            <tr
              :data-order="o.order_id || o.uuid"
              :class="{ 'row-highlight': highlightOrder === (o.order_id || o.uuid) }"
            >
              <td>{{ o.code }}</td>
              <td><span :class="directionColor(o.direction)">{{ directionLabel(o.direction) }}</span></td>
              <td>{{ o.order_type }}</td>
              <td>{{ o.transaction_volume }}</td>
              <td>{{ o.transaction_price }}</td>
              <td>{{ o.fee }}</td>
              <td>
                <span
                  v-if="o.signal_id"
                  class="lineage-chip"
                  :title="`信号 ${o.signal_id}\n点击跳转`"
                  @click="jumpToSignal(o.signal_id)"
                >{{ signalDigest(o.signal_id) }}</span>
                <span
                  v-else
                  class="empty-hint-inline"
                >-</span>
              </td>
              <td>{{ formatShortDate(o.timestamp) }}</td>
              <td>
                <button
                  class="expand-btn"
                  @click="toggleLifecycle(o.order_id || o.uuid)"
                >
                  {{ expandedOrder === (o.order_id || o.uuid) ? '收起' : '生命周期' }}
                </button>
              </td>
            </tr>
            <!-- 生命周期时间线:该订单全部状态流转(order_record 流水) -->
            <tr
              v-if="expandedOrder === (o.order_id || o.uuid)"
              class="lifecycle-row"
            >
              <td :colspan="9">
                <div
                  v-if="lifecycleLoading"
                  class="loading-center"
                >
                  <div class="spinner spinner-sm" />
                </div>
                <template v-else>
                  <div
                    v-if="lifecycleOf(o.order_id || o.uuid).length"
                    class="lifecycle-timeline"
                  >
                    <div
                      v-for="(st, i) in lifecycleOf(o.order_id || o.uuid)"
                      :key="i"
                      class="lifecycle-step"
                    >
                      <span
                        class="step-dot"
                        :class="stepClass(st.status)"
                      />
                      <span class="step-status">{{ orderStatusName(st.status) }}</span>
                      <span
                        v-if="Number(st.transaction_volume) > 0"
                        class="step-meta"
                      >{{ st.transaction_volume }}@{{ st.transaction_price || '-' }}</span>
                      <span class="step-time">{{ st.timestamp || '-' }}</span>
                    </div>
                  </div>
                  <p
                    v-else
                    class="empty-hint"
                  >
                    暂无状态流水
                  </p>
                </template>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p
        v-else
        class="empty-hint"
      >
        暂无订单记录
      </p>
    </div>

    <!-- 持仓 -->
    <div
      v-if="activeTradeTab === 'positions'"
      class="card"
    >
      <div
        v-if="positionsLoading"
        class="loading-center"
      >
        <div class="spinner spinner-sm" />
      </div>
      <table
        v-else-if="filteredPositions.length > 0"
        class="data-table"
      >
        <thead><tr><th>代码</th><th>方向</th><th>数量</th><th>成本</th><th>市值</th><th>盈亏</th><th>盈亏%</th><th>来源订单</th><th>时间</th></tr></thead>
        <tbody>
          <tr
            v-for="p in filteredPositions"
            :key="p.uuid"
          >
            <td>{{ p.code }}</td>
            <td><span :class="directionColor(p.direction)">{{ directionLabel(p.direction) }}</span></td>
            <td :style="{ color: p.volume >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
              {{ p.volume > 0 ? '+' : '' }}{{ p.volume }}
            </td><!-- 变动流水:带符号,+买/-卖 -->
            <td>{{ formatDecimal(p.cost) }}</td>
            <td>{{ formatDecimal(p.market_value) }}</td>
            <td :style="{ color: p.profit >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
              {{ formatDecimal(p.profit) }}
            </td>
            <td :style="{ color: p.profit_pct >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
              {{ (p.profit_pct * 100).toFixed(2) }}%
            </td>
            <td>
              <span
                v-if="p.order_id"
                class="lineage-chip"
                title="点击查看该订单生命周期"
                @click="jumpToOrder(p.order_id)"
              >{{ p.order_id.slice(0, 8) }}</span>
              <span
                v-else
                class="empty-hint-inline"
              >-</span>
            </td>
            <td>{{ formatShortDate(p.business_timestamp || p.timestamp) }}</td><!-- 业务时间优先,同信号列口径 -->
          </tr>
        </tbody>
      </table>
      <p
        v-else
        class="empty-hint"
      >
        暂无持仓记录
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 回测交易记录 tab(信号/订单/持仓三表 + 血缘追溯)
 *
 * 从 BacktestDetailPage 整体迁出。三表共享 code 多选筛选;订单行可展开
 * 生命周期时间线;Signal↔Order↔Position 血缘 chip 互相跳转(切子 tab +
 * 滚动定位 + 高亮)。子 tab 状态进 URL query(&trade=),可深链。
 */
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { backtestApi } from '@/api'
import TabsNav from '@/components/common/TabsNav.vue'
import CodeFilter from '@/components/common/CodeFilter.vue'
import {
  formatShortDate, formatDecimal, directionLabel, directionColor,
} from '@/composables/useBacktestFormatters'

const props = defineProps<{
  taskUuid: string
}>()

const route = useRoute()
const router = useRouter()

// 防止组件卸载后异步操作继续执行
let disposed = false

const TRADE_TABS = ['signals', 'orders', 'positions'] as const
const activeTradeTab = computed<string>({
  get: () => TRADE_TABS.includes(route.query.trade as any) ? String(route.query.trade) : 'signals',
  set: (v) => router.replace({ query: { ...route.query, trade: v } }),
})

const tradeSubTabs = [
  { key: 'signals', label: '信号' },
  { key: 'orders', label: '订单' },
  { key: 'positions', label: '持仓记录' },
]
const signals = ref<any[]>([])
const orders = ref<any[]>([])
const positions = ref<any[]>([])
const signalsLoading = ref(false)
const ordersLoading = ref(false)
const positionsLoading = ref(false)

// code 多选筛选(三表共享,纯前端过滤):空=全部
const selectedCodes = ref<string[]>([])
const allCodes = computed<string[]>(() =>
  [...new Set([...signals.value, ...orders.value, ...positions.value].map(x => x?.code).filter(Boolean))].sort())
const filteredSignals = computed(() =>
  selectedCodes.value.length ? signals.value.filter(s => selectedCodes.value.includes(s.code)) : signals.value)
const filteredOrders = computed(() =>
  selectedCodes.value.length ? orders.value.filter(o => selectedCodes.value.includes(o.code)) : orders.value)
const filteredPositions = computed(() =>
  selectedCodes.value.length ? positions.value.filter(p => selectedCodes.value.includes(p.code)) : positions.value)

// ---- 血缘追溯(2026-08-17):Signal→Order→PositionRecord ----
// 订单生命周期:expandedOrder=当前展开的 order uuid;orderRecords=全量状态流水
// (懒加载一次,按 order_id 分组取用)
const expandedOrder = ref<string | null>(null)
const orderRecords = ref<any[]>([])
const lifecycleLoading = ref(false)
// 分组键 = order_id(状态流水按它分组;列表行的 uuid 是"去重取最新那条流水行"的
// 行 uuid,与其它状态行的 uuid 各不相同,用它分组只能匹配到 1 条——即
// "生命周期只有一条"的根因)
const lifecycleOf = (orderId: string) =>
  orderRecords.value
    .filter(r => r.order_id === orderId || r.uuid === orderId)
    .sort((a: any, b: any) => Number(a.status) - Number(b.status))  // NEW(1)→FILLED(4) 生命周期顺序
const ORDER_STATUS_NAMES: Record<string, string> = {
  '1': '已创建', 'NEW': '已创建', '2': '已提交', 'SUBMITTED': '已提交',
  '3': '部分成交', 'PARTIAL_FILLED': '部分成交', '4': '已成交', 'FILLED': '已成交',
  '5': '已取消', 'CANCELED': '已取消', '6': '已拒绝', 'REJECTED': '已拒绝',
}
const orderStatusName = (st: any) => ORDER_STATUS_NAMES[String(st)] || String(st)
const stepClass = (st: any) => {
  const n = orderStatusName(st)
  if (n === '已成交') return 'ok'
  if (n === '已拒绝' || n === '已取消') return 'bad'
  return 'mid'
}
const toggleLifecycle = async (orderUuid: string) => {
  if (expandedOrder.value === orderUuid) { expandedOrder.value = null; return }
  expandedOrder.value = orderUuid
  if (orderRecords.value.length === 0) {
    lifecycleLoading.value = true
    try {
      const res = await backtestApi.getOrderRecords(props.taskUuid)
      orderRecords.value = ((res as any).data || res) as any[]
    } catch { orderRecords.value = [] }
    finally { lifecycleLoading.value = false }
  }
}
// 持仓"来源订单"chip → 跳订单 tab 并展开该订单生命周期
const jumpToOrder = async (orderUuid: string) => {
  // activeTradeTab 是 computed(router query 驱动),经 router.replace 切子 tab
  router.replace({ query: { ...route.query, trade: 'orders' } })
  await toggleLifecycle(orderUuid)
  await highlightRow(`[data-order="${orderUuid}"]`, 'highlightOrder', orderUuid)
}
// 订单"来源信号"chip → 跳信号 tab,滚动定位+高亮目标行(闭环 Signal→Order 追溯)
const jumpToSignal = (signalId: string) => {
  router.replace({ query: { ...route.query, trade: 'signals' } })
  highlightRow(`[data-uuid="${signalId}"]`, 'highlightUuid', signalId)
}

// ---- 血缘跳转高亮:切 tab 后滚动到目标行并高亮 2.5s(行可能因筛选不可见则仅置态) ----
const highlightUuid = ref<string | null>(null)
const highlightOrder = ref<string | null>(null)
let highlightTimer: ReturnType<typeof setTimeout> | null = null
async function highlightRow(selector: string, key: 'highlightUuid' | 'highlightOrder', id: string) {
  await nextTick()
  if (highlightTimer) clearTimeout(highlightTimer)
  if (key === 'highlightUuid') { highlightUuid.value = id; highlightOrder.value = null }
  else { highlightOrder.value = id; highlightUuid.value = null }
  document.querySelector(selector)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  highlightTimer = setTimeout(() => { highlightUuid.value = null; highlightOrder.value = null }, 2500)
}
// 来源信号摘要:uuid → "代码 方向 日期"(uuid 本身不可读;join 本页已加载的信号数据)
const signalDigest = (signalId: string) => {
  const sig = signals.value.find(s => s.uuid === signalId)
  if (!sig) return signalId
  const dir = Number(sig.direction) === 2 ? '卖出' : '买入'
  return `${sig.code} ${dir} ${formatShortDate(sig.business_timestamp || sig.timestamp).slice(5, 10)}`
}

const loadTrades = async () => {
  if (!props.taskUuid || disposed) return
  signalsLoading.value = true
  ordersLoading.value = true
  positionsLoading.value = true
  try {
    const [sigRes, ordRes, posRes] = await Promise.allSettled([
      backtestApi.getSignals(props.taskUuid),
      backtestApi.getOrders(props.taskUuid),
      backtestApi.getPositions(props.taskUuid),
    ])
    if (disposed) return
    // request.ts 拦截器已拆包: 分页端点 = {items, total, ...}, 直接取 .items
    if (sigRes.status === 'fulfilled') { signals.value = (sigRes.value as any)?.items || [] }
    if (ordRes.status === 'fulfilled') { orders.value = (ordRes.value as any)?.items || [] }
    if (posRes.status === 'fulfilled') { positions.value = (posRes.value as any)?.items || [] }
  } finally {
    if (!disposed) {
      signalsLoading.value = false
      ordersLoading.value = false
      positionsLoading.value = false
    }
  }
}

/** 父页可调:终态/静默刷新时重拉三表(defineExpose) */
defineExpose({ reload: loadTrades })

onMounted(() => loadTrades())

onUnmounted(() => {
  disposed = true
  if (highlightTimer) clearTimeout(highlightTimer)
})
</script>

<style scoped>
/* 样式自 BacktestDetailPage 原样迁入(视觉零变化) */
.bt-subtabs { margin-bottom: 16px; }

.card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 14px;
  margin-bottom: 12px;
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

/* 血缘追溯 chip + 订单生命周期时间线 */
.lineage-chip {
  font-family: monospace;
  font-size: 11px;
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
  border: 1px solid hsl(var(--primary) / 0.25);
  border-radius: 4px;
  padding: 1px 6px;
  cursor: pointer;
}
.lineage-chip:hover { background: hsl(var(--primary) / 0.15); }
.empty-hint-inline { color: hsl(var(--muted-foreground)); }
.expand-btn {
  font-size: 11px;
  padding: 2px 8px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}
.expand-btn:hover { color: hsl(var(--foreground)); border-color: hsl(var(--primary) / 0.5); }
.lifecycle-row > td { background: hsl(var(--foreground) / 0.02); padding: 8px 14px; }
.lifecycle-timeline { display: flex; flex-wrap: wrap; gap: 6px 22px; }
.lifecycle-step { display: flex; align-items: center; gap: 6px; font-size: 12px; }
.step-dot { width: 8px; height: 8px; border-radius: 50%; background: hsl(var(--muted-foreground)); }
.step-dot.ok { background: hsl(var(--success)); }
.step-dot.bad { background: hsl(var(--error)); }
.step-dot.mid { background: hsl(var(--primary)); }
.step-status { font-weight: 600; color: hsl(var(--foreground)); }
.step-meta { color: hsl(var(--muted-foreground)); font-family: monospace; }
.step-time { color: hsl(var(--muted-foreground)); font-size: 11px; }

/* 血缘跳转目标行高亮 */
.row-highlight {
  animation: row-flash 2.5s ease-out;
}
@keyframes row-flash {
  0%, 60% { background: hsl(var(--primary) / 0.18); }
  100% { background: transparent; }
}

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
</style>
