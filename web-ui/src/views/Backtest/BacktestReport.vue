<template>
  <div class="backtest-report">
    <div class="card">
      <div class="card-header">
        <h3>回测报告 - {{ backtestName || '' }}</h3>
        <div class="header-actions">
          <button class="btn-secondary" @click="$router.back()">返回</button>
          <button class="btn-primary" @click="exportReport">导出报告</button>
        </div>
      </div>

      <div class="card-body">
        <!-- 指标卡片 -->
        <div class="metrics-grid">
          <!-- 收益指标 -->
          <div class="metric-card">
            <h4 class="metric-title">收益指标</h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <span class="stat-label">总收益率</span>
                <span class="stat-value" :class="getChangeClass(summary.total_return)">
                  {{ summary.total_return.toFixed(2) }}%
                </span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">年化收益率</span>
                <span class="stat-value" :class="getChangeClass(summary.annual_return)">
                  {{ summary.annual_return.toFixed(2) }}%
                </span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">夏普比率</span>
                <span class="stat-value">{{ summary.sharpe_ratio.toFixed(2) }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">卡玛比率</span>
                <span class="stat-value">{{ summary.calmar_ratio.toFixed(2) }}</span>
              </div>
            </div>
          </div>

          <!-- 风险指标 -->
          <div class="metric-card">
            <h4 class="metric-title">风险指标</h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <span class="stat-label">最大回撤</span>
                <span class="stat-value value-down">{{ summary.max_drawdown.toFixed(2) }}%</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">胜率</span>
                <span class="stat-value">{{ summary.win_rate.toFixed(2) }}%</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">盈亏比</span>
                <span class="stat-value">{{ summary.profit_loss_ratio.toFixed(2) }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">最大连续亏损</span>
                <span class="stat-value">{{ summary.max_consecutive_losses }}</span>
              </div>
            </div>
          </div>

          <!-- 交易统计 -->
          <div class="metric-card">
            <h4 class="metric-title">交易统计</h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <span class="stat-label">总交易次数</span>
                <span class="stat-value">{{ summary.total_trades }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">盈利交易</span>
                <span class="stat-value stat-success">{{ summary.winning_trades }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">亏损交易</span>
                <span class="stat-value stat-danger">{{ summary.losing_trades }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">平均持仓天数</span>
                <span class="stat-value">{{ summary.avg_holding_days.toFixed(1) }}</span>
              </div>
            </div>
          </div>

          <!-- 资金分析 -->
          <div class="metric-card">
            <h4 class="metric-title">资金分析</h4>
            <div class="metric-stats">
              <div class="metric-stat">
                <span class="stat-label">初始资金</span>
                <span class="stat-value">¥{{ formatNumber(summary.initial_capital) }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">最终权益</span>
                <span class="stat-value">¥{{ formatNumber(summary.final_capital) }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">总手续费</span>
                <span class="stat-value">¥{{ formatNumber(summary.total_commission) }}</span>
              </div>
              <div class="metric-stat">
                <span class="stat-label">总滑点成本</span>
                <span class="stat-value">¥{{ formatNumber(summary.total_slippage) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 图表区域 -->
        <div class="charts-grid">
          <div class="chart-card">
            <h4 class="chart-title">净值曲线</h4>
            <div ref="netValueChartRef" class="chart-container"></div>
          </div>
          <div class="chart-card chart-small">
            <h4 class="chart-title">回撤曲线</h4>
            <div ref="drawdownChartRef" class="chart-container"></div>
          </div>
        </div>

        <!-- 交易记录 -->
        <div class="table-section">
          <div class="section-header">
            <h4>交易记录</h4>
            <input v-model="searchText" type="text" placeholder="搜索股票代码" class="form-input" />
          </div>
          <div class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>方向</th>
                  <th>买入价</th>
                  <th>卖出价</th>
                  <th>数量</th>
                  <th>买入时间</th>
                  <th>卖出时间</th>
                  <th>收益率%</th>
                  <th>盈亏</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in filteredTrades" :key="record.code">
                  <td>{{ record.code }}</td>
                  <td>{{ record.name }}</td>
                  <td>{{ record.direction }}</td>
                  <td>{{ record.buy_price.toFixed(2) }}</td>
                  <td>{{ record.sell_price.toFixed(2) }}</td>
                  <td>{{ record.volume }}</td>
                  <td>{{ record.buy_time }}</td>
                  <td>{{ record.sell_time }}</td>
                  <td :class="getChangeClass(record.return)">
                    {{ (record.return * 100).toFixed(2) }}%
                  </td>
                  <td :class="getChangeClass(record.pnl)">
                    {{ record.pnl.toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 分析器数据 -->
        <div class="table-section">
          <h4>分析器数据</h4>
          <div class="table-wrapper">
            <table class="data-table expandable">
              <thead>
                <tr>
                  <th>分析器名称</th>
                  <th>描述</th>
                  <th>数据点数</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="record in analyzerData" :key="record.name">
                  <td>{{ record.name }}</td>
                  <td>{{ record.description }}</td>
                  <td>{{ record.data_count }}</td>
                  <td>
                    <button class="btn-link" @click="toggleExpand(record.name)">
                      {{ expandedAnalyzers[record.name] ? '收起' : '展开' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="expandedAnalyzers[record.name]" :key="`${record.name}-expanded`">
                  <td colspan="4" class="expanded-row">
                    <div class="expanded-content">
                      <h5>{{ record.name }}</h5>
                      <p>{{ record.description }}</p>
                      <table class="data-table data-table-small">
                        <thead>
                          <tr>
                            <th>时间戳</th>
                            <th>值</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(data, i) in record.data" :key="`data-${i}`">
                            <td>{{ data.timestamp }}</td>
                            <td>{{ data.value }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'

const route = useRoute()
const backtestId = route.params.uuid || ''

const backtestName = ref('')
const searchText = ref('')
const expandedAnalyzers = ref<Record<string, boolean>>({})

// 报告摘要数据
const summary = ref({
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
})

// 交易记录
const trades = ref<any[]>([])

const filteredTrades = computed(() => {
  if (!searchText.value) return trades.value
  return trades.value.filter(t => t.code.includes(searchText.value) || t.name.includes(searchText.value))
})

// 分析器数据
const analyzerData = ref<any[]>([])

const netValueChartRef = ref<HTMLDivElement>()
const drawdownChartRef = ref<HTMLDivElement>()

// 辅助函数
const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}

const getChangeClass = (value: number) => {
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return ''
}

const toggleExpand = (name: string) => {
  expandedAnalyzers.value[name] = !expandedAnalyzers.value[name]
}

// 加载回测报告数据
const loadReport = async () => {
  try {
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
        data: Array.from({ length: 50 }, (_, i) => ({
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
    console.log('报告加载完成')
  } catch (e) {
    console.error('加载报告失败')
  }
}

// 渲染净值曲线
const renderNetValueChart = () => {
  if (!netValueChartRef.value) return

  const chart = echarts.init(netValueChartRef.value)

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
      areaStyle: { color: '#1890ff' }
    }],
    grid: { left: 60, right: 20, top: 20, bottom: 40 }
  })
}

// 渲染回撤曲线
const renderDrawdownChart = () => {
  if (!drawdownChartRef.value) return

  const chart = echarts.init(drawdownChartRef.value)

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
      areaStyle: { color: '#f5222d' }
    }],
    visualMap: {
      min: -20,
      max: 0,
      inRange: { color: '#52c41a' },
      outOfRange: { color: '#ef5350' }
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 }
  })
}

// 导出报告
const exportReport = async () => {
  console.log('导出回测报告...')
}

onMounted(() => {
  loadReport()
})
</script>

<style scoped>
.backtest-report {
  padding: 16px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.metric-title {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.metric-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.metric-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-danger {
  color: #f5222d;
}

.charts-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.chart-card {
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.chart-small {
  grid-column: span 1;
}

.chart-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.table-section {
  margin-bottom: 24px;
}

.table-section h4 {
  margin: 0 0 16px 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
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
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table.expandable {
  border-collapse: separate;
  border-spacing: 0;
}

.expanded-row {
  padding: 0;
}

.expanded-content {
  padding: 16px;
  background: #1a1a2e;
}

.expanded-content h5 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #ffffff;
}

.expanded-content p {
  margin: 0 0 12px 0;
  font-size: 13px;
  color: #8a8a9a;
}

.data-table-small {
  margin-top: 12px;
  background: #1a1a2e;
  border-radius: 4px;
}

.data-table-small th,
.data-table-small td {
  padding: 8px;
  font-size: 12px;
}

@media (max-width: 1200px) {
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metric-stats {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .form-input {
    width: 100%;
  }

  .charts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
