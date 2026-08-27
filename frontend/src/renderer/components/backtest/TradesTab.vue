<template>
  <div class="trades-columns">
    <!-- 三表(信号/订单/持仓记录)共用的 code 多选筛选 -->
    <CodeFilter
      v-model:selected="selectedCodes"
      :codes="allCodes"
    />

    <!-- 血缘联动状态条:当前选中链 + 清除 -->
    <div
      v-if="selection"
      class="linkage-bar"
    >
      <span class="linkage-label">血缘链:</span>
      <span
        v-if="selSignalDigest"
        class="linkage-node"
      >信号 {{ selSignalDigest }}</span>
      <span class="linkage-arrow">→</span>
      <span
        v-if="selOrderDigest"
        class="linkage-node"
      >订单 {{ selOrderDigest }}</span>
      <span class="linkage-arrow">→</span>
      <span class="linkage-node">持仓 {{ hlPositionKeys.size }} 条变动</span>
      <button
        class="linkage-clear"
        @click="clearSelection"
      >
        清除
      </button>
    </div>

    <!-- 三列联动:信号 → 订单(记录) → 持仓记录。不过滤,点选=高亮关联+滚动到位。
         窄列宽表不可读,三列统一用"卡片流"(主行=身份字段,次行=次要字段
         flex-wrap 换行)替代 table——自适应任意列宽,不截断不横滚。 -->
    <div class="three-col">
      <!-- 信号列 -->
      <section class="col">
        <header class="col-head">
          <span>信号</span>
          <span class="col-count">{{ filteredSignals.length }}{{ hlSignalKeys.size ? ` · ${hlSignalKeys.size} 关联` : '' }}</span>
        </header>
        <div
          ref="colSignals"
          class="col-body"
        >
          <div
            v-if="signalsLoading"
            class="loading-center"
          >
            <div class="spinner spinner-sm" />
          </div>
          <template v-else-if="filteredSignals.length > 0">
            <article
              v-for="s in filteredSignals"
              :key="s.uuid"
              class="item-card clickable"
              :class="{ 'row-selected': hlSignalKeys.has(s.uuid) }"
              @click="selectSignal(s)"
            >
              <div class="item-main">
                <span class="item-code">{{ s.code }}</span>
                <span :class="directionColor(s.direction)">{{ directionLabel(s.direction) }}</span>
                <span class="grow" />
                <span class="item-time">{{ formatShortDate(s.business_timestamp || s.timestamp) }}</span>
              </div>
              <div class="item-sub">
                <span>权重 {{ (s.weight * 100).toFixed(1) }}%</span>
                <span v-if="s.reason">{{ s.reason }}</span>
              </div>
            </article>
          </template>
          <p
            v-else
            class="empty-hint"
          >
            暂无信号记录
          </p>
        </div>
      </section>

      <!-- 订单列 -->
      <section class="col">
        <header class="col-head">
          <span>订单</span>
          <span class="col-count">{{ filteredOrders.length }}{{ hlOrderKeys.size ? ` · ${hlOrderKeys.size} 关联` : '' }}</span>
        </header>
        <div
          ref="colOrders"
          class="col-body"
        >
          <div
            v-if="ordersLoading"
            class="loading-center"
          >
            <div class="spinner spinner-sm" />
          </div>
          <template v-else-if="filteredOrders.length > 0">
            <article
              v-for="o in filteredOrders"
              :key="o.uuid"
              class="item-card clickable"
              :class="{ 'row-selected': hlOrderKeys.has(orderKey(o)) }"
              @click="selectOrder(o)"
            >
              <div class="item-main">
                <span class="item-code">{{ o.code }}</span>
                <span :class="directionColor(o.direction)">{{ directionLabel(o.direction) }}</span>
                <span class="item-qty">{{ o.transaction_volume }}@{{ o.transaction_price }}</span>
                <span class="grow" />
                <span class="item-time">{{ formatShortDate(o.timestamp) }}</span>
              </div>
              <div class="item-sub">
                <span>费 {{ o.fee }}</span>
                <span
                  v-if="o.signal_id"
                  class="lineage-chip"
                  :title="`信号 ${o.signal_id}`"
                  @click.stop="selectSignalById(o.signal_id)"
                >{{ signalDigest(o.signal_id) }}</span>
                <span class="grow" />
                <button
                  class="expand-btn"
                  @click.stop="toggleLifecycle(orderKey(o))"
                >
                  {{ expandedOrder === orderKey(o) ? '收起' : '生命周期' }}
                </button>
              </div>
              <!-- 生命周期时间线:该订单全部状态流转(order_record 流水) -->
              <div
                v-if="expandedOrder === orderKey(o)"
                class="lifecycle-box"
              >
                <div
                  v-if="lifecycleLoading"
                  class="loading-center"
                >
                  <div class="spinner spinner-sm" />
                </div>
                <template v-else>
                  <div
                    v-if="expandedLifecycle.length"
                    class="lifecycle-timeline"
                  >
                    <div
                      v-for="(st, i) in expandedLifecycle"
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
              </div>
            </article>
          </template>
          <p
            v-else
            class="empty-hint"
          >
            暂无订单记录
          </p>
        </div>
      </section>

      <!-- 持仓记录列 -->
      <section class="col">
        <header class="col-head">
          <span>持仓记录</span>
          <span class="col-count">{{ filteredPositions.length }}{{ hlPositionKeys.size ? ` · ${hlPositionKeys.size} 关联` : '' }}</span>
        </header>
        <div
          ref="colPositions"
          class="col-body"
        >
          <div
            v-if="positionsLoading"
            class="loading-center"
          >
            <div class="spinner spinner-sm" />
          </div>
          <template v-else-if="filteredPositions.length > 0">
            <article
              v-for="p in filteredPositions"
              :key="p.uuid"
              class="item-card clickable"
              :class="{ 'row-selected': hlPositionKeys.has(p.uuid) }"
              @click="selectPosition(p)"
            >
              <div class="item-main">
                <span class="item-code">{{ p.code }}</span>
                <span :class="directionColor(p.direction)">{{ directionLabel(p.direction) }}</span>
                <!-- 变动流水:带符号,+买/-卖 -->
                <span
                  class="item-qty"
                  :style="{ color: getPnLColor(p.volume) }"
                >{{ p.volume > 0 ? '+' : '' }}{{ p.volume }}</span>
                <span class="grow" />
                <span class="item-time">{{ formatShortDate(p.business_timestamp || p.timestamp) }}</span>
              </div>
              <div class="item-sub">
                <span>市值 {{ formatDecimal(p.market_value) }}</span>
                <!-- 买入行无盈亏语义(cost=成交后均价,(price-cost)×vol 是残差),后端恒 null → 不展示 -->
                <template v-if="p.profit != null">
                  <span :style="{ color: getPnLColor(p.profit) }">
                    盈亏 {{ formatDecimal(p.profit) }}{{ p.profit_pct != null ? ` (${(p.profit_pct * 100).toFixed(2)}%)` : '' }}
                  </span>
                </template>
                <span
                  v-if="p.order_id"
                  class="lineage-chip"
                  title="点击联动该订单"
                  @click.stop="selectOrderByKey(p.order_id)"
                >{{ p.order_id.slice(0, 8) }}</span>
              </div>
            </article>
          </template>
          <p
            v-else
            class="empty-hint"
          >
            暂无持仓记录
          </p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 回测交易记录三列联动视图(信号 → 订单 → 持仓记录)
 *
 * 血缘横向成链(2026-08-17):Signal.uuid → Order.signal_id / Order.order_id →
 * PositionRecord.order_id。三列并排展示全量数据,点选任一行 = 高亮血缘关联行
 * + 滚动到位(不做过滤,保持全局上下文);再次点击取消选中。
 * 订单卡片可展开生命周期时间线(order_record 状态流水,选中订单时自动展开)。
 *
 * 展示形态:三列统一"卡片流"(主行=身份字段 代码/方向/数量/时间,次行=次要
 * 字段 flex-wrap)——窄列表格挤压不可读,卡片流自适应任意列宽,不截断不横滚。
 */
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { backtestApi } from '@/api'
import CodeFilter from '@/components/common/CodeFilter.vue'
import {
  formatShortDate, formatDecimal, directionLabel, directionColor, getPnLColor,
} from '@/composables/useBacktestFormatters'

const props = defineProps<{
  taskUuid: string
}>()

// 防止组件卸载后异步操作继续执行
let disposed = false

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

// ---- 血缘联动(2026-08-17):单锚点选中态唯一驱动,三列高亮集合由此派生 ----
// 锚定信号(kind='signal',key=uuid)或订单(kind='order',key=order_id||uuid),
// 高亮互相派生:选信号→订单由 signal_id 反查;选订单→信号由 order.signal_id 派生。
const selection = ref<{ kind: 'signal' | 'order'; key: string } | null>(null)
// 订单分组键:状态流水按 order_id 分组;列表行的 uuid 是"去重取最新那条流水行"
// 的行 uuid,与其它状态行的 uuid 各不相同,统一用 order_id 作键
const orderKey = (o: any) => o.order_id || o.uuid
// uuid → 信号对象(订单行 digest 查找 O(1),避免逐行 find 的 O(n²))
const signalById = computed(() => new Map(signals.value.map(s => [s.uuid, s])))

// 当前锚定订单对象(信号锚点取首个关联订单,供血缘链摘要展示)
const selOrderObj = computed(() => {
  if (selection.value?.kind === 'order') {
    return orders.value.find(x => orderKey(x) === selection.value?.key)
  }
  if (selection.value?.kind === 'signal') {
    return orders.value.find(o => o.signal_id === selection.value?.key)
  }
  return undefined
})

// 高亮集合(派生):信号列/订单列/持仓列各自命中的行
const hlSignalKeys = computed<Set<string>>(() => {
  const sel = selection.value
  if (sel?.kind === 'signal') return new Set([sel.key])
  const sid = selOrderObj.value?.signal_id
  return sid ? new Set([sid]) : new Set()
})
const hlOrderKeys = computed<Set<string>>(() => {
  const sel = selection.value
  if (sel?.kind === 'order') return new Set([sel.key])
  if (sel?.kind === 'signal') {
    return new Set(orders.value.filter(o => o.signal_id === sel.key).map(orderKey))
  }
  return new Set()
})
const hlPositionKeys = computed<Set<string>>(() => {
  if (!hlOrderKeys.value.size) return new Set()
  return new Set(positions.value.filter(p => p.order_id && hlOrderKeys.value.has(p.order_id)).map(p => p.uuid))
})

// 顶部血缘链摘要
const selSignalDigest = computed(() => {
  if (selection.value?.kind === 'signal') return signalDigest(selection.value.key)
  const sid = selOrderObj.value?.signal_id
  return sid ? signalDigest(sid) : ''
})
const selOrderDigest = computed(() => {
  const o = selOrderObj.value
  if (o) return `${o.code} ${formatShortDate(o.timestamp).slice(5, 10)}`
  return selection.value?.kind === 'order' ? selection.value.key.slice(0, 8) : ''
})

const clearSelection = () => { selection.value = null }

// 三列容器 ref:联动后滚动到各列首个高亮行
const colSignals = ref<HTMLElement | null>(null)
const colOrders = ref<HTMLElement | null>(null)
const colPositions = ref<HTMLElement | null>(null)
const scrollToFirst = (root: HTMLElement | null, selector: string) => {
  root?.querySelector<HTMLElement>(selector)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}
const scrollAllColumns = async () => {
  await nextTick()
  scrollToFirst(colSignals.value, '.row-selected')
  scrollToFirst(colOrders.value, '.row-selected')
  scrollToFirst(colPositions.value, '.row-selected')
}

// ---- 点选联动(不过滤,高亮+滚动;再点同卡取消) ----
const selectSignalById = (signalId: string) => {
  selection.value = { kind: 'signal', key: signalId }
  scrollAllColumns()
}
const selectSignal = (s: any) => {
  if (selection.value?.kind === 'signal' && selection.value.key === s.uuid) { clearSelection(); return }
  selectSignalById(s.uuid)
}
const selectOrderByKey = async (key: string) => {
  if (selection.value?.kind === 'order' && selection.value.key === key) { clearSelection(); return }
  selection.value = { kind: 'order', key }
  await ensureLifecycleExpanded(key)  // 选中订单=自动展开生命周期
  scrollAllColumns()
}
const selectOrder = (o: any) => selectOrderByKey(orderKey(o))
// 点持仓行:联动其来源订单(信号由订单的 signal_id 派生)
const selectPosition = (p: any) => {
  if (p.order_id) return selectOrderByKey(p.order_id)
}

// ---- 订单生命周期:expandedOrder=当前展开的订单键;orderRecords=全量状态流水 ----
const expandedOrder = ref<string | null>(null)
const orderRecords = ref<any[]>([])
// 已加载标记:空结果也视为已加载(按 length 判会被空数据击穿缓存,每次点选重复请求)
const recordsLoaded = ref(false)
const lifecycleLoading = ref(false)
const lifecycleOf = (orderId: string) =>
  orderRecords.value
    .filter(r => r.order_id === orderId || r.uuid === orderId)
    .sort((a: any, b: any) => Number(a.status) - Number(b.status))  // NEW(1)→FILLED(4) 生命周期顺序
// 单订单可展开,计算属性缓存住 filter+sort,模板单点引用
const expandedLifecycle = computed(() =>
  expandedOrder.value ? lifecycleOf(expandedOrder.value) : [])
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
const loadOrderRecords = async () => {
  if (recordsLoaded.value || lifecycleLoading.value) return
  lifecycleLoading.value = true
  try {
    const res = await backtestApi.getOrderRecords(props.taskUuid)
    if (!disposed) {
      orderRecords.value = ((res as any).data || res) as any[]
      recordsLoaded.value = true
    }
  } catch { orderRecords.value = [] }  // 失败不置 recordsLoaded,下次点击可重试
  finally { lifecycleLoading.value = false }
}
const toggleLifecycle = async (orderK: string) => {
  if (expandedOrder.value === orderK) { expandedOrder.value = null; return }
  expandedOrder.value = orderK
  await loadOrderRecords()
}
const ensureLifecycleExpanded = async (orderK: string) => {
  expandedOrder.value = orderK
  await loadOrderRecords()
}

// 来源信号摘要:uuid → "代码 方向 日期"(uuid 本身不可读;join 本页已加载的信号数据)
const signalDigest = (signalId: string) => {
  const sig = signalById.value.get(signalId)
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

onUnmounted(() => { disposed = true })
</script>

<style scoped>
.trades-columns { display: flex; flex-direction: column; gap: 12px; }

/* 血缘联动状态条 */
.linkage-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 12px;
  background: hsl(var(--primary) / 0.06);
  border: 1px solid hsl(var(--primary) / 0.2);
  border-radius: var(--radius);
  padding: 6px 10px;
}
.linkage-label { color: hsl(var(--muted-foreground)); }
.linkage-node { font-weight: 600; color: hsl(var(--foreground)); }
.linkage-arrow { color: hsl(var(--muted-foreground)); }
.linkage-clear {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 10px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}
.linkage-clear:hover { color: hsl(var(--foreground)); border-color: hsl(var(--primary) / 0.5); }

/* 三列布局:订单列稍宽(含生命周期展开) */
.three-col {
  display: grid;
  grid-template-columns: 1fr 1.25fr 1fr;
  gap: 12px;
  align-items: start;
}
.col {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  min-width: 0;
}
.col-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid hsl(var(--border));
}
.col-count { font-size: 11px; font-weight: 400; color: hsl(var(--muted-foreground)); }
.col-body { max-height: 560px; overflow-y: auto; overflow-x: hidden; padding: 6px; }

/* ---- 通用卡片流:主行(身份字段)+次行(次要字段 flex-wrap) ----
   窄列宽表的通用替代:不截断不横滚,字段多时自然换行 */
.item-card {
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  margin-bottom: 4px;
}
.item-card:hover { background: hsl(var(--foreground) / 0.03); }
.item-main {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: hsl(var(--foreground));
}
.item-code { font-weight: 600; font-family: monospace; }
.item-qty { font-family: monospace; color: hsl(var(--foreground) / 0.85); }
.item-time { color: hsl(var(--muted-foreground)); font-size: 11px; white-space: nowrap; }
.item-sub {
  display: flex;
  align-items: center;
  gap: 4px 10px;
  flex-wrap: wrap;
  margin-top: 3px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}
.grow { flex: 1 1 auto; }
.clickable { cursor: pointer; }

/* 血缘联动选中卡片:持续高亮(非闪现),点击同卡取消 */
.row-selected {
  border-color: hsl(var(--primary) / 0.5);
  background: hsl(var(--primary) / 0.08);
}
.row-selected:hover { background: hsl(var(--primary) / 0.1); }

/* 血缘 chip */
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

/* 订单生命周期:卡片内展开区(竖向时间线,窄列不横滚) */
.expand-btn {
  font-size: 11px;
  padding: 1px 8px;
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}
.expand-btn:hover { color: hsl(var(--foreground)); border-color: hsl(var(--primary) / 0.5); }
.lifecycle-box {
  margin-top: 6px;
  padding: 6px 8px;
  background: hsl(var(--foreground) / 0.03);
  border-radius: var(--radius-sm);
}
.lifecycle-timeline { display: flex; flex-direction: column; gap: 4px; }
.lifecycle-step { display: flex; align-items: center; gap: 6px; font-size: 11px; flex-wrap: wrap; }
.step-dot { width: 7px; height: 7px; border-radius: 50%; background: hsl(var(--muted-foreground)); flex: none; }
.step-dot.ok { background: hsl(var(--success)); }
.step-dot.bad { background: hsl(var(--error)); }
.step-dot.mid { background: hsl(var(--primary)); }
.step-status { font-weight: 600; color: hsl(var(--foreground)); }
.step-meta { color: hsl(var(--muted-foreground)); font-family: monospace; }
.step-time { color: hsl(var(--muted-foreground)); font-size: 10px; }

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
