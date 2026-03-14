<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Wallet, TrendingUp, TrendingDown, AlertCircle } from 'lucide-vue-next'

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

// 刷新定时器
let refreshInterval: ReturnType<typeof setInterval> | null = null

// 加载账户信息
const loadAccountInfo = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/v1/accounts/')
    if (response.ok) {
      const result = await response.json()
      const accountList = result.data || []

      // 获取每个账户的余额和持仓信息
      const enrichedAccounts = await Promise.all(
        accountList.map(async (account: any) => {
          const enriched: AccountData = {
            uuid: account.uuid,
            name: account.name,
            exchange: account.exchange,
            environment: account.environment,
            status: account.status
          }

          // 获取余额信息
          try {
            const balanceResponse = await fetch(`/api/v1/accounts/${account.uuid}/balance`)
            if (balanceResponse.ok) {
              const balanceResult = await balanceResponse.json()
              enriched.balance = balanceResult.data
            }
          } catch (e) {
            console.error(`Failed to load balance for ${account.uuid}:`, e)
          }

          // TODO: 获取持仓信息（需要后端API支持）
          // enriched.positions = ...

          enriched.last_update = new Date().toISOString()
          return enriched
        })
      )

      accounts.value = enrichedAccounts
    }
  } catch (error) {
    console.error('Failed to load account info:', error)
  } finally {
    loading.value = false
  }
}

// 刷新单个账户
const refreshAccount = async (accountId: string) => {
  const account = accounts.value.find(a => a.uuid === accountId)
  if (!account) return

  try {
    const response = await fetch(`/api/v1/accounts/${accountId}/balance`)
    if (response.ok) {
      const result = await response.json()
      account.balance = result.data
      account.last_update = new Date().toISOString()
      account.error = undefined
    }
  } catch (error) {
    console.error(`Failed to refresh account ${accountId}:`, error)
    account.error = '刷新失败'
  }
}

// 刷新全部
const refreshAll = async () => {
  refreshing.value = true
  try {
    await loadAccountInfo()
  } finally {
    refreshing.value = false
  }
}

// 格式化数字
const formatNumber = (num: string | number, decimals = 2) => {
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return '-'
  return n.toFixed(decimals)
}

// 格式化货币
const formatCurrency = (num: string) => {
  return formatNumber(num, 2)
}

// 获取未实现盈亏颜色
const getPnLColor = (pnl: string) => {
  const n = parseFloat(pnl)
  if (isNaN(n)) return 'text-muted-foreground'
  if (n > 0) return 'text-green-600'
  if (n < 0) return 'text-red-600'
  return 'text-muted-foreground'
}

// 计算总权益
const getTotalEquity = (account: AccountData) => {
  if (!account.balance) return '0.00'
  return formatCurrency(account.balance.total_equity)
}

// 计算可用余额
const getAvailableBalance = (account: AccountData) => {
  if (!account.balance) return '0.00'
  return formatCurrency(account.balance.available_balance)
}

// 计算冻结余额
const getFrozenBalance = (account: AccountData) => {
  if (!account.balance) return '0.00'
  return formatCurrency(account.balance.frozen_balance)
}

// 获取币种余额
const getCurrencyBalances = (account: AccountData) => {
  if (!account.balance?.currency_balances) return []
  return account.balance.currency_balances
}

// 组件挂载
onMounted(() => {
  loadAccountInfo()
  // 每5秒自动刷新
  refreshInterval = setInterval(loadAccountInfo, 5000)
})

// 组件卸载
onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="account-info">
    <Card>
      <CardHeader>
        <div class="flex justify-between items-center">
          <div>
            <CardTitle>实盘账户信息</CardTitle>
            <CardDescription>实时显示账户余额和持仓信息</CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            :disabled="refreshing"
            @click="refreshAll"
          >
            <RefreshCw :class="['w-4 h-4', refreshing && 'animate-spin']" />
            刷新
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-8">
          <p>加载中...</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="accounts.length === 0" class="text-center py-8 text-muted-foreground">
          <Wallet class="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>暂无实盘账户</p>
        </div>

        <!-- 账户列表 -->
        <div v-else class="space-y-6">
          <div
            v-for="account in accounts"
            :key="account.uuid"
            class="border rounded-lg p-4"
          >
            <!-- 账户头部 -->
            <div class="flex justify-between items-start mb-4">
              <div>
                <div class="flex items-center gap-2">
                  <h3 class="text-lg font-semibold">{{ account.name }}</h3>
                  <Badge :variant="account.status === 'enabled' ? 'success' : 'secondary'">
                    {{ account.status === 'enabled' ? '已启用' : '已禁用' }}
                  </Badge>
                </div>
                <p class="text-sm text-muted-foreground mt-1">
                  {{ account.exchange }} / {{ account.environment }}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                @click="refreshAccount(account.uuid)"
              >
                <RefreshCw class="w-4 h-4" />
              </Button>
            </div>

            <!-- 错误提示 -->
            <div v-if="account.error" class="mb-4 p-3 bg-destructive/10 text-destructive rounded flex items-center gap-2">
              <AlertCircle class="w-4 h-4" />
              <span class="text-sm">{{ account.error }}</span>
            </div>

            <!-- 余额信息 -->
            <div v-if="account.balance" class="grid grid-cols-3 gap-4 mb-4">
              <div class="p-3 bg-muted rounded-lg">
                <div class="text-sm text-muted-foreground">总权益</div>
                <div class="text-2xl font-bold">
                  {{ getTotalEquity(account) }}
                </div>
              </div>
              <div class="p-3 bg-muted rounded-lg">
                <div class="text-sm text-muted-foreground">可用余额</div>
                <div class="text-2xl font-bold text-green-600">
                  {{ getAvailableBalance(account) }}
                </div>
              </div>
              <div class="p-3 bg-muted rounded-lg">
                <div class="text-sm text-muted-foreground">冻结余额</div>
                <div class="text-2xl font-bold text-yellow-600">
                  {{ getFrozenBalance(account) }}
                </div>
              </div>
            </div>

            <!-- 币种余额 -->
            <div v-if="getCurrencyBalances(account).length > 0" class="mb-4">
              <h4 class="text-sm font-medium mb-2">币种余额</h4>
              <div class="grid grid-cols-2 gap-2">
                <div
                  v-for="cb in getCurrencyBalances(account)"
                  :key="cb.currency"
                  class="p-2 bg-muted rounded text-sm"
                >
                  <div class="flex justify-between">
                    <span class="font-medium">{{ cb.currency }}</span>
                    <span>{{ formatNumber(cb.balance) }}</span>
                  </div>
                  <div class="flex justify-between text-muted-foreground text-xs">
                    <span>可用: {{ formatNumber(cb.available) }}</span>
                    <span>冻结: {{ formatNumber(cb.frozen) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 持仓信息 -->
            <div v-if="account.positions && account.positions.length > 0">
              <h4 class="text-sm font-medium mb-2">持仓信息</h4>
              <div class="space-y-2">
                <div
                  v-for="position in account.positions"
                  :key="position.symbol"
                  class="p-3 border rounded-lg"
                >
                  <div class="flex justify-between items-center">
                    <div class="flex items-center gap-2">
                      <span class="font-medium">{{ position.symbol }}</span>
                      <Badge :variant="position.side === 'long' ? 'success' : 'destructive'">
                        {{ position.side === 'long' ? '做多' : '做空' }}
                      </Badge>
                    </div>
                    <div :class="['text-lg font-semibold', getPnLColor(position.unrealized_pnl)]">
                      <TrendingUp v-if="parseFloat(position.unrealized_pnl) > 0" class="w-4 h-4 inline mr-1" />
                      <TrendingDown v-else-if="parseFloat(position.unrealized_pnl) < 0" class="w-4 h-4 inline mr-1" />
                      {{ formatNumber(position.unrealized_pnl) }}
                      <span class="text-xs text-muted-foreground">({{ position.unrealized_pnl_percentage }}%)</span>
                    </div>
                  </div>
                  <div class="grid grid-cols-4 gap-2 mt-2 text-sm">
                    <div>
                      <span class="text-muted-foreground">数量:</span>
                      <span class="ml-1">{{ formatNumber(position.size) }}</span>
                    </div>
                    <div>
                      <span class="text-muted-foreground">均价:</span>
                      <span class="ml-1">{{ formatNumber(position.avg_price) }}</span>
                    </div>
                    <div>
                      <span class="text-muted-foreground">现价:</span>
                      <span class="ml-1">{{ formatNumber(position.current_price) }}</span>
                    </div>
                    <div>
                      <span class="text-muted-foreground">保证金:</span>
                      <span class="ml-1">{{ formatNumber(position.margin) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 最后更新时间 -->
            <div v-if="account.last_update" class="mt-4 text-xs text-muted-foreground">
              最后更新: {{ new Date(account.last_update).toLocaleString() }}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<style scoped>
.account-info {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>
