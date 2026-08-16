<template>
  <PageLayout>
    <template #title>
      <PageTitle :title="pageTitle" back-to="/backtests" back-label="回测中心" />
    </template>
    <template #meta>
      <template v-if="currentTask">
        <span class="tag" :class="statusTagClass(currentTask.status)">{{ statusLabel(currentTask.status) }}</span>
        <span class="task-uuid" :title="`${currentTask.uuid}（点击复制）`" @click="copyUuid">{{ currentTask.uuid.slice(0, 8) }}</span>
        <router-link
          v-if="currentTask.portfolio_id"
          :to="`/portfolios/${currentTask.portfolio_id}`"
          class="portfolio-link"
        >组合：{{ portfolioLabel }}</router-link>
      </template>
    </template>
    <template #actions>
      <div v-if="currentTask" class="detail-actions">
        <button v-if="canStartByState(currentTask.status)" class="btn-primary" @click="handleReRun">重新运行</button>
        <button v-if="canStopByState(currentTask.status)" class="btn-danger" @click="handleStop">停止</button>
        <button v-if="currentTask.status !== 'running'" class="btn-danger-outline" @click="handleDelete">删除</button>
      </div>
    </template>

    <!-- 详情内容 -->
    <div v-if="detailLoading" class="loading-center"><div class="spinner"></div></div>

    <div v-else-if="currentTask" class="detail-content">
      <!-- 回测区间 + 配置摘要(可折叠):config 来自任务 config_snapshot,口径对齐依据) -->
      <div v-if="currentTask.backtest_start_date || currentTask.backtest_end_date" class="date-range-bar">
        <span class="date-range-label">回测区间</span>
        <span class="date-range-value">{{ formatShortDate(currentTask.backtest_start_date) }} ~ {{ formatShortDate(currentTask.backtest_end_date) }}</span>
        <button v-if="configItems.length" class="config-toggle" @click="showConfig = !showConfig">
          回测配置 {{ showConfig ? '▲' : '▼' }}
        </button>
      </div>
      <div v-if="showConfig && configItems.length" class="config-summary">
        <div v-for="item in configItems" :key="item.label" class="config-cell">
          <span class="config-label">{{ item.label }}</span>
          <span class="config-val">{{ item.value }}</span>
        </div>
      </div>

      <!-- 进度 -->
      <div v-if="currentTask.status === 'running' || currentTask.status === 'pending'" class="card">
        <div class="progress-section">
          <span>{{ currentTask.current_stage || '处理中' }}</span>
          <span>{{ (currentTask.progress || 0).toFixed(1) }}%</span>
        </div>
        <div class="progress-bar-lg"><div class="progress-fill active" :style="{ width: (currentTask.progress || 0) + '%' }"></div></div>
      </div>

      <!-- 详情 tab(L2,状态进 URL query: ?tab=) -->
      <TabsNav v-model="activeDetailTab" size="small" :items="detailTabs" class="bt-subtabs" />

      <!-- 概览 -->
      <div v-if="activeDetailTab === 'overview'" class="tab-panel">
        <!-- 净值曲线 -->
        <div class="card">
          <h4>净值曲线</h4>
          <NetValueChart v-if="netValueData.length > 0" :data="netValueData" :benchmark-data="benchmarkData" :height="300" />
          <p v-else class="empty-hint">暂无净值数据</p>
        </div>

        <!-- 指标(hover 出口径说明;'—'=分析器未产出该指标,与真实 0 区分) -->
        <div class="metrics-grid">
          <div v-for="m in metrics" :key="m.label" class="metric-card" :title="m.hint">
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-value" :class="{ 'metric-empty': m.empty }" :style="!m.empty && m.color ? { color: m.color } : undefined">{{ m.value }}</div>
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
        <div v-if="analyzers.length > 0" class="card">
          <h4>分析器</h4>
          <table class="data-table">
            <thead><tr><th>名称</th><th>最新值</th><th>记录数</th><th>变化</th></tr></thead>
            <tbody>
              <tr v-for="a in analyzers" :key="a.name">
                <td><span class="tag tag-blue">{{ a.name }}</span></td>
                <td :style="{ color: getAnalyzerColor(a.name, a.latest_value) }">{{ fmtAnalyzer(a.name, a.latest_value) }}</td>
                <td>{{ a.stats?.count || 0 }}</td>
                <td :style="{ color: (a.stats?.change || 0) >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
                  {{ (a.stats?.change || 0) >= 0 ? '↑' : '↓' }} {{ fmtAnalyzer(a.name, Math.abs(a.stats?.change || 0)) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 错误 -->
        <div v-if="currentTask.error_message" class="card card-error">
          <h4>错误信息</h4>
          <pre>{{ currentTask.error_message }}</pre>
        </div>
      </div>

      <!-- 分析器详情 -->
      <div v-if="activeDetailTab === 'analyzers'" class="tab-panel">
        <div class="card">
          <div v-if="analyzerLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
          <template v-else-if="analyzerStats">
            <NetValueChart v-if="analyzerChartData.length > 0" :data="analyzerChartData" :height="250" />
            <div class="analyzer-header">
              <select v-model="selectedAnalyzer" class="form-select" @change="loadAnalyzerData">
                <option v-for="a in analyzers" :key="a.name" :value="a.name">{{ a.name }}</option>
              </select>
            </div>
            <div class="stats-row">
              <span>Count: {{ analyzerStats.count }}</span>
              <span>Min: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.min) }}</span>
              <span>Max: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.max) }}</span>
              <span>Avg: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.avg) }}</span>
              <span>Change: {{ fmtAnalyzer(selectedAnalyzer, analyzerStats.change) }}</span>
            </div>
            <table v-if="analyzerTimeseries.length > 0" class="data-table">
              <thead><tr><th>时间</th><th>值</th></tr></thead>
              <tbody>
                <tr v-for="(row, i) in analyzerTimeseries.slice(-50)" :key="i">
                  <td>{{ row.time }}</td>
                  <td :style="{ color: getAnalyzerColor(selectedAnalyzer, row.value) }">{{ fmtAnalyzer(selectedAnalyzer, row.value) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-hint">暂无时序数据</p>
          </template>
          <p v-else class="empty-hint">请选择分析器</p>
        </div>
      </div>

      <!-- 交易记录 -->
      <div v-if="activeDetailTab === 'trades'" class="tab-panel">
        <!-- 交易子 tab(L3,状态进 URL query: &trade=) -->
        <TabsNav v-model="activeTradeTab" size="small" :items="tradeSubTabs" class="bt-subtabs" />

        <!-- 三表(信号/订单/持仓记录)共用的 code 多选筛选 -->
        <CodeFilter v-model:selected="selectedCodes" :codes="allCodes" />

        <!-- 信号 -->
        <div v-if="activeTradeTab === 'signals'" class="card">
          <div v-if="signalsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
          <table v-else-if="filteredSignals.length > 0" class="data-table">
            <thead><tr><th>代码</th><th>方向</th><th>权重</th><th>原因</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="s in filteredSignals" :key="s.uuid" :data-uuid="s.uuid" :class="{ 'row-highlight': highlightUuid === s.uuid }">
                <td>{{ s.code }}</td>
                <td><span :class="directionColor(s.direction)">{{ directionLabel(s.direction) }}</span></td>
                <td>{{ (s.weight * 100).toFixed(1) }}%</td>
                <td>{{ s.reason || '-' }}</td>
                <td>{{ formatShortDate(s.business_timestamp || s.timestamp) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="empty-hint">暂无信号记录</p>
        </div>

        <!-- 订单 -->
        <div v-if="activeTradeTab === 'orders'" class="card">
          <div v-if="ordersLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
          <table v-else-if="filteredOrders.length > 0" class="data-table">
            <thead><tr><th>代码</th><th>方向</th><th>类型</th><th>数量</th><th>成交价</th><th>手续费</th><th>来源信号</th><th>时间</th><th></th></tr></thead>
            <tbody>
              <template v-for="o in filteredOrders" :key="o.uuid">
                <tr :data-order="o.order_id || o.uuid" :class="{ 'row-highlight': highlightOrder === (o.order_id || o.uuid) }">
                  <td>{{ o.code }}</td>
                  <td><span :class="directionColor(o.direction)">{{ directionLabel(o.direction) }}</span></td>
                  <td>{{ o.order_type }}</td>
                  <td>{{ o.transaction_volume }}</td>
                  <td>{{ o.transaction_price }}</td>
                  <td>{{ o.fee }}</td>
                  <td>
                    <span v-if="o.signal_id" class="lineage-chip" :title="`信号 ${o.signal_id}\n点击跳转`"
                      @click="jumpToSignal(o.signal_id)">{{ signalDigest(o.signal_id) }}</span>
                    <span v-else class="empty-hint-inline">-</span>
                  </td>
                  <td>{{ formatShortDate(o.timestamp) }}</td>
                  <td><button class="expand-btn" @click="toggleLifecycle(o.order_id || o.uuid)">
                    {{ expandedOrder === (o.order_id || o.uuid) ? '收起' : '生命周期' }}
                  </button></td>
                </tr>
                <!-- 生命周期时间线:该订单全部状态流转(order_record 流水) -->
                <tr v-if="expandedOrder === (o.order_id || o.uuid)" class="lifecycle-row">
                  <td :colspan="9">
                    <div v-if="lifecycleLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
                    <template v-else>
                      <div v-if="lifecycleOf(o.order_id || o.uuid).length" class="lifecycle-timeline">
                        <div v-for="(st, i) in lifecycleOf(o.order_id || o.uuid)" :key="i" class="lifecycle-step">
                          <span class="step-dot" :class="stepClass(st.status)"></span>
                          <span class="step-status">{{ orderStatusName(st.status) }}</span>
                          <span v-if="Number(st.transaction_volume) > 0" class="step-meta">{{ st.transaction_volume }}@{{ st.transaction_price || '-' }}</span>
                          <span class="step-time">{{ st.timestamp || '-' }}</span>
                        </div>
                      </div>
                      <p v-else class="empty-hint">暂无状态流水</p>
                    </template>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
          <p v-else class="empty-hint">暂无订单记录</p>
        </div>

        <!-- 持仓 -->
        <div v-if="activeTradeTab === 'positions'" class="card">
          <div v-if="positionsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
          <table v-else-if="filteredPositions.length > 0" class="data-table">
            <thead><tr><th>代码</th><th>方向</th><th>数量</th><th>成本</th><th>市值</th><th>盈亏</th><th>盈亏%</th><th>来源订单</th><th>时间</th></tr></thead>
            <tbody>
              <tr v-for="p in filteredPositions" :key="p.uuid">
                <td>{{ p.code }}</td>
                <td><span :class="directionColor(p.direction)">{{ directionLabel(p.direction) }}</span></td>
                <td :style="{ color: p.volume >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">{{ p.volume > 0 ? '+' : '' }}{{ p.volume }}</td><!-- 变动流水:带符号,+买/-卖 -->
                <td>{{ formatDecimal(p.cost) }}</td>
                <td>{{ formatDecimal(p.market_value) }}</td>
                <td :style="{ color: p.profit >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">{{ formatDecimal(p.profit) }}</td>
                <td :style="{ color: p.profit_pct >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">{{ (p.profit_pct * 100).toFixed(2) }}%</td>
                <td>
                  <span v-if="p.order_id" class="lineage-chip" title="点击查看该订单生命周期"
                    @click="jumpToOrder(p.order_id)">{{ p.order_id.slice(0, 8) }}</span>
                  <span v-else class="empty-hint-inline">-</span>
                </td>
                <td>{{ formatShortDate(p.business_timestamp || p.timestamp) }}</td><!-- 业务时间优先,同信号列口径 -->
              </tr>
            </tbody>
          </table>
          <p v-else class="empty-hint">暂无持仓记录</p>
        </div>
      </div>

      <!-- 日志 -->
      <div v-if="activeDetailTab === 'logs'" class="tab-panel">
        <!-- 筛选栏 -->
        <div class="card logs-filter">
          <div class="filter-row">
            <select v-model="logFilters.level" class="form-select filter-select" @change="loadLogs(true)">
              <option value="">全部级别</option>
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
            <select v-model="logFilters.event_type" class="form-select filter-select" @change="loadLogs(true)">
              <option value="">全部事件</option>
              <option value="SIGNALGENERATION">信号</option>
              <option value="ORDERSUBMITTED">订单提交</option>
              <option value="ORDERFILLED">成交</option>
              <option value="ORDERREJECTED">订单拒绝</option>
              <option value="ORDERCANCELACK">订单取消</option>
              <option value="ORDEREXPIRED">订单过期</option>
              <option value="POSITIONUPDATE">持仓更新</option>
              <option value="CAPITALUPDATE">资金更新</option>
              <option value="RISKBREACH">风控触发</option>
              <option value="ENGINESTART">引擎启动</option>
              <option value="ENGINESTOP">引擎停止</option>
              <option value="ENGINEERROR">引擎错误</option>
              <option value="ENGINECOMPLETE">引擎完成</option>
              <option value="T1SETTLEMENT">T+1结算</option>
              <option value="T1DELAYDECISION">T+1延迟</option>
              <option value="TIMEADVANCE">时间推进</option>
              <option value="PRICERECEIVED">行情接收</option>
              <option value="STRATEGYSIGNAL">策略信号</option>
            </select>
            <input v-model="logFilters.start_time" type="date" class="form-input filter-date" @change="loadLogs(true)" />
            <span class="filter-sep">~</span>
            <input v-model="logFilters.end_time" type="date" class="form-input filter-date" @change="loadLogs(true)" />
            <!-- 关键词:前端过滤已加载日志(message/symbol/事件字段),后端无 keyword 参数 -->
            <input v-model="logKeyword" type="search" placeholder="关键词过滤已加载日志…" class="form-input filter-keyword" />
          </div>
        </div>

        <!-- 日志列表 -->
        <div class="logs-container" @scroll="onLogsScroll">
          <div v-if="logsLoading && logs.length === 0" class="loading-center"><div class="spinner spinner-sm"></div></div>
          <template v-else-if="filteredLogs.length > 0">
            <div v-for="(log, i) in filteredLogs" :key="i" class="log-entry">
              <span class="log-time-col">
                <span class="log-bt">{{ formatLogTime(log.business_timestamp) }}</span>
                <span class="log-wt">{{ formatLogTime(log.timestamp) }}</span>
              </span>
              <span class="log-level" :class="levelClass(log.level)">{{ log.level }}</span>
              <span v-if="log.event_type" class="log-event" :class="eventClass(log.event_type)">{{ log.event_type }}</span>
              <!-- 结构化事件展示 -->
              <span v-if="log.event_type === 'SIGNALGENERATION'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span :class="directionColor(log.direction)">{{ dirLabel(log.direction) }}</span>
                <span v-if="log.signal_volume" class="log-kv">vol={{ log.signal_volume }}</span>
                <span v-if="log.signal_reason" class="log-reason">{{ log.signal_reason }}</span>
                <span v-if="log.strategy_id" class="log-kv dim">strategy={{ log.strategy_id.substring(0, 8) }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ORDERSUBMITTED'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span class="log-kv">{{ log.order_type || 'MARKET' }}</span>
                <span v-if="log.limit_price" class="log-kv">price={{ log.limit_price }}</span>
                <span v-if="log.order_id" class="log-kv dim">{{ log.order_id }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ORDERACK'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span class="log-kv">accepted</span>
                <span v-if="log.broker_order_id" class="log-kv dim">{{ log.broker_order_id }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ORDERFILLED'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span :class="directionColor(log.direction)">{{ dirLabel(log.direction) }}</span>
                <span class="log-kv">{{ log.transaction_volume }}@{{ log.transaction_price }}</span>
                <span v-if="log.commission" class="log-kv dim">fee={{ log.commission }}</span>
                <span v-if="log.slippage" class="log-kv dim">slip={{ log.slippage }}</span>
                <span class="log-msg-inline">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ORDERREJECTED'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span class="log-kv text-red">REJECTED</span>
                <span v-if="log.reject_reason" class="log-reason">{{ log.reject_reason }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ORDERCANCELACK'" class="log-detail">
                <span class="log-symbol">{{ log.symbol }}</span>
                <span class="log-kv dim">cancelled</span>
                <span v-if="log.cancel_reason" class="log-reason">{{ log.cancel_reason }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'POSITIONUPDATE'" class="log-detail">
                <span class="log-symbol">{{ log.position_code || log.symbol }}</span>
                <span class="log-kv">vol={{ log.position_volume }}</span>
                <span class="log-kv">cost={{ log.position_cost }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'CAPITALUPDATE'" class="log-detail">
                <span class="log-kv">NAV={{ log.net_value || log.total_value }}</span>
                <span class="log-kv">cash={{ log.available_cash }}</span>
                <span v-if="log.pnl" :style="{ color: log.pnl >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">PnL={{ log.pnl }}</span>
                <span v-if="log.drawdown" class="log-kv dim">DD={{ log.drawdown }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ENGINESTART' || log.event_type === 'ENGINESTOP' || log.event_type === 'ENGINECOMPLETE'" class="log-detail">
                <span v-if="log.engine_status" class="log-kv">{{ log.engine_status }}</span>
                <span v-if="log.progress" class="log-kv">{{ (log.progress * 100).toFixed(0) }}%</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'ENGINEERROR'" class="log-detail">
                <span v-if="log.error_code" class="log-kv text-red">{{ log.error_code }}</span>
                <span class="log-reason">{{ log.error_message || log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'RISKBREACH'" class="log-detail">
                <span class="log-kv text-red">{{ log.risk_type }}</span>
                <span v-if="log.risk_reason" class="log-reason">{{ log.risk_reason }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'T1SETTLEMENT'" class="log-detail">
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'T1DELAYDECISION'" class="log-detail">
                <span v-if="log.symbol" class="log-kv">{{ log.symbol }}</span>
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'TIMEADVANCE'" class="log-detail">
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'PRICERECEIVED'" class="log-detail">
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <span v-else-if="log.event_type === 'STRATEGYSIGNAL'" class="log-detail">
                <span class="log-kv dim">{{ log.message }}</span>
              </span>
              <!-- 默认：纯文本 -->
              <span v-else class="log-msg">{{ log.message }}</span>
            </div>
            <div v-if="logsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
            <div v-if="!logsHasMore" class="logs-end">
              {{ logKeyword ? `已加载 ${logsTotal} 条中匹配 ${filteredLogs.length} 条` : `已加载全部 ${logsTotal} 条日志` }}
            </div>
          </template>
          <p v-else-if="logKeyword && logs.length > 0" class="empty-hint">已加载日志中无「{{ logKeyword }}」匹配（下拉加载更多后自动生效）</p>
          <p v-else class="empty-hint">暂无日志数据</p>
        </div>
      </div>

    </div>

    <!-- 任务不存在 -->
    <EmptyState v-else description="回测任务不存在" action-text="返回列表" :on-action="goBack" />
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
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
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
import CodeFilter from '@/components/common/CodeFilter.vue'
import { formatMoney } from '@/utils/format'
import dayjs from 'dayjs'
import {
  formatShortDate, formatDecimal,
  directionLabel, directionColor, dirLabel, fmtAnalyzer, getAnalyzerColor,
  formatLogTime, levelClass, eventClass,
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
const TRADE_TABS = ['signals', 'orders', 'positions'] as const
const activeTradeTab = computed<string>({
  get: () => TRADE_TABS.includes(route.query.trade as any) ? String(route.query.trade) : 'signals',
  set: (v) => router.replace({ query: { ...route.query, trade: v } }),
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

// 日志状态
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
// 切到日志 tab 时懒加载(深链直达由 onMounted 兜底;非 immediate,回调运行时 loadLogs 已初始化,无 TDZ)
watch(activeDetailTab, (tab) => {
  if (tab === 'logs' && logs.value.length === 0) loadLogs(true)
})

// 分析器详情
const selectedAnalyzer = ref('')
const analyzerLoading = ref(false)
const analyzerStats = ref<any>(null)
const analyzerTimeseries = ref<any[]>([])
const analyzerChartData = computed<LineData[]>(() =>
  analyzerTimeseries.value.map((r: any) => ({ time: String(r.time).substring(0, 10), value: Number(r.value) }))
)

// 交易记录
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
      const res = await backtestApi.getOrderRecords(backtestId.value)
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
    // 日志筛选默认回测区间
    const t = currentTask.value
    if (t?.backtest_start_date) logFilters.value.start_time = dayjs(t.backtest_start_date).format('YYYY-MM-DD')
    if (t?.backtest_end_date) logFilters.value.end_time = dayjs(t.backtest_end_date).format('YYYY-MM-DD')
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
    // trades
    loadTrades()
  } catch (e) {
    console.error('Failed to load detail:', e)
    // silent 刷新失败(如限流 429)保留旧数据续命,不清空页面——清空会让 WS 就地
    // 更新失配、页面假死;仅首次显式加载失败才回退空态
    if (!disposed && !silent) currentTask.value = null
  } finally {
    if (!disposed && !silent) detailLoading.value = false
  }
}

const loadTrades = async () => {
  if (!backtestId.value || disposed) return
  signalsLoading.value = true
  ordersLoading.value = true
  positionsLoading.value = true
  try {
    const [sigRes, ordRes, posRes] = await Promise.allSettled([
      backtestApi.getSignals(backtestId.value),
      backtestApi.getOrders(backtestId.value),
      backtestApi.getPositions(backtestId.value),
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

const loadLogs = async (reset = false) => {
  if (!backtestId.value || disposed) return
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
    const res = await backtestApi.getLogs(backtestId.value, params)
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
  // 深链直达 ?tab=logs 时 watch 不 fire(初始即 logs),须显式加载
  if (route.query.tab === 'logs') loadLogs(true)

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

.filter-keyword {
  width: 200px;
  padding: 5px 10px;
  font-size: 12px;
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
.metric-value { font-size: 18px; font-weight: 600; color: hsl(var(--foreground)); }

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

/* Logs */
.logs-filter { margin-bottom: 8px; }
.filter-row { display: flex; align-items: center; gap: 8px; }
.filter-select { width: auto; min-width: 100px; }
.filter-date { width: 140px; font-size: 12px; }
.filter-sep { color: hsl(var(--muted-foreground)); font-size: 12px; }

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
.text-orange { color: hsl(var(--warning)); }
.log-detail { color: hsl(var(--muted-foreground)); display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
.log-symbol { color: hsl(var(--foreground)); font-weight: 600; }
.log-kv { color: hsl(var(--muted-foreground)); }
.log-kv.dim { color: hsl(var(--muted-foreground)); }
.log-reason { color: hsl(var(--muted-foreground)); font-style: italic; }
.log-msg { color: hsl(var(--foreground)); word-break: break-all; }
.logs-end { text-align: center; font-size: 11px; color: hsl(var(--muted-foreground)); padding: 10px 0; }

/* Responsive */
@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
