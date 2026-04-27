<template>
  <div class="backtest-tab">
    <!-- ========== 列表视图 ========== -->
    <template v-if="!backtestId">
      <!-- 工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <div class="radio-group">
            <button
              v-for="opt in statusOptions"
              :key="opt.value"
              class="radio-button"
              :class="{ active: filterStatus === opt.value }"
              @click="setFilter(opt.value)"
            >
              {{ opt.label }}
            </button>
          </div>
          <div class="search-box">
            <input
              v-model="searchKeyword"
              type="search"
              placeholder="搜索任务..."
              class="search-input"
              @keyup.enter="loadList"
            />
          </div>
        </div>
        <button class="btn-primary" @click="showCreateModal = true">新建回测</button>
      </div>

      <!-- 加载 -->
      <div v-if="loading" class="loading-center"><div class="spinner"></div></div>

      <!-- 空状态 -->
      <div v-else-if="tasks.length === 0" class="empty-state">
        <p>暂无回测任务</p>
        <button class="btn-primary" @click="showCreateModal = true">创建第一个回测</button>
      </div>

      <!-- 任务卡片列表 -->
      <div v-else class="task-list">
        <div
          v-for="task in tasks"
          :key="task.uuid"
          class="task-card"
          @click="viewDetail(task.uuid)"
        >
          <div class="task-card-main">
            <div class="task-name">{{ task.name || '(未命名)' }} <span class="task-uuid">{{ task.uuid }}</span></div>
            <div class="task-meta">
              <span class="tag" :class="statusTagClass(task.status)">{{ statusLabel(task.status) }}</span>
              <span v-if="task.status === 'running' || task.status === 'pending'" class="progress-info">
                <div class="progress-bar-sm"><div class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></div></div>
                <span class="progress-text">{{ (task.progress || 0).toFixed(0) }}%</span>
              </span>
              <span class="meta-item" :style="{ color: getPnLColor(task.total_pnl) }">{{ formatDecimal(task.total_pnl) }} PnL</span>
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
              <button v-if="task.status === 'completed'" class="link-btn link-deploy" @click="openDeployModal(task.uuid)">部署</button>
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
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showCreateModal = false">取消</button>
            <button class="btn-primary" :disabled="creating" @click="handleCreate">
              {{ creating ? '创建中...' : '创建并启动' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 部署模态框 -->
      <div v-if="showDeployModal" class="modal-overlay" @click.self="showDeployModal = false">
        <div class="modal-box">
          <div class="modal-header">
            <h3>部署到模拟盘/实盘</h3>
            <button class="btn-close" @click="showDeployModal = false">×</button>
          </div>
          <div class="modal-body">
            <div class="form-item">
              <label>目标模式</label>
              <div class="radio-group">
                <button class="radio-button" :class="{ active: deployMode === 'paper' }" @click="deployMode = 'paper'">模拟盘</button>
                <button class="radio-button" :class="{ active: deployMode === 'live' }" @click="deployMode = 'live'">实盘</button>
              </div>
            </div>
            <div v-if="deployMode === 'live'" class="form-item">
              <label>实盘账号</label>
              <select v-model="deployAccountId" class="form-select">
                <option value="">选择实盘账号</option>
                <option v-for="acc in liveAccounts" :key="acc.uuid" :value="acc.uuid">
                  {{ acc.name }} ({{ acc.exchange }} - {{ acc.environment }})
                </option>
              </select>
              <p v-if="liveAccounts.length === 0" class="form-hint">暂无可用实盘账号，请先在实盘账号管理中添加</p>
            </div>
            <div class="form-item">
              <label>组合名称（可选）</label>
              <input v-model="deployName" type="text" placeholder="留空自动生成" class="form-input" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn-secondary" @click="showDeployModal = false">取消</button>
            <button class="btn-primary" :disabled="deploying || (deployMode === 'live' && !deployAccountId)" @click="handleDeploy">
              {{ deploying ? '部署中...' : '确认部署' }}
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- ========== 详情视图 ========== -->
    <template v-else>
      <!-- 加载 -->
      <div v-if="detailLoading" class="loading-center"><div class="spinner"></div></div>

      <!-- 详情内容 -->
      <div v-else-if="currentTask" class="detail-content">
        <!-- 详情头部 -->
        <div class="detail-header">
          <div class="detail-title">
            <button class="btn-back" @click="goBack">← 返回列表</button>
            <span class="tag" :class="statusTagClass(currentTask.status)">{{ statusLabel(currentTask.status) }}</span>
            <span class="task-name-label">{{ currentTask.name || currentTask.uuid?.substring(0, 8) }}</span>
            <span class="task-uuid">{{ currentTask.uuid }}</span>
          </div>
          <div class="detail-actions">
            <button v-if="currentTask.status === 'completed'" class="btn-deploy" @click="openDeployModal(currentTask.uuid)">部署</button>
            <button v-if="canStartByState(currentTask.status)" class="btn-primary" @click="handleReRun">重新运行</button>
            <button v-if="canStopByState(currentTask.status)" class="btn-danger" @click="handleStopDetail">停止</button>
            <button v-if="currentTask.status !== 'running'" class="btn-danger-outline" @click="handleDelete">删除</button>
          </div>
        </div>

        <!-- 回测区间 -->
        <div v-if="currentTask.backtest_start_date || currentTask.backtest_end_date" class="date-range-bar">
          <span class="date-range-label">回测区间</span>
          <span class="date-range-value">{{ formatShortDate(currentTask.backtest_start_date) }} ~ {{ formatShortDate(currentTask.backtest_end_date) }}</span>
        </div>

        <!-- 进度 -->
        <div v-if="currentTask.status === 'running' || currentTask.status === 'pending'" class="card">
          <div class="progress-section">
            <span>{{ currentTask.current_stage || '处理中' }}</span>
            <span>{{ (currentTask.progress || 0).toFixed(1) }}%</span>
          </div>
          <div class="progress-bar-lg"><div class="progress-fill active" :style="{ width: (currentTask.progress || 0) + '%' }"></div></div>
        </div>

        <!-- 详情 tab -->
        <div class="inner-tabs">
          <button
            v-for="t in detailTabs"
            :key="t.key"
            class="inner-tab"
            :class="{ active: activeDetailTab === t.key }"
            @click="activeDetailTab = t.key"
          >{{ t.label }}</button>
        </div>

        <!-- 概览 -->
        <div v-if="activeDetailTab === 'overview'" class="tab-panel">
          <!-- 净值曲线 -->
          <div class="card">
            <h4>净值曲线</h4>
            <NetValueChart v-if="netValueData.length > 0" :data="netValueData" :benchmark-data="benchmarkData" :height="300" />
            <p v-else class="empty-hint">暂无净值数据</p>
          </div>

          <!-- 指标 -->
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-label">最终资产</div>
              <div class="metric-value">{{ formatMoney(currentTask.final_portfolio_value ?? 0) }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">总盈亏</div>
              <div class="metric-value" :style="{ color: pnlColor }">{{ formatMoney(currentTask.total_pnl ?? 0) }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">年化收益</div>
              <div class="metric-value" :style="{ color: (currentTask.annual_return ?? 0) >= 0 ? '#52c41a' : '#f5222d' }">
                {{ ((currentTask.annual_return ?? 0) * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-label">夏普比率</div>
              <div class="metric-value">{{ (currentTask.sharpe_ratio ?? 0).toFixed(2) }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">最大回撤</div>
              <div class="metric-value" :style="{ color: (currentTask.max_drawdown ?? 0) <= 0.1 ? '#52c41a' : '#f5222d' }">
                {{ ((currentTask.max_drawdown ?? 0) * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="metric-card">
              <div class="metric-label">胜率</div>
              <div class="metric-value">{{ ((currentTask.win_rate ?? 0) * 100).toFixed(1) }}%</div>
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
                  <td :style="{ color: (a.stats?.change || 0) >= 0 ? '#52c41a' : '#f5222d' }">
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
          <div class="inner-tabs">
            <button
              v-for="t in tradeSubTabs"
              :key="t.key"
              class="inner-tab"
              :class="{ active: activeTradeTab === t.key }"
              @click="activeTradeTab = t.key"
            >{{ t.label }}</button>
          </div>

          <!-- 信号 -->
          <div v-if="activeTradeTab === 'signals'" class="card">
            <div v-if="signalsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
            <table v-else-if="signals.length > 0" class="data-table">
              <thead><tr><th>代码</th><th>方向</th><th>权重</th><th>原因</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-for="s in signals" :key="s.uuid">
                  <td>{{ s.code }}</td>
                  <td><span :class="directionColor(s.direction)">{{ directionLabel(s.direction) }}</span></td>
                  <td>{{ (s.weight * 100).toFixed(1) }}%</td>
                  <td>{{ s.reason || '-' }}</td>
                  <td>{{ formatShortDate(s.timestamp) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-hint">暂无信号记录</p>
          </div>

          <!-- 订单 -->
          <div v-if="activeTradeTab === 'orders'" class="card">
            <div v-if="ordersLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
            <table v-else-if="orders.length > 0" class="data-table">
              <thead><tr><th>代码</th><th>方向</th><th>类型</th><th>数量</th><th>成交价</th><th>手续费</th><th>时间</th></tr></thead>
              <tbody>
                <tr v-for="o in orders" :key="o.uuid">
                  <td>{{ o.code }}</td>
                  <td><span :class="directionColor(o.direction)">{{ directionLabel(o.direction) }}</span></td>
                  <td>{{ o.order_type }}</td>
                  <td>{{ o.transaction_volume }}</td>
                  <td>{{ o.transaction_price }}</td>
                  <td>{{ o.fee }}</td>
                  <td>{{ formatShortDate(o.timestamp) }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="empty-hint">暂无订单记录</p>
          </div>

          <!-- 持仓 -->
          <div v-if="activeTradeTab === 'positions'" class="card">
            <div v-if="positionsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
            <table v-else-if="positions.length > 0" class="data-table">
              <thead><tr><th>代码</th><th>方向</th><th>数量</th><th>成本</th><th>市值</th><th>盈亏</th><th>盈亏%</th></tr></thead>
              <tbody>
                <tr v-for="p in positions" :key="p.uuid">
                  <td>{{ p.code }}</td>
                  <td><span :class="directionColor(p.direction)">{{ directionLabel(p.direction) }}</span></td>
                  <td>{{ p.volume }}</td>
                  <td>{{ p.cost }}</td>
                  <td>{{ p.market_value }}</td>
                  <td :style="{ color: p.profit >= 0 ? '#52c41a' : '#f5222d' }">{{ p.profit }}</td>
                  <td :style="{ color: p.profit_pct >= 0 ? '#52c41a' : '#f5222d' }">{{ (p.profit_pct * 100).toFixed(2) }}%</td>
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
              <input v-model="logFilters.start_time" type="date" class="form-input filter-date" @change="loadLogs(true)" />
              <span class="filter-sep">~</span>
              <input v-model="logFilters.end_time" type="date" class="form-input filter-date" @change="loadLogs(true)" />
            </div>
          </div>

          <!-- 日志列表 -->
          <div class="logs-container" @scroll="onLogsScroll">
            <div v-if="logsLoading && logs.length === 0" class="loading-center"><div class="spinner spinner-sm"></div></div>
            <template v-else-if="logs.length > 0">
              <div v-for="(log, i) in logs" :key="i" class="log-entry">
                <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
                <span class="log-level" :class="levelClass(log.level)">{{ log.level }}</span>
                <span v-if="log.event_type" class="log-event">{{ log.event_type }}</span>
                <span class="log-msg">{{ log.message }}</span>
              </div>
              <div v-if="logsLoading" class="loading-center"><div class="spinner spinner-sm"></div></div>
              <div v-if="!logsHasMore" class="logs-end">已加载全部 {{ logsTotal }} 条日志</div>
            </template>
            <p v-else class="empty-hint">暂无日志数据</p>
          </div>
        </div>

      </div>

      <!-- 任务不存在 -->
      <div v-else class="empty-state">
        <p>回测任务不存在</p>
        <button class="btn-primary" @click="goBack">返回列表</button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { backtestApi, deploymentApi, liveAccountApi } from '@/api'
import type { BacktestTask, AnalyzerInfo } from '@/api'
import type { LiveAccount } from '@/api'
import { useBacktestStore } from '@/stores'
import { useBacktestStatus } from '@/composables'
import { useWebSocket } from '@/composables'
import { canStartByState, canStopByState, canCancelByState } from '@/constants/backtest'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'
import { message } from '@/utils/toast'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const backtestStore = useBacktestStore()
const { getTagClass: statusTagClass, getLabel: statusLabel } = useBacktestStatus()

// 防止组件卸载后异步操作继续执行
let disposed = false

// ========== 路由参数 ==========
const portfolioId = computed(() => route.params.id as string)
const backtestId = computed(() => route.params.backtestId as string || '')

// ========== 列表状态 ==========
const tasks = ref<BacktestTask[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(0)
const size = ref(20)
const filterStatus = ref('')
const searchKeyword = ref('')

const statusOptions = [
  { value: '', label: '全部' },
  { value: 'running', label: '进行中' },
  { value: 'completed', label: '已完成' },
  { value: 'stopped', label: '已停止' },
  { value: 'failed', label: '失败' },
  { value: 'pending', label: '排队中' },
]

// ========== 创建状态 ==========
const showCreateModal = ref(false)
const creating = ref(false)
const createForm = ref({ name: '', start_date: '', end_date: '', initial_cash: 1000000 })

// ========== 部署状态 ==========
const showDeployModal = ref(false)
const deployTaskId = ref('')
const deployMode = ref<'paper' | 'live'>('paper')
const deployAccountId = ref('')
const deployName = ref('')
const deploying = ref(false)
const liveAccounts = ref<LiveAccount[]>([])

const openDeployModal = (taskId: string) => {
  deployTaskId.value = taskId
  deployMode.value = 'paper'
  deployAccountId.value = ''
  deployName.value = ''
  showDeployModal.value = true
  loadLiveAccounts()
}

const loadLiveAccounts = async () => {
  try {
    const res: any = await liveAccountApi.getAccounts({ page: 1, page_size: 100, status: 'enabled' })
    liveAccounts.value = res?.data?.accounts || []
  } catch { liveAccounts.value = [] }
}

const handleDeploy = async () => {
  if (!deployTaskId.value) return
  if (deployMode.value === 'live' && !deployAccountId.value) {
    message('请选择实盘账号', 'warning')
    return
  }
  deploying.value = true
  try {
    const res: any = await deploymentApi.deploy({
      backtest_task_id: deployTaskId.value,
      mode: deployMode.value,
      account_id: deployMode.value === 'live' ? deployAccountId.value : undefined,
      name: deployName.value || undefined,
    })
    showDeployModal.value = false
    const newPortfolioId = res?.data?.portfolio_id
    if (newPortfolioId) {
      message('部署成功', 'success')
      router.push(`/portfolios/${newPortfolioId}`)
    } else {
      message('部署成功', 'success')
      loadList()
    }
  } catch (e: any) {
    message('部署失败: ' + (e?.message || e), 'error')
  } finally {
    deploying.value = false
  }
}

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

// ========== 详情状态 ==========
const currentTask = ref<BacktestTask | null>(null)
const detailLoading = ref(false)
const analyzers = ref<AnalyzerInfo[]>([])
const netValueData = ref<LineData[]>([])
const benchmarkData = ref<LineData[]>([])
const activeDetailTab = ref('overview')
watch(activeDetailTab, (tab) => {
  if (tab === 'logs' && logs.value.length === 0) loadLogs(true)
})
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
const logFilters = ref({ level: '', start_time: '', end_time: '' })

// 分析器详情
const selectedAnalyzer = ref('')
const analyzerLoading = ref(false)
const analyzerStats = ref<any>(null)
const analyzerTimeseries = ref<any[]>([])
const analyzerChartData = computed<LineData[]>(() =>
  analyzerTimeseries.value.map((r: any) => ({ time: String(r.time).substring(0, 10), value: Number(r.value) }))
)

// 交易记录
const activeTradeTab = ref('signals')
const tradeSubTabs = [
  { key: 'signals', label: '信号' },
  { key: 'orders', label: '订单' },
  { key: 'positions', label: '持仓' },
]
const signals = ref<any[]>([])
const orders = ref<any[]>([])
const positions = ref<any[]>([])
const signalsLoading = ref(false)
const ordersLoading = ref(false)
const positionsLoading = ref(false)

// ========== 列表方法 ==========
const loadList = async () => {
  if (disposed) return
  loading.value = true
  try {
    const params: any = { page: page.value + 1, page_size: size.value, portfolio_id: portfolioId.value }
    if (filterStatus.value) params.status = filterStatus.value
    if (searchKeyword.value) params.keyword = searchKeyword.value
    const res = await backtestApi.list(params)
    if (disposed) return
    tasks.value = res.data || []
    total.value = res.meta?.total || res.total || 0
  } catch (e) {
    console.error('Failed to load backtests:', e)
  } finally {
    if (!disposed) loading.value = false
  }
}

const setFilter = (val: string) => {
  filterStatus.value = val
  page.value = 0
  loadList()
}

const viewDetail = (uuid: string) => {
  router.push(`/portfolios/${portfolioId.value}/backtests/${uuid}`)
}

const handleStart = async (task: BacktestTask) => {
  try {
    let params: any = {}
    if (task.config_snapshot) {
      const config = typeof task.config_snapshot === 'string' ? JSON.parse(task.config_snapshot) : task.config_snapshot
      params = { start_date: config.start_date, end_date: config.end_date }
    }
    await backtestStore.startTask(task.uuid, params)
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
  creating.value = true
  try {
    const task = await backtestStore.createTask({
      name: createForm.value.name,
      portfolio_uuids: [portfolioId.value],
      engine_config: {
        start_date: createForm.value.start_date,
        end_date: createForm.value.end_date,
        initial_cash: createForm.value.initial_cash || undefined,
      },
    })
    if (task?.uuid) {
      await backtestStore.startTask(task.uuid)
    }
    message.success('回测任务已创建并启动')
    showCreateModal.value = false
    createForm.value = { name: '', start_date: '', end_date: '', initial_cash: 1000000 }
    loadList()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '创建失败')
  } finally {
    creating.value = false
  }
}

// ========== 详情方法 ==========
const loadDetail = async () => {
  if (!backtestId.value || disposed) return
  detailLoading.value = true
  try {
    const task = await backtestApi.get(backtestId.value)
    if (disposed) return
    currentTask.value = task.data || task
    // 日志筛选默认回测区间
    const t = currentTask.value
    if (t?.backtest_start_date) logFilters.value.start_time = dayjs(t.backtest_start_date).format('YYYY-MM-DD')
    if (t?.backtest_end_date) logFilters.value.end_time = dayjs(t.backtest_end_date).format('YYYY-MM-DD')
    // net value
    try {
      const nv = await backtestApi.getNetValue(backtestId.value)
      if (disposed) return
      const nvData = nv.data || nv
      netValueData.value = (nvData?.strategy || []).map((i: any) => ({ time: String(i.time).substring(0, 10), value: i.value }))
      benchmarkData.value = (nvData?.benchmark || []).map((i: any) => ({ time: String(i.time).substring(0, 10), value: i.value }))
    } catch { /* net value may not exist */ }
    // analyzers
    try {
      const ar = await backtestApi.getAnalyzers(backtestId.value)
      if (disposed) return
      const arData = ar.data || ar
      analyzers.value = arData?.analyzers || []
      if (analyzers.value.length > 0) {
        selectedAnalyzer.value = analyzers.value[0].name
        loadAnalyzerData()
      }
    } catch { /* analyzers may not exist */ }
    // trades
    loadTrades()
  } catch (e) {
    console.error('Failed to load detail:', e)
    if (!disposed) currentTask.value = null
  } finally {
    if (!disposed) detailLoading.value = false
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
    if (sigRes.status === 'fulfilled') { const d = sigRes.value.data || sigRes.value; signals.value = d.data || d || [] }
    if (ordRes.status === 'fulfilled') { const d = ordRes.value.data || ordRes.value; orders.value = d.data || d || [] }
    if (posRes.status === 'fulfilled') { const d = posRes.value.data || posRes.value; positions.value = d.data || d || [] }
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
    const d = res.data || res
    analyzerStats.value = d.stats
    analyzerTimeseries.value = d.data || []
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
    if (logFilters.value.start_time) params.start_time = logFilters.value.start_time
    if (logFilters.value.end_time) params.end_time = logFilters.value.end_time
    const res = await backtestApi.getLogs(backtestId.value, params)
    if (disposed) return
    const d = res.data || res
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

const handleReRun = async () => {
  if (!currentTask.value) return
  try {
    let params: any = {}
    if (currentTask.value.config_snapshot) {
      const config = typeof currentTask.value.config_snapshot === 'string'
        ? JSON.parse(currentTask.value.config_snapshot) : currentTask.value.config_snapshot
      params = { start_date: config.start_date, end_date: config.end_date }
    }
    const result = await backtestStore.startTask(currentTask.value.uuid)
    message.success('已重新启动回测')
    if (result?.task_uuid) {
      router.push(`/portfolios/${portfolioId.value}/backtests/${result.task_uuid}`)
    } else {
      loadDetail()
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '重新运行失败')
  }
}

const handleStopDetail = async () => {
  if (!currentTask.value?.uuid) return
  if (!confirm('确定要停止此回测？')) return
  try {
    await backtestStore.stopTask(currentTask.value.uuid)
    message.success('已停止')
    loadDetail()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '停止失败')
  }
}

const handleDelete = async () => {
  if (!currentTask.value?.uuid) return
  if (!confirm('删除后不可恢复，确定要删除？')) return
  try {
    await backtestStore.deleteTask(currentTask.value.uuid)
    message.success('已删除')
    goBack()
  } catch (e: any) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

const goBack = () => {
  router.push(`/portfolios/${portfolioId.value}/backtests`)
}

// ========== 工具函数 ==========
const formatShortDate = (d?: string | null) => {
  if (!d) return '-'
  return dayjs(d).format('YYYY-MM-DD HH:mm')
}

const formatDecimal = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '-' : n.toFixed(2)
}

const formatPercent = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '-' : (n * 100).toFixed(2) + '%'
}

const getPnLColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '#8a8a9a' : n >= 0 ? '#cf1322' : '#3f8600'
}

const getSharpeColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '#8a8a9a' : n >= 1 ? '#52c41a' : '#faad14'
}

const getDrawdownColor = (val: string | number) => {
  const n = typeof val === 'number' ? val : parseFloat(String(val))
  return isNaN(n) ? '#8a8a9a' : n <= 0.1 ? '#52c41a' : '#f5222d'
}

const DIR_MAP: Record<number, string> = { 1: 'LONG', 2: 'SHORT' }
const directionLabel = (d: number | string) => DIR_MAP[Number(d)] || String(d)
const directionColor = (d: number | string) => Number(d) === 1 ? 'text-green' : 'text-red'

const formatMoney = (val: number) => {
  return '¥' + val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const pnlColor = computed(() => {
  const v = currentTask.value?.total_pnl ?? 0
  return v >= 0 ? '#52c41a' : '#f5222d'
})

const fmtAnalyzer = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return '-'
  const nl = name.toLowerCase()
  if (['max_drawdown', 'win_rate', 'hold_pct', 'annual_return'].some(a => nl.includes(a))) return `${(value * 100).toFixed(2)}%`
  if (['sharpe', 'sortino', 'calmar'].some(a => nl.includes(a))) return value.toFixed(3)
  if (['signal_count', 'trade_count', 'order_count'].some(a => nl.includes(a))) return Math.round(value).toString()
  if (['net_value', 'profit', 'pnl', 'capital'].some(a => nl.includes(a))) return `¥${value.toFixed(2)}`
  return value.toFixed(4)
}

const formatLogTime = (ts?: string | null) => {
  if (!ts) return '-'
  return dayjs(ts).format('YYYY-MM-DD HH:mm:ss.SSS')
}

const levelClass = (level?: string | null) => {
  if (!level) return ''
  const l = level.toUpperCase()
  if (l === 'ERROR' || l === 'CRITICAL') return 'level-error'
  if (l === 'WARNING') return 'level-warning'
  if (l === 'INFO') return 'level-info'
  if (l === 'DEBUG') return 'level-debug'
  return ''
}

const getAnalyzerColor = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return '#666'
  const nl = name.toLowerCase()
  if (nl.includes('drawdown')) return value <= 0.1 ? '#52c41a' : value <= 0.2 ? '#faad14' : '#f5222d'
  if (nl.includes('return') || nl.includes('win_rate')) return value >= 0 ? '#52c41a' : '#f5222d'
  if (nl.includes('sharpe') || nl.includes('sortino')) return value >= 1 ? '#52c41a' : value >= 0 ? '#faad14' : '#f5222d'
  if (nl.includes('profit') || nl.includes('pnl')) return value >= 0 ? '#52c41a' : '#f5222d'
  return '#666'
}

// ========== WebSocket ==========
const { subscribe } = useWebSocket()
let unsubscribe: (() => void) | null = null

onMounted(() => {
  if (!backtestId.value) {
    loadList()
    if (route.query.action === 'create') {
      showCreateModal.value = true
      router.replace({ query: {} })
    }
  } else {
    loadDetail()
  }

  unsubscribe = subscribe('*', (data) => {
    const taskId = data.task_id || data.task_uuid
    if (!taskId) return
    if (backtestId.value && taskId === currentTask.value?.uuid) {
      backtestStore.updateProgress({ task_id: taskId, status: data.type === 'progress' ? undefined : data.type, progress: data.progress })
      loadDetail()
    } else {
      loadList()
    }
  })
})

watch(backtestId, (newVal) => {
  if (newVal) {
    loadDetail()
  } else {
    loadList()
  }
})

onUnmounted(() => {
  disposed = true
  backtestStore.clearCurrentTask()
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

.radio-group {
  display: inline-flex;
  background: #2a2a3e;
  border-radius: 4px;
  padding: 2px;
}

.radio-button {
  padding: 5px 12px;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-button:hover { color: #fff; }
.radio-button.active { background: #1890ff; color: #fff; }

.search-input {
  padding: 5px 10px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  width: 160px;
}

.search-input:focus { border-color: #1890ff; outline: none; }

/* Buttons */
.btn-primary {
  padding: 6px 14px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.btn-primary:hover { background: #40a9ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-secondary {
  padding: 6px 14px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.btn-danger {
  padding: 6px 14px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}

.btn-danger:hover { background: #ff4d4f; }

.btn-danger-outline {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid #f5222d;
  border-radius: 4px;
  color: #f5222d;
  font-size: 13px;
  cursor: pointer;
}

.btn-back {
  background: none;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  font-size: 13px;
  padding: 0;
}

.btn-back:hover { color: #fff; }

.btn-sm {
  padding: 4px 10px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-close { background: none; border: none; color: #8a8a9a; font-size: 18px; cursor: pointer; }
.btn-close:hover { color: #fff; }

/* Link button */
.link-btn {
  background: none;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
}

.link-btn:hover { color: #40a9ff; }
.link-btn.link-danger { color: #f5222d; }
.link-btn.link-danger:hover { color: #ff4d4f; }
.link-btn.link-deploy { color: #52c41a; }
.link-btn.link-deploy:hover { color: #73d13d; }

.btn-deploy {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 16px; background: transparent;
  border: 1px solid #52c41a; border-radius: 4px;
  color: #52c41a; font-size: 13px; cursor: pointer;
  transition: all 0.2s;
}
.btn-deploy:hover { background: #52c41a; color: #fff; }

.form-select {
  width: 100%; padding: 8px 12px;
  background: #1a1a2e; border: 1px solid #2a2a3e;
  border-radius: 6px; color: #fff; font-size: 14px;
}
.form-select:focus { outline: none; border-color: #1890ff; }
.form-hint { margin: 6px 0 0; font-size: 12px; color: #8a8a9a; }

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
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.task-card:hover { border-color: #3a3a4e; background: #1e1e32; }

.task-card-main { flex: 1; min-width: 0; }

.task-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-uuid {
  font-size: 11px;
  color: #6a6a7a;
  font-family: monospace;
  margin-left: 6px;
  user-select: all;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item { font-size: 12px; color: #8a8a9a; }

.task-card-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
  flex-shrink: 0;
  margin-left: 16px;
}

.task-date { font-size: 11px; color: #6a6a7a; }

.task-actions { display: flex; gap: 4px; }

/* Progress bar small */
.progress-info { display: flex; align-items: center; gap: 6px; }

.progress-bar-sm {
  width: 60px;
  height: 4px;
  background: #2a2a3e;
  border-radius: 2px;
  overflow: hidden;
}

.progress-text { font-size: 11px; color: #8a8a9a; }

.progress-bar-lg {
  height: 6px;
  background: #2a2a3e;
  border-radius: 3px;
  overflow: hidden;
  margin-top: 8px;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-fill.active {
  background: linear-gradient(90deg, #1890ff, #40a9ff);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Tags */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24,144,255,0.15); color: #69c0ff; }
.tag-green { background: rgba(82,196,26,0.15); color: #95de64; }
.tag-orange { background: rgba(250,173,20,0.15); color: #ffc53d; }
.tag-red { background: rgba(245,34,45,0.15); color: #ff7875; }
.tag-gray { background: rgba(255,255,255,0.08); color: #8a8a9a; }
.tag-processing { background: rgba(24,144,255,0.15); color: #69c0ff; }

.text-green { color: #52c41a; }
.text-red { color: #f5222d; }

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 12px 0;
  flex-shrink: 0;
}

.page-info { font-size: 12px; color: #8a8a9a; }

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
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
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
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 { margin: 0; color: #fff; font-size: 16px; }

.modal-body { padding: 20px; overflow: visible; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #2a2a3e;
}

/* Form */
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 12px; color: #8a8a9a; margin-bottom: 4px; }

.form-input, .form-select {
  width: 100%;
  padding: 7px 10px;
  background: #0f0f1a;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
}

.form-input:focus, .form-select:focus { border-color: #1890ff; outline: none; }

.form-row { display: flex; gap: 12px; }
.form-row .form-item { flex: 1; }

/* Date range bar */
.date-range-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 14px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  margin-bottom: 12px;
}
.date-range-label {
  font-size: 12px;
  color: #6a6a7a;
}
.date-range-value {
  font-size: 13px;
  color: #ccc;
  font-family: monospace;
}

/* Detail */
.detail-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.detail-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-name-label {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
}

.detail-actions { display: flex; gap: 8px; }

/* Progress section */
.progress-section {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #8a8a9a;
}

/* Inner tabs */
.inner-tabs {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid #2a2a3e;
  margin-bottom: 16px;
}

.inner-tab {
  padding: 8px 16px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8a8a9a;
  font-size: 13px;
  cursor: pointer;
}

.inner-tab:hover { color: #fff; }
.inner-tab.active { color: #1890ff; border-bottom-color: #1890ff; }

.tab-panel { flex: 1; }

/* Metrics grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.metric-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 12px;
}

.metric-label { font-size: 11px; color: #6a6a7a; margin-bottom: 4px; }
.metric-value { font-size: 18px; font-weight: 600; color: #fff; }

/* Card */
.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 14px;
  margin-bottom: 12px;
}

.card h4 {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 10px 0;
}

.card-error pre {
  color: #ff7875;
  font-size: 12px;
  white-space: pre-wrap;
  margin: 0;
}

.card-error { border-color: rgba(245,34,45,0.3); }

/* Exec stats */
.exec-stats {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #8a8a9a;
}

.exec-stats strong { color: #fff; }

/* Stats row */
.stats-row {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

/* Analyzer header */
.analyzer-header { margin-bottom: 12px; }

.form-select {
  appearance: auto;
}

/* Data table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th {
  text-align: left;
  padding: 6px 8px;
  color: #6a6a7a;
  font-weight: 500;
  border-bottom: 1px solid #2a2a3e;
}

.data-table td {
  padding: 6px 8px;
  color: #ccc;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}

.data-table tr:hover td { background: rgba(255,255,255,0.02); }

/* Loading */
.loading-center {
  display: flex;
  justify-content: center;
  padding: 40px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-sm {
  width: 16px;
  height: 16px;
  border-width: 2px;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
  gap: 12px;
}

.empty-hint {
  color: rgba(255,255,255,0.3);
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

/* Date field */
.date-field {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: #fff;
}

.date-field .placeholder { color: #6a6a7a; }
.date-field svg { color: #6a6a7a; flex-shrink: 0; }

/* Picker panel */
.picker-panel {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 10px;
  z-index: 1100;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
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
  color: #fff;
}

.picker-nav {
  background: none;
  border: none;
  color: #8a8a9a;
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
}

.picker-nav:hover { color: #fff; background: #2a2a3e; }

.picker-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  margin-bottom: 4px;
}

.picker-wd {
  text-align: center;
  font-size: 11px;
  color: #6a6a7a;
  font-weight: 500;
  height: 24px;
  line-height: 24px;
}

.picker-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}

.picker-day {
  width: 32px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  font-size: 12px;
  color: #ccc;
  background: transparent;
  border: none;
  cursor: pointer;
  margin: 1px auto;
}

.picker-day:hover:not(:disabled) { background: #2a2a3e; color: #fff; }
.picker-day:disabled { visibility: hidden; }
.picker-day.selected { background: #1890ff; color: #fff; }
.picker-day.today { font-weight: 700; color: #1890ff; }
.picker-day.today.selected { color: #fff; }

/* Logs */
.logs-filter { margin-bottom: 8px; }
.filter-row { display: flex; align-items: center; gap: 8px; }
.filter-select { width: auto; min-width: 100px; }
.filter-date { width: 140px; font-size: 12px; }
.filter-sep { color: #6a6a7a; font-size: 12px; }

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
  border-radius: 2px;
}
.log-entry:hover { background: rgba(255,255,255,0.02); }

.log-time { color: #6a6a7a; flex-shrink: 0; white-space: nowrap; }
.log-level {
  flex-shrink: 0;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.level-debug { background: rgba(255,255,255,0.06); color: #8a8a9a; }
.level-info { background: rgba(24,144,255,0.15); color: #69c0ff; }
.level-warning { background: rgba(250,173,20,0.15); color: #ffc53d; }
.level-error { background: rgba(245,34,45,0.15); color: #ff7875; }
.log-event { color: #1890ff; flex-shrink: 0; }
.log-msg { color: #ccc; word-break: break-all; }
.logs-end { text-align: center; font-size: 11px; color: #6a6a7a; padding: 10px 0; }

/* Responsive */
@media (max-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(2, 1fr); }
  .toolbar { flex-wrap: wrap; }
}
</style>
