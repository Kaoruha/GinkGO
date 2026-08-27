<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-blue">市场数据</span>
      交易对订阅管理
    </template>
    <template #actions>
      <button
        class="btn-primary"
        @click="refreshPairs"
      >
        刷新交易对
      </button>
      <button
        class="btn-secondary"
        @click="toggleWebSocket"
      >
        {{ wsConnected ? '已连接' : '连接' }}
      </button>
    </template>

    <!-- 行情服务不可用:后端 market 模块缺失,已停自动轮询/重连,手动刷新可重试 -->
    <div
      v-if="serviceUnavailable"
      class="service-unavailable"
    >
      行情服务不可用：后端尚未提供 market 接口（/api/v1/market/* 404）。已停止自动轮询与实时连接，可点"刷新交易对"重试。
    </div>

    <!-- 订阅统计 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">
          总交易对
        </div>
        <div class="stat-value">
          {{ totalPairs }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">
          已订阅
        </div>
        <div class="stat-value stat-primary">
          {{ subscriptions.length }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">
          API 连接
        </div>
        <div
          class="stat-value"
          :class="wsConnected ? 'stat-success' : 'stat-danger'"
        >
          {{ wsConnected ? '已连接' : '未连接' }}
        </div>
      </div>
      <!-- 实时数据状态 -->
      <div class="stat-card">
        <div class="stat-label">
          实时数据
        </div>
        <div
          class="stat-value"
          :class="tickerDataKeysCount > 0 ? 'stat-success' : 'stat-danger'"
        >
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
            <select
              v-model="selectedQuoteCurrency"
              class="filter-select"
            >
              <option value="">
                全部币种
              </option>
              <option value="USDT">
                USDT
              </option>
              <option value="USD">
                USD
              </option>
              <option value="BTC">
                BTC
              </option>
              <option value="ETH">
                ETH
              </option>
              <option value="USDC">
                USDC
              </option>
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
          <div
            v-if="loadingPairs"
            class="loading"
          >
            加载中...
          </div>
          <div
            v-else
            class="pairs-list"
          >
            <div
              v-for="pair in filteredPairs"
              :key="pair.symbol"
              class="pair-item"
              :class="{ subscribed: isSubscribed(pair.symbol) }"
              @contextmenu="openPairMenu($event, pair)"
            >
              <div class="pair-info">
                <span class="pair-symbol">{{ pair.symbol }}</span>
                <span class="pair-state">{{ pair.state }}</span>
              </div>
              <div
                v-if="getPairTicker(pair.symbol)"
                class="pair-price"
              >
                <span class="price-label">价格:</span>
                <span
                  class="price-value"
                  :class="getPairPriceClass(pair.symbol)"
                >
                  {{ formatPrice(getPairPrice(pair.symbol)) }}
                </span>
                <span class="volume-label">成交量:</span>
                <span class="volume-value">{{ formatVolume(getPairVolume(pair.symbol)) }}</span>
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
              :class="{ connected: wsConnected, disconnected: !wsConnected }"
              class="ws-toggle-btn"
              @click="toggleWebSocket"
            >
              {{ wsConnected ? '🟢 已连接' : '🔴 未连接' }}
            </button>
          </div>
        </div>
        <div class="card-body">
          <div
            v-if="!wsConnected"
            class="disconnected"
          >
            WebSocket 未连接，无法获取实时数据
          </div>
          <div
            v-else-if="activeTickers.length === 0"
            class="empty"
          >
            暂无数据，请先订阅交易对
          </div>
          <div
            v-else-if="tickerDataForTemplate"
            class="ticker-table"
          >
            <table>
              <thead>
                <tr>
                  <th>交易对</th>
                  <th class="num">
                    最新价
                  </th>
                  <th class="num">
                    买一价
                  </th>
                  <th class="num">
                    卖一价
                  </th>
                  <th class="num">
                    24H涨跌
                  </th>
                  <th class="num">
                    24H成交量
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="sub in subscriptions"
                  :key="sub.symbol"
                >
                  <td>{{ sub.symbol }}</td>
                  <td
                    class="price-cell num"
                    :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]"
                  >
                    {{ tickerDataForTemplate[sub.symbol]?.price ? tickerDataForTemplate[sub.symbol].price.toFixed(3) : '-' }}
                  </td>
                  <td
                    class="price-cell num"
                    :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]"
                  >
                    {{ tickerDataForTemplate[sub.symbol]?.bid_price ? tickerDataForTemplate[sub.symbol].bid_price.toFixed(3) : '-' }}
                  </td>
                  <td
                    class="price-cell num"
                    :class="[getPriceAnimationClass(sub.symbol), getPairPriceClass(sub.symbol)]"
                  >
                    {{ tickerDataForTemplate[sub.symbol]?.ask_price ? tickerDataForTemplate[sub.symbol].ask_price.toFixed(3) : '-' }}
                  </td>
                  <td
                    class="change-cell num"
                    :class="get24hChangeClass(sub.symbol)"
                  >
                    {{ format24hChange(tickerDataForTemplate[sub.symbol]) }}
                  </td>
                  <td class="num">
                    {{ formatTickerVolume(tickerDataForTemplate[sub.symbol]?.volume_24h) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { marketApi, type TradingPair, type MarketSubscription, DataType } from '@/api/modules/market'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import { usePolling, useAsyncAction } from '@/composables'
import { createReconnectingSocket } from '@/composables/reconnectingSocket'

/** 交易对卡片右键菜单(替代卡片内订阅按钮) */
const { open: openCtxMenu } = useContextMenu()
const openPairMenu = (e: MouseEvent, pair: TradingPair) => {
  openCtxMenu(e, [
    ...(isSubscribed(pair.symbol)
      ? [{ label: '取消订阅', action: () => unsubscribe(pair.symbol) }]
      : [{ label: '订阅', action: () => subscribe(pair.symbol) }]),
    { label: '复制交易对', action: () => { navigator.clipboard.writeText(pair.symbol); toast.success('已复制') } },
  ])
}

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
// 双形态对齐 request.ts 契约:Electron 优先 window.appConfig.apiBase,浏览器回退 env
// 注:apiBase 为 HTTP 格式(http://host:port),wsUrl 内 new URL + protocol 转换
const wsUrl = () => {
  const apiBase = window.appConfig?.apiBase || import.meta.env.VITE_API_BASE_URL || ''
  const url = new URL(apiBase || `${window.location.protocol}//${window.location.hostname}:8000`)
  const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${url.host}/ws`
}
const wsConnected = ref(false)
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
// 行情服务不可用(后端 market 模块缺失,接口 404):
// 停止 5s 轮询与 WS 重连,避免无谓重试刷屏;手动"刷新交易对"成功后自动恢复
const serviceUnavailable = ref(false)

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

const { run: subscribe } = useAsyncAction(async (symbol: string) => {
  await marketApi.createSubscription({
    exchange: 'okx',
    symbol,
    data_types: ['ticker']
  })
  await loadSubscriptions()
  subscribeWs(symbol)
}, { success: false })

const { run: unsubscribe } = useAsyncAction(async (symbol: string) => {
  const sub = subscriptions.value.find(s => s.symbol === symbol)
  if (!sub) return
  await marketApi.deleteSubscription(sub.uuid)
  await loadSubscriptions()
  unsubscribeWs(symbol)
}, { success: false })

const refreshPairs = async () => {
  await loadPairs()
}

// 404 = 后端无 market 模块,标记不可用并停掉轮询/WS 重连
const markUnavailableIf404 = (error: any): boolean => {
  if (error?.response?.status === 404) {
    serviceUnavailable.value = true
    stopTickersPolling()
    sock.disconnect()
    return true
  }
  return false
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
    // 拦截器已拆信封:resolve 即 {pairs} payload
    const response = await marketApi.getTradingPairs(params)
    pairs.value = response?.pairs || []
    // 后端恢复(手动刷新成功)则解除降级
    serviceUnavailable.value = false
  } catch (error) {
    if (!markUnavailableIf404(error)) console.error('加载交易对失败:', error)
  } finally {
    loadingPairs.value = false
  }
}

const loadSubscriptions = async () => {
  try {
    // 拦截器已拆信封:resolve 即 {subscriptions} payload
    const response = await marketApi.getSubscriptions()
    subscriptions.value = response?.subscriptions || []
  } catch (error) {
    if (!markUnavailableIf404(error)) console.error('加载订阅失败:', error)
  }
}

const loadAllTickers = async () => {
  try {
    const response: any = await marketApi.getAllTickers({
      exchange: 'okx',
      environment: 'production'
    })
    // 拦截器已拆信封:resolve 即 {tickers} payload
    const newTickers = response?.tickers || {}

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
  } catch (error) {
    // 404 已停轮询;其他错误静默(轮询读接口,toast 会刷屏)
    if (!markUnavailableIf404(error)) console.error('加载所有 ticker 失败:', error)
  }
}

// ticker 轮询闸门:服务降级期不发请求直接停轮询(手动刷新恢复后重启)
const pollAllTickers = async () => {
  if (serviceUnavailable.value) return stopTickersPolling()
  await loadAllTickers()
}
// 5s 轮询(usePolling 自带卸载清理 + 可见性暂停;不 immediate——
// 首拉时序保持原版:onMounted 先判 404 降级,可用时才手动拉第一次)
const { start: startTickersPolling, stop: stopTickersPolling } = usePolling(pollAllTickers, 5000)

/** WS 消息处理:market_data/ticker → 价格方向/闪烁动画/tickerData 就地更新 */
const handleWsMessage = (raw: string) => {
  try {
    const message = JSON.parse(raw)

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
    }
  } catch (error: any) {
    console.error('[WS] 错误:', error.message)
  }
}

// 可重连 socket(重连延迟固定 5s 与原实现等价;enabled 闸门=服务降级期停重试)
const sock = createReconnectingSocket({
  url: wsUrl,
  onMessage: handleWsMessage,
  onStatusChange: (connected) => {
    wsConnected.value = connected
    // (重)连接成功后重新订阅已保存的交易对(原 onopen 语义)
    if (connected) {
      subscriptions.value.forEach(sub => {
        subscribeWs(sub.symbol)
      })
    }
  },
  enabled: () => !serviceUnavailable.value,
})

const toggleWebSocket = () => {
  if (wsConnected.value) {
    sock.disconnect()
  } else {
    sock.connect()
  }
}

const subscribeWs = (symbol: string) => {
  sock.send(JSON.stringify({
    action: 'subscribe',
    symbols: [symbol],
    data_types: ['ticker']
  }))
}

const unsubscribeWs = (symbol: string) => {
  sock.send(JSON.stringify({
    action: 'unsubscribe',
    symbols: [symbol]
  }))
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

// formatTickerVolume 与 formatVolume 逻辑逐字节相同(模板两处历史命名),复用同一实现
const formatTickerVolume = formatVolume

// 监听计价货币变化
watch(selectedQuoteCurrency, async () => {
  await loadPairs()
})

// 生命周期
onMounted(async () => {
  await loadPairs()
  await loadSubscriptions()
  // 后端 market 模块缺失(404)时不再起 WS 重连循环与 5s 轮询
  if (serviceUnavailable.value) return
  sock.connect()
  loadAllTickers()
  startTickersPolling()
})

onUnmounted(() => {
  sock.disconnect()
})
</script>

<style scoped>
/* 行情服务不可用降级提示 */
.service-unavailable {
  padding: 12px 16px;
  margin-bottom: 16px;
  border: 1px solid hsl(var(--warning-border, hsl(var(--border))));
  border-left: 3px solid hsl(var(--primary));
  border-radius: var(--radius-sm);
  background: hsl(var(--muted));
  color: hsl(var(--foreground));
  font-size: 13px;
}

/* 按钮 */

.btn-sm {
  padding: 4px 12px;
  font-size: 12px;
}

/* 标签 */

/* 统计卡片 */

.stat-primary {
  color: hsl(var(--primary));
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
  background: hsl(var(--background));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 14px;
  outline: none;
  cursor: pointer;
}

.filter-select:focus {
  border-color: hsl(var(--primary));
}

.search-input {
  padding: 6px 12px;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 14px;
  outline: none;
}

.search-input:focus {
  border-color: hsl(var(--primary));
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
  background: hsl(var(--background));
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.pair-item:hover {
  background: hsl(var(--card));
}

.pair-item.subscribed {
  background: hsl(var(--primary) / 0.1);
  border: 1px solid hsl(var(--primary) / 0.3);
}

.pair-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pair-symbol {
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.pair-state {
  font-size: 12px;
  color: hsl(var(--success));
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
  color: hsl(var(--muted-foreground));
}

.price-value {
  font-weight: 600;
  font-size: 13px;
}

.volume-value {
  color: hsl(var(--muted-foreground));
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
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--foreground));
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.ws-toggle-btn.connected {
  border-color: hsl(var(--success));
  background: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
}

.ws-toggle-btn.disconnected {
  border-color: hsl(var(--error));
  background: hsl(var(--error) / 0.1);
  color: hsl(var(--error));
}

.ws-toggle-btn:hover {
  opacity: 0.8;
}

.type-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
}

.type-btn.active {
  background: hsl(var(--primary));
  border-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

/* 表格 */
.ticker-table table {
  width: 100%;
  border-collapse: collapse;
}

.ticker-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--card));
  text-align: left;
  padding: 8px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  border-bottom: 1px solid hsl(var(--border));
}

.ticker-table td {
  padding: 8px;
  font-size: 13px;
  color: hsl(var(--foreground));
  border-bottom: 1px solid hsl(var(--card));
}

/* 优先级：价格颜色类覆盖表格默认颜色 */
.ticker-table td.text-success {
  color: hsl(var(--success)) !important;
}

.ticker-table td.text-danger {
  color: hsl(var(--error)) !important;
}

.text-success {
  color: hsl(var(--success));
}

.text-danger {
  color: hsl(var(--error));
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
    background-color: hsl(var(--success) / 0.4);
  }
  100% {
    background-color: transparent;
  }
}

@keyframes flashRed {
  0% {
    background-color: hsl(var(--error) / 0.4);
  }
  100% {
    background-color: transparent;
  }
}

/* 状态提示 */
.loading, .disconnected, .empty {
  text-align: center;
  padding: 40px;
  color: hsl(var(--muted-foreground));
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
}
</style>
