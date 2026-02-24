<template>
  <div class="portfolio-detail-container">
    <!-- 固定的页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <a-button
          class="back-btn"
          @click="goBack"
        >
          <ArrowLeftOutlined /> 返回
        </a-button>
        <div class="title-section">
          <h1 class="page-title">
            {{ portfolio?.name || '加载中...' }}
          </h1>
          <div class="tags">
            <a-tag :color="getModeColor(portfolio?.mode)">
              {{ getModeLabel(portfolio?.mode) }}
            </a-tag>
            <a-tag :color="getStateColor(portfolio?.state)">
              <a-badge :status="getStateStatus(portfolio?.state)" />
              {{ getStateLabel(portfolio?.state) }}
            </a-tag>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <a-button
          v-if="portfolio?.state === 'RUNNING'"
          danger
          size="large"
          @click="handleStop"
        >
          <PauseOutlined /> 停止
        </a-button>
        <a-button
          v-else-if="portfolio?.state === 'PAUSED' || portfolio?.state === 'STOPPED'"
          type="primary"
          size="large"
          @click="handleStart"
        >
          <PlayCircleOutlined /> 启动
        </a-button>
        <a-button
          size="large"
          @click="goToEditGraph"
        >
          <EditOutlined /> 编辑
        </a-button>
        <a-button
          size="large"
          @click="showConfigModal = true"
        >
          <SettingOutlined /> 配置
        </a-button>
      </div>
    </div>

    <!-- 可滚动的内容区域 -->
    <div class="scrollable-content">
      <!-- 加载状态 -->
      <div
        v-if="loading"
        class="loading-container"
      >
        <a-spin size="large" />
      </div>

      <!-- 详情内容 -->
      <div
        v-else-if="portfolio"
        class="detail-content"
      >
      <!-- 统计卡片 -->
      <div class="stats-row">
        <a-card class="stat-card">
          <div class="stat-item">
            <span class="stat-label">平均净值</span>
            <span v-if="avgNetValue" class="stat-value">{{ avgNetValue.toFixed(3) }}</span>
            <span v-else class="stat-value">-</span>
            <span
              v-if="avgNetValue"
              class="stat-change"
              :class="getChangeClass(avgNetValue)"
            >
              {{ ((avgNetValue - 1) * 100).toFixed(2) }}%
            </span>
          </div>
        </a-card>
        <a-card class="stat-card">
          <div class="stat-item">
            <span class="stat-label">回测次数</span>
            <span class="stat-value">{{ backtestTasks.filter(t => t.status === 'completed').length }}</span>
          </div>
        </a-card>
        <a-card class="stat-card">
          <div class="stat-item">
            <span class="stat-label">初始资金</span>
            <span class="stat-value">¥{{ formatNumber(portfolio.initial_cash) }}</span>
          </div>
        </a-card>
        <a-card class="stat-card">
          <div class="stat-item">
            <span class="stat-label">平均盈亏</span>
            <span v-if="avgNetValue" class="stat-value" :class="getChangeClass(avgNetValue)">
              {{ ((avgNetValue - 1) * 100).toFixed(2) }}%
            </span>
            <span v-else class="stat-value">-</span>
          </div>
        </a-card>
      </div>

      <!-- 组件配置 -->
      <a-card
        title="组件配置"
        class="components-card"
      >
        <div class="components-grid">
          <!-- 选股器 -->
          <div v-if="portfolio.components?.selectors?.length" class="component-section">
            <div class="section-title">
              <a-tag color="lime">选股器</a-tag>
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
              <a-tag color="gold">仓位管理</a-tag>
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
              <a-tag color="cyan">策略</a-tag>
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
              <a-tag color="red">风控</a-tag>
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
              <a-tag color="purple">分析器</a-tag>
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
      </a-card>

      <!-- 关联回测任务 -->
      <a-card title="回测任务" class="backtests-card">
        <a-spin v-if="backtestLoading" />
        <div v-else-if="backtestTasks.length === 0" class="empty-text">
          暂无回测任务
        </div>
        <a-table
          v-else
          :columns="backtestColumns"
          :data-source="backtestTasks"
          :pagination="false"
          row-key="uuid"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <a @click="goToBacktest(record.uuid)">{{ record.name || '(未命名)' }}</a>
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="getBacktestStatusColor(record.status)">
                {{ getBacktestStatusLabel(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'total_pnl'">
              <span :style="{ color: parseFloat(record.total_pnl) >= 0 ? '#f5222d' : '#52c41a' }">
                {{ parseFloat(record.total_pnl).toFixed(2) }}
              </span>
            </template>
            <template v-else-if="column.key === 'create_at'">
              {{ formatDate(record.create_at) }}
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 净值历史 (预留 TradingView 集成) -->
      <a-card
        title="净值曲线"
        class="chart-card"
      >
        <div class="chart-placeholder">
          <LineChartOutlined style="font-size: 48px; color: #d9d9d9;" />
          <p>图表功能正在开发中</p>
          <p class="chart-tip">
            将集成 TradingView 图表组件
          </p>
        </div>
      </a-card>

      <!-- 持仓详情 -->
      <a-card
        title="持仓详情"
        class="positions-card"
      >
        <div
          v-if="!portfolio.positions?.length"
          class="empty-text"
        >
          暂无持仓
        </div>
        <a-table
          v-else
          :columns="positionColumns"
          :data-source="portfolio.positions"
          :pagination="{ pageSize: 10 }"
          row-key="code"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'code'">
              <a-tag color="blue">
                {{ record.code }}
              </a-tag>
            </template>
            <template v-if="column.key === 'volume'">
              {{ formatNumber(record.volume) }}
            </template>
            <template v-if="column.key === 'cost_price'">
              ¥{{ record.cost_price.toFixed(2) }}
            </template>
            <template v-if="column.key === 'current_price'">
              ¥{{ record.current_price.toFixed(2) }}
            </template>
            <template v-if="column.key === 'market_value'">
              ¥{{ formatNumber(record.volume * record.current_price) }}
            </template>
            <template v-if="column.key === 'profit_loss'">
              <span :class="getProfitClass(record.current_price, record.cost_price)">
                {{ ((record.current_price - record.cost_price) / record.cost_price * 100).toFixed(2) }}%
              </span>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 策略表现 -->
      <a-card
        v-if="portfolio.strategies?.length > 0"
        title="策略表现"
        class="strategies-card"
      >
        <div class="strategies-grid">
          <div
            v-for="strategy in portfolio.strategies"
            :key="strategy.uuid"
            class="strategy-item"
          >
            <div class="strategy-header">
              <span class="strategy-name">{{ strategy.name }}</span>
              <a-tag color="blue">
                {{ strategy.type }}
              </a-tag>
            </div>
            <div class="strategy-stats">
              <div class="strategy-stat">
                <span class="stat-label">权重</span>
                <span class="stat-value">{{ (strategy.weight * 100).toFixed(0) }}%</span>
              </div>
              <div class="strategy-stat">
                <span class="stat-label">收益率</span>
                <span
                  class="stat-value"
                  :class="getChangeClass((strategy.performance?.return || 0) + 1)"
                >
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
      </a-card>

      <!-- 风控告警 -->
      <a-card
        v-if="portfolio.risk_alerts?.length > 0"
        title="风控告警"
        class="alerts-card"
      >
        <a-list
          :data-source="portfolio.risk_alerts"
          row-key="uuid"
        >
          <template #renderItem="{ item }">
            <a-list-item>
              <a-list-item-meta>
                <template #title>
                  <a-space>
                    <a-tag :color="getAlertLevelColor(item.level)">
                      {{ item.level }}
                    </a-tag>
                    <span>{{ item.type }}</span>
                    <a-tag
                      v-if="item.handled"
                      color="green"
                    >
                      已处理
                    </a-tag>
                    <a-tag
                      v-else
                      color="orange"
                    >
                      待处理
                    </a-tag>
                  </a-space>
                </template>
                <template #description>
                  {{ item.message }}
                </template>
              </a-list-item-meta>
              <template #actions>
                <span class="alert-time">{{ formatDate(item.triggered_at) }}</span>
                <a
                  v-if="!item.handled"
                  @click="handleAlert(item)"
                >处理</a>
              </template>
            </a-list-item>
          </template>
        </a-list>
      </a-card>
      </div>
    </div>

    <!-- 配置弹窗 -->
    <a-modal
      v-model:open="showConfigModal"
      title="投资组合配置"
      width="600px"
      @ok="handleSaveConfig"
    >
      <a-form layout="vertical">
        <a-form-item label="配置锁定">
          <a-switch v-model:checked="configForm.config_locked" />
          <span class="form-tip">锁定后将无法修改策略配置</span>
        </a-form-item>
        <a-form-item label="初始资金">
          <a-input-number
            v-model:value="configForm.initial_cash"
            :min="1000"
            :max="100000000"
            :precision="2"
            style="width: 100%"
            :disabled="portfolio?.config_locked"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  PauseOutlined,
  SettingOutlined,
  LineChartOutlined,
  EditOutlined
} from '@ant-design/icons-vue'
import { portfolioApi, type PortfolioDetail } from '@/api/modules/portfolio'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'
import {
  getModeLabel,
  getModeColor,
  getStateLabel,
  getStateColor,
  getStateStatus
} from '@/constants'
import { formatDate, formatNumber } from '@/utils/format'

const router = useRouter()
const route = useRoute()

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

// 持仓表格列
const positionColumns = [
  { title: '代码', dataIndex: 'code', key: 'code', width: 120 },
  { title: '持仓量', dataIndex: 'volume', key: 'volume', width: 120, align: 'right' },
  { title: '成本价', dataIndex: 'cost_price', key: 'cost_price', width: 120, align: 'right' },
  { title: '现价', dataIndex: 'current_price', key: 'current_price', width: 120, align: 'right' },
  { title: '市值', key: 'market_value', width: 150, align: 'right' },
  { title: '盈亏', key: 'profit_loss', width: 100, align: 'right' }
]

// 回测任务表格列
const backtestColumns = [
  { title: '任务名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '总盈亏', dataIndex: 'total_pnl', key: 'total_pnl', width: 100, align: 'right' },
  { title: '订单数', dataIndex: 'total_orders', key: 'total_orders', width: 80, align: 'right' },
  { title: '创建时间', dataIndex: 'create_at', key: 'create_at', width: 150 },
]

// 加载数据
const loadData = async () => {
  const uuid = route.params.id as string
  loading.value = true
  try {
    const data = await portfolioApi.get(uuid)
    portfolio.value = data
    configForm.config_locked = data.config_locked
    configForm.initial_cash = data.initial_cash
    // 加载关联的回测任务
    loadBacktestTasks(uuid)
  } catch (error: any) {
    message.error(`加载失败: ${error.message || '未知错误'}`)
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

// 获取回测状态颜色
const getBacktestStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    created: 'default',
    pending: 'warning',
    running: 'processing',
    completed: 'success',
    failed: 'error',
    stopped: 'default',
  }
  return colors[status] || 'default'
}

// 获取回测状态标签
const getBacktestStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    created: '待启动',
    pending: '等待中',
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
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
const getAlertLevelColor = (level: string) => {
  const colors: Record<string, string> = {
    'INFO': 'blue',
    'WARNING': 'orange',
    'ERROR': 'red',
    'CRITICAL': 'red'
  }
  return colors[level] || 'default'
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
  Modal.confirm({
    title: '确认启动',
    content: `确定要启动投资组合"${portfolio.value?.name}"吗？`,
    onOk: async () => {
      try {
        await portfolioApi.update(route.params.id as string, { state: 'RUNNING' })
        message.success('启动成功')
        loadData()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 停止
const handleStop = () => {
  Modal.confirm({
    title: '确认停止',
    content: `确定要停止投资组合"${portfolio.value?.name}"吗？`,
    onOk: async () => {
      try {
        await portfolioApi.update(route.params.id as string, { state: 'STOPPED' })
        message.success('已停止')
        loadData()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 保存配置
const handleSaveConfig = async () => {
  try {
    await portfolioApi.update(route.params.id as string, {
      config_locked: configForm.config_locked,
      initial_cash: configForm.initial_cash
    })
    message.success('保存成功')
    showConfigModal.value = false
    loadData()
  } catch (error: any) {
    message.error(`保存失败: ${error.message || '未知错误'}`)
  }
}

// 处理告警
const handleAlert = (alert: any) => {
  Modal.confirm({
    title: '处理告警',
    content: `确定要标记此告警为已处理吗？\n\n${alert.message}`,
    onOk: async () => {
      try {
        // TODO: 调用告警处理API
        message.success('已标记为已处理')
        loadData()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
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
  background: #fff;
}

.page-header {
  flex-shrink: 0;
  padding-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0;
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
  padding-top: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-btn {
  flex-shrink: 0;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.tags {
  display: flex;
  gap: 8px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
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
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #8c8c8c;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
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
  color: #8c8c8c;
}

.chart-card,
.positions-card,
.strategies-card,
.alerts-card,
.components-card,
.backtests-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #8c8c8c;
}

.chart-tip {
  font-size: 12px;
  color: #bfbfbf;
}

.empty-text {
  text-align: center;
  padding: 40px;
  color: #8c8c8c;
}

.strategies-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.strategy-item {
  padding: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
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
  color: #1a1a1a;
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

.alert-time {
  font-size: 12px;
  color: #8c8c8c;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: #8c8c8c;
}

/* 组件配置样式 */
.components-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.component-section {
  padding: 12px;
  background: #fafafa;
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
  background: #fff;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.component-name {
  font-weight: 500;
  color: #1a1a1a;
}

.weight-tag {
  font-size: 12px;
  color: #1890ff;
  background: #e6f7ff;
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
  color: #666;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.empty-components {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: #8c8c8c;
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
    gap: 16px;
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
