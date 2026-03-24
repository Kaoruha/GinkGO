<template>
  <div class="portfolio-detail-container">
    <!-- 固定的页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <button class="btn-text" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回
        </button>
        <div class="title-section">
          <h1 class="page-title">{{ portfolio?.name || '加载中...' }}</h1>
          <div class="tags">
            <span class="tag" :class="'tag-' + getModeTagColor(portfolio?.mode)">
              {{ getModeLabel(portfolio?.mode) }}
            </span>
            <span class="tag" :class="'tag-' + getStateTagColor(portfolio?.state)">
              <span class="status-dot" :class="'status-' + getStateStatus(portfolio?.state)"></span>
              {{ getStateLabel(portfolio?.state) }}
            </span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <button
          v-if="portfolio?.state === 'RUNNING'"
          class="btn-danger"
          @click="handleStop"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="6" width="12" height="12"/>
          </svg>
          停止
        </button>
        <button
          v-else-if="portfolio?.state === 'PAUSED' || portfolio?.state === 'STOPPED'"
          class="btn-primary"
          @click="handleStart"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21"/>
          </svg>
          启动
        </button>
        <button class="btn-secondary" @click="goToEditGraph">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
          编辑
        </button>
        <button class="btn-secondary" @click="showConfigModal = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6M4.22 4.22l4.24 4.24m5.08 5.08l4.24 4.24M1 12h6m6 0h6M4.22 19.78l4.24-4.24m5.08-5.08l4.24-4.24"/>
          </svg>
          配置
        </button>
      </div>
    </div>

    <!-- 可滚动的内容区域 -->
    <div class="scrollable-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>

      <!-- 详情内容 -->
      <div v-else-if="portfolio" class="detail-content">
        <!-- 统计卡片 -->
        <div class="stats-row">
          <div class="stat-card">
            <div class="stat-item">
              <span class="stat-label">平均净值</span>
              <span v-if="avgNetValue" class="stat-value">{{ avgNetValue.toFixed(3) }}</span>
              <span v-else class="stat-value">-</span>
              <span v-if="avgNetValue" class="stat-change" :class="getChangeClass(avgNetValue)">
                {{ ((avgNetValue - 1) * 100).toFixed(2) }}%
              </span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-item">
              <span class="stat-label">回测次数</span>
              <span class="stat-value">{{ backtestTasks.filter(t => t.status === 'completed').length }}</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-item">
              <span class="stat-label">初始资金</span>
              <span class="stat-value">¥{{ formatNumber(portfolio.initial_cash) }}</span>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-item">
              <span class="stat-label">平均盈亏</span>
              <span v-if="avgNetValue" class="stat-value" :class="getChangeClass(avgNetValue)">
                {{ ((avgNetValue - 1) * 100).toFixed(2) }}%
              </span>
              <span v-else class="stat-value">-</span>
            </div>
          </div>
        </div>

        <!-- 组件配置 -->
        <div class="card components-card">
          <div class="card-header">
            <h4>组件配置</h4>
          </div>
          <div class="card-body">
            <div class="components-grid">
              <!-- 选股器 -->
              <div v-if="portfolio.components?.selectors?.length" class="component-section">
                <div class="section-title">
                  <span class="tag tag-lime">选股器</span>
                </div>
                <div class="component-list">
                  <div v-for="s in portfolio.components.selectors" :key="s.uuid" class="component-item">
                    <span class="component-name">{{ s.name }}</span>
                    <span v-if="Object.keys(s.config || {}).length > 0" class="component-config">
                      <span v-for="(value, key) in s.config" :key="key" class="config-tag">
                        {{ key }}: {{ value }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 仓位管理器 -->
              <div v-if="portfolio.components?.sizer" class="component-section">
                <div class="section-title">
                  <span class="tag tag-gold">仓位管理</span>
                </div>
                <div class="component-list">
                  <div class="component-item">
                    <span class="component-name">{{ portfolio.components.sizer.name }}</span>
                    <span v-if="Object.keys(portfolio.components.sizer.config || {}).length > 0" class="component-config">
                      <span v-for="(value, key) in portfolio.components.sizer.config" :key="key" class="config-tag">
                        {{ key }}: {{ value }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 策略 -->
              <div v-if="portfolio.components?.strategies?.length" class="component-section">
                <div class="section-title">
                  <span class="tag tag-cyan">策略</span>
                </div>
                <div class="component-list">
                  <div v-for="s in portfolio.components.strategies" :key="s.uuid" class="component-item">
                    <span class="component-name">{{ s.name }}</span>
                    <span v-if="s.weight" class="weight-tag">权重: {{ (s.weight * 100).toFixed(0) }}%</span>
                    <span v-if="Object.keys(s.config || {}).length > 0" class="component-config">
                      <span v-for="(value, key) in s.config" :key="key" class="config-tag">
                        {{ key }}: {{ value }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 风控 -->
              <div v-if="portfolio.components?.risk_managers?.length" class="component-section">
                <div class="section-title">
                  <span class="tag tag-red">风控</span>
                </div>
                <div class="component-list">
                  <div v-for="r in portfolio.components.risk_managers" :key="r.uuid" class="component-item">
                    <span class="component-name">{{ r.name }}</span>
                    <span v-if="Object.keys(r.config || {}).length > 0" class="component-config">
                      <span v-for="(value, key) in r.config" :key="key" class="config-tag">
                        {{ key }}: {{ value }}
                      </span>
                    </span>
                  </div>
                </div>
              </div>

              <!-- 分析器 -->
              <div v-if="portfolio.components?.analyzers?.length" class="component-section">
                <div class="section-title">
                  <span class="tag tag-purple">分析器</span>
                </div>
                <div class="component-list">
                  <div v-for="a in portfolio.components.analyzers" :key="a.uuid" class="component-item">
                    <span class="component-name">{{ a.name }}</span>
                  </div>
                </div>
              </div>

              <!-- 无组件提示 -->
              <div
                v-if="!portfolio.components?.selectors?.length &&
                      !portfolio.components?.sizer &&
                      !portfolio.components?.strategies?.length &&
                      !portfolio.components?.risk_managers?.length"
                class="empty-components"
              >
                暂无组件配置
              </div>
            </div>
          </div>
        </div>

        <!-- 关联回测任务 -->
        <div class="card backtests-card">
          <div class="card-header">
            <h4>回测任务</h4>
          </div>
          <div class="card-body">
            <div v-if="backtestLoading" class="loading-container">
              <div class="spinner small"></div>
            </div>
            <div v-else-if="backtestTasks.length === 0" class="empty-text">
              暂无回测任务
            </div>
            <div v-else class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>任务名称</th>
                    <th>状态</th>
                    <th>总盈亏</th>
                    <th>订单数</th>
                    <th>创建时间</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in backtestTasks" :key="record.uuid">
                    <td><a class="link" @click="goToBacktest(record.uuid)">{{ record.name || '(未命名)' }}</a></td>
                    <td>
                      <span class="tag" :class="'tag-' + getBacktestStatusTagColor(record.status)">
                        {{ getBacktestStatusLabel(record.status) }}
                      </span>
                    </td>
                    <td :style="{ color: parseFloat(record.total_pnl) >= 0 ? '#f5222d' : '#52c41a' }">
                      {{ parseFloat(record.total_pnl).toFixed(2) }}
                    </td>
                    <td>{{ record.total_orders }}</td>
                    <td>{{ formatDate(record.create_at) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 净值历史 -->
        <div class="card chart-card">
          <div class="card-header">
            <h4>净值曲线</h4>
          </div>
          <div class="card-body">
            <div class="chart-placeholder">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#8a8a9a" stroke-width="2">
                <polyline points="3 17 9 11 13 15 21 7"/>
                <polyline points="14 7 21 7 21 14"/>
              </svg>
              <p>图表功能正在开发中</p>
              <p class="chart-tip">将集成 TradingView 图表组件</p>
            </div>
          </div>
        </div>

        <!-- 持仓详情 -->
        <div class="card positions-card">
          <div class="card-header">
            <h4>持仓详情</h4>
          </div>
          <div class="card-body">
            <div v-if="!portfolio.positions?.length" class="empty-text">
              暂无持仓
            </div>
            <div v-else class="table-wrapper">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>代码</th>
                    <th>持仓量</th>
                    <th>成本价</th>
                    <th>现价</th>
                    <th>市值</th>
                    <th>盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in portfolio.positions" :key="record.code">
                    <td>
                      <span class="tag tag-blue">{{ record.code }}</span>
                    </td>
                    <td>{{ formatNumber(record.volume) }}</td>
                    <td>¥{{ record.cost_price.toFixed(2) }}</td>
                    <td>¥{{ record.current_price.toFixed(2) }}</td>
                    <td>¥{{ formatNumber(record.volume * record.current_price) }}</td>
                    <td>
                      <span :class="getProfitClass(record.current_price, record.cost_price)">
                        {{ ((record.current_price - record.cost_price) / record.cost_price * 100).toFixed(2) }}%
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- 策略表现 -->
        <div v-if="portfolio.strategies?.length > 0" class="card strategies-card">
          <div class="card-header">
            <h4>策略表现</h4>
          </div>
          <div class="card-body">
            <div class="strategies-grid">
              <div v-for="strategy in portfolio.strategies" :key="strategy.uuid" class="strategy-item">
                <div class="strategy-header">
                  <span class="strategy-name">{{ strategy.name }}</span>
                  <span class="tag tag-blue">{{ strategy.type }}</span>
                </div>
                <div class="strategy-stats">
                  <div class="strategy-stat">
                    <span class="stat-label">权重</span>
                    <span class="stat-value">{{ (strategy.weight * 100).toFixed(0) }}%</span>
                  </div>
                  <div class="strategy-stat">
                    <span class="stat-label">收益率</span>
                    <span class="stat-value" :class="getChangeClass((strategy.performance?.return || 0) + 1)">
                      {{ ((strategy.performance?.return || 0) * 100).toFixed(2) }}%
                    </span>
                  </div>
                  <div class="strategy-stat">
                    <span class="stat-label">夏普比率</span>
                    <span class="stat-value">{{ (strategy.performance?.sharpe || 0).toFixed(2) }}</span>
                  </div>
                  <div class="strategy-stat">
                    <span class="stat-label">最大回撤</span>
                    <span class="stat-value value-down">
                      {{ ((strategy.performance?.max_drawdown || 0) * 100).toFixed(2) }}%
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 风控告警 -->
        <div v-if="portfolio.risk_alerts?.length > 0" class="card alerts-card">
          <div class="card-header">
            <h4>风控告警</h4>
          </div>
          <div class="card-body">
            <div class="alert-list">
              <div v-for="item in portfolio.risk_alerts" :key="item.uuid" class="alert-item">
                <div class="alert-main">
                  <div class="alert-header">
                    <span class="tag" :class="'tag-' + getAlertLevelTagColor(item.level)">{{ item.level }}</span>
                    <span>{{ item.type }}</span>
                    <span class="tag" :class="item.handled ? 'tag-green' : 'tag-orange'">
                      {{ item.handled ? '已处理' : '待处理' }}
                    </span>
                  </div>
                  <div class="alert-message">{{ item.message }}</div>
                </div>
                <div class="alert-actions">
                  <span class="alert-time">{{ formatDate(item.triggered_at) }}</span>
                  <a v-if="!item.handled" class="link" @click="handleAlert(item)">处理</a>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 配置弹窗 -->
    <div v-if="showConfigModal" class="modal-overlay" @click.self="showConfigModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>投资组合配置</h3>
          <button class="modal-close" @click="showConfigModal = false">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleSaveConfig">
            <div class="form-group">
              <label class="form-label">配置锁定</label>
              <div class="switch-container">
                <input v-model="configForm.config_locked" type="checkbox" id="config_locked" class="switch-input" />
                <label for="config_locked" class="switch-label"></label>
                <span class="form-tip">锁定后将无法修改策略配置</span>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">初始资金</label>
              <input
                v-model.number="configForm.initial_cash"
                type="number"
                :min="1000"
                :max="100000000"
                :step="0.01"
                class="form-input"
                :disabled="portfolio?.config_locked"
              />
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="showConfigModal = false">取消</button>
              <button type="submit" class="btn-primary">保存</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { portfolioApi, type PortfolioDetail } from '@/api/modules/portfolio'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'
import { formatDate, formatNumber } from '@/utils/format'

const router = useRouter()
const route = useRoute()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 自定义确认对话框
const showConfirm = (title: string, content: string, onOk: () => void) => {
  if (confirm(`${title}\n\n${content}`)) {
    onOk()
  }
}

// 状态管理
const loading = ref(false)
const portfolio = ref<PortfolioDetail | null>(null)
const showConfigModal = ref(false)
const backtestTasks = ref<BacktestTask[]>([])
const backtestLoading = ref(false)

// 计算回测平均净值
const avgNetValue = computed(() => {
  const completedTasks = backtestTasks.value.filter(t => t.status === 'completed')
  if (completedTasks.length === 0) return null

  const initialValues = completedTasks.map(t => {
    try {
      const config = JSON.parse(t.config_snapshot || '{}')
      return config.initial_capital || 1000000
    } catch {
      return 1000000
    }
  })

  const netValues = completedTasks.map((t, i) => {
    const finalValue = parseFloat(t.final_portfolio_value) || 0
    const initialValue = initialValues[i]
    return finalValue / initialValue
  })

  const sum = netValues.reduce((a, b) => a + b, 0)
  return sum / netValues.length
})

// 配置表单
const configForm = reactive({
  config_locked: false,
  initial_cash: 100000
})

// 加载数据
const loadData = async () => {
  const uuid = route.params.id as string
  loading.value = true
  try {
    const data = await portfolioApi.get(uuid)
    portfolio.value = data
    configForm.config_locked = data.config_locked
    configForm.initial_cash = data.initial_cash
    loadBacktestTasks(uuid)
  } catch (error: any) {
    showToast(`加载失败: ${error.message || '未知错误'}`, 'error')
  } finally {
    loading.value = false
  }
}

// 加载关联的回测任务
const loadBacktestTasks = async (portfolioId: string) => {
  backtestLoading.value = true
  try {
    const res = await backtestApi.list({ portfolio_id: portfolioId, size: 10 })
    backtestTasks.value = res.data || []
  } catch (error: any) {
    console.error('Failed to load backtest tasks:', error)
  } finally {
    backtestLoading.value = false
  }
}

// 跳转到回测详情
const goToBacktest = (uuid: string) => {
  router.push(`/stage1/backtest/${uuid}`)
}

// 获取模式标签
const getModeLabel = (mode?: string) => {
  if (!mode) return '-'
  const labels: Record<string, string> = {
    BACKTEST: '回测',
    LIVE: '实盘',
    PAPER: '模拟盘'
  }
  return labels[mode] || mode
}

// 获取模式标签颜色
const getModeTagColor = (mode?: string) => {
  if (!mode) return 'gray'
  const colors: Record<string, string> = {
    BACKTEST: 'blue',
    LIVE: 'green',
    PAPER: 'orange'
  }
  return colors[mode] || 'gray'
}

// 获取状态标签
const getStateLabel = (state?: string) => {
  if (!state) return '-'
  const labels: Record<string, string> = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    STOPPED: '已停止',
    CREATED: '已创建'
  }
  return labels[state] || state
}

// 获取状态标签颜色
const getStateTagColor = (state?: string) => {
  if (!state) return 'gray'
  const colors: Record<string, string> = {
    RUNNING: 'blue',
    PAUSED: 'orange',
    STOPPED: 'gray',
    CREATED: 'cyan'
  }
  return colors[state] || 'gray'
}

// 获取状态指示器
const getStateStatus = (state?: string) => {
  if (!state) return 'default'
  const statuses: Record<string, string> = {
    RUNNING: 'processing',
    PAUSED: 'warning',
    STOPPED: 'default',
    CREATED: 'default'
  }
  return statuses[state] || 'default'
}

// 获取回测状态标签颜色
const getBacktestStatusTagColor = (status: string) => {
  const colors: Record<string, string> = {
    created: 'gray',
    pending: 'orange',
    running: 'blue',
    completed: 'green',
    failed: 'red',
    stopped: 'gray'
  }
  return colors[status] || 'gray'
}

// 获取回测状态标签
const getBacktestStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    created: '待启动',
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止'
  }
  return labels[status] || status
}

// 获取变化样式
const getChangeClass = (value: number) => {
  if (value > 1) return 'value-up'
  if (value < 1) return 'value-down'
  return 'value-flat'
}

// 获取盈利样式
const getProfitClass = (current: number, cost: number) => {
  if (current > cost) return 'value-up'
  if (current < cost) return 'value-down'
  return 'value-flat'
}

// 获取告警级别颜色
const getAlertLevelTagColor = (level: string) => {
  const colors: Record<string, string> = {
    'INFO': 'blue',
    'WARNING': 'orange',
    'ERROR': 'red',
    'CRITICAL': 'red'
  }
  return colors[level] || 'gray'
}

// 返回
const goBack = () => {
  router.push('/portfolio')
}

// 跳转到图编辑器
const goToEditGraph = () => {
  router.push(`/portfolio/${route.params.id}/edit`)
}

// 启动
const handleStart = () => {
  showConfirm(
    '确认启动',
    `确定要启动投资组合"${portfolio.value?.name}"吗？`,
    async () => {
      try {
        await portfolioApi.update(route.params.id as string, { state: 'RUNNING' })
        showToast('启动成功')
        loadData()
      } catch (error: any) {
        showToast(`操作失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 停止
const handleStop = () => {
  showConfirm(
    '确认停止',
    `确定要停止投资组合"${portfolio.value?.name}"吗？`,
    async () => {
      try {
        await portfolioApi.update(route.params.id as string, { state: 'STOPPED' })
        showToast('已停止')
        loadData()
      } catch (error: any) {
        showToast(`操作失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 保存配置
const handleSaveConfig = async () => {
  try {
    await portfolioApi.update(route.params.id as string, {
      config_locked: configForm.config_locked,
      initial_cash: configForm.initial_cash
    })
    showToast('保存成功')
    showConfigModal.value = false
    loadData()
  } catch (error: any) {
    showToast(`保存失败: ${error.message || '未知错误'}`, 'error')
  }
}

// 处理告警
const handleAlert = (alert: any) => {
  showConfirm(
    '处理告警',
    `确定要标记此告警为已处理吗？\n\n${alert.message}`,
    async () => {
      // TODO: 调用告警处理API
      showToast('已标记为已处理')
      loadData()
    }
  )
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.portfolio-detail-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #0f0f1a;
}

.page-header {
  flex-shrink: 0;
  padding: 16px 24px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
  flex-wrap: wrap;
  gap: 16px;
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-text:hover {
  background: #2a2a3e;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-gray {
  background: #2a2a3e;
  color: #8a8a9a;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-orange {
  background: rgba(250, 140, 22, 0.2);
  color: #fa8c16;
}

.tag-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.tag-cyan {
  background: rgba(19, 194, 194, 0.2);
  color: #13c2c2;
}

.tag-lime {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-gold {
  background: rgba(250, 173, 20, 0.2);
  color: #faad14;
}

.tag-purple {
  background: rgba(114, 46, 209, 0.2);
  color: #722ed1;
}

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 4px;
}

.status-processing {
  background: #1890ff;
  animation: pulse 2s infinite;
}

.status-warning {
  background: #faad14;
}

.status-default {
  background: #8a8a9a;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-danger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #ff4d4f;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.spinner.small {
  width: 24px;
  height: 24px;
  border-width: 2px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.stat-change {
  font-size: 14px;
  font-weight: 500;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

.value-flat {
  color: #8a8a9a;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #8a8a9a;
}

.chart-placeholder p {
  margin: 8px 0 0 0;
}

.chart-tip {
  font-size: 12px;
  color: #5a5a6e;
}

.empty-text {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
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
  font-size: 13px;
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tr:hover {
  background: #2a2a3e;
}

.link {
  color: #1890ff;
  cursor: pointer;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.strategy-item {
  padding: 16px;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  background: #2a2a3e;
}

.strategy-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.strategy-name {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.strategy-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.strategy-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-item {
  padding: 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.alert-main {
  flex: 1;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.alert-message {
  font-size: 13px;
  color: #8a8a9a;
}

.alert-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.alert-time {
  font-size: 12px;
  color: #8a8a9a;
}

/* 组件配置样式 */
.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.component-section {
  padding: 12px;
  background: #2a2a3e;
  border-radius: 8px;
}

.component-section .section-title {
  margin-bottom: 8px;
}

.component-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.component-item {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #1a1a2e;
  border-radius: 4px;
  border: 1px solid #2a2a3e;
}

.component-name {
  font-weight: 500;
  color: #ffffff;
}

.weight-tag {
  font-size: 12px;
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.component-config {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.config-tag {
  font-size: 11px;
  color: #8a8a9a;
  background: #1a1a2e;
  padding: 2px 6px;
  border-radius: 4px;
}

.empty-components {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
  padding: 4px 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.switch-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-input {
  display: none;
}

.switch-label {
  position: relative;
  width: 44px;
  height: 22px;
  background: #3a3a4e;
  border-radius: 11px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-label::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #ffffff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked + .switch-label {
  background: #1890ff;
}

.switch-input:checked + .switch-label::after {
  transform: translateX(22px);
}

.form-tip {
  font-size: 12px;
  color: #8a8a9a;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .stats-row {
    grid-template-columns: 1fr;
  }

  .strategies-grid {
    grid-template-columns: 1fr;
  }
}
</style>
