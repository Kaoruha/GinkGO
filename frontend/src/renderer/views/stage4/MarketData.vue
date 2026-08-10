<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-blue">市场数据</span>
        交易对订阅管理
      </h1>
      <div class="page-actions">
        <button class="btn-primary" @click="refreshPairs">刷新交易对</button>
        <button class="btn-secondary" @click="toggleWebSocket">
          {{ wsConnected ? '已连接' : '连接' }}
        </button>
      </div>
    </div>

    <!-- 订阅统计 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">总交易对</div>
        <div class="stat-value">{{ totalPairs }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已订阅</div>
        <div class="stat-value stat-primary">{{ subscriptions.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">API 连接</div>
        <div class="stat-value" :class="wsConnected ? 'stat-success' : 'stat-danger'">
          {{ wsConnected ? '已连接' : '未连接' }}
        </div>
      </div>
      <!-- 实时数据状态 -->
      <div class="stat-card">
        <div class="stat-label">实时数据</div>
        <div class="stat-value" :class="tickerDataKeysCount > 0 ? 'stat-success' : 'stat-danger'">
          {{ tickerDataKeysCount }} / {{ subscriptions.length }}
        </div>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="content-grid">
      <!-- 交易对列表 -->
      <div class="card pairs-card">
        <div class="card-header">
          <h3>交易对列表</h3>
          <div class="header-controls">
            <select v-model="selectedQuoteCurrency" class="filter-select">
              <option value="">全部币种</option>
              <option value="USDT">USDT</option>
              <option value="USD">USD</option>
              <option value="BTC">BTC</option>
              <option value="ETH">ETH</option>
              <option value="USDC">USDC</option>
            </select>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="搜索交易对..."
              class="search-input"
            >
          </div>
        </div>
        <div class="card-body">
          <div v-if="loadingPairs" class="loading">加载中...</div>
          <div v-else class="pairs-list">
            <div
              v-for="pair in filteredPairs"
              :key="pair.symbol"
              class="pair-item"
              :class="{ subscribed: isSubscribed(pair.symbol) }"
            >
              <div class="pair-info">
                <span class="pair-symbol">{{ pair.symbol }}</span>
                <span class="pair-state">{{ pair.state }}</span>
              </div>
              <div class="pair-price" v-if="getPairTicker(pair.symbol)">
                <span class="price-label">价格:</span>
                <span class="price-value" :class="getPairPriceClass(pair.symbol)">
                  {{ formatPrice(getPairPrice(pair.symbol)) }}
                </span>
                <span class="volume-label">成交量:</span>
                <span class="volume-value">{{ formatVolume(getPairVolume(pair.symbol)) }}</span>
              </div>
              <div class="pair-actions">
                <button
                  v-if="isSubscribed(pair.symbol)"
                  class="btn-danger btn-sm"
                  @click="unsubscribe(pair.symbol)"
                >
                  取消订阅
                </button>
                <button
                  v-else
                  class="btn-primary btn-sm"
                  @click="subscribe(pair.symbol)"
                >
                  订阅
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 实时行情 -->
      <div class="card ticker-card">
        <div class="card-header">
          <h3>实时行情</h3>
          <div class="ticker-types">
            <button
              v-for="type in ['ticker', 'candlesticks', 'orderbook', 'trades']"
              :key="type"
              class="type-btn"
              :class="{ active: selectedDataType === type }"
              @click="selectedDataType = type as DataType"
            >
              {{ typeLabels[type as DataType] }}
            </button>
          </div>
          <div class="ws-controls">
            <button
              @click="toggleWebSocket"
              :class="{ connected: wsConnected, disconnected: !wsConnected }"
              class="ws-toggle-btn"
            >
              {{ wsConnected ? '🟢 已连接' : '🔴 未连接' }}
            </button>
          </div>
        </div>
        <div class="card-body">
          <div v-if="!wsConnected" class="disconnected">
            WebSocket 未连接，无法获取实时数据
          </div>
          <div v-else-if="activeTickers.length === 0" class="empty">
            暂无数据，请先订阅交易对
          </div>
          <div v-else class="ticker-table" v-if="tickerDataForTemplate">
            <table>
              <thead>
                <tr>
                  <th>交易对</th>
                  <th>最新价</th>
                  <th>买一价</th>
                  <th>卖一价</th>
                  <th>24H涨跌</th>
                  <th>24H成交量</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sub in subscriptions" :key="sub.symbol">
                  <td>{{ sub.symbol }}</td>
                  <td class="price-cell" :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]">
                    {{ tickerDataForTemplate[sub.symbol]?.price ? tickerDataForTemplate[sub.symbol].price.toFixed(3) : '-' }}
                  </td>
                  <td class="price-cell" :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]">
                    {{ tickerDataForTemplate[sub.symbol]?.bid_price ? tickerDataForTemplate[sub.symbol].bid_price.toFixed(3) : '-' }}
                  </td>
                  <td class="price-cell" :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]">
                    {{ tickerDataForTemplate[sub.symbol]?.ask_price ? tickerDataForTemplate[sub.symbol].ask_price.toFixed(3) : '-' }}
                  </td>
                  <td class="change-cell" :class="get24hChangeClass(sub.symbol)">
                    {{ format24hChange(tickerDataForTemplate[sub.symbol]) }}
                  </td>
                  <td>{{ formatTickerVolume(tickerDataForTemplate[sub.symbol]?.volume_24h) }}</td>
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { marketApi, type TradingPair, type MarketSubscription, DataType } from '@/api/modules/market'

// 数据类型标签
const typeLabels: Record<DataType, string> = {
  ticker: 'Tickers',
  candlesticks: 'K线',
  orderbook: '订单簿',
  trades: '成交'
}

// 状态
const loadingPairs = ref(false)
const searchQuery = ref('')
const selectedQuoteCurrency = ref('')
const pairs = ref<TradingPair[]>([])
const subscriptions = ref<MarketSubscription[]>([])
const selectedDataType = ref<DataType>('ticker')

// API Server WebSocket（通过 API Server 中转 OKX WebSocket）
let ws: WebSocket | null = null
const wsConnected = ref(false)
// 标记是否应该重连（组件卸载时不应该重连）
const shouldReconnect = ref(true)
// 订阅交易对的实时数据（从 OKX WebSocket）- 使用 ref 确保响应式
const tickerData = ref<Record<string, any>>({})
// 所有交易对的 ticker 数据（从 REST API 定期获取）
const allTickers = ref<Record<string, any>>({})
// 价格变化状态 {symbol: 'up' | 'down' | ''}
const priceDirection = ref<Record<string, string>>({})
// 上一次价格 {symbol: price}
const lastPrices = ref<Record<string, number>>({})
// 价格动画状态 {symbol: 'flash-up' | 'flash-down' | ''}
const priceAnimation = ref<Record<string, string>>({})
// 定时刷新所有 ticker 的定时器
let allTickersTimer: number | null = null
// 强制刷新计数器
const refreshKey = ref(0)

// tickerData 的计数器用于强制刷新
const tickerDataCount = ref(0)

// 用于模板访问的计算属性 - 确保 Vue 正确追踪响应式
const tickerDataForTemplate = computed(() => {
  const data = tickerData?.value || {}
  return data
})

// tickerData 的 key 数量，避免在模板中直接调用 Object.keys
const tickerDataKeysCount = computed(() => {
  const data = tickerData?.value
  if (!data) return 0
  return Object.keys(data).length
})

// 计算属性
const totalPairs = computed(() => pairs.value.length)

// 调试：tickerData 快照，用于验证响应式
const tickerDataSnapshot = computed(() => {
  void refreshKey.value
  const snapshot: Record<string, any> = {}
  Object.keys(tickerData.value).forEach(symbol => {
    const ticker = tickerData.value[symbol]
    snapshot[symbol] = {
      price: ticker?.price,
      bid_price: ticker?.bid_price,
      ask_price: ticker?.ask_price
    }
  })

  return snapshot
})
void tickerDataSnapshot

const filteredPairs = computed(() => {
  let result = pairs.value

  // 先过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toUpperCase()
    result = result.filter(p => p.symbol.includes(query))
  }

  // 排序：已订阅的在前，未订阅的按成交量降序
  result = [...result].sort((a, b) => {
    const aSubscribed = isSubscribed(a.symbol)
    const bSubscribed = isSubscribed(b.symbol)

    // 已订阅的优先
    if (aSubscribed && !bSubscribed) return -1
    if (!aSubscribed && bSubscribed) return 1

    // 都已订阅或都未订阅时，按成交量降序
    const aVolume = Number(getPairVolume(a.symbol)) || 0
    const bVolume = Number(getPairVolume(b.symbol)) || 0
    return bVolume - aVolume
  })

  return result
})

const activeTickers = computed(() => {
  // 显式依赖 tickerDataCount 确保响应式
  void tickerDataCount.value
  const currentTickerData = tickerData.value || {}
  const currentSubscriptions = subscriptions.value

  const result = currentSubscriptions.map(sub => {
    const ticker = currentTickerData[sub.symbol]

    return {
      symbol: sub.symbol,
      price: ticker?.price ?? 0,
      bid_price: ticker?.bid_price ?? 0,
      ask_price: ticker?.ask_price ?? 0,
      volume_24h: ticker?.volume_24h ?? 0
    }
  })

  return result
})

// 方法
const isSubscribed = (symbol: string) => {
  return subscriptions.value.some(sub => sub.symbol === symbol)
}

const subscribe = async (symbol: string) => {
  try {
    await marketApi.createSubscription({
      exchange: 'okx',
      symbol,
      data_types: ['ticker']
    })
    await loadSubscriptions()
    subscribeWs(symbol)
  } catch (error) {
    console.error('订阅失败:', error)
  }
}

const unsubscribe = async (symbol: string) => {
  try {
    const sub = subscriptions.value.find(s => s.symbol === symbol)
    if (sub) {
      await marketApi.deleteSubscription(sub.uuid)
      await loadSubscriptions()
      unsubscribeWs(symbol)
    }
  } catch (error) {
    console.error('取消订阅失败:', error)
  }
}

const refreshPairs = async () => {
  await loadPairs()
}

const loadPairs = async () => {
  loadingPairs.value = true
  try {
    const params: any = {
      exchange: 'okx',
      environment: 'production'
    }
    if (selectedQuoteCurrency.value) {
      params.quote_ccy = selectedQuoteCurrency.value
    }
    const response: any = await marketApi.getTradingPairs(params)
    if (response.code === 0) {
      pairs.value = response.data?.pairs || []
    }
  } catch (error) {
    console.error('加载交易对失败:', error)
  } finally {
    loadingPairs.value = false
  }
}

const loadSubscriptions = async () => {
  try {
    const response: any = await marketApi.getSubscriptions()
    if (response.code === 0) {
      subscriptions.value = response.data?.subscriptions || []
      console.log('[MarketData] 订阅列表加载成功:', subscriptions.value.length, '个订阅')
      console.log('[MarketData] 订阅列表:', subscriptions.value.map(s => s.symbol))
    }
  } catch (error) {
    console.error('加载订阅失败:', error)
  }
}

const loadAllTickers = async () => {
  try {
    const response: any = await marketApi.getAllTickers({
      exchange: 'okx',
      environment: 'production'
    })
    if (response.code === 0) {
      const newTickers = response.data?.tickers || {}

      // 检测价格变化
      Object.keys(newTickers).forEach(symbol => {
        const ticker = newTickers[symbol]
        const newPrice = parseFloat(ticker.last_price || 0)
        const oldPrice = lastPrices.value[symbol]

        if (oldPrice && newPrice !== oldPrice && newPrice > 0) {
          priceDirection.value[symbol] = newPrice > oldPrice ? 'up' : 'down'
        }

        if (newPrice > 0) {
          lastPrices.value[symbol] = newPrice
        }
      })

      allTickers.value = newTickers
    }
  } catch (error) {
    console.error('加载所有 ticker 失败:', error)
  }
}

const startAllTickersPolling = () => {
  // 立即加载一次
  loadAllTickers()
  // 每 5 秒刷新一次
  allTickersTimer = window.setInterval(() => {
    loadAllTickers()
  }, 5000)
}

const stopAllTickersPolling = () => {
  if (allTickersTimer !== null) {
    window.clearInterval(allTickersTimer)
    allTickersTimer = null
  }
}

// API Server WebSocket（通过 API Server 中转 OKX WebSocket）
const connectWebSocket = () => {
  // 连接到 API Server WebSocket
  const apiBase = import.meta.env.VITE_API_BASE_URL || ''
  const url = new URL(apiBase || `${window.location.protocol}//${window.location.hostname}:8000`)
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${url.host}/ws`

  // 启用自动重连
  shouldReconnect.value = true

  ws = new WebSocket(wsUrl)

  ws.onopen = () => {
    wsConnected.value = true
    console.log('[WS] WebSocket 已连接')

    // 订阅已保存的交易对
    subscriptions.value.forEach(sub => {
      subscribeWs(sub.symbol)
    })

    console.log('[WS] 已订阅', subscriptions.value.length, '个交易对')
  }

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)

      if (message.type === 'market_data' && message.data_type === 'ticker') {
        const symbol = message.symbol
        const data = message.data || {}

        const newPrice = data.price || 0
        const oldPrice = lastPrices.value[symbol]

        // 更新价格方向（每次都更新以保持颜色）
        let direction = ''
        if (oldPrice && newPrice !== oldPrice) {
          direction = newPrice > oldPrice ? 'up' : 'down'
        }

        // 始终设置方向状态（用于颜色显示）
        // 如果有旧价格且价格变化了，更新方向；否则保持当前方向或默认为 up
        if (direction) {
          priceDirection.value = { ...priceDirection.value, [symbol]: direction }
        } else if (!priceDirection.value[symbol] && newPrice > 0) {
          // 首次收到价格时，设置默认方向为 up（绿色）
          priceDirection.value = { ...priceDirection.value, [symbol]: 'up' }
        }

        // 只有价格真正变化时才触发动画
        if (newPrice !== oldPrice && direction) {
          priceAnimation.value[symbol] = direction === 'up' ? 'flash-up' : 'flash-down'

          // 600ms 后清除动画类，这样下次价格变化会重新触发
          setTimeout(() => {
            if (priceAnimation.value[symbol]) {
              delete priceAnimation.value[symbol]
              // 创建新对象引用以触发响应式更新
              priceAnimation.value = { ...priceAnimation.value }
            }
          }, 600)
        }

        lastPrices.value[symbol] = newPrice

        // 创建新对象引用以确保 Vue 响应式系统正确追踪
        const newData = { ...data }
        const newTickerData = { ...tickerData.value }
        newTickerData[symbol] = newData
        tickerData.value = newTickerData

        // 调试：打印收到的完整数据
        if (tickerDataCount.value % 20 === 1) {
          console.log(`[WS Debug] ${symbol} 完整数据:`, {
            price: newData.price,
            open_24h: newData.open_24h,
            bid_price: newData.bid_price,
            ask_price: newData.ask_price
          })
        }

        // 强制触发响应式更新
        tickerDataCount.value++

        // 每10条消息打印一次
        if (tickerDataCount.value % 10 === 1) {
          console.log(`[WS] 收到: ${symbol}, price=$${data.price}, keys=${Object.keys(tickerData.value).length}`)
        }
      }
    } catch (error: any) {
      console.error('[WS] 错误:', error.message)
    }
  }

  ws.onclose = () => {
    wsConnected.value = false
    console.log('[WS] WebSocket 已断开，5秒后重连...')
    setTimeout(() => {
      // 只有在应该重连且未连接时才重连
      if (shouldReconnect.value && !wsConnected.value) {
        connectWebSocket()
      }
    }, 5000)
  }

  ws.onerror = (error) => {
    console.error('[WS] WebSocket 错误:', error)
    wsConnected.value = false
  }
}

const disconnectWebSocket = () => {
  // 设置标志，防止自动重连
  shouldReconnect.value = false
  if (ws) {
    ws.close()
    ws = null
  }
  wsConnected.value = false
}

const toggleWebSocket = () => {
  if (wsConnected.value) {
    disconnectWebSocket()
  } else {
    connectWebSocket()
  }
}

const subscribeWs = (symbol: string) => {
  if (ws && wsConnected.value && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({
      action: 'subscribe',
      symbols: [symbol],
      data_types: ['ticker']
    }))
  }
}

const unsubscribeWs = (symbol: string) => {
  if (ws && wsConnected.value) {
    ws.send(JSON.stringify({
      action: 'unsubscribe',
      symbols: [symbol]
    }))
  }
}

// 格式化
const formatPrice = (price: number | string) => {
  // 处理 "NO DATA" 字符串或其他非数字值
  if (typeof price === 'string' || !price || isNaN(Number(price))) {
    return '-'
  }
  return Number(price).toFixed(3)
}

const formatVolume = (volume: number | string | undefined | null) => {
  // 处理非数字值
  if (volume === undefined || volume === null || volume === '') return '-'
  const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
  if (isNaN(numVolume) || numVolume === 0) return '-'
  if (numVolume >= 1000000) return (numVolume / 1000000).toFixed(2) + 'M'
  if (numVolume >= 1000) return (numVolume / 1000).toFixed(2) + 'K'
  return numVolume.toFixed(2)
}

const format24hChange = (ticker: any) => {
  if (!ticker || !ticker.price || !ticker.open_24h || ticker.open_24h === 0) return '-'
  const change = ((ticker.price - ticker.open_24h) / ticker.open_24h * 100)
  const sign = change >= 0 ? '+' : ''
  return sign + change.toFixed(2) + '%'
}

const get24hChangeClass = (symbol: string) => {
  // 基于24H涨跌设置颜色
  const ticker = tickerDataForTemplate.value?.[symbol]
  if (!ticker || !ticker.price || !ticker.open_24h || ticker.open_24h === 0) return ''
  const change = ticker.price - ticker.open_24h
  return change >= 0 ? 'text-success' : 'text-danger'
}

const getPairPriceClass = (symbol: string) => {
  // 获取交易对的价格方向颜色
  const direction = priceDirection.value[symbol]
  if (direction === 'up') return 'text-success'
  if (direction === 'down') return 'text-danger'
  return ''
}

const getPriceAnimationClass = (symbol: string) => {
  // 获取价格动画类
  const animation = priceAnimation.value[symbol]
  return animation || ''
}

const getPairTicker = (symbol: string) => {
  // 优先使用 WebSocket 实时数据
  if (tickerData.value[symbol]) {
    return tickerData.value[symbol]
  }
  // 否则使用批量数据
  if (allTickers.value[symbol]) {
    return allTickers.value[symbol]
  }
  return null
}

const getPairPrice = (symbol: string) => {
  const ticker = getPairTicker(symbol)
  if (!ticker) return 0
  // WebSocket 数据格式: price
  // 批量数据格式: last_price
  const price = ticker.price || ticker.last_price
  // 确保返回数字，过滤掉 "NO DATA" 等字符串
  if (typeof price === 'number' && !isNaN(price)) {
    return price
  }
  return 0
}

const getPairVolume = (symbol: string) => {
  const ticker = getPairTicker(symbol)
  if (!ticker) return 0
  // 两种数据格式都有 volume_24h
  return ticker.volume_24h || 0
}

// 格式化 ticker 成交量（用于模板）
const formatTickerVolume = (volume: number | string | undefined | null) => {
  if (volume === undefined || volume === null || volume === '') return '-'
  const numVolume = typeof volume === 'string' ? parseFloat(volume) : volume
  if (isNaN(numVolume) || numVolume === 0) return '-'
  if (numVolume >= 1000000) return (numVolume / 1000000).toFixed(2) + 'M'
  if (numVolume >= 1000) return (numVolume / 1000).toFixed(2) + 'K'
  return numVolume.toFixed(2)
}

// 监听计价货币变化
watch(selectedQuoteCurrency, async () => {
  await loadPairs()
})

// 监听订阅变化（调试）
watch(subscriptions, (newSubs) => {
  console.log('[MarketData] 订阅列表已更新，数量:', newSubs.length)
}, { deep: true })

// 监听 tickerData 变化 - 不需要 deep 选项，因为我们创建新对象引用
watch(tickerData, (newData) => {
  const keys = Object.keys(newData || {})
  console.log('[MarketData] tickerData 已更新，keys:', keys.length)
  // 检查每个订阅的 symbol 是否能访问到数据
  subscriptions.value.forEach(sub => {
    const ticker = newData[sub.symbol]
    console.log(`[MarketData] ${sub.symbol}:`, ticker ? `price=$${ticker.price}` : '无数据')
  })
})

// 监听 activeTickers 变化
watch(activeTickers, (newTickers) => {
  console.log('[MarketData] activeTickers changed:', newTickers.length, 'items')
  newTickers.forEach(item => {
    console.log(`[MarketData] activeTicker: ${item.symbol}, price=$${item.price}`)
  })
})

// 生命周期
onMounted(async () => {
  await loadPairs()
  await loadSubscriptions()
  connectWebSocket()
  startAllTickersPolling()
})

onUnmounted(() => {
  disconnectWebSocket()
  stopAllTickersPolling()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-actions {
  display: flex;
  gap: 12px;
}

/* 按钮 */

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

/* 标签 */

/* 统计卡片 */

.stat-primary {
  color: #1890ff;
}

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.header-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.filter-select {
  padding: 6px 12px;
  background: #0f0f1a;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: #1890ff;
}

.search-input {
  padding: 6px 12px;
  background: #0f0f1a;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: #1890ff;
}

/* 交易对列表 */
.pairs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pair-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #0f0f1a;
  border-radius: 4px;
  transition: all 0.2s;
}

.pair-item:hover {
  background: #1a1a2e;
}

.pair-item.subscribed {
  background: rgba(24, 144, 255, 0.1);
  border: 1px solid rgba(24, 144, 255, 0.3);
}

.pair-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pair-symbol {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.pair-state {
  font-size: 12px;
  color: #52c41a;
}

.pair-price {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  flex: 1;
  justify-content: center;
}

.price-label, .volume-label {
  color: #8a8a9a;
}

.price-value {
  font-weight: 600;
  font-size: 13px;
}

.volume-value {
  color: #8a8a9a;
}

/* 数据类型按钮 */
.ticker-types {
  display: flex;
  gap: 8px;
}

/* WebSocket 控制按钮 */
.ws-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.ws-toggle-btn {
  padding: 6px 12px;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  background: transparent;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.ws-toggle-btn.connected {
  border-color: #52c41a;
  background: rgba(82, 196, 26, 0.1);
  color: #52c41a;
}

.ws-toggle-btn.disconnected {
  border-color: #f5222d;
  background: rgba(245, 34, 45, 0.1);
  color: #f5222d;
}

.ws-toggle-btn:hover {
  opacity: 0.8;
}

.type-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.type-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #ffffff;
}

/* 表格 */
.ticker-table table {
  width: 100%;
  border-collapse: collapse;
}

.ticker-table th {
  text-align: left;
  padding: 8px;
  font-size: 12px;
  color: #8a8a9a;
  border-bottom: 1px solid #2a2a3e;
}

.ticker-table td {
  padding: 8px;
  font-size: 13px;
  color: #ffffff;
  border-bottom: 1px solid #1a1a2e;
}

/* 优先级：价格颜色类覆盖表格默认颜色 */
.ticker-table td.text-success {
  color: #52c41a !important;
}

.ticker-table td.text-danger {
  color: #f5222d !important;
}

.text-success {
  color: #52c41a;
}

.text-danger {
  color: #f5222d;
}

/* 价格闪烁动画 */
.price-cell {
  transition: background-color 0.3s ease;
}

.flash-up {
  animation: flashGreen 0.5s ease-out;
}

.flash-down {
  animation: flashRed 0.5s ease-out;
}

@keyframes flashGreen {
  0% {
    background-color: rgba(82, 196, 26, 0.4);
  }
  100% {
    background-color: transparent;
  }
}

@keyframes flashRed {
  0% {
    background-color: rgba(245, 34, 45, 0.4);
  }
  100% {
    background-color: transparent;
  }
}

/* 状态提示 */
.loading, .disconnected, .empty {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

/* 响应式 */
@media (max-width: 1200px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-actions {
    width: 100%;
  }
}
</style>
