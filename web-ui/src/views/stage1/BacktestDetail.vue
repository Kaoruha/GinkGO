<template>
  <div class="page-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
    </div>

    <!-- 详情内容 -->
    <div v-else-if="backtest" class="detail-content">
      <div class="page-header">
        <div class="page-title">
          <span class="tag" :class="`tag-${getStatusColor(backtest.status)}`">{{ getStatusLabel(backtest.status) }}</span>
          <span class="run-id">{{ backtest.run_id?.substring(0, 16) }}...</span>
        </div>
        <div class="header-actions">
          <!-- 重新运行按钮：已完成/失败/已停止状态显示 -->
          <button
            v-if="canReRun"
            class="btn btn-primary"
            :disabled="!hasPermission"
            :title="reRunTooltip"
            @click="handleReRun"
          >
            重新运行
          </button>
          <!-- 停止按钮：进行中状态显示 -->
          <button
            v-if="canStop"
            class="btn btn-danger"
            :disabled="!hasPermission"
            :title="stopTooltip"
            @click="stopBacktest"
          >
            停止回测
          </button>
          <!-- 删除按钮 -->
          <button
            v-if="canDelete"
            class="btn btn-danger"
            :disabled="!hasPermission"
            :title="deleteTooltip"
            @click="handleDelete"
          >
            删除
          </button>
          <button class="btn btn-secondary" @click="goBack">返回列表</button>
        </div>
      </div>

      <!-- Tab 标签页 -->
      <div class="tabs-container">
        <div class="tabs-header">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="tab-button"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <!-- 概览 -->
        <div v-show="activeTab === 'overview'" class="tab-panel">
          <!-- 基本信息 -->
          <div class="card">
            <h3 class="card-title">基本信息</h3>
            <div class="descriptions">
              <div class="desc-item">
                <span class="desc-label">UUID</span>
                <span class="desc-value">{{ backtest.uuid?.substring(0, 8) }}...</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">状态</span>
                <span class="desc-value">
                  <span class="tag" :class="`tag-${getStatusColor(backtest.status)}`">{{ getStatusLabel(backtest.status) }}</span>
                </span>
              </div>
              <div class="desc-item">
                <span class="desc-label">投资组合</span>
                <span class="desc-value">{{ backtest.portfolio_id || '-' }}</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">运行时长</span>
                <span class="desc-value">{{ formatDuration(backtest) }}</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">开始时间</span>
                <span class="desc-value">{{ formatDateTime(backtest.start_time) }}</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">结束时间</span>
                <span class="desc-value">{{ formatDateTime(backtest.end_time) }}</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">创建时间</span>
                <span class="desc-value">{{ formatDateTime(backtest.create_at) }}</span>
              </div>
            </div>
          </div>

          <!-- 回测进度 -->
          <div v-if="backtest.status === 'running' || backtest.status === 'pending'" class="card">
            <h3 class="card-title">回测进度</h3>
            <div class="progress-section">
              <div class="progress-header">
                <span class="progress-label">{{ backtest.current_stage || '处理中' }}</span>
                <span class="progress-value">{{ ((backtest.progress || 0)).toFixed(1) }}%</span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :class="backtest.status === 'running' ? 'active' : 'normal'"
                  :style="{ width: `${backtest.progress || 0}%` }"
                ></div>
              </div>
            </div>
          </div>

          <!-- 配置快照 -->
          <div class="card">
            <h3 class="card-title">配置快照</h3>
            <div class="descriptions">
              <div class="desc-item">
                <span class="desc-label">配置名称</span>
                <span class="desc-value">{{ configSnapshot.name || backtest.uuid }}</span>
              </div>
              <div class="desc-item">
                <span class="desc-label">初始资金</span>
                <span class="desc-value">{{ formatMoney(configSnapshot.initial_cash) }}</span>
              </div>
              <div class="desc-item full-width">
                <span class="desc-label">回测区间</span>
                <span class="desc-value">{{ configSnapshot.start_date || '-' }} 至 {{ configSnapshot.end_date || '-' }}</span>
              </div>
            </div>

            <!-- Portfolio 组件配置 -->
            <div v-if="configSnapshot.portfolio_snapshot" class="portfolio-snapshot">
              <div class="divider"></div>
              <h4 class="section-title">Portfolio 组件</h4>
              <div class="descriptions">
                <div class="desc-item">
                  <span class="desc-label">Portfolio</span>
                  <span class="desc-value">{{ configSnapshot.portfolio_snapshot.name }} ({{ configSnapshot.portfolio_snapshot.uuid?.substring(0, 8) }}...)</span>
                </div>
              </div>

              <!-- Selectors -->
              <div v-if="configSnapshot.portfolio_snapshot.components?.selectors?.length" class="component-section">
                <span class="component-label text-blue">选股器 ({{ configSnapshot.portfolio_snapshot.components.selectors.length }})</span>
                <div v-for="(selector, idx) in configSnapshot.portfolio_snapshot.components.selectors" :key="idx" class="component-item">
                  <span class="tag tag-blue">{{ getComponentName(selector) }}</span>
                  <span class="component-config">{{ formatConfigParams(selector.config) }}</span>
                </div>
              </div>

              <!-- Sizer -->
              <div v-if="configSnapshot.portfolio_snapshot.components?.sizer" class="component-section">
                <span class="component-label text-green">仓位管理</span>
                <div class="component-item">
                  <span class="tag tag-green">{{ getComponentName(configSnapshot.portfolio_snapshot.components.sizer) }}</span>
                  <span class="component-config">{{ formatConfigParams(configSnapshot.portfolio_snapshot.components.sizer.config) }}</span>
                </div>
              </div>

              <!-- Strategies -->
              <div v-if="configSnapshot.portfolio_snapshot.components?.strategies?.length" class="component-section">
                <span class="component-label text-orange">策略 ({{ configSnapshot.portfolio_snapshot.components.strategies.length }})</span>
                <div v-for="(strategy, idx) in configSnapshot.portfolio_snapshot.components.strategies" :key="idx" class="component-item">
                  <span class="tag tag-orange">{{ getComponentName(strategy) }}</span>
                  <span class="component-config">{{ formatConfigParams(strategy.config) }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- 统计指标 -->
          <div class="card">
            <h3 class="card-title">回测指标</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-label">最终资产</div>
                <div class="stat-value">¥{{ parseFloat(backtest.final_portfolio_value || '0').toFixed(2) }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">总盈亏</div>
                <div class="stat-value" :style="{ color: pnlColor }">{{ parseFloat(backtest.total_pnl || '0').toFixed(2) }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">年化收益</div>
                <div class="stat-value" :style="{ color: parseFloat(backtest.annual_return || '0') >= 0 ? '#52c41a' : '#f5222d' }">
                  {{ (parseFloat(backtest.annual_return || '0') * 100).toFixed(2) }}%
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-label">夏普比率</div>
                <div class="stat-value">{{ parseFloat(backtest.sharpe_ratio || '0').toFixed(2) }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">最大回撤</div>
                <div class="stat-value" :style="{ color: parseFloat(backtest.max_drawdown || '0') <= 0.1 ? '#52c41a' : '#f5222d' }">
                  {{ (parseFloat(backtest.max_drawdown || '0') * 100).toFixed(2) }}%
                </div>
              </div>
              <div class="stat-item">
                <div class="stat-label">胜率</div>
                <div class="stat-value">{{ (parseFloat(backtest.win_rate || '0') * 100).toFixed(1) }}%</div>
              </div>
            </div>
          </div>

          <!-- 执行统计 -->
          <div class="card">
            <h3 class="card-title">执行统计</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-label">订单数</div>
                <div class="stat-value">{{ backtest.total_orders || 0 }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">信号数</div>
                <div class="stat-value">{{ backtest.total_signals || 0 }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">持仓记录</div>
                <div class="stat-value">{{ backtest.total_positions || 0 }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">事件数</div>
                <div class="stat-value">{{ backtest.total_events || 0 }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">平均处理</div>
                <div class="stat-value">{{ parseFloat(backtest.avg_event_processing_ms || '0').toFixed(1) }} ms</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">峰值内存</div>
                <div class="stat-value">{{ parseFloat(backtest.peak_memory_mb || '0').toFixed(1) }} MB</div>
              </div>
            </div>
          </div>

          <!-- 分析器列表 -->
          <div class="card">
            <h3 class="card-title">分析器</h3>
            <div v-if="analyzersLoading" class="loading-inline">
              <div class="spinner spinner-small"></div>
            </div>
            <table v-else-if="analyzers.length > 0" class="data-table">
              <thead>
                <tr>
                  <th>分析器名称</th>
                  <th>最新值</th>
                  <th>记录数</th>
                  <th>变化趋势</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in analyzers" :key="record.name">
                  <td><span class="tag tag-blue">{{ record.name }}</span></td>
                  <td>
                    <span :style="{ color: getAnalyzerValueColor(record.name, record.latest_value) }">
                      {{ formatAnalyzerValue(record.name, record.latest_value) }}
                    </span>
                  </td>
                  <td>
                    <span class="stats-detail" :title="`最小: ${formatAnalyzerValue(record.name, record.stats?.min)}\n最大: ${formatAnalyzerValue(record.name, record.stats?.max)}\n平均: ${formatAnalyzerValue(record.name, record.stats?.avg)}`">
                      {{ record.stats?.count }} 条记录
                    </span>
                  </td>
                  <td>
                    <span :style="{ color: record.stats?.change >= 0 ? '#52c41a' : '#f5222d' }">
                      {{ record.stats?.change >= 0 ? '↑' : '↓' }} {{ formatAnalyzerValue(record.name, Math.abs(record.stats?.change || 0)) }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="empty-state">
              <p>暂无分析器数据（回测完成后生成）</p>
            </div>
          </div>

          <!-- 净值曲线 -->
          <div class="card">
            <h3 class="card-title">净值曲线</h3>
            <NetValueChart v-if="netValueData.length > 0" :data="netValueData" :benchmark-data="benchmarkData" :height="350" />
            <div v-else class="empty-state">
              <p>暂无净值数据（回测完成后生成）</p>
            </div>
          </div>

          <!-- 错误信息 -->
          <div v-if="backtest.error_message" class="card">
            <h3 class="card-title">错误信息</h3>
            <div class="alert alert-error">{{ backtest.error_message }}</div>
          </div>

          <!-- 环境信息 -->
          <div v-if="environmentInfo && Object.keys(environmentInfo).length > 0" class="card">
            <h3 class="card-title">环境信息</h3>
            <pre class="env-info">{{ JSON.stringify(environmentInfo, null, 2) }}</pre>
          </div>
        </div>

        <!-- 分析器详情 -->
        <div v-show="activeTab === 'analyzers'" class="tab-panel">
          <AnalyzerPanel
            :taskId="backtest.run_id"
            :portfolioId="backtest.portfolio_id"
            :analyzers="analyzers"
          />
        </div>

        <!-- 交易记录 -->
        <div v-show="activeTab === 'trades'" class="tab-panel">
          <TradeRecordsPanel :taskId="backtest.run_id" />
        </div>

        <!-- 日志 -->
        <div v-show="activeTab === 'logs'" class="tab-panel">
          <div class="empty-state">
            <p>日志功能开发中</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else class="result-page">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="15" y1="9" x2="9" y2="15"></line>
        <line x1="9" y1="9" x2="15" y2="15"></line>
      </svg>
      <h2>回测任务不存在</h2>
      <p>请检查任务ID是否正确</p>
      <button class="btn btn-primary" @click="goBack">返回列表</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'
import { useBacktestStore, useAuthStore } from '@/stores'
import { useWebSocket, useBacktestStatus } from '@/composables'
import { BACKTEST_STATES, canStartByState, canStopByState } from '@/constants/backtest'
import AnalyzerPanel from './components/AnalyzerPanel.vue'
import TradeRecordsPanel from './components/TradeRecordsPanel.vue'
import dayjs from 'dayjs'

// 简化的通知和确认函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const confirm = (message: string, onOk: () => void) => {
  if (window.confirm(message)) {
    onOk()
  }
}

const route = useRoute()
const router = useRouter()

// ========== Store ==========
const backtestStore = useBacktestStore()
const authStore = useAuthStore()
const { getColor: getStatusColor, getLabel: getStatusLabel } = useBacktestStatus()

// ========== 本地状态 ==========
const netValueData = ref<LineData[]>([])
const benchmarkData = ref<LineData[]>([])
const activeTab = ref('overview')

const tabs = [
  { key: 'overview', label: '概览' },
  { key: 'analyzers', label: '分析器' },
  { key: 'trades', label: '交易记录' },
  { key: 'logs', label: '日志' },
]

// ========== 计算属性（从 Store 获取） ==========
const loading = computed(() => backtestStore.detailLoading)
const backtest = computed(() => backtestStore.currentTask)
const analyzers = computed(() => backtestStore.currentAnalyzers)
const analyzersLoading = ref(false)

// 解析配置快照
const configSnapshot = computed(() => {
  try {
    if (typeof backtest.value?.config_snapshot === 'string') {
      return JSON.parse(backtest.value.config_snapshot)
    }
    return backtest.value?.config_snapshot || {}
  } catch {
    return {}
  }
})

// 解析环境信息
const environmentInfo = computed(() => {
  try {
    if (typeof backtest.value?.environment_info === 'string') {
      const parsed = JSON.parse(backtest.value.environment_info)
      return Object.keys(parsed).length > 0 ? parsed : null
    }
    return backtest.value?.environment_info || null
  } catch {
    return null
  }
})

// 总盈亏颜色
const pnlColor = computed(() => {
  const pnl = parseFloat(backtest.value?.total_pnl || '0')
  return pnl >= 0 ? '#52c41a' : '#f5222d'
})

// 权限检查 - 简化版，使用 admin 权限
const hasPermission = computed(() => {
  // 暂时只检查 admin 权限，等待后端 API 添加 creator_id 字段
  return authStore.isAdmin
})

// 状态检查
const canReRun = computed(() => {
  if (!backtest.value) return false
  return canStartByState(backtest.value.status)
})

const canStop = computed(() => {
  if (!backtest.value) return false
  return canStopByState(backtest.value.status)
})

const canDelete = computed(() => {
  if (!backtest.value) return false
  // 只能删除已完成、已停止、失败状态的任务
  return [BACKTEST_STATES.COMPLETED, BACKTEST_STATES.STOPPED, BACKTEST_STATES.FAILED].includes(backtest.value.status)
})

// Tooltip 文本
const reRunTooltip = computed(() => {
  return hasPermission.value ? '创建新任务并运行相同的配置' : '你没有权限操作此任务'
})

const stopTooltip = computed(() => {
  return hasPermission.value ? '停止正在运行的任务' : '你没有权限操作此任务'
})

const deleteTooltip = computed(() => {
  return hasPermission.value ? '删除此回测任务' : '你没有权限操作此任务'
})

// 加载回测详情
const loadBacktest = async () => {
  const uuid = route.params.id as string
  if (!uuid) {
    showToast('缺少任务ID', 'error')
    return
  }

  try {
    await backtestStore.fetchTask(uuid)

    // 加载净值数据
    const netValue = await backtestStore.fetchNetValue(uuid)
    if (netValue?.strategy) {
      netValueData.value = netValue.strategy.map((item: any) => ({
        time: item.time,
        value: item.value
      }))
    }
    if (netValue?.benchmark) {
      benchmarkData.value = netValue.benchmark.map((item: any) => ({
        time: item.time,
        value: item.value
      }))
    }

    // 加载分析器列表
    loadAnalyzers(uuid)
  } catch (e: any) {
    console.error('Failed to load backtest:', e)
    showToast('加载回测详情失败', 'error')
  }
}

// ========== 运行控制 ==========

// 加载分析器列表
const loadAnalyzers = async (uuid: string) => {
  analyzersLoading.value = true
  try {
    await backtestStore.fetchAnalyzers(uuid)
  } catch (e) {
    console.error('Failed to load analyzers:', e)
  } finally {
    analyzersLoading.value = false
  }
}

const goBack = () => {
  router.push('/stage1/backtest')
}

const stopBacktest = async () => {
  if (!backtest.value?.uuid) return

  confirm('确定要停止此回测任务吗？', async () => {
    try {
      await backtestStore.stopTask(backtest.value.uuid)
      showToast('回测已停止')
    } catch (e) {
      showToast('停止失败', 'error')
    }
  })
}

const handleReRun = async () => {
  if (!backtest.value) return

  try {
    // 从配置快照中获取日期参数
    const params = {
      start_date: configSnapshot.value?.start_date,
      end_date: configSnapshot.value?.end_date
    }

    // 调用启动接口，会创建新任务
    const result = await backtestStore.startTask(backtest.value.uuid, params)
    showToast('已创建新回测任务')

    // 跳转到新任务详情页
    if (result?.task_uuid) {
      router.push(`/stage1/backtest/${result.task_uuid}`)
    }
  } catch (e: any) {
    showToast(e.response?.data?.detail || '重新运行失败', 'error')
  }
}

const handleDelete = async () => {
  if (!backtest.value?.uuid) return

  confirm('删除后无法恢复，确定要删除此回测任务吗？', async () => {
    try {
      await backtestStore.deleteTask(backtest.value.uuid)
      showToast('删除成功')
      goBack()
    } catch (e: any) {
      showToast(e.response?.data?.detail || '删除失败', 'error')
    }
  })
}

// 工具函数
const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

const formatDuration = (backtest: any) => {
  // 优先使用 duration_seconds
  if (backtest.duration_seconds && backtest.duration_seconds > 0) {
    const seconds = backtest.duration_seconds
    if (seconds < 60) return `${seconds}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
    return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
  }
  // 如果没有 duration_seconds，从 start_time 和 end_time 计算
  if (backtest.start_time && backtest.end_time) {
    const start = dayjs(backtest.start_time)
    const end = dayjs(backtest.end_time)
    const diff = end.diff(start, 'second')
    if (diff < 60) return `${diff}秒`
    if (diff < 3600) return `${Math.floor(diff / 60)}分${diff % 60}秒`
    return `${Math.floor(diff / 3600)}时${Math.floor((diff % 3600) / 60)}分`
  }
  return '-'
}

const formatMoney = (value?: number) => {
  if (value === undefined || value === null) return '-'
  return `¥${value.toLocaleString()}`
}

// 获取组件名称
const getComponentName = (component: any) => {
  if (!component) return '-'
  return component.name || '-'
}

// 格式化组件配置 - 按顺序显示所有参数
const formatConfigParams = (config: Record<string, any>) => {
  if (!config) return '-'

  // 按 param_0, param_1, param_2... 顺序显示
  const paramKeys = Object.keys(config)
    .filter(k => k.startsWith('param_'))
    .sort((a, b) => {
      const numA = parseInt(a.replace('param_', '')) || 0
      const numB = parseInt(b.replace('param_', '')) || 0
      return numA - numB
    })

  if (paramKeys.length === 0) return '-'

  return paramKeys.map(k => `${k}: ${config[k]}`).join(', ')
}

// 格式化分析器值
const formatAnalyzerValue = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return '-'

  // 百分比类分析器
  const percentAnalyzers = ['max_drawdown', 'win_rate', 'hold_pct', 'annual_return']
  if (percentAnalyzers.some(a => name.toLowerCase().includes(a))) {
    return `${(value * 100).toFixed(2)}%`
  }

  // 比率类分析器
  const ratioAnalyzers = ['sharpe', 'sortino', 'calmar']
  if (ratioAnalyzers.some(a => name.toLowerCase().includes(a))) {
    return value.toFixed(3)
  }

  // 计数类分析器
  const countAnalyzers = ['signal_count', 'trade_count', 'order_count']
  if (countAnalyzers.some(a => name.toLowerCase().includes(a))) {
    return Math.round(value).toString()
  }

  // 资金类分析器
  const moneyAnalyzers = ['net_value', 'profit', 'pnl', 'capital']
  if (moneyAnalyzers.some(a => name.toLowerCase().includes(a))) {
    return `¥${value.toFixed(2)}`
  }

  // 默认格式
  return value.toFixed(4)
}

// 获取分析器值颜色
const getAnalyzerValueColor = (name: string, value: number | null): string => {
  if (value === null || value === undefined) return '#666'

  // 回撤类 - 越低越好
  if (name.toLowerCase().includes('drawdown')) {
    return value <= 0.1 ? '#52c41a' : value <= 0.2 ? '#faad14' : '#f5222d'
  }

  // 收益/胜率类 - 越高越好
  if (name.toLowerCase().includes('return') || name.toLowerCase().includes('win_rate')) {
    return value >= 0 ? '#52c41a' : '#f5222d'
  }

  // 比率类
  if (name.toLowerCase().includes('sharpe') || name.toLowerCase().includes('sortino')) {
    return value >= 1 ? '#52c41a' : value >= 0 ? '#faad14' : '#f5222d'
  }

  // 净值/盈亏类
  if (name.toLowerCase().includes('profit') || name.toLowerCase().includes('pnl')) {
    return value >= 0 ? '#52c41a' : '#f5222d'
  }

  return '#666'
}

// ========== 生命周期 ==========
// WebSocket 实时更新
const { subscribe } = useWebSocket()
let unsubscribe: (() => void) | null = null

onMounted(() => {
  loadBacktest()

  // 订阅 WebSocket 更新
  unsubscribe = subscribe('*', (data) => {
    const taskId = data.task_id || data.task_uuid
    if (!taskId || taskId !== backtest.value?.uuid) return

    backtestStore.updateProgress({
      task_id: taskId,
      status: data.type === 'progress' ? undefined : data.type,
      progress: data.progress,
    })
  })
})

onUnmounted(() => {
  backtestStore.clearCurrentTask()
  if (unsubscribe) unsubscribe()
})
</script>

<style scoped>
.page-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f0f1a;
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-shrink: 0;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.run-id {
  font-family: monospace;
  font-size: 13px;
  color: #8a8a9a;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* Loading */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 100px;
  flex: 1;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner-small {
  width: 24px;
  height: 24px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
}

.loading-inline {
  display: flex;
  justify-content: center;
  padding: 40px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Button */
.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 1px solid #3a3a4e;
  color: #ffffff;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-danger {
  background: #f5222d;
  color: #ffffff;
}

.btn-danger:hover:not(:disabled) {
  background: #ff4d4f;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }
.tag-cyan { background: rgba(19, 194, 194, 0.2); color: #13c2c2; }

/* Tabs */
.tabs-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tabs-header {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid #2a2a3e;
  flex-shrink: 0;
}

.tab-button {
  padding: 12px 20px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #ffffff;
}

.tab-button.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
}

.tab-panel {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}

/* Card */
.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 20px;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 16px 0 12px 0;
}

/* Descriptions */
.descriptions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px 24px;
}

.desc-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.desc-item.full-width {
  grid-column: 1 / -1;
}

.desc-label {
  font-size: 12px;
  color: #8a8a9a;
}

.desc-value {
  font-size: 14px;
  color: #ffffff;
}

/* Divider */
.divider {
  height: 1px;
  background: #2a2a3e;
  margin: 16px 0;
}

/* Progress */
.progress-section {
  padding: 8px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.progress-label {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.progress-value {
  font-size: 16px;
  font-weight: 600;
  color: #1890ff;
}

.progress-bar {
  height: 8px;
  background: #2a2a3e;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #1890ff;
  transition: width 0.3s ease;
}

.progress-fill.active {
  animation: progress-pulse 1.5s ease-in-out infinite;
}

.progress-fill.normal {
  background: #52c41a;
}

@keyframes progress-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* Portfolio Snapshot */
.portfolio-snapshot {
  margin-top: 16px;
}

.component-section {
  margin-top: 12px;
}

.component-label {
  font-size: 13px;
  font-weight: 500;
  display: block;
  margin-bottom: 8px;
}

.component-label.text-blue { color: #1890ff; }
.component-label.text-green { color: #52c41a; }
.component-label.text-orange { color: #faad14; }

.component-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
  margin-top: 4px;
}

.component-config {
  font-size: 12px;
  color: #8a8a9a;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
}

.stat-label {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

/* Data Table */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.stats-detail {
  color: #1890ff;
  font-size: 12px;
  cursor: pointer;
}

.stats-detail:hover {
  color: #40a9ff;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

/* Alert */
.alert {
  padding: 12px 16px;
  border-radius: 4px;
  font-size: 14px;
}

.alert-error {
  background: rgba(245, 34, 45, 0.1);
  border: 1px solid #f5222d;
  color: #f5222d;
}

/* Result Page */
.result-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #8a8a9a;
}

.result-page svg {
  opacity: 0.3;
  margin-bottom: 16px;
}

.result-page h2 {
  font-size: 20px;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.result-page p {
  margin: 0 0 24px 0;
}

/* Env Info */
.env-info {
  background: #0f0f1a;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 200px;
  color: #a0d911;
}
</style>
