<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="green">K线</a-tag>
        K线数据
        <a-tag v-if="isLoadingMore" color="blue" style="margin-left: 8px">
          <LoadingOutlined spin /> 加载历史数据...
        </a-tag>
      </div>
      <a-space>
        <a-select
          v-model:value="selectedCode"
          show-search
          placeholder="选择股票"
          style="width: 180px"
          :options="stockOptions"
          :filter-option="filterOption"
          @change="handleCodeChange"
        />
        <a-range-picker
          v-model:value="dateRange"
          format="YYYY-MM-DD"
          @change="loadBars"
        />
        <a-select v-model:value="frequency" style="width: 100px" @change="loadBars">
          <a-select-option value="day">日线</a-select-option>
          <a-select-option value="week">周线</a-select-option>
          <a-select-option value="month">月线</a-select-option>
        </a-select>
        <a-select v-model:value="adjustment" style="width: 100px" @change="loadBars">
          <a-select-option value="fore">前复权</a-select-option>
          <a-select-option value="back">后复权</a-select-option>
          <a-select-option value="none">不复权</a-select-option>
        </a-select>
        <a-button :loading="loading" @click="loadBars">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </a-space>
    </div>

    <!-- K线图表 - TradingView 风格 -->
    <a-card title="K线图" style="margin-bottom: 16px" :body-style="{ padding: '12px' }">
      <div ref="chartContainer" class="chart-container">
        <!-- 加载更多指示器 -->
        <div v-if="isLoadingMore" class="loading-more-indicator">
          <LoadingOutlined spin />
          <span>正在加载历史数据...</span>
        </div>
      </div>
      <div v-if="!selectedCode" class="chart-empty">
        <a-empty description="请选择股票查看K线图" />
      </div>
      <!-- 数据加载状态提示 -->
      <div v-if="selectedCode && !hasMoreHistory" class="no-more-data">
        已加载全部历史数据 (共 {{ barData.length }} 条)
      </div>
    </a-card>

    <!-- 数据统计 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="数据条数" :value="barData.length" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="最新价" :value="latestBar?.close" :precision="2" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic
            title="涨跌幅"
            :value="priceChange"
            :precision="2"
            suffix="%"
            :value-style="{ color: priceChange >= 0 ? '#ef5350' : '#26a69a' }"
          />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="最高" :value="priceStats.high" :precision="2" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="最低" :value="priceStats.low" :precision="2" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card size="small">
          <a-statistic title="成交量" :value="priceStats.totalVolume" />
        </a-card>
      </a-col>
    </a-row>

    <!-- K线数据表格 -->
    <a-card title="数据明细">
      <a-table
        :columns="columns"
        :data-source="barData"
        :loading="loading"
        :pagination="pagination"
        row-key="timestamp"
        size="small"
        :scroll="{ x: 800 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'timestamp'">
            {{ formatDate(record.timestamp) }}
          </template>
          <template v-if="column.dataIndex === 'change'">
            <span :style="{ color: record.change >= 0 ? '#ef5350' : '#26a69a' }">
              {{ record.change >= 0 ? '+' : '' }}{{ record.change?.toFixed(2) }}%
            </span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined, LoadingOutlined } from '@ant-design/icons-vue'
import dayjs, { Dayjs } from 'dayjs'
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  HistogramData,
  ColorType,
  CrosshairMode,
  Time,
  Range,
} from 'lightweight-charts'

const route = useRoute()
const loading = ref(false)
const isLoadingMore = ref(false)
const chartContainer = ref<HTMLElement | null>(null)
const selectedCode = ref<string>('')
const dateRange = ref<[Dayjs, Dayjs]>([
  dayjs().subtract(6, 'month'),
  dayjs()
])
const frequency = ref('day')
const adjustment = ref('fore')
const barData = ref<any[]>([])

// 懒加载状态
const hasMoreHistory = ref(true)
const earliestDate = ref<Dayjs | null>(null)
const BATCH_SIZE = 300 // 每次加载的数据条数（增大减少加载频率）
const LOAD_THRESHOLD = 0.4 // 当滚动到左边40%时提前触发加载
const MAX_DATA_POINTS = 3000 // 最大数据点限制

// 图表相关
let chart: IChartApi | null = null
let candlestickSeries: ISeriesApi<'Candlestick'> | null = null
let volumeSeries: ISeriesApi<'Histogram'> | null = null
let isLoadingLocked = false // 防止重复加载

const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const stockOptions = [
  { value: '000001.SZ', label: '000001.SZ 平安银行' },
  { value: '000002.SZ', label: '000002.SZ 万科A' },
  { value: '600519.SH', label: '600519.SH 贵州茅台' },
]

const columns = [
  { title: '日期', dataIndex: 'timestamp', width: 120 },
  { title: '开盘', dataIndex: 'open', width: 100 },
  { title: '最高', dataIndex: 'high', width: 100 },
  { title: '最低', dataIndex: 'low', width: 100 },
  { title: '收盘', dataIndex: 'close', width: 100 },
  { title: '涨跌幅', dataIndex: 'change', width: 100 },
  { title: '成交量', dataIndex: 'volume', width: 120 },
  { title: '成交额', dataIndex: 'amount', width: 120 }
]

const latestBar = computed(() => barData.value[barData.value.length - 1])
const prevBar = computed(() => barData.value[barData.value.length - 2])

const priceChange = computed(() => {
  if (!latestBar.value || !prevBar.value) return 0
  return ((latestBar.value.close - prevBar.value.close) / prevBar.value.close) * 100
})

const priceStats = computed(() => {
  if (barData.value.length === 0) return { high: 0, low: 0, totalVolume: 0 }
  const closes = barData.value.map(b => b.close)
  const volumes = barData.value.map(b => b.volume || 0)
  return {
    high: Math.max(...closes),
    low: Math.min(...closes),
    totalVolume: volumes.reduce((a, b) => a + b, 0)
  }
})

const filterOption = (input: string, option: any) => {
  return option.label.toLowerCase().indexOf(input.toLowerCase()) >= 0
}

const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

// 模拟 API 获取数据（实际应调用后端 API）
const fetchBarsFromAPI = async (code: string, startDate: Dayjs, count: number): Promise<any[]> => {
  // 模拟网络延迟
  await new Promise(resolve => setTimeout(resolve, 500))

  const mockData = []
  let price = 10 + Math.random() * 100

  for (let i = 0; i < count; i++) {
    const currentDate = startDate.add(i, 'day')
    // 跳过周末
    if (currentDate.day() === 0 || currentDate.day() === 6) continue

    const change = (Math.random() - 0.5) * 5
    const open = price
    const close = price + change
    const high = Math.max(open, close) + Math.random() * 2
    const low = Math.min(open, close) - Math.random() * 2

    mockData.push({
      timestamp: currentDate.toISOString(),
      open: +open.toFixed(2),
      high: +high.toFixed(2),
      low: +low.toFixed(2),
      close: +close.toFixed(2),
      volume: Math.floor(Math.random() * 10000000),
      amount: Math.floor(Math.random() * 1000000000),
      change: 0 // 稍后计算
    })
    price = close
  }

  // 计算涨跌幅
  for (let i = 1; i < mockData.length; i++) {
    mockData[i].change = ((mockData[i].close - mockData[i-1].close) / mockData[i-1].close * 100)
  }

  return mockData
}

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) return

  // 清理旧图表
  if (chart) {
    chart.remove()
    chart = null
  }

  const containerWidth = chartContainer.value.clientWidth
  const containerHeight = 500

  chart = createChart(chartContainer.value, {
    width: containerWidth,
    height: containerHeight,
    layout: {
      background: { type: ColorType.Solid, color: '#ffffff' },
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#f0f0f0' },
      horzLines: { color: '#f0f0f0' },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: {
        color: '#758696',
        width: 1,
        style: 3,
        labelBackgroundColor: '#2962ff',
      },
      horzLine: {
        color: '#758696',
        width: 1,
        style: 3,
        labelBackgroundColor: '#2962ff',
      },
    },
    rightPriceScale: {
      borderColor: '#ddd',
      scaleMargins: {
        top: 0.1,
        bottom: 0.25,
      },
    },
    timeScale: {
      borderColor: '#ddd',
      timeVisible: true,
      secondsVisible: false,
    },
  })

  // 创建K线图（蜡烛图）
  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#ef5350',
    downColor: '#26a69a',
    borderUpColor: '#ef5350',
    borderDownColor: '#26a69a',
    wickUpColor: '#ef5350',
    wickDownColor: '#26a69a',
  })

  // 创建成交量图
  volumeSeries = chart.addHistogramSeries({
    color: '#26a69a',
    priceFormat: {
      type: 'volume',
    },
    priceScaleId: 'volume',
  })

  // 设置成交量图的价格轴
  chart.priceScale('volume').applyOptions({
    scaleMargins: {
      top: 0.8,
      bottom: 0,
    },
  })

  // 监听可见范围变化，实现懒加载
  chart.timeScale().subscribeVisibleTimeRangeChange((range: Range<Time> | null) => {
    if (!range || isLoadingLocked) return
    handleVisibleRangeChange(range)
  })

  // 响应窗口大小变化
  const handleResize = () => {
    if (chart && chartContainer.value) {
      chart.applyOptions({
        width: chartContainer.value.clientWidth,
      })
    }
  }
  window.addEventListener('resize', handleResize)
}

// 处理可见范围变化
const handleVisibleRangeChange = async (range: Range<Time>) => {
  if (!chart || isLoadingLocked || !hasMoreHistory.value || isLoadingMore.value) return

  const logicalRange = chart.timeScale().getVisibleLogicalRange()
  if (!logicalRange) return

  // 计算可见区域相对于总数据的位置
  // barsInLogicalRange 返回可见区域内的数据条数信息
  const totalBars = barData.value.length
  const visibleFrom = Math.max(0, Math.floor(logicalRange.from as number))
  const visibleBars = Math.ceil((logicalRange.to as number) - (logicalRange.from as number))

  // 当可见区域的左边缘距离数据起点小于阈值时，加载更多
  const positionRatio = totalBars > 0 ? visibleFrom / totalBars : 0

  if (positionRatio < LOAD_THRESHOLD) {
    await loadMoreHistory()
  }
}

// 加载更多历史数据
const loadMoreHistory = async () => {
  if (!selectedCode.value || isLoadingLocked || !hasMoreHistory.value || !earliestDate.value) return

  isLoadingLocked = true
  isLoadingMore.value = true

  try {
    // 计算新的起始日期（往前推）
    const newStartDate = earliestDate.value.subtract(BATCH_SIZE, 'day')

    // 检查是否超过合理范围（例如：不超过10年）
    const minDate = dayjs().subtract(10, 'year')
    if (newStartDate.isBefore(minDate)) {
      hasMoreHistory.value = false
      return
    }

    // 记录当前可视位置（用于恢复）
    const scrollPosition = chart?.timeScale().scrollPosition()

    // 获取历史数据
    const historicalData = await fetchBarsFromAPI(selectedCode.value, newStartDate, BATCH_SIZE)

    if (historicalData.length === 0) {
      hasMoreHistory.value = false
      return
    }

    // 将新数据前置到现有数据
    barData.value = [...historicalData, ...barData.value]

    // 更新最早日期
    earliestDate.value = dayjs(historicalData[0].timestamp)

    // 更新图表数据（使用优化版本）
    updateChartDataPrepend(historicalData)

    // 恢复滚动位置，保持用户当前视图
    if (chart && scrollPosition !== undefined) {
      requestAnimationFrame(() => {
        chart?.timeScale().scrollToPosition(scrollPosition, false)
      })
    }

    pagination.total = barData.value.length

    // 仅在首次加载大量数据时提示
    if (barData.value.length === historicalData.length + BATCH_SIZE) {
      message.success(`已加载 ${historicalData.length} 条历史数据`)
    }

  } catch (error: any) {
    message.error(`加载历史数据失败: ${error.message}`)
  } finally {
    isLoadingMore.value = false
    // 延迟解锁，防止连续触发（增大延迟时间）
    setTimeout(() => {
      isLoadingLocked = false
    }, 800)
  }
}

// 缓存已转换的数据，避免重复计算
let cachedCandleData: CandlestickData[] = []
let cachedVolumeData: HistogramData[] = []

// 转换数据格式
const convertToChartData = (data: any[]): { candles: CandlestickData[], volumes: HistogramData[] } => {
  const candles: CandlestickData[] = []
  const volumes: HistogramData[] = []

  for (const item of data) {
    const time = dayjs(item.timestamp).format('YYYY-MM-DD') as any
    candles.push({
      time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close,
    })
    volumes.push({
      time,
      value: item.volume,
      color: item.close >= item.open ? '#ef535080' : '#26a69a80',
    })
  }

  return { candles, volumes }
}

// 前置更新图表数据（优化版）
const updateChartDataPrepend = (newData: any[]) => {
  if (!candlestickSeries || !volumeSeries || newData.length === 0) return

  // 转换新数据
  const { candles: newCandles, volumes: newVolumes } = convertToChartData(newData)

  // 使用 requestAnimationFrame 避免阻塞 UI
  requestAnimationFrame(() => {
    if (!candlestickSeries || !volumeSeries) return

    // 合并数据（新数据在前）
    cachedCandleData = [...newCandles, ...cachedCandleData]
    cachedVolumeData = [...newVolumes, ...cachedVolumeData]

    // 限制最大数据点数量，防止内存过大
    if (cachedCandleData.length > MAX_DATA_POINTS) {
      cachedCandleData = cachedCandleData.slice(0, MAX_DATA_POINTS)
      cachedVolumeData = cachedVolumeData.slice(0, MAX_DATA_POINTS)
    }

    // 批量更新
    candlestickSeries.setData(cachedCandleData)
    volumeSeries.setData(cachedVolumeData)
  })
}

// 更新图表数据
const updateChartData = () => {
  if (!candlestickSeries || !volumeSeries || barData.value.length === 0) return

  // 转换并缓存数据
  const { candles, volumes } = convertToChartData(barData.value)
  cachedCandleData = candles
  cachedVolumeData = volumes

  candlestickSeries.setData(cachedCandleData)
  volumeSeries.setData(cachedVolumeData)

  // 自动缩放到最新数据
  if (chart) {
    chart.timeScale().scrollToRealTime()
  }
}

const handleCodeChange = () => {
  // 切换股票时重置状态和缓存
  hasMoreHistory.value = true
  earliestDate.value = null
  isLoadingLocked = false
  cachedCandleData = []
  cachedVolumeData = []
  loadBars()
}

const loadBars = async () => {
  if (!selectedCode.value) return

  loading.value = true
  hasMoreHistory.value = true
  isLoadingLocked = false
  cachedCandleData = []
  cachedVolumeData = []

  try {
    const startDate = dateRange.value[0]
    const data = await fetchBarsFromAPI(selectedCode.value, startDate, BATCH_SIZE)

    barData.value = data
    pagination.total = data.length

    // 记录最早日期
    if (data.length > 0) {
      earliestDate.value = dayjs(data[0].timestamp)
    }

    // 更新图表
    await nextTick()
    if (!chart) {
      initChart()
    }
    updateChartData()
  } catch (error: any) {
    message.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // 从URL参数获取股票代码
  if (route.query.code) {
    selectedCode.value = route.query.code as string
    loadBars()
  }
})

onUnmounted(() => {
  // 清理图表
  if (chart) {
    chart.remove()
    chart = null
  }
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chart-container {
  width: 100%;
  height: 500px;
  position: relative;
}

.chart-empty {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  z-index: 10;
}

.loading-more-indicator {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(24, 144, 255, 0.9);
  color: white;
  padding: 6px 16px;
  border-radius: 4px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  z-index: 20;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}

.no-more-data {
  text-align: center;
  padding: 8px;
  color: #999;
  font-size: 12px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}
</style>
