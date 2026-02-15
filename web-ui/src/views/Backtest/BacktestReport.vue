<template>
  <div class="backtest-report">
    <a-card :title="`回测报告 - ${backtestName || ''}`">
      <template #extra>
        <a-space>
          <a-button @click="$router.back()">返回</a-button>
          <a-button type="primary" @click="exportReport">导出报告</a-button>
        </a-space>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-card title="收益指标" size="small">
            <a-row>
              <a-col :span="12">
                <a-statistic title="总收益率" :value="summary.total_return" suffix="%" :precision="2" />
              </a-col>
              <a-col :span="12">
                <a-statistic title="年化收益率" :value="summary.annual_return" suffix="%" :precision="2" />
              </a-col>
            </a-row>
            <a-row class="mt-3">
              <a-col :span="12">
                <a-statistic title="夏普比率" :value="summary.sharpe_ratio" :precision="2" />
              </a-col>
              <a-col :span="12">
                <a-statistic title="卡玛比率" :value="summary.calmar_ratio" :precision="2" />
              </a-col>
            </a-row>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="风险指标" size="small">
            <a-row>
              <a-col :span="12">
                <a-statistic title="最大回撤" :value="summary.max_drawdown" suffix="%" :precision="2" />
              </a-col>
              <a-col :span="12">
                <a-statistic title="胜率" :value="summary.win_rate" suffix="%" :precision="2" />
              </a-col>
            </a-row>
            <a-row class="mt-3">
              <a-col :span="12">
                <a-statistic title="盈亏比" :value="summary.profit_loss_ratio" :precision="2" />
              </a-col>
              <a-col :span="12">
                <a-statistic title="最大连续亏损" :value="summary.max_consecutive_losses" />
              </a-col>
            </a-row>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-card title="交易统计" size="small">
            <a-statistic title="总交易次数" :value="summary.total_trades" />
            <a-statistic title="盈利交易" :value="summary.winning_trades" />
            <a-statistic title="亏损交易" :value="summary.losing_trades" />
            <a-statistic title="平均持仓天数" :value="summary.avg_holding_days" :precision="1" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="资金分析" size="small">
            <a-statistic title="初始资金" :value="summary.initial_capital" />
            <a-statistic title="最终权益" :value="summary.final_capital" />
            <a-statistic title="总手续费" :value="summary.total_commission" />
            <a-statistic title="总滑点成本" :value="summary.total_slippage" />
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="16">
          <a-card title="净值曲线" size="small">
            <div ref="netValueChartRef" class="chart-container" style="height: 350px"></div>
          </a-card>
        </a-col>
        <a-col :span="8">
          <a-card title="回撤曲线" size="small">
            <div ref="drawdownChartRef" class="chart-container" style="height: 250px"></div>
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-card title="交易记录" class="mb-4">
        <template #extra>
          <a-input-search v-model:value="searchText" placeholder="搜索股票代码" style="width: 200px" allow-clear />
        </template>
        <a-table
          :columns="tradeColumns"
          :data-source="filteredTrades"
          :pagination="{ pageSize: 20, showSizeChanger: true }"
          :scroll="{ y: 400 }"
          size="small"
        >
          <template #bodyCell="{ column, record }">
            <span v-if="column.dataIndex === 'pnl'" :style="{ color: record.pnl >= 0 ? '#f5222d' : '#52c41a' }">
              {{ record.pnl.toFixed(2) }}
            </span>
            <span v-else-if="column.dataIndex === 'return'" :style="{ color: record.return >= 0 ? '#f5222d' : '#52c41a' }">
              {{ (record.return * 100).toFixed(2) }}%
            </span>
          </template>
        </a-table>
      </a-card>

      <!-- Custom -->
      <a-card title="分析器数据">
        <a-table
          :columns="analyzerColumns"
          :data-source="analyzerData"
          :pagination="{ pageSize: 10 }"
          size="small"
          :default-expand-all-rows="false"
        >
          <template #expandedRowRender="{ record }">
            <div style="padding: 16px">
              <h4>{{ record.name }}</h4>
              <p>{{ record.description }}</p>
              <a-table
                :columns="['timestamp', 'value']"
                :data-source="record.data"
                :pagination="false"
                size="small"
                :scroll="{ y: 200 }"
              />
            </div>
          </template>
        </a-table>
      </a-card>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import { NetValueChart, DrawdownChart } from '@/components/charts/backtest'

const route = useRoute()
const backtestId = route.params.uuid || ''

const backtestName = ref('')
const searchText = ref('')

// 报告摘要数据
const summary = ref({
  total_return: 0,
  annual_return: 0,
  sharpe_ratio: 0,
  calmar_ratio: 0,
  max_drawdown: 0,
  win_rate: 0,
  profit_loss_ratio: 0,
  max_consecutive_losses: 0,
  total_trades: 0,
  winning_trades: 0,
  losing_trades: 0,
  avg_holding_days: 0,
  initial_capital: 0,
  final_capital: 0,
  total_commission: 0,
  total_slippage: 0
})

// 交易记录
const trades = ref<any[]>([])
const tradeColumns = [
  { title: '代码', dataIndex: 'code', width: 100, fixed: 'left' },
  { title: '名称', dataIndex: 'name', width: 120 },
  { title: '方向', dataIndex: 'direction', width: 80 },
  { title: '买入价', dataIndex: 'buy_price', width: 100 },
  { title: '卖出价', dataIndex: 'sell_price', width: 100 },
  { title: '数量', dataIndex: 'volume', width: 80 },
  { title: '买入时间', dataIndex: 'buy_time', width: 150 },
  { title: '卖出时间', dataIndex: 'sell_time', width: 150 },
  { title: '收益率%', dataIndex: 'return', width: 100 },
  { title: '盈亏', dataIndex: 'pnl', width: 100, align: 'right' },
]

const filteredTrades = computed(() => {
  if (!searchText.value) return trades.value
  return trades.value.filter(t => t.code.includes(searchText.value) || t.name.includes(searchText.value))
})

// 分析器数据
const analyzerData = ref<any[]>([])
const analyzerColumns = [
  { title: '分析器名称', dataIndex: 'name', width: 150 },
  { title: '描述', dataIndex: 'description', width: 200 },
  { title: '数据点数', dataIndex: 'data_count', width: 100 },
]

const netValueChartRef = ref<HTMLDivElement>()
const drawdownChartRef = ref<HTMLDivElement>()

// 加载回测报告数据
const loadReport = async () => {
  try {
    // TODO: 调用API获取回测报告
    // const res = await getBacktestReport(backtestId)

    // 模拟数据
    summary.value = {
      total_return: 25.6,
      annual_return: 18.3,
      sharpe_ratio: 1.25,
      calmar_ratio: 0.85,
      max_drawdown: -12.5,
      win_rate: 58.3,
      profit_loss_ratio: 1.45,
      max_consecutive_losses: 5,
      total_trades: 156,
      winning_trades: 92,
      losing_trades: 64,
      avg_holding_days: 8.5,
      initial_capital: 1000000,
      final_capital: 1256000,
      total_commission: 8900,
      total_slippage: 3500
    }

    // 模拟交易记录
    trades.value = Array.from({ length: 20 }, (_, i) => ({
      code: `00000${i + 1}.SZ`,
      name: `测试股票${i + 1}`,
      direction: i % 2 === 0 ? '买入' : '卖出',
      buy_price: 10 + Math.random() * 5,
      sell_price: 11 + Math.random() * 5,
      volume: Math.floor(Math.random() * 1000 + 100),
      buy_time: '2024-01-10 09:30:00',
      sell_time: '2024-01-18 14:00:00',
      return: Math.random() * 0.4 - 0.1,
      pnl: (Math.random() * 2000 - 800)
    }))

    // 模拟分析器数据
    analyzerData.value = [
      {
        name: '净值分析器',
        description: '记录投资组合净值变化',
        data_count: 252,
        data: Array.from({ length: 252 }, (_, i) => ({
          timestamp: `2024-01-${String(i + 1).padStart(2, '0')} 09:30:00`,
          value: 1000000 + i * 1000
        }))
      },
      {
        name: '回撤分析器',
        description: '计算最大回撤和回撤持续时间',
        data_count: 252,
        data: []
      },
      {
        name: '交易统计分析器',
        description: '统计交易次数、胜率等',
        data_count: 156,
        data: []
      }
    ]

    // 渲染图表
    renderNetValueChart()
    renderDrawdownChart()

    backtestName.value = '双均线策略回测'
    message.success('报告加载完成')
  } catch (e) {
    message.error('加载报告失败')
  }
}

// 渲染净值曲线
const renderNetValueChart = () => {
  if (!netValueChartRef.value) return

  const chart = echarts.init(netValueChartRef.value, {
    height: 350,
    width: netValueChartRef.value.clientWidth
  })

  // TODO: 使用真实数据
  const dates = Array.from({ length: 100 }, (_, i) => `2024-${String(i + 1).padStart(2, '0')}`)
  const values = Array.from({ length: 100 }, () => 1000000 + Math.random() * 50000)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '净值(元)' },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      areaStyle: { color: '#2196F3' }
    }],
    grid: { left: { show: true }, right: { show: false } }
  })
}

// 渲染回撤曲线
const renderDrawdownChart = () => {
  if (!drawdownChartRef.value) return

  const chart = echarts.init(drawdownChartRef.value, {
    height: 250,
    width: drawdownChartRef.value.clientWidth
  })

  const dates = Array.from({ length: 100 }, (_, i) => `2024-${String(i + 1).padStart(2, '0')}`)
  const values = Array.from({ length: 100 }, () => -(Math.random() * 15))

  chart.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: '回撤(%)' },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      areaStyle: { color: '#ef5350' }
    }],
    visualMap: {
      min: -20,
      max: 0,
      inRange: { color: '#52c41a' },
      outOfRange: { color: '#ef5350' }
    }
  })
}

// 导出报告
const exportReport = async () => {
  // TODO: 实现报告导出
  message.info('导出回测报告...')
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.backtest-report {
  padding: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
}
</style>
