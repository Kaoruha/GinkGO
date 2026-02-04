<template>
  <div class="data-management-container">
    <!-- 页面标题 -->
    <div class="page-header">
      <div>
        <h1 class="page-title">数据管理</h1>
        <p class="page-subtitle">管理股票信息、K线数据、Tick数据等市场数据</p>
      </div>
      <a-button @click="refreshStats" :loading="refreshing">
        <template #icon>
          <ReloadOutlined />
        </template>
        刷新统计
      </a-button>
    </div>

    <!-- 数据统计卡片 -->
    <a-row :gutter="16" class="stats-row">
      <a-col :span="6">
        <a-card class="stat-card stat-card-blue">
          <a-statistic
            title="股票总数"
            :value="dataStats.total_stocks"
            :value-style="{ color: '#1890ff', fontSize: '32px' }"
          >
            <template #prefix>
              <DatabaseOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-card-green">
          <a-statistic
            title="K线数据量"
            :value="dataStats.total_bars"
            :value-style="{ color: '#52c41a', fontSize: '32px' }"
          >
            <template #prefix>
              <LineChartOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-card-orange">
          <a-statistic
            title="Tick数据量"
            :value="dataStats.total_ticks"
            :value-style="{ color: '#fa8c16', fontSize: '32px' }"
          >
            <template #prefix>
              <DotChartOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card stat-card-purple">
          <a-statistic
            title="复权因子"
            :value="dataStats.total_adjust_factors"
            :value-style="{ color: '#722ed1', fontSize: '32px' }"
          >
            <template #prefix>
              <RiseOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 数据源状态 -->
    <a-card class="data-sources-card">
      <div class="flex items-center justify-between">
        <div class="flex-1">
          <div class="text-gray-500 text-sm mb-2">数据源状态</div>
          <div class="flex flex-wrap gap-2">
            <a-tag
              v-for="source in dataSources"
              :key="source.name"
              :color="source.enabled ? 'success' : 'default'"
            >
              {{ source.name }}
              <span class="ml-1 text-xs">({{ source.status }})</span>
            </a-tag>
          </div>
        </div>
      </div>
    </a-card>

    <!-- Sticky 数据浏览头部 -->
    <div class="data-browser-header" :class="{ 'is-sticky': isSticky }">
      <div class="browser-header-content">
        <!-- Tab 切换 -->
        <a-radio-group v-model:value="dataType" button-style="solid" size="large" @change="handleDataTypeChange">
          <a-radio-button value="stockinfo">
            <DatabaseOutlined class="mr-1" />
            股票信息
          </a-radio-button>
          <a-radio-button value="bars">
            <LineChartOutlined class="mr-1" />
            K线数据
          </a-radio-button>
          <a-radio-button value="ticks">
            <DotChartOutlined class="mr-1" />
            Tick数据
          </a-radio-button>
          <a-radio-button value="adjustfactors">
            <RiseOutlined class="mr-1" />
            复权因子
          </a-radio-button>
        </a-radio-group>
      </div>
    </div>

    <!-- 数据列表 -->
    <a-card class="data-table-card">
      <!-- 卡片标题：K线/Tick/复权因子使用，股票信息使用表格内标题 -->
      <template v-if="dataType !== 'stockinfo'" #title>
        <span class="text-lg font-semibold">{{ dataTypeTitle }}</span>
      </template>

      <!-- K线数据：左右分栏布局 -->
      <template v-if="dataType === 'bars'">
        <div class="bars-layout">
          <!-- 左侧：股票选择 -->
          <div class="bars-sidebar">
            <div class="sidebar-title">选择股票</div>
            <a-select
              v-model:value="selectedBarCode"
              placeholder="选择股票代码"
              :options="stockCodeOptions"
              show-search
              :filter-option="filterStockOption"
              size="large"
              @change="handleBarCodeChange"
              style="width: 100%"
            />

            <a-divider class="my-4" />

            <div class="sidebar-info">
              <div class="text-sm text-gray-500 mb-2">已加载 {{ barDataPoints }} 条数据</div>
              <div v-if="barDateRange" class="text-xs text-gray-400">
                {{ barDateRange }}
              </div>
            </div>
          </div>

          <!-- 右侧：K线图表 -->
          <div class="bars-chart">
            <div v-if="!selectedBarCode" class="chart-placeholder">
              <a-empty description="请选择股票代码查看K线图表" />
            </div>
            <div v-else ref="barChartRef" class="chart-container" @mouseleave="hideTooltip"></div>
          </div>
        </div>
      </template>

      <!-- Tick数据：左右分栏布局 -->
      <template v-else-if="dataType === 'ticks'">
        <div class="bars-layout">
          <!-- 左侧：股票选择 -->
          <div class="bars-sidebar">
            <div class="sidebar-title">选择股票</div>
            <a-select
              v-model:value="selectedTickCode"
              placeholder="选择股票代码"
              :options="stockCodeOptions"
              show-search
              :filter-option="filterStockOption"
              size="large"
              @change="handleTickCodeChange"
              style="width: 100%"
            />
          </div>

          <!-- 右侧：Tick数据图表 -->
          <div class="bars-chart">
            <div v-if="!selectedTickCode" class="chart-placeholder">
              <DotChartOutlined style="font-size: 48px; color: #ccc;" />
              <p class="text-gray-400">请选择股票查看Tick数据</p>
            </div>
            <div v-else>
              <!-- 时间范围快速选择 -->
              <div class="tick-time-range">
                <span class="range-label">显示范围：</span>
                <a-radio-group v-model:value="tickTimeRange" size="small" @change="handleTickTimeRangeChange">
                  <a-radio-button value="last100">最近100笔</a-radio-button>
                  <a-radio-button value="last500">最近500笔</a-radio-button>
                  <a-radio-button value="last1000">最近1000笔</a-radio-button>
                  <a-radio-button value="all">全部</a-radio-button>
                </a-radio-group>
                <span class="tick-info">共 {{ tickDataCount }} 笔</span>
              </div>
              <div ref="tickChartRef" class="chart-container" style="height: calc(100% - 40px); min-height: 400px;"></div>
            </div>
          </div>
        </div>
      </template>

      <!-- 其他数据类型：表格展示 -->
      <template v-else>
        <!-- 表格容器 -->
        <div class="table-container">
          <a-table
            :columns="currentColumns"
            :data-source="currentItems"
            :loading="loading"
            :pagination="false"
            row-key="uuid"
            :scroll="{ x: 1500 }"
          >
            <!-- 表格标题插槽：添加搜索框 -->
            <template #title>
              <div class="table-header-with-search">
                <span class="text-lg font-semibold">{{ dataTypeTitle }}</span>
                <!-- 股票信息表格内嵌搜索 -->
                <a-input-search
                  v-if="dataType === 'stockinfo'"
                  v-model:value="searchText"
                  placeholder="搜索股票代码或名称"
                  style="width: 260px"
                  @search="loadData"
                  allow-clear
                  size="small"
                />
              </div>
            </template>
          <template #bodyCell="{ column, record }">
            <!-- 股票信息 -->
            <template v-if="dataType === 'stockinfo'">
              <template v-if="column.key === 'code'">
                <a-tag color="blue">{{ record.code }}</a-tag>
              </template>
              <template v-if="column.key === 'name'">
                <span :class="record.is_active ? '' : 'text-gray-400'">
                  {{ record.name || '-' }}
                </span>
              </template>
              <template v-if="column.key === 'market'">
                <a-tag v-if="record.market">{{ record.market }}</a-tag>
                <span v-else class="text-gray-400">-</span>
              </template>
              <template v-if="column.key === 'updated_at'">
                <span class="text-sm text-gray-500">
                  {{ record.updated_at ? formatDate(record.updated_at) : '-' }}
                </span>
              </template>
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'success' : 'default'">
                  {{ record.is_active ? '正常' : '停牌' }}
                </a-tag>
              </template>
            </template>

            <!-- K线数据 -->
            <template v-if="dataType === 'bars'">
              <template v-if="column.key === 'code'">
                <a-tag color="blue">{{ record.code }}</a-tag>
              </template>
              <template v-if="column.key === 'close'">
                <span :class="getPriceClass(record.open, record.close)">
                  {{ record.close?.toFixed(2) }}
                </span>
              </template>
              <template v-if="column.key === 'change'">
                <span :class="getChangeClass(record.open, record.close)">
                  {{ getChangePercent(record.open, record.close) }}%
                </span>
              </template>
            </template>

            <!-- Tick数据 -->
            <template v-if="dataType === 'ticks'">
              <template v-if="column.key === 'code'">
                <a-tag color="blue">{{ record.code }}</a-tag>
              </template>
              <template v-if="column.key === 'direction'">
                <a-tag :color="getDirectionColor(record.direction)">
                  {{ getDirectionLabel(record.direction) }}
                </a-tag>
              </template>
            </template>

            <!-- 复权因子 -->
            <template v-if="dataType === 'adjustfactors'">
              <template v-if="column.key === 'code'">
                <a-tag color="blue">{{ record.code }}</a-tag>
              </template>
              <template v-if="column.key === 'factor'">
                <span class="font-mono">{{ record.factor?.toFixed(6) }}</span>
              </template>
            </template>
          </template>
        </a-table>
      </div>

      <!-- 固定在底部的翻页器（仅非K线模式） -->
      <div v-if="dataType !== 'bars'" class="table-pagination">
        <a-pagination
          v-model:current="pagination.current"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :show-size-changer="true"
          :show-quick-jumper="true"
          :show-total="(total: number) => `共 ${total} 条记录`"
          :page-size-options="['10', '20', '50', '100', '200']"
          @change="handleTableChange"
        />
      </div>
      </template>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  DatabaseOutlined,
  LineChartOutlined,
  DotChartOutlined,
  RiseOutlined,
  SyncOutlined,
  ReloadOutlined,
  SearchOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import {
  dataApi,
  type DataStats,
  type StockInfoSummary,
  type BarDataSummary,
  type TickDataSummary,
  type AdjustFactorSummary,
  type DataSource
} from '@/api/modules/components'
import { createChart, IChartApi, Time, CandlestickSeries, HistogramSeries, LineSeries, ColorType } from 'lightweight-charts'
import * as echarts from 'echarts'

const router = useRouter()

// Sticky 状态
const isSticky = ref(false)

// 数据类型
const dataType = ref('stockinfo')
const dataTypeTitle = computed(() => {
  const titles: Record<string, string> = {
    stockinfo: '股票信息',
    bars: 'K线数据',
    ticks: 'Tick数据',
    adjustfactors: '复权因子'
  }
  return titles[dataType.value] || '数据列表'
})

// 数据统计
const dataStats = reactive<DataStats>({
  total_stocks: 0,
  total_bars: 0,
  total_ticks: 0,
  total_adjust_factors: 0,
  tick_data_summary: undefined,
  data_sources: [],
  latest_update: undefined
})

const dataSources = ref<DataSource[]>([])
const refreshing = ref(false)

// 通用数据状态
const loading = ref(false)
const searchText = ref('')
const filterCode = ref('')
const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0
})

// 股票信息数据
const stockItems = ref<StockInfoSummary[]>([])
const stockColumns = [
  { title: '代码', dataIndex: 'code', key: 'code', width: 120, fixed: 'left' },
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '市场', dataIndex: 'market', key: 'market', width: 100 },
  { title: '行业', dataIndex: 'industry', key: 'industry', ellipsis: true },
  { title: '更新时间', key: 'updated_at', width: 140 },
  { title: '状态', key: 'is_active', width: 80 }
]

// K线数据
const barItems = ref<BarDataSummary[]>([])

// K线图表状态
const selectedBarCode = ref<string>('')
const barChartRef = ref<HTMLDivElement>()
const chartInstance = ref<IChartApi | null>(null)
const candleSeriesRef = ref<any>(null)
const volumeSeriesRef = ref<any>(null)
const barDataPoints = ref(0)
const barDateRange = ref('')
const loadingBarChart = ref(false)

// Tick图表状态
const selectedTickCode = ref<string>('')
const tickChartRef = ref<HTMLDivElement>()
const tickChartInstance = ref<echarts.ECharts | null>(null)
const tickTimeRange = ref<string>('last1000')
const tickDataCount = ref<number>(0)
const tickAllData = ref<TickDataSummary[]>([])
const loadedTickRange = ref<{ min: number; max: number } | null>(null)  // 已加载的Tick时间范围
const isLoadingMoreTick = ref<boolean>(false)  // 是否正在加载更多Tick数据
let tickLoadMoreTimer: any = null  // 防抖定时器
const barColumns = [
  { title: '代码', dataIndex: 'code', key: 'code', width: 120, fixed: 'left' },
  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
  { title: '开盘', dataIndex: 'open', key: 'open', width: 100 },
  { title: '最高', dataIndex: 'high', key: 'high', width: 100 },
  { title: '最低', dataIndex: 'low', key: 'low', width: 100 },
  { title: '收盘', dataIndex: 'close', key: 'close', width: 100 },
  { title: '成交量', dataIndex: 'volume', key: 'volume', width: 120 },
  { title: '涨跌幅', key: 'change', width: 100 }
]

// Tick数据
const tickItems = ref<TickDataSummary[]>([])
const tickColumns = [
  { title: '代码', dataIndex: 'code', key: 'code', width: 120, fixed: 'left' },
  { title: '时间', dataIndex: 'timestamp', key: 'timestamp', width: 180 },
  { title: '价格', dataIndex: 'price', key: 'price', width: 100 },
  { title: '成交量', dataIndex: 'volume', key: 'volume', width: 100 },
  { title: '方向', key: 'direction', width: 80 }
]

// 复权因子数据
const adjustFactorItems = ref<AdjustFactorSummary[]>([])
const adjustFactorColumns = [
  { title: '代码', dataIndex: 'code', key: 'code', width: 120, fixed: 'left' },
  { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
  { title: '因子', key: 'factor', width: 150 }
]

// 当前表格列和数据
const currentColumns = computed(() => {
  switch (dataType.value) {
    case 'stockinfo': return stockColumns
    case 'bars': return barColumns
    case 'ticks': return tickColumns
    case 'adjustfactors': return adjustFactorColumns
    default: return []
  }
})

const currentItems = computed(() => {
  switch (dataType.value) {
    case 'stockinfo': return stockItems.value
    case 'bars': return barItems.value
    case 'ticks': return tickItems.value
    case 'adjustfactors': return adjustFactorItems.value
    default: return []
  }
})

// 股票代码选项
const stockCodeOptions = ref<{ value: string; label: string }[]>([])

// 过滤股票选项
const filterStockOption = (input: string, option: any) => {
  const label = option.label as string
  return label.toLowerCase().includes(input.toLowerCase())
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

// 格式化数字（添加千分位）
const formatNumber = (num: number) => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(2) + '亿'
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(2) + '万'
  }
  return num.toLocaleString()
}

// 价格涨跌颜色
const getPriceClass = (open: number, close: number) => {
  if (close > open) return 'text-red-600'
  if (close < open) return 'text-green-600'
  return ''
}

const getChangeClass = (open: number, close: number) => {
  return getPriceClass(open, close)
}

const getChangePercent = (open: number, close: number) => {
  if (!open || !close) return '0.00'
  return ((close - open) / open * 100).toFixed(2)
}

// Tick方向颜色和标签
const getDirectionColor = (direction: number) => {
  if (direction === 1) return 'red'
  if (direction === -1) return 'green'
  return 'default'
}

const getDirectionLabel = (direction: number) => {
  if (direction === 1) return '买'
  if (direction === -1) return '卖'
  return '平'
}

// Sticky 滚动处理
const handleScroll = () => {
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  isSticky.value = scrollTop > 200
}

// 刷新统计数据
const refreshStats = async () => {
  refreshing.value = true
  try {
    const [stats, sources] = await Promise.all([
      dataApi.getStats(),
      dataApi.getDataSources()
    ])

    Object.assign(dataStats, stats)
    dataSources.value = sources

    message.success('统计数据已刷新')
  } catch (error: any) {
    message.error('刷新统计数据失败')
  } finally {
    refreshing.value = false
  }
}

// 数据类型切换
const handleDataTypeChange = async () => {
  pagination.current = 1
  searchText.value = ''
  filterCode.value = ''

  // 如果切换到K线数据，自动选中第一个股票
  if (dataType.value === 'bars') {
    // 如果股票代码选项为空，先加载股票信息
    if (stockCodeOptions.value.length === 0) {
      try {
        const response = await dataApi.getStockInfo({
          page: 1,
          page_size: 50
        })
        stockCodeOptions.value = response.items.map(stock => ({
          value: stock.code,
          label: `${stock.code} - ${stock.name || '未知名称'}`
        }))
      } catch (error) {
        console.error('Failed to load stock info:', error)
      }
    }

    // 自动选择第一个股票代码
    if (stockCodeOptions.value.length > 0 && !selectedBarCode.value) {
      const firstCode = stockCodeOptions.value[0].value
      selectedBarCode.value = firstCode
      loadBarChart(firstCode)
    }
  }

  loadData()
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    if (dataType.value === 'stockinfo') {
      const response = await dataApi.getStockInfo({
        search: searchText.value || undefined,
        page: pagination.current,
        page_size: pagination.pageSize
      })
      stockItems.value = response.items
      pagination.total = response.total

      // 更新股票代码选项
      stockCodeOptions.value = response.items.map(stock => ({
        value: stock.code,
        label: `${stock.code} - ${stock.name || '未知名称'}`
      }))
    } else if (dataType.value === 'bars') {
      const response = await dataApi.getBars({
        code: filterCode.value || undefined,
        page: pagination.current,
        page_size: pagination.pageSize
      })
      barItems.value = response.items
      pagination.total = response.total
    } else if (dataType.value === 'ticks') {
      // Tick数据不需要自动加载表格，需要用户先选择股票查看图表
      tickItems.value = []
      pagination.total = 0
    } else if (dataType.value === 'adjustfactors') {
      const response = await dataApi.getAdjustFactors({
        code: filterCode.value || undefined,
        page: pagination.current,
        page_size: pagination.pageSize
      })
      adjustFactorItems.value = response.items
      pagination.total = response.total
    }
  } catch (error: any) {
    message.error(`加载数据失败: ${error?.response?.data?.detail || error?.message}`)
  } finally {
    loading.value = false
  }
}

// 表格分页变化
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadData()
}

// K线图表相关方法
const handleBarCodeChange = (code: string) => {
  selectedBarCode.value = code
  if (code) {
    // 切换股票时清空缓存
    loadedBarsData.value = []
    loadedTimeRange.value = null
    loadBarChart(code)
  } else {
    destroyChart()
    loadedBarsData.value = []
    loadedTimeRange.value = null
    barDataPoints.value = 0
    barDateRange.value = ''
  }
}

// Tick图表相关方法
const handleTickCodeChange = (code: string) => {
  selectedTickCode.value = code
  if (code) {
    loadTickChart(code)
  }
}

// 加载Tick图表数据
const loadTickChart = async (code: string) => {
  try {
    const endDate = dayjs().format('YYYY-MM-DD')
    const startDate = dayjs().subtract(7, 'day').format('YYYY-MM-DD')

    const response = await dataApi.getTicks({
      code,
      start_date: startDate,
      end_date: endDate,
      page: 1,
      page_size: 10000
    })

    if (response.items.length > 0) {
      // 存储完整数据
      tickAllData.value = response.items
      tickDataCount.value = response.items.length

      // 记录已加载的时间范围
      const timestamps = response.items.map(t => new Date(t.timestamp).getTime())
      loadedTickRange.value = {
        min: Math.min(...timestamps),
        max: Math.max(...timestamps)
      }

      // 等待DOM更新后再初始化图表
      await nextTick()
      initTickChart(getTickDataByRange())
    } else {
      tickAllData.value = []
      tickDataCount.value = 0
      loadedTickRange.value = null
      message.info(`股票 ${code} 暂无Tick数据`)
    }
  } catch (error: any) {
    message.error(`加载Tick数据失败: ${error.message || '未知错误'}`)
  }
}

// 根据时间范围获取数据
const getTickDataByRange = () => {
  const allData = tickAllData.value
  const range = tickTimeRange.value

  if (range === 'all') {
    return allData
  }

  const count = parseInt(range.replace('last', ''), 10)
  return allData.slice(-count)
}

// 处理时间范围变化
const handleTickTimeRangeChange = () => {
  if (tickAllData.value.length > 0) {
    initTickChart(getTickDataByRange())
  }
}

// 初始化Tick图表
const initTickChart = (ticks: TickDataSummary[]) => {
  console.log('initTickChart called with ticks:', ticks.length)

  if (!tickChartRef.value) {
    console.error('tickChartRef.value is null')
    return
  }

  // 检查容器尺寸
  const rect = tickChartRef.value.getBoundingClientRect()
  console.log('Chart container size:', rect.width, 'x', rect.height)

  if (rect.width === 0 || rect.height === 0) {
    console.error('Chart container has zero size, waiting for nextTick...')
    // 容器尺寸为0，等待DOM渲染完成
    setTimeout(() => {
      if (tickChartRef.value) {
        const newRect = tickChartRef.value.getBoundingClientRect()
        console.log('Retry chart container size:', newRect.width, 'x', newRect.height)
        if (newRect.width > 0 && newRect.height > 0) {
          initTickChart(ticks)
        }
      }
    }, 100)
    return
  }

  if (ticks.length === 0) {
    console.warn('No tick data to display')
    return
  }

  // 按时间戳排序
  const sortedTicks = [...ticks].sort((a, b) =>
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )

  console.log('Sorted ticks, first:', sortedTicks[0], 'last:', sortedTicks[sortedTicks.length - 1])

  // 计算成交量的范围，用于点的大小映射
  const volumes = sortedTicks.map(t => t.volume)
  const minVolume = Math.min(...volumes)
  const maxVolume = Math.max(...volumes)
  const volumeRange = maxVolume - minVolume || 1

  // 准备散点图数据
  // 买入数据 (direction=1)
  const buyData = sortedTicks
    .filter(t => t.direction === 1)
    .map(tick => {
      const timestamp = new Date(tick.timestamp).getTime()
      return {
        name: dayjs(tick.timestamp).format('HH:mm:ss'),
        value: [timestamp, tick.price, tick.volume],
        timestamp: tick.timestamp,
        direction: '买入'
      }
    })

  // 卖出数据 (direction=2)
  const sellData = sortedTicks
    .filter(t => t.direction === 2)
    .map(tick => {
      const timestamp = new Date(tick.timestamp).getTime()
      return {
        name: dayjs(tick.timestamp).format('HH:mm:ss'),
        value: [timestamp, tick.price, tick.volume],
        timestamp: tick.timestamp,
        direction: '卖出'
      }
    })

  console.log('Buy ticks:', buyData.length, 'Sell ticks:', sellData.length)

  // 销毁旧图表
  if (tickChartInstance.value) {
    tickChartInstance.value.dispose()
    tickChartInstance.value = null
  }

  // 创建ECharts实例
  tickChartInstance.value = echarts.init(tickChartRef.value)

  // 获取价格范围用于Y轴
  const prices = sortedTicks.map(t => t.price)
  const minPrice = Math.min(...prices)
  const maxPrice = Math.max(...prices)
  const priceMargin = (maxPrice - minPrice) * 0.1

  const option = {
    title: {
      text: `${selectedTickCode.value} - Tick逐笔成交`,
      left: 'center',
      textStyle: { fontSize: 14, color: '#333' }
    },
    tooltip: {
      trigger: 'item',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#ddd',
      borderWidth: 1,
      textStyle: { color: '#333' },
      formatter: (params: any) => {
        if (!params.data) return ''
        const tick = params.data
        const timeStr = dayjs(tick.timestamp).format('YYYY-MM-DD HH:mm:ss')
        const dirColor = tick.direction === '买入' ? '#ef5350' : '#26a69a'
        return `
          <div style="font-weight:600; margin-bottom:6px; color:${dirColor}">${tick.direction}</div>
          <div style="margin-bottom:3px;"><span style="color:#999">代码:</span> ${selectedTickCode.value}</div>
          <div style="margin-bottom:3px;"><span style="color:#999">时间:</span> ${timeStr}</div>
          <div style="margin-bottom:3px;"><span style="color:#999">价格:</span> <strong>${tick.value[1].toFixed(2)}</strong></div>
          <div><span style="color:#999">成交量:</span> ${tick.value[2]}</div>
        `
      }
    },
    grid: {
      left: '8%',
      right: '4%',
      top: '12%',
      bottom: '18%'
    },
    xAxis: {
      type: 'time',
      scale: true,
      axisLabel: {
        formatter: (value: number) => dayjs(value).format('HH:mm:ss'),
        color: '#666'
      },
      axisLine: {
        lineStyle: { color: '#ddd' }
      }
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: {
        formatter: (value: number) => value.toFixed(2),
        color: '#666'
      },
      splitLine: {
        lineStyle: {
          color: '#f0f0f0',
          type: 'dashed'
        }
      },
      min: minPrice - priceMargin,
      max: maxPrice + priceMargin
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        minSpan: 1,
        maxSpan: 100,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
        preventDefaultMouseMove: false
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        minSpan: 1,
        maxSpan: 100,
        height: 30,
        bottom: 5,
        borderColor: '#e0e0e0',
        fillerColor: 'rgba(33, 150, 243, 0.15)',
        handleStyle: {
          color: '#2196f3',
          borderColor: '#2196f3'
        },
        textStyle: {
          color: '#999',
          fontSize: 11
        },
        brushSelect: true
      }
    ],
    series: [
      {
        name: '买入',
        type: 'scatter',
        data: buyData,
        symbolSize: (data: number[]) => {
          // 根据成交量映射点的大小 (8-32)
          const volume = data[2]
          const normalized = (volume - minVolume) / volumeRange
          return 8 + normalized * 24
        },
        itemStyle: {
          color: '#ef5350',
          opacity: 0.85,
          borderColor: '#d32f2f',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            color: '#ef5350',
            opacity: 1,
            borderColor: '#d32f2f',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(239, 83, 80, 0.5)'
          }
        },
        large: false,
        progressive: 200
      },
      {
        name: '卖出',
        type: 'scatter',
        data: sellData,
        symbolSize: (data: number[]) => {
          // 根据成交量映射点的大小 (8-32)
          const volume = data[2]
          const normalized = (volume - minVolume) / volumeRange
          return 8 + normalized * 24
        },
        itemStyle: {
          color: '#26a69a',
          opacity: 0.85,
          borderColor: '#00796b',
          borderWidth: 1
        },
        emphasis: {
          itemStyle: {
            color: '#26a69a',
            opacity: 1,
            borderColor: '#00796b',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(38, 166, 154, 0.5)'
          }
        },
        large: false,
        progressive: 200
      }
    ]
  }

  tickChartInstance.value.setOption(option)

  // 响应式处理
  const handleResize = () => {
    if (tickChartInstance.value) {
      tickChartInstance.value.resize()
    }
  }

  window.addEventListener('resize', handleResize)

  // 保存清理函数
  ;(tickChartRef.value as any)._chartCleanup = () => {
    window.removeEventListener('resize', handleResize)
    if (tickChartInstance.value) {
      tickChartInstance.value.dispose()
      tickChartInstance.value = null
    }
  }

  console.log('Tick chart created successfully')

  // 监听dataZoom事件，实现无限滚动加载
  tickChartInstance.value.on('dataZoom', (params: any) => {
    checkAndLoadMoreTickData()
  })
}

// 检查并加载更多Tick数据
const checkAndLoadMoreTickData = () => {
  if (!tickChartInstance.value || !loadedTickRange.value) return

  if (tickLoadMoreTimer) {
    clearTimeout(tickLoadMoreTimer)
  }

  tickLoadMoreTimer = setTimeout(async () => {
    if (isLoadingMoreTick.value) return

    // 获取当前显示的数据范围
    const option = tickChartInstance.value.getOption()
    const xAxis = option.xAxis[0] as any

    if (!xAxis || !xAxis.rangeStart || !xAxis.rangeEnd) return

    // rangeStart和rangeEnd是百分比（0-100），需要转换为实际时间范围
    const allData = tickAllData.value
    if (allData.length === 0) return

    const timestamps = allData.map(t => new Date(t.timestamp).getTime())
    const minTime = Math.min(...timestamps)
    const maxTime = Math.max(...timestamps)
    const timeSpan = maxTime - minTime

    // 计算当前可见范围的时间
    const visibleStart = minTime + timeSpan * (xAxis.rangeStart / 100)
    const visibleEnd = minTime + timeSpan * (xAxis.rangeEnd / 100)

    // 检查是否接近边界（10%缓冲）
    const buffer = timeSpan * 0.1
    const needLoadOlder = visibleStart < (loadedTickRange.value.min + buffer)
    const needLoadNewer = visibleEnd > (loadedTickRange.value.max - buffer)

    if (needLoadOlder || needLoadNewer) {
      await loadMoreTickData(needLoadOlder, needLoadNewer)
    }

    tickLoadMoreTimer = null
  }, 100)
}

// 加载更多Tick数据
const loadMoreTickData = async (loadOlder: boolean, loadNewer: boolean) => {
  if (isLoadingMoreTick.value || !selectedTickCode.value) return

  isLoadingMoreTick.value = true

  try {
    if (loadOlder) {
      // 加载更早的数据
      const oldestTimestamp = loadedTickRange.value.min
      const endDate = dayjs(oldestTimestamp).format('YYYY-MM-DD')
      const startDate = dayjs(endDate).subtract(7, 'day').format('YYYY-MM-DD')

      const response = await dataApi.getTicks({
        code: selectedTickCode.value,
        start_date: startDate,
        end_date: endDate,
        page: 1,
        page_size: 10000
      })

      if (response.items.length > 0) {
        // 合并数据，去重
        const existingTimestamps = new Set(tickAllData.value.map(t => t.timestamp))
        const newItems = response.items.filter(t => !existingTimestamps.has(t.timestamp))

        tickAllData.value = [...newItems, ...tickAllData.value]
        tickDataCount.value = tickAllData.value.length

        // 更新已加载范围
        const newTimestamps = newItems.map(t => new Date(t.timestamp).getTime())
        loadedTickRange.value.min = Math.min(loadedTickRange.value.min, ...newTimestamps)

        // 更新图表
        await nextTick()
        initTickChart(getTickDataByRange())
      }
    }

    if (loadNewer) {
      // 加载更新的数据
      const newestTimestamp = loadedTickRange.value.max
      const startDate = dayjs(newestTimestamp).add(1, 'day').format('YYYY-MM-DD')
      const endDate = dayjs().format('YYYY-MM-DD')

      if (startDate <= endDate) {
        const response = await dataApi.getTicks({
          code: selectedTickCode.value,
          start_date: startDate,
          end_date: endDate,
          page: 1,
          page_size: 10000
        })

        if (response.items.length > 0) {
          // 合并数据，去重
          const existingTimestamps = new Set(tickAllData.value.map(t => t.timestamp))
          const newItems = response.items.filter(t => !existingTimestamps.has(t.timestamp))

          tickAllData.value = [...tickAllData.value, ...newItems]
          tickDataCount.value = tickAllData.value.length

          // 更新已加载范围
          const newTimestamps = newItems.map(t => new Date(t.timestamp).getTime())
          loadedTickRange.value.max = Math.max(loadedTickRange.value.max, ...newTimestamps)

          // 更新图表
          await nextTick()
          initTickChart(getTickDataByRange())
        }
      }
    }
  } catch (error: any) {
    console.error('加载更多Tick数据失败:', error)
  } finally {
    isLoadingMoreTick.value = false
  }
}

// 已加载的数据缓存
const loadedBarsData = ref<BarDataSummary[]>([])
const currentBarCode = ref<string>('')
const isLoadingMore = ref(false)
const loadedTimeRange = ref<{ min: number; max: number } | null>(null)
let loadMoreTimer: ReturnType<typeof setTimeout> | null = null

const loadBarChart = async (code: string, initial: boolean = true) => {
  if (isLoadingMore.value) return

  loadingBarChart.value = true
  currentBarCode.value = code

  try {
    // 优化加载策略：使用更合理的历史数据范围
    // 由于数据可能不是实时的，使用较长的历史范围确保能获取到数据
    const endDate = dayjs().format('YYYY-MM-DD')
    const startDate = initial
      ? dayjs().subtract(2, 'year').format('YYYY-MM-DD')  // 初始加载2年数据
      : dayjs().subtract(5, 'year').format('YYYY-MM-DD')    // 延迟加载5年数据

    console.log('Loading bar data:', code, 'from', startDate, 'to', endDate, 'initial:', initial)

    const response = await dataApi.getBars({
      code,
      start_date: startDate,
      end_date: endDate,
      page: 1,
      page_size: 2000  // 减少单次加载量，提高响应速度
    })

    console.log('Loaded', response.items.length, 'bars')

    if (response.items.length > 0) {
      // 合并数据（去重）
      const newItems = response.items.filter(
        item => !loadedBarsData.value.some(existing => existing.date === item.date)
      )
      loadedBarsData.value = [...loadedBarsData.value, ...newItems]

      // 按日期排序
      const sortedData = [...loadedBarsData.value].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )

      // 更新已加载时间范围
      const timestamps = sortedData.map(d => dayjs(d.date).unix() * 1000)
      loadedTimeRange.value = {
        min: Math.min(...timestamps),
        max: Math.max(...timestamps)
      }

      barDataPoints.value = sortedData.length

      // 计算日期范围
      const dates = sortedData.map(item => item.date).filter(Boolean)
      if (dates.length > 0) {
        barDateRange.value = `${dates[0]} ~ ${dates[dates.length - 1]}`
      }

      if (initial) {
        await nextTick()
        initChart(sortedData)
      }
    } else {
      if (initial) {
        // 如果初始查询没有数据，尝试扩大时间范围（可能是数据较旧）
        console.log('No data in initial range, trying extended range...')
        try {
          const extendedStartDate = dayjs().subtract(10, 'year').format('YYYY-MM-DD')
          const extendedResponse = await dataApi.getBars({
            code,
            start_date: extendedStartDate,
            end_date: endDate,
            page: 1,
            page_size: 2000
          })

          if (extendedResponse.items.length > 0) {
            // 使用扩展范围的数据
            loadedBarsData.value = extendedResponse.items
            const sortedData = [...extendedResponse.items].sort((a, b) =>
              new Date(a.date).getTime() - new Date(b.date).getTime()
            )

            const timestamps = sortedData.map(d => dayjs(d.date).unix() * 1000)
            loadedTimeRange.value = {
              min: Math.min(...timestamps),
              max: Math.max(...timestamps)
            }

            barDataPoints.value = sortedData.length

            const dates = sortedData.map(item => item.date).filter(Boolean)
            if (dates.length > 0) {
              barDateRange.value = `${dates[0]} ~ ${dates[dates.length - 1]}`
            }

            await nextTick()
            initChart(sortedData)
          } else {
            message.warning(`股票 ${code} 没有K线数据`)
            destroyChart()
          }
        } catch (retryError) {
          message.warning(`股票 ${code} 没有K线数据`)
          destroyChart()
        }
      }
    }
  } catch (error: any) {
    message.error(`加载K线数据失败: ${error.message || '未知错误'}`)
    if (initial) destroyChart()
  } finally {
    loadingBarChart.value = false
    isLoadingMore.value = false
  }
}

const initChart = (bars: BarDataSummary[]) => {
  if (!barChartRef.value) {
    console.error('Chart ref not available')
    return
  }

  // 销毁旧图表实例，但不清理数据缓存
  if (chartInstance.value) {
    chartInstance.value.remove()
    chartInstance.value = null
  }
  candleSeriesRef.value = null
  volumeSeriesRef.value = null

  // 按日期排序
  const sortedBars = [...bars].sort((a, b) =>
    new Date(a.date).getTime() - new Date(b.date).getTime()
  )

  // 准备K线数据
  const candlestickData = sortedBars.map(bar => {
    const timestamp = dayjs(bar.date).unix()
    if (isNaN(timestamp)) {
      console.error('Invalid date:', bar.date)
    }
    return {
      time: timestamp,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close
    }
  }).filter(item => !isNaN(item.time))

  // 准备成交量数据（根据涨跌设置颜色）
  const volumeData = sortedBars.map(bar => {
    const timestamp = dayjs(bar.date).unix()
    const isUp = bar.close >= bar.open
    return {
      time: timestamp,
      value: bar.volume,
      color: isUp ? '#26a69a' : '#ef5350'  // 涨绿跌红
    }
  }).filter(item => !isNaN(item.time))

  if (candlestickData.length === 0) {
    console.error('No valid data points after filtering')
    return
  }

  try {
    // 创建图表
    chartInstance.value = createChart(barChartRef.value, {
      width: barChartRef.value.clientWidth,
      height: barChartRef.value.clientHeight,
      layout: {
        background: {
          type: 'solid',
          color: '#fafafa',
        },
        textColor: '#333333',
      },
      grid: {
        vertLines: { color: 'rgba(197, 203, 229, 0.1)' },
        horzLines: { color: 'rgba(197, 203, 229, 0.1)' },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        axisWheelPress: true,
        mouseWheel: true,
        pinch: true,
      },
      timeScale: {
        borderColor: 'rgba(197, 203, 229, 0.2)',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 0,
        fixRightEdge: true,
        fixLeftEdge: false,
        minBarSpacing: 0.5,
        maxBarSpacing: 50,
        // 数据压缩配置 - 大数据集性能优化 (v5.1.0+)
        enableConflation: true,              // 启用数据压缩
        conflationThresholdFactor: 2.0,     // 压缩阈值因子，值越大压缩越积极
        precomputeConflationOnInit: false,   // 初始化时是否预计算（false=首次缩放时计算）
      },
      rightPriceScale: {
        borderVisible: true,
        borderColor: 'rgba(197, 203, 229, 0.2)',
      },
      leftPriceScale: {
        visible: true,
        borderVisible: true,
        borderColor: 'rgba(197, 203, 229, 0.2)',
      },
      crosshair: {
        mode: 0,
        vertLine: {
          color: '#758696',
          width: 1,
          style: 3,
          labelBackgroundColor: '#4c525e',
          labelColor: '#ffffff',
        },
        horzLine: {
          color: '#758696',
          width: 1,
          style: 3,
          labelBackgroundColor: '#4c525e',
          labelColor: '#ffffff',
        },
      },
    })

    // 添加K线系列 - 使用独立的价格刻度
    candleSeriesRef.value = chartInstance.value.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceScaleId: 'candlestick',
    })

    candleSeriesRef.value.setData(candlestickData)

    // 配置K线价格刻度位置（顶部）
    const candlestickPriceScale = chartInstance.value.priceScale('candlestick')
    if (candlestickPriceScale) {
      candlestickPriceScale.applyOptions({
        scaleMargins: {
          top: 0.05,
          bottom: 0.35,  // K线占用顶部5%-65%（60%空间）
        },
      })
    }

    // 添加成交量系列 - 使用独立的价格刻度
    volumeSeriesRef.value = chartInstance.value.addSeries(HistogramSeries, {
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
      color: '#26a69a',
    })

    volumeSeriesRef.value.setData(volumeData)

    // 配置成交量价格刻度位置（底部）
    const volumePriceScale = chartInstance.value.priceScale('volume')
    if (volumePriceScale) {
      volumePriceScale.applyOptions({
        scaleMargins: {
          top: 0.7,    // 成交量占用底部30%（70%-100%）
          bottom: 0.05,
        },
        borderVisible: false,
      })
    }

    // 滚动到最新数据位置（右侧对齐）
    chartInstance.value.timeScale().scrollToPosition(0, false)

    // 创建 tooltip 元素
    const tooltip = document.createElement('div')
    tooltip.className = 'chart-tooltip'
    tooltip.style.position = 'absolute'
    tooltip.style.display = 'none'
    tooltip.style.background = 'rgba(0, 0, 0, 0.8)'
    tooltip.style.color = '#ffffff'
    tooltip.style.padding = '8px 12px'
    tooltip.style.borderRadius = '4px'
    tooltip.style.fontSize = '12px'
    tooltip.style.pointerEvents = 'none'
    tooltip.style.zIndex = '1000'
    tooltip.style.whiteSpace = 'pre-line'
    barChartRef.value.appendChild(tooltip)

    // 订阅 crosshair 移动事件
    chartInstance.value.subscribeCrosshairMove((param) => {
      try {
        // 如果鼠标不在有效数据区域，隐藏tooltip
        if (!param || !param.time || !param.point || !barChartRef.value) {
          tooltip.style.display = 'none'
          return
        }

        // 获取对应日期的数据
        const time = param.time as number
        const barData = loadedBarsData.value.find(bar => {
          const barTime = dayjs(bar.date).unix()
          return barTime === time
        })

        if (!barData) {
          tooltip.style.display = 'none'
          return
        }

        // 构建 tooltip 内容
        const dateStr = dayjs(barData.date).format('YYYY-MM-DD')
        const openColor = barData.open >= barData.close ? '#ef5350' : '#26a69a'
        const closeColor = barData.close >= barData.open ? '#26a69a' : '#ef5350'

        let content = `<div style="font-weight:600; margin-bottom: 4px;">${dateStr}</div>`
        content += `<div>开: <span style="color: ${openColor}">${barData.open?.toFixed(2) || '-'}</span></div>`
        content += `<div>高: ${barData.high?.toFixed(2) || '-'}</div>`
        content += `<div>低: ${barData.low?.toFixed(2) || '-'}</div>`
        content += `<div>收: <span style="color: ${closeColor}">${barData.close?.toFixed(2) || '-'}</span></div>`
        content += `<div style="margin-top: 4px; padding-top: 4px; border-top: 1px solid rgba(255,255,255,0.2);">`
        content += `<div>成交量: ${(barData.volume / 10000).toFixed(2)}万</div>`
        content += `</div>`

        tooltip.innerHTML = content
        tooltip.style.display = 'block'

        // 定位 tooltip
        const chartRect = barChartRef.value.getBoundingClientRect()
        const x = param.point.x
        const y = param.point.y

        // 确保不超出边界
        const tooltipRect = tooltip.getBoundingClientRect()
        let left = x + 15
        let top = y + 15

        if (left + tooltipRect.width > chartRect.width) {
          left = x - tooltipRect.width - 15
        }
        if (top + tooltipRect.height > chartRect.height) {
          top = y - tooltipRect.height - 15
        }

        tooltip.style.left = `${left}px`
        tooltip.style.top = `${top}px`
      } catch (error) {
        console.error('Tooltip error:', error)
        tooltip.style.display = 'none'
      }
    })

    // 监听可见时间范围变化，实现按需加载
    chartInstance.value.timeScale().subscribeVisibleLogicalRangeChange(() => {
      checkAndLoadMoreData()
    })
  } catch (error) {
    console.error('Chart creation error:', error)
  }
}

// 检查并加载更多数据（带防抖）
const checkAndLoadMoreData = () => {
  // 如果正在加载初始数据，跳过检查
  if (loadingBarChart.value) {
    return
  }

  console.log('checkAndLoadMoreData called, loadedBarsData:', loadedBarsData.value.length)

  if (loadMoreTimer) {
    clearTimeout(loadMoreTimer)
  }

  loadMoreTimer = setTimeout(async () => {
    console.log('Executing load check...')
    if (!currentBarCode.value) {
      console.log('No current bar code')
      return
    }
    if (isLoadingMore.value) {
      console.log('Already loading')
      return
    }
    if (!chartInstance.value) {
      console.log('No chart instance')
      return
    }

    // 获取已加载数据的时间范围
    if (loadedBarsData.value.length === 0) {
      console.log('No loaded bars data')
      return
    }
    if (!loadedTimeRange.value) {
      console.log('No loaded time range')
      return
    }

    // 获取可见的物理时间范围
    const visibleRange = chartInstance.value.timeScale().getVisibleRange()
    console.log('Visible range from API:', visibleRange)
    if (!visibleRange) {
      console.log('No visible range returned')
      return
    }

    const { from, to } = visibleRange
    const bufferTime = 30 * 24 * 60 * 60  // 30天的缓冲（秒）- 优化加载时机

    console.log('Visible (sec):', from, to)
    console.log('Loaded (ms):', loadedTimeRange.value.min, loadedTimeRange.value.max)
    console.log('Visible:', new Date(from * 1000).toLocaleDateString(), '-', new Date(to * 1000).toLocaleDateString())
    console.log('Loaded:', new Date(loadedTimeRange.value.min).toLocaleDateString(), '-', new Date(loadedTimeRange.value.max).toLocaleDateString())

    // 检查是否需要加载更早或更晚的数据
    const minLoadedSec = loadedTimeRange.value.min / 1000
    const maxLoadedSec = loadedTimeRange.value.max / 1000
    const needLoadOlder = from < (minLoadedSec + bufferTime)
    const needLoadNewer = to > (maxLoadedSec - bufferTime)

    console.log('needLoadOlder:', needLoadOlder, 'needLoadNewer:', needLoadNewer)

    if (needLoadOlder || needLoadNewer) {
      console.log('Loading more data...')
      await loadMoreData(needLoadOlder, needLoadNewer)
    } else {
      console.log('No need to load more data')
    }

    loadMoreTimer = null
  }, 50)  // 50ms防抖 - 更快响应
}

// 加载更多历史数据或最新数据
const loadMoreData = async (loadOlder: boolean, loadNewer: boolean) => {
  if (isLoadingMore.value) return
  isLoadingMore.value = true

  try {
    if (loadOlder) {
      // 加载更早的数据
      const oldestDate = loadedBarsData.value[0]?.date
      if (oldestDate) {
        const endDate = dayjs(oldestDate).subtract(1, 'day').format('YYYY-MM-DD')
        const startDate = dayjs(endDate).subtract(6, 'month').format('YYYY-MM-DD')  // 减少到6个月

        console.log('Loading older data:', startDate, 'to', endDate)

        const response = await dataApi.getBars({
          code: currentBarCode.value,
          start_date: startDate,
          end_date: endDate,
          page: 1,
          page_size: 2000  // 减少单次加载量
        })

        if (response.items.length > 0) {
          const newItems = response.items.filter(
            item => !loadedBarsData.value.some(existing => existing.date === item.date)
          )
          if (newItems.length > 0) {
            loadedBarsData.value = [...newItems, ...loadedBarsData.value]
            // 注意：不在这里更新 loadedTimeRange，而是在 updateChartData 使用 setData 后更新
            await updateChartData(newItems, true)  // 传递 true 表示这是更早的数据
            console.log('Loaded', newItems.length, 'older bars')
          }
        }
      }
    }

    if (loadNewer) {
      // 加载更新的数据
      const newestDate = loadedBarsData.value[loadedBarsData.value.length - 1]?.date
      if (newestDate) {
        const startDate = dayjs(newestDate).add(1, 'day').format('YYYY-MM-DD')
        const endDate = dayjs().format('YYYY-MM-DD')

        console.log('Loading newer data:', startDate, 'to', endDate)

        const response = await dataApi.getBars({
          code: currentBarCode.value,
          start_date: startDate,
          end_date: endDate,
          page: 1,
          page_size: 2000  // 减少单次加载量
        })

        if (response.items.length > 0) {
          const newItems = response.items.filter(
            item => !loadedBarsData.value.some(existing => existing.date === item.date)
          )
          if (newItems.length > 0) {
            loadedBarsData.value = [...loadedBarsData.value, ...newItems]
            // 注意：不在这里更新 loadedTimeRange
            await updateChartData(newItems, false)  // 传递 false 表示这是更新的数据
            console.log('Loaded', newItems.length, 'newer bars')
          }
        }
      }
    }
  } catch (error) {
    console.error('Failed to load more data:', error)
  } finally {
    isLoadingMore.value = false
  }
}

// 更新图表数据
const updateChartData = async (newBars: BarDataSummary[] = [], isOlderData: boolean = false) => {
  if (!chartInstance.value) return

  // 如果没有提供新数据，使用全部数据（仅在初始化时）
  const barsToUpdate = newBars.length > 0 ? newBars : loadedBarsData.value
  if (barsToUpdate.length === 0) return

  console.log('updateChartData called with', barsToUpdate.length, 'bars, isOlder:', isOlderData)

  // 过滤无效数据并按日期排序
  const validBars = barsToUpdate.filter(bar => {
    const isValid = bar.date && bar.open !== undefined && bar.high !== undefined &&
                    bar.low !== undefined && bar.close !== undefined && bar.volume !== undefined
    if (!isValid) {
      console.log('Invalid bar:', bar)
    }
    return isValid
  })

  const sortedBars = [...validBars].sort((a, b) =>
    new Date(a.date).getTime() - new Date(b.date).getTime()
  )

  console.log('After filter, have', sortedBars.length, 'valid bars')

  if (isOlderData) {
    // 如果是更早的数据，需要使用 setData 重新设置整个数据集
    console.log('Using setData for older data')

    // 使用全部数据重新设置
    const allSortedBars = [...loadedBarsData.value].sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    )

    if (candleSeriesRef.value) {
      const candlestickData = allSortedBars.map(bar => ({
        time: dayjs(bar.date).unix(),
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close
      }))
      try {
        candleSeriesRef.value.setData(candlestickData)
        console.log('Set candlestick data:', candlestickData.length, 'bars')
      } catch (error) {
        console.error('Failed to set candlestick data:', error)
      }
    }

    if (volumeSeriesRef.value) {
      const volumeData = allSortedBars.map(bar => {
        const isUp = bar.close >= bar.open
        return {
          time: dayjs(bar.date).unix(),
          value: bar.volume,
          color: isUp ? '#26a69a' : '#ef5350'
        }
      })
      try {
        volumeSeriesRef.value.setData(volumeData)
        console.log('Set volume data:', volumeData.length, 'bars')
      } catch (error) {
        console.error('Failed to set volume data:', error)
      }
    }

    // setData 成功后，更新 loadedTimeRange
    const timestamps = allSortedBars.map(d => dayjs(d.date).unix() * 1000)
    loadedTimeRange.value = {
      min: Math.min(...timestamps),
      max: Math.max(...timestamps)
    }
    console.log('Updated loadedTimeRange:', new Date(loadedTimeRange.value.min).toLocaleDateString(), '-', new Date(loadedTimeRange.value.max).toLocaleDateString())
  } else {
    // 如果是更新的数据，使用 update 方法追加
    console.log('Using update for newer data')

    if (candleSeriesRef.value) {
      let successCount = 0
      sortedBars.forEach(bar => {
        try {
          const data = {
            time: dayjs(bar.date).unix(),
            open: bar.open,
            high: bar.high,
            low: bar.low,
            close: bar.close
          }
          candleSeriesRef.value.update(data)
          successCount++
        } catch (error) {
          // 忽略"Cannot update oldest data"错误
          const errorMsg = error?.message || ''
          if (!errorMsg.includes('Cannot update oldest data')) {
            console.error('Failed to update candlestick for bar:', bar.date, error)
          }
        }
      })
      console.log('Updated candlestick:', successCount, '/', sortedBars.length)

      // 更新 loadedTimeRange
      if (successCount > 0 && loadedTimeRange.value) {
        const newMaxTime = Math.max(...sortedBars.map(d => dayjs(d.date).unix() * 1000))
        loadedTimeRange.value.max = newMaxTime
      }
    }

    if (volumeSeriesRef.value) {
      let successCount = 0
      sortedBars.forEach(bar => {
        try {
          const isUp = bar.close >= bar.open
          const data = {
            time: dayjs(bar.date).unix(),
            value: bar.volume,
            color: isUp ? '#26a69a' : '#ef5350'
          }
          volumeSeriesRef.value.update(data)
          successCount++
        } catch (error) {
          // 忽略"Cannot update oldest data"错误
          const errorMsg = error?.message || ''
          if (!errorMsg.includes('Cannot update oldest data')) {
            console.error('Failed to update volume for bar:', bar.date, error)
          }
        }
      })
      console.log('Updated volume:', successCount, '/', sortedBars.length)
    }
  }

  // 更新数据点统计
  barDataPoints.value = loadedBarsData.value.length

  // 更新日期范围显示
  const allDates = loadedBarsData.value.map(item => item.date).filter(Boolean)
  if (allDates.length > 0) {
    barDateRange.value = `${allDates[0]} ~ ${allDates[allDates.length - 1]}`
  }
}

// 隐藏 tooltip
const hideTooltip = () => {
  const tooltip = barChartRef.value?.querySelector('.chart-tooltip')
  if (tooltip) {
    tooltip.style.display = 'none'
  }
}

const destroyChart = () => {
  if (chartInstance.value) {
    chartInstance.value.remove()
    chartInstance.value = null
  }
  // 清空series引用
  candleSeriesRef.value = null
  volumeSeriesRef.value = null
  // 清理 tooltip 元素
  const existingTooltip = barChartRef.value?.querySelector('.chart-tooltip')
  if (existingTooltip) {
    existingTooltip.remove()
  }
}

onMounted(() => {
  refreshStats()
  loadData()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  destroyChart()
})
</script>

<style scoped>
.data-management-container {
  padding: 24px;
  background: #f0f2f5;
  height: calc(100vh - 62px);
  overflow: hidden;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

/* 页面标题 */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.page-subtitle {
  color: #6b7280;
  margin: 4px 0 0 0;
  font-size: 14px;
}

/* 统计卡片 */
.stats-row {
  margin-bottom: 12px;
}

.stat-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-card-blue {
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
}

.stat-card-green {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
}

.stat-card-purple {
  background: linear-gradient(135deg, #f3e8ff 0%, #e9d5ff 100%);
}

/* 数据源卡片 */
.data-sources-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Sticky 数据浏览头部 */
.data-browser-header {
  position: sticky;
  top: 0;
  z-index: 100;
  background: #fff;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

/* 当头部固定时，添加额外的上边距避免遮挡内容 */
.data-browser-header.is-sticky {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  border: 1px solid #e5e7eb;
  margin-bottom: 16px;
}

.browser-header-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.search-section {
  flex: 1;
  min-width: 200px;
}

.action-buttons {
  display: flex;
  gap: 8px;
}

/* 数据表格卡片 */
.data-table-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.data-table-card :deep(.ant-card-head) {
  border-bottom: none;
}

.data-table-card :deep(.ant-card-body) {
  padding: 0;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 表格容器 - 支持滚动 */
.table-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 表格标题搜索框布局 */
.table-header-with-search {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  flex-shrink: 0;
}

.table-header-with-search .ant-input-search {
  flex-shrink: 0;
}

.table-container :deep(.ant-table) {
  font-size: 14px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.table-container :deep(.ant-table-container) {
  flex: 1;
  min-height: 0;
}

.table-container :deep(.ant-table-body) {
  min-height: 0 !important;
}

.table-container :deep(.ant-table-thead > tr > th) {
  background: #f9fafb;
  font-weight: 600;
  color: #374151;
}

.table-container :deep(.ant-table-tbody > tr:hover > td) {
  background: #f9fafb;
}

/* 固定在底部的翻页器 */
.table-pagination {
  padding: 16px 24px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
  position: sticky;
  bottom: 0;
  z-index: 99;
}

.table-pagination :deep(.ant-pagination) {
  margin: 0;
}

.table-pagination :deep(.ant-pagination-total-text) {
  color: #6b7280;
}

/* 价格涨跌颜色 */
.text-red-600 {
  color: #ef4444;
}

.text-green-600 {
  color: #22c55e;
}

/* K线图表布局 */
.bars-layout {
  display: flex;
  gap: 24px;
  flex: 1;
  min-height: 400px;
}

.bars-sidebar {
  width: 260px;
  flex-shrink: 0;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 16px;
}

.sidebar-info {
  padding: 12px;
  background: #fff;
  border-radius: 6px;
}

.bars-chart {
  flex: 1;
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 400px;  /* 确保有最小高度 */
}

.chart-container {
  width: 100%;
  height: 100%;
  min-height: 400px;  /* 确保图表容器有最小高度 */
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .browser-header-content {
    flex-direction: column;
    align-items: stretch;
  }

  .action-buttons {
    justify-content: center;
  }

  /* K线图表响应式 */
  .bars-layout {
    flex-direction: column;
    height: auto;
  }

  .bars-sidebar {
    width: 100%;
    margin-bottom: 16px;
  }

  .bars-chart {
    min-height: 400px;
  }
}
</style>
