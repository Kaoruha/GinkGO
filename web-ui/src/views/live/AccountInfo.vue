<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Wallet, TrendingUp, TrendingDown, AlertCircle, DollarSign, Coins, Clock, Activity } from 'lucide-vue-next'
import { liveAccountApi } from '@/api'

// Types
interface BalanceInfo {
  total_equity: string
  available_balance: string
  frozen_balance: string
  currency_balances: Array<{
    currency: string
    available: string
    frozen: string
    balance: string
  }>
}

interface PositionInfo {
  symbol: string
  side: 'long' | 'short'
  size: string
  avg_price: string
  current_price: string
  unrealized_pnl: string
  unrealized_pnl_percentage: string
  margin: string
  is_spot?: boolean  // 标记为现货持仓（币种余额）
}

interface AccountData {
  uuid: string
  name: string
  exchange: string
  environment: string
  status: string
  balance?: BalanceInfo
  positions?: PositionInfo[]
  last_update?: string
  error?: string
}

// 状态
const accounts = ref<AccountData[]>([])
const loading = ref(true)
const refreshing = ref(false)
const accountLoadingStates = ref<Record<string, { balance: boolean; positions: boolean }>>({})

// 刷新定时器
let refreshInterval: ReturnType<typeof setInterval> | null = null

// 统计数据
const totalEquity = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.balance) {
      const value = parseFloat(acc.balance.total_equity || '0')
      return sum + (isNaN(value) ? 0 : value)
    }
    return sum
  }, 0)
})

const totalAvailable = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.balance) {
      const value = parseFloat(acc.balance.available_balance || '0')
      return sum + (isNaN(value) ? 0 : value)
    }
    return sum
  }, 0)
})

const totalPositions = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.positions && Array.isArray(acc.positions)) {
      return sum + acc.positions.length
    }
    return sum
  }, 0)
})

// 加载账户信息（首次加载）
const loadAccountInfo = async () => {
  try {
    const response = await liveAccountApi.getAccounts() as any
    console.log('getAccounts response:', response)
    if (response?.code === 0) {
      // 分页响应中，账号列表在 data.accounts 中
      const accountList = response.data?.accounts || response.data || []
      console.log('Account list:', accountList)

      // 创建账户对象（保持引用稳定）
      const newAccounts: AccountData[] = accountList.map((account: any) => ({
        uuid: account.uuid,
        name: account.name,
        exchange: account.exchange,
        environment: account.environment,
        status: account.status,
        balance: undefined,
        positions: undefined,
        last_update: undefined,
        error: undefined
      }))

      accounts.value = newAccounts

      // 初始化加载状态
      accountLoadingStates.value = {}
      newAccounts.forEach(account => {
        accountLoadingStates.value[account.uuid] = { balance: true, positions: true }
      })

      // 异步加载每个账户的详细信息（不阻塞 UI）
      Promise.all(
        newAccounts.map(account => updateAccountDetails(account))
      ).finally(() => {
        loading.value = false
      })
    }
  } catch (error) {
    console.error('Failed to load account info:', error)
    loading.value = false
  }
}

// 更新单个账户的详细信息（通过替换对象触发响应式更新）
const updateAccountDetails = async (account: AccountData) => {
  const accountId = account.uuid
  // 设置加载状态
  if (accountLoadingStates.value[accountId]) {
    accountLoadingStates.value[accountId].balance = true
    accountLoadingStates.value[accountId].positions = true
  }

  try {
    const [balanceRes, positionsRes] = await liveAccountApi.getAccountInfo(accountId) as [any, any]

    // 调试日志
    console.log(`[${accountId}] Balance response:`, balanceRes)
    console.log(`[${accountId}] Positions response:`, positionsRes)

    // 创建更新后的账户对象
    const updatedAccount: AccountData = {
      ...account,
      last_update: new Date().toISOString(),
      error: undefined
    }

    if (balanceRes?.code === 0) {
      updatedAccount.balance = balanceRes.data
      console.log(`[${accountId}] Updated balance:`, updatedAccount.balance)
    } else {
      console.warn(`[${accountId}] Balance response code:`, balanceRes?.code)
    }

    if (positionsRes?.code === 0) {
      // 合并现货持仓（币种余额）和合约持仓
      const contractPositions = positionsRes.data?.positions || []
      const spotPositions = balanceRes.data?.spot_positions || []
      updatedAccount.positions = [...spotPositions, ...contractPositions]
      console.log(`[${accountId}] Updated positions:`, updatedAccount.positions)
    } else {
      console.warn(`[${accountId}] Positions response code:`, positionsRes?.code)
    }

    // 在数组中找到索引并替换整个对象，触发响应式更新
    const index = accounts.value.findIndex(a => a.uuid === accountId)
    if (index !== -1) {
      accounts.value[index] = updatedAccount
      console.log(`[${accountId}] Account updated at index ${index}`)
    }

    // 清除加载状态
    if (accountLoadingStates.value[accountId]) {
      accountLoadingStates.value[accountId].balance = false
      accountLoadingStates.value[accountId].positions = false
    }
  } catch (e) {
    console.error(`Failed to load info for ${accountId}:`, e)
    // 更新错误状态
    const index = accounts.value.findIndex(a => a.uuid === accountId)
    if (index !== -1) {
      accounts.value[index] = {
        ...accounts.value[index],
        error: '加载失败'
      }
    }
    // 加载失败时也清除加载状态
    if (accountLoadingStates.value[accountId]) {
      accountLoadingStates.value[accountId].balance = false
      accountLoadingStates.value[accountId].positions = false
    }
  }
}

// 刷新单个账户
const refreshAccount = async (accountId: string) => {
  const account = accounts.value.find(a => a.uuid === accountId)
  if (!account) return

  await updateAccountDetails(account)
}

// 刷新全部（只更新数据，不重新创建对象）
const refreshAll = async () => {
  refreshing.value = true
  try {
    // 只更新每个账户的数据，不重新加载账号列表
    await Promise.all(
      accounts.value.map(account => updateAccountDetails(account))
    )
  } finally {
    refreshing.value = false
  }
}

// 格式化数字
const formatNumber = (num: string | number, decimals = 2) => {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return '0.00'
  return n.toFixed(decimals)
}

// 格式化货币
const formatCurrency = (num: string) => {
  return formatNumber(num, 2)
}

// 获取未实现盈亏颜色
const getPnLColor = (pnl: string) => {
  const n = parseFloat(pnl)
  if (isNaN(n)) return 'text-gray-400'
  if (n > 0) return 'text-green-400'
  if (n < 0) return 'text-red-400'
  return 'text-gray-400'
}

// 获取交易所图标样式
const getExchangeIcon = (exchange: string) => {
  const icons: Record<string, string> = {
    okx: '🔷',
    binance: '🟡',
    bybit: '⚡'
  }
  return icons[exchange.toLowerCase()] || '💱'
}

// 获取环境样式
const getEnvironmentVariant = (environment: string) => {
  return environment === 'production' ? 'destructive' : 'secondary'
}

// 组件挂载
onMounted(() => {
  loadAccountInfo()
  // 每10秒自动刷新数据（不重新创建对象，只更新数据）
  refreshInterval = setInterval(refreshAll, 10000)
})

// 组件卸载
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="account-info-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="title-section">
          <div class="page-icon">
            <Wallet class="w-6 h-6" />
          </div>
          <div>
            <h1 class="page-title">实盘账户信息</h1>
            <p class="page-subtitle">实时监控账户余额与持仓</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          :disabled="refreshing"
          @click="refreshAll"
          class="refresh-button"
        >
          <RefreshCw :class="['w-4 h-4 mr-2', refreshing && 'animate-spin']" />
          刷新
        </Button>
      </div>
    </div>

    <!-- 加载状态：仅首次加载且无账户时显示 -->
    <div v-if="loading && accounts.length === 0" class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载账户信息...</p>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && accounts.length === 0" class="empty-state">
      <Wallet class="w-16 h-16 mx-auto mb-4 opacity-30" />
      <p class="empty-text">暂无实盘账户</p>
      <p class="empty-hint">请先配置实盘账号</p>
    </div>

    <!-- 账户内容 -->
    <div v-else class="account-content">
      <!-- 全局统计卡片 -->
      <div class="stats-section">
        <div class="stats-grid">
          <div class="stat-card primary">
            <div class="stat-icon">
              <DollarSign class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">总权益</div>
              <div class="stat-value">${{ formatNumber(totalEquity) }}</div>
            </div>
          </div>

          <div class="stat-card success">
            <div class="stat-icon">
              <Coins class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">可用余额</div>
              <div class="stat-value">${{ formatNumber(totalAvailable) }}</div>
            </div>
          </div>

          <div class="stat-card info">
            <div class="stat-icon">
              <Activity class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">持仓数量</div>
              <div class="stat-value">{{ totalPositions }}</div>
            </div>
          </div>

          <div class="stat-card neutral">
            <div class="stat-icon">
              <Clock class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">账户数量</div>
              <div class="stat-value">{{ accounts.length }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 账户卡片列表 -->
      <div class="accounts-section">
        <div
          v-for="account in accounts"
          :key="account.uuid"
          class="account-card"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <div class="account-info">
              <div class="account-name">
                <span class="exchange-icon">{{ getExchangeIcon(account.exchange) }}</span>
                <h3>{{ account.name }}</h3>
              </div>
              <div class="account-meta">
                <Badge :variant="getEnvironmentVariant(account.environment)" class="env-badge">
                  {{ account.environment }}
                </Badge>
                <Badge :variant="account.status === 'enabled' ? 'success' : 'secondary'" class="status-badge">
                  {{ account.status === 'enabled' ? '运行中' : '已停用' }}
                </Badge>
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              @click="refreshAccount(account.uuid)"
              class="card-refresh"
            >
              <RefreshCw class="w-4 h-4" />
            </Button>
          </div>

          <!-- 错误提示 -->
          <div v-if="account.error" class="error-banner">
            <AlertCircle class="w-4 h-4" />
            <span>{{ account.error }}</span>
          </div>

          <!-- 余额信息 -->
          <div class="balance-section">
            <!-- 骨架屏：余额加载中 -->
            <div v-if="accountLoadingStates[account.uuid]?.balance && !account.balance" class="skeleton-grid">
              <div v-for="i in 3" :key="i" class="skeleton-item">
                <div class="skeleton-line skeleton-label"></div>
                <div class="skeleton-line skeleton-value"></div>
              </div>
            </div>

            <!-- 实际余额数据 -->
            <div v-else-if="account.balance">
            <div class="balance-grid">
              <div class="balance-item">
                <div class="balance-label">总权益</div>
                <div class="balance-value primary">
                  ${{ formatCurrency(account.balance.total_equity) }}
                </div>
              </div>
              <div class="balance-item">
                <div class="balance-label">可用余额</div>
                <div class="balance-value success">
                  ${{ formatCurrency(account.balance.available_balance) }}
                </div>
              </div>
              <div class="balance-item">
                <div class="balance-label">冻结余额</div>
                <div class="balance-value warning">
                  ${{ formatCurrency(account.balance.frozen_balance) }}
                </div>
              </div>
            </div>

            <!-- 币种余额 -->
            <div v-if="account.balance.currency_balances?.length > 0" class="currency-balances">
              <div
                v-for="cb in account.balance.currency_balances.filter(c => parseFloat(c.available) > 0 || parseFloat(c.frozen) > 0)"
                :key="cb.currency"
                class="currency-item"
              >
                <span class="currency-name">{{ cb.currency }}</span>
                <span class="currency-amount">
                  <span class="available">{{ formatNumber(cb.available) }}</span>
                  <span v-if="parseFloat(cb.frozen) > 0" class="frozen">
                    (冻结: {{ formatNumber(cb.frozen) }})
                  </span>
                </span>
              </div>
            </div>
            </div>
          </div>

          <!-- 持仓信息（包含现货余额） -->
          <div class="positions-section">
            <!-- 骨架屏：持仓加载中 -->
            <div v-if="accountLoadingStates[account.uuid]?.positions && !account.positions" class="skeleton-positions">
              <div v-for="i in 2" :key="i" class="skeleton-position">
                <div class="skeleton-line skeleton-position-title"></div>
                <div class="skeleton-position-details">
                  <div v-for="j in 4" :key="j" class="skeleton-line"></div>
                </div>
              </div>
            </div>

            <!-- 实际持仓数据 -->
            <template v-else-if="account.positions?.length > 0">
            <div class="section-title">
              <Activity class="w-4 h-4 mr-2" />
              持仓信息 ({{ account.positions.length }})
            </div>
            <div class="positions-list">
              <div
                v-for="position in account.positions"
                :key="position.symbol"
                :class="['position-item', position.is_spot ? 'spot-position' : 'contract-position']"
              >
                <div class="position-header">
                  <div class="position-title">
                    <span class="position-symbol">{{ position.symbol }}</span>
                    <!-- 现货持仓特殊标识 -->
                    <Badge v-if="position.is_spot" variant="secondary" class="spot-badge">
                      💰 现货
                    </Badge>
                    <Badge :variant="position.side === 'long' ? 'success' : 'destructive'">
                      {{ position.side === 'long' ? '做多' : '做空' }}
                    </Badge>
                  </div>
                </div>
                <div class="position-details">
                  <!-- 统一的持仓信息显示 -->
                  <div class="position-stat">
                    <span class="stat-label">数量</span>
                    <span class="stat-value">{{ formatNumber(position.size) }}</span>
                  </div>
                  <div class="position-stat">
                    <span class="stat-label">成本价</span>
                    <span class="stat-value">${{ formatNumber(position.avg_price) }}</span>
                  </div>
                  <div class="position-stat">
                    <span class="stat-label">现价</span>
                    <span class="stat-value">${{ formatNumber(position.current_price) }}</span>
                  </div>
                  <div class="position-stat pnl">
                    <span class="stat-label">盈亏</span>
                    <span :class="['stat-value', getPnLColor(position.unrealized_pnl)]">
                      <TrendingUp v-if="parseFloat(position.unrealized_pnl) > 0" class="w-3 h-3 inline mr-1" />
                      <TrendingDown v-else-if="parseFloat(position.unrealized_pnl) < 0" class="w-3 h-3 inline mr-1" />
                      {{ formatNumber(position.unrealized_pnl) }}
                      <span class="pnl-percent">({{ formatNumber(position.unrealized_pnl_percentage, 3) }}%)</span>
                    </span>
                  </div>
                </div>
              </div>
            </div>
            </template>

            <!-- 无持仓 -->
            <div v-else-if="!accountLoadingStates[account.uuid]?.positions" class="no-positions">
              <Activity class="w-4 h-4 mr-2" />
              <span class="text-gray-500">暂无持仓</span>
            </div>
          </div>

          <!-- 卡片底部 -->
          <div class="card-footer">
            <Clock class="w-3 h-3 mr-1" />
            <span class="update-time">
              最后更新: {{ account.last_update ? new Date(account.last_update).toLocaleString() : '-' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.account-info-page {
  padding: 0;
  background: transparent;
}

/* 页面头部 */
.page-header {
  margin-bottom: 24px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 4px 0 0 0;
}

.refresh-button {
  border-color: #2a2a3e;
  color: #8a8a9a;
}

.refresh-button:hover:not(:disabled) {
  border-color: #667eea;
  color: #667eea;
}

/* 加载状态 */

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: #8a8a9a;
}

.empty-text {
  font-size: 16px;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: #666;
}

/* 账户内容 */
.account-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片 */
.stats-section {
  margin-bottom: 8px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  border-radius: 10px;
  color: #667eea;
}

.stat-card.primary .stat-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-card.success .stat-icon {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
  color: white;
}

.stat-card.info .stat-icon {
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  color: white;
}

.stat-card.neutral .stat-icon {
  background: linear-gradient(135deg, #8a8a9a 0%, #5a5a6a 100%);
  color: white;
}

.stat-content {
  flex: 1;
}

/* 账户卡片 */
.accounts-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.account-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.account-card:hover {
  border-color: #2a2a3e;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.account-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.exchange-icon {
  font-size: 24px;
}

.account-name h3 {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.account-meta {
  display: flex;
  gap: 8px;
}

.env-badge,
.status-badge {
  font-size: 12px;
}

.card-refresh {
  color: #8a8a9a;
}

.card-refresh:hover {
  color: #667eea;
}

/* 错误提示 */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 20px;
  padding: 12px;
  background: rgba(255, 77, 79, 0.1);
  border-left: 3px solid #ff4d4f;
  color: #ff4d4f;
  font-size: 14px;
}

/* 余额部分 */
.balance-section {
  padding: 20px;
  border-bottom: 1px solid #2a2a3e;
}

.balance-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.balance-item {
  background: #121226;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid #2a2a3e;
  transition: all 0.2s ease;
}

.balance-item:hover {
  border-color: #667eea;
}

.balance-label {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.balance-value {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.balance-value.primary {
  color: #667eea;
}

.balance-value.success {
  color: #52c41a;
}

.balance-value.warning {
  color: #faad14;
}

/* 币种余额 */
.currency-balances {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.currency-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #121226;
  border-radius: 8px;
  font-size: 14px;
}

.currency-name {
  font-weight: 600;
  color: #ffffff;
}

.currency-amount {
  color: #8a8a9a;
}

.currency-amount .available {
  color: #52c41a;
}

.currency-amount .frozen {
  color: #faad14;
  font-size: 12px;
}

/* 持仓部分 */
.positions-section {
  padding: 20px;
  border-bottom: 1px solid #2a2a3e;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  color: #8a8a9a;
  margin-bottom: 16px;
}

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.position-item {
  background: #121226;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 16px;
  transition: all 0.2s ease;
}

.position-item:hover {
  border-color: #2a2a3e;
  background: #1a1a30;
}

.position-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.position-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.position-symbol {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.position-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.position-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.position-stat .stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.position-stat .stat-value {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.position-stat.pnl .stat-value {
  display: flex;
  align-items: center;
}

.pnl-percent {
  font-size: 12px;
  margin-left: 4px;
  opacity: 0.8;
}

.no-positions {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #666;
  font-size: 14px;
}

/* 卡片底部 */

.update-time {
  font-size: 12px;
  color: #666;
}

/* 骨架屏加载样式 */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.skeleton-item {
  background: #121226;
  border-radius: 10px;
  padding: 16px;
  border: 1px solid #2a2a3e;
}

.skeleton-line {
  background: linear-gradient(90deg, #2a2a3e 25%, #3a3a4e 50%, #2a2a3e 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-label {
  height: 12px;
  width: 60px;
  margin-bottom: 12px;
}

.skeleton-value {
  height: 24px;
  width: 100px;
}

.skeleton-positions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-position {
  background: #121226;
  border: 1px solid #2a2a3e;
  border-radius: 10px;
  padding: 16px;
}

.skeleton-position-title {
  height: 16px;
  width: 120px;
  margin-bottom: 12px;
}

.skeleton-position-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.skeleton-position-details .skeleton-line {
  height: 32px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .balance-grid {
    grid-template-columns: 1fr;
  }

  .position-details {
    grid-template-columns: repeat(2, 1fr);
  }

  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
}
</style>
