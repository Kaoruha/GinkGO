<template>
  <div class="page-container">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <a-spin size="large" />
    </div>

    <!-- 详情内容 -->
    <div v-else-if="backtest">
      <div class="page-header">
        <div class="page-title">
          <a-tag :color="getStatusColor(backtest.status)">{{ getStatusLabel(backtest.status) }}</a-tag>
          {{ backtest.task_id }}
        </div>
        <a-space>
          <a-button v-if="backtest.status === 'running'" type="primary" danger @click="stopBacktest">停止回测</a-button>
          <a-button @click="goBack">返回列表</a-button>
        </a-space>
      </div>

      <!-- 基本信息 -->
      <a-card title="基本信息" style="margin-bottom: 16px">
        <a-descriptions :column="3" bordered size="small">
          <a-descriptions-item label="任务ID">{{ backtest.task_id }}</a-descriptions-item>
          <a-descriptions-item label="UUID">
            <a-typography-text copyable :copy-text="backtest.uuid" style="font-size: 12px;">
              {{ backtest.uuid?.substring(0, 8) }}...
            </a-typography-text>
          </a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="getStatusColor(backtest.status)">{{ getStatusLabel(backtest.status) }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="关联引擎">{{ backtest.engine_id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="投资组合">{{ backtest.portfolio_id || '-' }}</a-descriptions-item>
          <a-descriptions-item label="运行时长">{{ formatDuration(backtest.duration_seconds) }}</a-descriptions-item>
          <a-descriptions-item label="开始时间">{{ formatDateTime(backtest.start_time) }}</a-descriptions-item>
          <a-descriptions-item label="结束时间">{{ formatDateTime(backtest.end_time) }}</a-descriptions-item>
          <a-descriptions-item label="创建时间">{{ formatDateTime(backtest.create_at) }}</a-descriptions-item>
        </a-descriptions>
      </a-card>

      <!-- 配置快照 -->
      <a-card title="配置快照" style="margin-bottom: 16px">
        <a-descriptions :column="3" bordered size="small">
          <a-descriptions-item label="配置名称">{{ configSnapshot.name || backtest.task_id }}</a-descriptions-item>
          <a-descriptions-item label="初始资金">{{ formatMoney(configSnapshot.initial_capital) }}</a-descriptions-item>
          <a-descriptions-item label="数据源">{{ configSnapshot.data_source || '-' }}</a-descriptions-item>
          <a-descriptions-item label="回测区间" :span="3">
            {{ formatDate(backtest.start_time) }} 至 {{ formatDate(backtest.end_time) }}
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <!-- 统计指标 -->
      <a-card title="回测指标" style="margin-bottom: 16px">
        <a-row :gutter="16">
          <a-col :span="4">
            <a-statistic
              title="最终资产"
              :value="parseFloat(backtest.final_portfolio_value || '0')"
              :precision="2"
              prefix="¥"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="总盈亏"
              :value="parseFloat(backtest.total_pnl || '0')"
              :precision="2"
              :value-style="{ color: pnlColor }"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="年化收益"
              :value="parseFloat(backtest.annual_return || '0') * 100"
              :precision="2"
              suffix="%"
              :value-style="{ color: parseFloat(backtest.annual_return || '0') >= 0 ? '#52c41a' : '#f5222d' }"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic title="夏普比率" :value="parseFloat(backtest.sharpe_ratio || '0')" :precision="2" />
          </a-col>
          <a-col :span="4">
            <a-statistic
              title="最大回撤"
              :value="parseFloat(backtest.max_drawdown || '0') * 100"
              :precision="2"
              suffix="%"
              :value-style="{ color: parseFloat(backtest.max_drawdown || '0') <= 0.1 ? '#52c41a' : '#f5222d' }"
            />
          </a-col>
          <a-col :span="4">
            <a-statistic title="胜率" :value="parseFloat(backtest.win_rate || '0') * 100" :precision="1" suffix="%" />
          </a-col>
        </a-row>
      </a-card>

      <!-- 执行统计 -->
      <a-card title="执行统计" style="margin-bottom: 16px">
        <a-row :gutter="24">
          <a-col :span="4">
            <a-statistic title="订单数" :value="backtest.total_orders || 0" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="信号数" :value="backtest.total_signals || 0" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="持仓记录" :value="backtest.total_positions || 0" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="事件数" :value="backtest.total_events || 0" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="平均处理" :value="parseFloat(backtest.avg_event_processing_ms || '0')" :precision="1" suffix="ms" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="峰值内存" :value="parseFloat(backtest.peak_memory_mb || '0')" :precision="1" suffix="MB" />
          </a-col>
        </a-row>
      </a-card>

      <!-- 分析器列表 -->
      <a-card title="分析器" style="margin-bottom: 16px">
        <a-spin :spinning="analyzersLoading">
          <a-table
            v-if="analyzers.length > 0"
            :columns="analyzerColumns"
            :data-source="analyzers"
            :pagination="false"
            size="small"
            row-key="name"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <a-tag color="blue">{{ record.name }}</a-tag>
              </template>
              <template v-else-if="column.key === 'latest_value'">
                <span :style="{ color: getAnalyzerValueColor(record.name, record.latest_value) }">
                  {{ formatAnalyzerValue(record.name, record.latest_value) }}
                </span>
              </template>
              <template v-else-if="column.key === 'stats' && record.stats">
                <a-tooltip>
                  <template #title>
                    <div>最小: {{ formatAnalyzerValue(record.name, record.stats.min) }}</div>
                    <div>最大: {{ formatAnalyzerValue(record.name, record.stats.max) }}</div>
                    <div>平均: {{ formatAnalyzerValue(record.name, record.stats.avg) }}</div>
                    <div>变化: {{ formatAnalyzerValue(record.name, record.stats.change) }}</div>
                  </template>
                  <span class="stats-detail">
                    {{ record.stats.count }} 条记录
                  </span>
                </a-tooltip>
              </template>
              <template v-else-if="column.key === 'trend' && record.stats">
                <a-tooltip :title="`首: ${formatAnalyzerValue(record.name, record.stats.first)} → 末: ${formatAnalyzerValue(record.name, record.stats.latest)}`">
                  <span :style="{ color: record.stats.change >= 0 ? '#52c41a' : '#f5222d' }">
                    {{ record.stats.change >= 0 ? '↑' : '↓' }} {{ formatAnalyzerValue(record.name, Math.abs(record.stats.change)) }}
                  </span>
                </a-tooltip>
              </template>
            </template>
          </a-table>
          <a-empty v-else description="暂无分析器数据（回测完成后生成）" />
        </a-spin>
      </a-card>

      <!-- 净值曲线 -->
      <a-card title="净值曲线">
        <NetValueChart v-if="netValueData.length > 0" :data="netValueData" :benchmark-data="benchmarkData" :height="350" />
        <a-empty v-else description="暂无净值数据（回测完成后生成）" />
      </a-card>

      <!-- 错误信息 -->
      <a-card v-if="backtest.error_message" title="错误信息" style="margin-top: 16px">
        <a-alert type="error" :message="backtest.error_message" show-icon />
      </a-card>

      <!-- 环境信息 -->
      <a-card v-if="environmentInfo && Object.keys(environmentInfo).length > 0" title="环境信息" style="margin-top: 16px">
        <pre class="env-info">{{ JSON.stringify(environmentInfo, null, 2) }}</pre>
      </a-card>
    </div>

    <!-- 错误状态 -->
    <a-result v-else status="404" title="回测任务不存在" sub-title="请检查任务ID是否正确">
      <template #extra>
        <a-button type="primary" @click="goBack">返回列表</a-button>
      </template>
    </a-result>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'
import { backtestApi, type BacktestTask, type AnalyzerInfo } from '@/api/modules/backtest'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const backtest = ref<BacktestTask | null>(null)
const netValueData = ref<LineData[]>([])
const benchmarkData = ref<LineData[]>([])
const analyzers = ref<AnalyzerInfo[]>([])
const analyzersLoading = ref(false)

// 分析器表格列定义
const analyzerColumns = [
  {
    title: '分析器名称',
    key: 'name',
    dataIndex: 'name',
    width: 180,
  },
  {
    title: '最新值',
    key: 'latest_value',
    dataIndex: 'latest_value',
    width: 120,
  },
  {
    title: '记录数',
    key: 'stats',
    width: 100,
  },
  {
    title: '变化趋势',
    key: 'trend',
    width: 120,
  },
]

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

// 加载回测详情
const loadBacktest = async () => {
  const uuid = route.params.id as string
  if (!uuid) {
    message.error('缺少任务ID')
    return
  }

  loading.value = true
  try {
    const data = await backtestApi.get(uuid)
    backtest.value = data

    // 加载净值数据
    try {
      const netValue = await backtestApi.getNetValue(uuid)
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
    } catch {
      // 净值数据加载失败不影响主流程
    }

    // 加载分析器列表
    loadAnalyzers(uuid)
  } catch (e: any) {
    console.error('Failed to load backtest:', e)
    message.error('加载回测详情失败')
  } finally {
    loading.value = false
  }
}

// 加载分析器列表
const loadAnalyzers = async (uuid: string) => {
  analyzersLoading.value = true
  try {
    const data = await backtestApi.getAnalyzers(uuid)
    analyzers.value = data.analyzers || []
  } catch (e) {
    console.error('Failed to load analyzers:', e)
    // 分析器加载失败不影响主流程
  } finally {
    analyzersLoading.value = false
  }
}

const goBack = () => {
  router.push('/stage1/backtest')
}

const stopBacktest = () => {
  message.info('停止回测功能待实现')
}

// 工具函数
const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    running: 'processing',
    completed: 'success',
    failed: 'error',
    stopped: 'default',
  }
  return colors[status] || 'default'
}

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    stopped: '已停止',
  }
  return labels[status] || status
}

const formatDate = (dateStr?: string) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD')
}

const formatDateTime = (dateStr?: string) => {
  if (!dateStr) return '-'
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

const formatDuration = (seconds?: number) => {
  if (!seconds) return '-'
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${seconds % 60}秒`
  return `${Math.floor(seconds / 3600)}时${Math.floor((seconds % 3600) / 60)}分`
}

const formatMoney = (value?: number) => {
  if (value === undefined || value === null) return '-'
  return `¥${value.toLocaleString()}`
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

onMounted(() => {
  loadBacktest()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 100px;
}

.env-info {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  overflow: auto;
  max-height: 200px;
}

.stats-detail {
  color: #666;
  font-size: 12px;
  cursor: pointer;
}

.stats-detail:hover {
  color: #1890ff;
}
</style>
