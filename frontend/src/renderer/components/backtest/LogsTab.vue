<template>
  <div>
    <!-- 筛选栏 -->
    <div class="card logs-filter">
      <div class="filter-row">
        <select
          v-model="logFilters.level"
          class="form-select filter-select"
          @change="loadLogs(true)"
        >
          <option value="">
            全部级别
          </option>
          <option value="DEBUG">
            DEBUG
          </option>
          <option value="INFO">
            INFO
          </option>
          <option value="WARNING">
            WARNING
          </option>
          <option value="ERROR">
            ERROR
          </option>
          <option value="CRITICAL">
            CRITICAL
          </option>
        </select>
        <select
          v-model="logFilters.event_type"
          class="form-select filter-select"
          @change="loadLogs(true)"
        >
          <option value="">
            全部事件
          </option>
          <option value="SIGNALGENERATION">
            信号
          </option>
          <option value="ORDERSUBMITTED">
            订单提交
          </option>
          <option value="ORDERFILLED">
            成交
          </option>
          <option value="ORDERREJECTED">
            订单拒绝
          </option>
          <option value="ORDERCANCELACK">
            订单取消
          </option>
          <option value="ORDEREXPIRED">
            订单过期
          </option>
          <option value="POSITIONUPDATE">
            持仓更新
          </option>
          <option value="CAPITALUPDATE">
            资金更新
          </option>
          <option value="RISKBREACH">
            风控触发
          </option>
          <option value="ENGINESTART">
            引擎启动
          </option>
          <option value="ENGINESTOP">
            引擎停止
          </option>
          <option value="ENGINEERROR">
            引擎错误
          </option>
          <option value="ENGINECOMPLETE">
            引擎完成
          </option>
          <option value="T1SETTLEMENT">
            T+1结算
          </option>
          <option value="T1DELAYDECISION">
            T+1延迟
          </option>
          <option value="TIMEADVANCE">
            时间推进
          </option>
          <option value="PRICERECEIVED">
            行情接收
          </option>
          <option value="STRATEGYSIGNAL">
            策略信号
          </option>
        </select>
        <DateField
          v-model="logFilters.start_time"
          class="filter-date"
          bordered
          clearable
          @update:model-value="loadLogs(true)"
        />
        <span class="filter-sep">~</span>
        <DateField
          v-model="logFilters.end_time"
          class="filter-date"
          bordered
          clearable
          @update:model-value="loadLogs(true)"
        />
        <!-- 关键词:前端过滤已加载日志(message/symbol/事件字段),后端无 keyword 参数 -->
        <input
          v-model="logKeyword"
          type="search"
          placeholder="关键词过滤已加载日志…"
          class="form-input filter-keyword"
        >
      </div>
    </div>

    <!-- 日志列表 -->
    <div
      class="logs-container"
      @scroll="onLogsScroll"
    >
      <div
        v-if="logsLoading && logs.length === 0"
        class="loading-center"
      >
        <div class="spinner spinner-sm" />
      </div>
      <template v-else-if="filteredLogs.length > 0">
        <div
          v-for="(log, i) in filteredLogs"
          :key="i"
          class="log-entry"
        >
          <span class="log-time-col">
            <span class="log-bt">{{ formatLogTime(log.business_timestamp) }}</span>
            <span class="log-wt">{{ formatLogTime(log.timestamp) }}</span>
          </span>
          <span
            class="log-level"
            :class="levelClass(log.level)"
          >{{ log.level }}</span>
          <span
            v-if="log.event_type"
            class="log-event"
            :class="eventClass(log.event_type)"
          >{{ log.event_type }}</span>
          <!-- 结构化事件展示 -->
          <span
            v-if="log.event_type === 'SIGNALGENERATION'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span :class="directionColor(log.direction)">{{ dirLabel(log.direction) }}</span>
            <span
              v-if="log.signal_volume"
              class="log-kv"
            >vol={{ log.signal_volume }}</span>
            <span
              v-if="log.signal_reason"
              class="log-reason"
            >{{ log.signal_reason }}</span>
            <span
              v-if="log.strategy_id"
              class="log-kv dim"
            >strategy={{ log.strategy_id.substring(0, 8) }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ORDERSUBMITTED'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span class="log-kv">{{ log.order_type || 'MARKET' }}</span>
            <span
              v-if="log.limit_price"
              class="log-kv"
            >price={{ log.limit_price }}</span>
            <span
              v-if="log.order_id"
              class="log-kv dim"
            >{{ log.order_id }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ORDERACK'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span class="log-kv">accepted</span>
            <span
              v-if="log.broker_order_id"
              class="log-kv dim"
            >{{ log.broker_order_id }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ORDERFILLED'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span :class="directionColor(log.direction)">{{ dirLabel(log.direction) }}</span>
            <span class="log-kv">{{ log.transaction_volume }}@{{ log.transaction_price }}</span>
            <span
              v-if="log.commission"
              class="log-kv dim"
            >fee={{ log.commission }}</span>
            <span
              v-if="log.slippage"
              class="log-kv dim"
            >slip={{ log.slippage }}</span>
            <span class="log-msg-inline">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ORDERREJECTED'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span class="log-kv text-red">REJECTED</span>
            <span
              v-if="log.reject_reason"
              class="log-reason"
            >{{ log.reject_reason }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ORDERCANCELACK'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.symbol }}</span>
            <span class="log-kv dim">cancelled</span>
            <span
              v-if="log.cancel_reason"
              class="log-reason"
            >{{ log.cancel_reason }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'POSITIONUPDATE'"
            class="log-detail"
          >
            <span class="log-symbol">{{ log.position_code || log.symbol }}</span>
            <span class="log-kv">vol={{ log.position_volume }}</span>
            <span class="log-kv">cost={{ log.position_cost }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'CAPITALUPDATE'"
            class="log-detail"
          >
            <span class="log-kv">NAV={{ log.net_value || log.total_value }}</span>
            <span class="log-kv">cash={{ log.available_cash }}</span>
            <span
              v-if="log.pnl"
              :style="{ color: log.pnl >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }"
            >PnL={{ log.pnl }}</span>
            <span
              v-if="log.drawdown"
              class="log-kv dim"
            >DD={{ log.drawdown }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ENGINESTART' || log.event_type === 'ENGINESTOP' || log.event_type === 'ENGINECOMPLETE'"
            class="log-detail"
          >
            <span
              v-if="log.engine_status"
              class="log-kv"
            >{{ log.engine_status }}</span>
            <span
              v-if="log.progress"
              class="log-kv"
            >{{ (log.progress * 100).toFixed(0) }}%</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'ENGINEERROR'"
            class="log-detail"
          >
            <span
              v-if="log.error_code"
              class="log-kv text-red"
            >{{ log.error_code }}</span>
            <span class="log-reason">{{ log.error_message || log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'RISKBREACH'"
            class="log-detail"
          >
            <span class="log-kv text-red">{{ log.risk_type }}</span>
            <span
              v-if="log.risk_reason"
              class="log-reason"
            >{{ log.risk_reason }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'T1SETTLEMENT'"
            class="log-detail"
          >
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'T1DELAYDECISION'"
            class="log-detail"
          >
            <span
              v-if="log.symbol"
              class="log-kv"
            >{{ log.symbol }}</span>
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'TIMEADVANCE'"
            class="log-detail"
          >
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'PRICERECEIVED'"
            class="log-detail"
          >
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <span
            v-else-if="log.event_type === 'STRATEGYSIGNAL'"
            class="log-detail"
          >
            <span class="log-kv dim">{{ log.message }}</span>
          </span>
          <!-- 默认：纯文本 -->
          <span
            v-else
            class="log-msg"
          >{{ log.message }}</span>
        </div>
        <div
          v-if="logsLoading"
          class="loading-center"
        >
          <div class="spinner spinner-sm" />
        </div>
        <div
          v-if="!logsHasMore"
          class="logs-end"
        >
          {{ logKeyword ? `已加载 ${logsTotal} 条中匹配 ${filteredLogs.length} 条` : `已加载全部 ${logsTotal} 条日志` }}
        </div>
      </template>
      <p
        v-else-if="logKeyword && logs.length > 0"
        class="empty-hint"
      >
        已加载日志中无「{{ logKeyword }}」匹配（下拉加载更多后自动生效）
      </p>
      <p
        v-else
        class="empty-hint"
      >
        暂无日志数据
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 回测日志 tab(筛选 + 结构化事件流 + 下拉加载)
 *
 * 从 BacktestDetailPage 整体迁出:挂载即加载(父页 v-if 切 tab 控制懒加载,
 * 深链直达同样成立)。筛选/分页/关键词过滤全部内聚,父页只传任务 id 与
 * 默认时间范围。
 */
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { backtestApi } from '@/api'
import DateField from '@/components/common/DateField.vue'
import {
  formatLogTime, levelClass, eventClass, dirLabel, directionColor,
} from '@/composables/useBacktestFormatters'

const props = defineProps<{
  taskUuid: string
  /** 默认筛选区间(回测起止);详情刷新后随 prop 更新,与原 loadDetail 覆盖语义一致(只改值不重拉) */
  defaultRange?: { start?: string; end?: string }
}>()

// 防止组件卸载后异步操作继续执行
let disposed = false

const logs = ref<any[]>([])
const logsLoading = ref(false)
const logsTotal = ref(0)
const logsHasMore = ref(true)
const logsOffset = ref(0)
const logsPageSize = 100
const logFilters = ref({ level: '', event_type: '', start_time: '', end_time: '' })
// 关键词前端过滤:后端日志端点无 keyword 参数,对已加载批次做展示层过滤
const logKeyword = ref('')
const filteredLogs = computed(() => {
  const kw = logKeyword.value.trim().toLowerCase()
  if (!kw) return logs.value
  return logs.value.filter((l: any) =>
    [l.message, l.symbol, l.event_type, l.signal_reason, l.order_id, l.error_message]
      .some(f => f && String(f).toLowerCase().includes(kw)))
})

const loadLogs = async (reset = false) => {
  if (!props.taskUuid || disposed) return
  if (reset) {
    logsOffset.value = 0
    logs.value = []
    logsHasMore.value = true
  }
  if (!logsHasMore.value) return
  logsLoading.value = true
  try {
    const params: any = { limit: logsPageSize, offset: logsOffset.value }
    if (logFilters.value.level) params.level = logFilters.value.level
    if (logFilters.value.event_type) params.event_type = logFilters.value.event_type
    if (logFilters.value.start_time) params.start_time = logFilters.value.start_time
    if (logFilters.value.end_time) params.end_time = logFilters.value.end_time
    const res = await backtestApi.getLogs(props.taskUuid, params)
    if (disposed) return
    const d = res
    const newLogs = d.logs || []
    logsTotal.value = d.total || 0
    if (reset) {
      logs.value = newLogs
    } else {
      logs.value.push(...newLogs)
    }
    logsOffset.value += newLogs.length
    logsHasMore.value = logs.value.length < logsTotal.value
  } catch {
    logsHasMore.value = false
  } finally {
    if (!disposed) logsLoading.value = false
  }
}

const onLogsScroll = (e: Event) => {
  const el = e.target as HTMLElement
  if (el.scrollTop + el.clientHeight >= el.scrollHeight - 50 && !logsLoading.value && logsHasMore.value) {
    loadLogs()
  }
}

// 挂载即加载(父页 v-if 控制挂载时机=懒加载)。原版时序:首拉不带默认区间
// (loadLogs 先跑,logFilters 赋值在后且不重拉)——区间过滤若进首拉,时间口径
// 不匹配会把日志全滤空,故首拉完成后才应用默认区间值
onMounted(async () => {
  await loadLogs(true)
  applyDefaultRange(props.defaultRange)
})

onUnmounted(() => { disposed = true })

// 默认区间应用:只改筛选值,不触发重拉(与原 loadDetail 覆盖语义一致)
const applyDefaultRange = (r?: { start?: string; end?: string }) => {
  if (!r) return
  if (r.start) logFilters.value.start_time = r.start
  if (r.end) logFilters.value.end_time = r.end
}
// 详情晚到位(深链直达)时补应用
watch(() => props.defaultRange, applyDefaultRange)
</script>

<style scoped>
/* 样式自 BacktestDetailPage 原样迁入(视觉零变化) */
.card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 14px;
  margin-bottom: 12px;
}

.logs-filter { margin-bottom: 8px; }
.filter-row { display: flex; align-items: center; gap: 8px; }
.filter-select { width: auto; min-width: 100px; }
.filter-date { width: 140px; font-size: 12px; }
.filter-sep { color: hsl(var(--muted-foreground)); font-size: 12px; }

.filter-keyword {
  width: 200px;
  padding: 5px 10px;
  font-size: 12px;
}

.logs-container {
  max-height: 500px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.log-entry {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 4px 8px;
  font-size: 12px;
  font-family: 'SF Mono', 'Menlo', 'Consolas', monospace;
  border-radius: var(--radius-sm);
}
.log-entry:hover { background: hsl(var(--foreground) / 0.02); }

.log-time-col { display: inline-flex; flex-direction: column; flex-shrink: 0; line-height: 1.3; }
.log-bt { color: hsl(var(--muted-foreground)); font-size: 11px; white-space: nowrap; }
.log-wt { color: hsl(var(--muted-foreground)); font-size: 9px; white-space: nowrap; }
.log-level {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  display: inline-block;
  min-width: 52px;
  text-align: center;
}
.level-debug { background: hsl(var(--foreground) / 0.06); color: hsl(var(--muted-foreground)); }
.level-info { background: hsl(var(--primary) / 0.15); color: hsl(var(--primary)); }
.level-warning { background: hsl(var(--warning) / 0.15); color: hsl(var(--warning)); }
.level-error { background: hsl(var(--error) / 0.15); color: hsl(var(--error)); }
.log-event {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.3px;
  display: inline-block;
  width: 110px;
  text-align: center;
}
.event-signal { background: hsl(var(--secondary-foreground) / 0.15); color: hsl(var(--secondary-foreground)); }
.event-order { background: hsl(var(--success) / 0.15); color: hsl(var(--success)); }
.event-position { background: hsl(var(--warning) / 0.15); color: hsl(var(--warning)); }
.event-capital { background: hsl(var(--success) / 0.15); color: hsl(var(--success)); }
.event-engine { background: hsl(var(--primary) / 0.15); color: hsl(var(--primary)); }
.event-risk { background: hsl(var(--error) / 0.15); color: hsl(var(--error)); }
.event-price { background: hsl(var(--foreground) / 0.06); color: hsl(var(--muted-foreground)); }
.event-t1 { background: hsl(var(--warning) / 0.15); color: hsl(var(--warning)); }
.text-red { color: hsl(var(--error)); }
.text-orange { color: hsl(var(--warning)); }
.log-detail { color: hsl(var(--muted-foreground)); display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
.log-symbol { color: hsl(var(--foreground)); font-weight: 600; }
.log-kv { color: hsl(var(--muted-foreground)); }
.log-kv.dim { color: hsl(var(--muted-foreground)); }
.log-reason { color: hsl(var(--muted-foreground)); font-style: italic; }
.log-msg { color: hsl(var(--foreground)); word-break: break-all; }
.logs-end { text-align: center; font-size: 11px; color: hsl(var(--muted-foreground)); padding: 10px 0; }

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
