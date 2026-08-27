<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Download, Filter } from 'lucide-vue-next'
import PageLayout from '@/components/common/PageLayout.vue'
import DateField from '@/components/common/DateField.vue'
import { tradeHistoryApi, liveAccountApi } from '@/api'
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { formatDate } from '@/utils/format'

/** 行右键菜单(本页无行操作,给复制类) */
const { open: openCtxMenu } = useContextMenu()
const openTradeMenu = (e: MouseEvent, trade: TradeRecord) => {
  openCtxMenu(e, [
    { label: '复制交易对', action: () => { navigator.clipboard.writeText(trade.symbol); toast.success('已复制') } },
    { label: '复制订单ID', action: () => { navigator.clipboard.writeText(trade.exchange_order_id || trade.uuid); toast.success('已复制') } },
    { label: '复制成交ID', action: () => { navigator.clipboard.writeText(trade.exchange_trade_id || trade.uuid); toast.success('已复制') } },
  ])
}

// Types
interface TradeRecord {
  uuid: string
  symbol: string
  side: 'buy' | 'sell'
  price: number
  quantity: number
  quote_quantity: number | null
  fee: number | null
  fee_currency: string | null
  exchange_order_id: string | null
  exchange_trade_id: string | null
  order_type: string | null
  trade_time: string
}

interface TradeStatistics {
  total_trades: number
  buy_trades: number
  sell_trades: number
  total_quantity: number
  total_value: number
  total_fee: number
  symbols_traded: string[]
  first_trade_time: string | null
  last_trade_time: string | null
}

interface DailySummary {
  date: string
  total_trades: number
  buy_trades: number
  sell_trades: number
  total_quantity: number
  total_value: number
  total_fee: number
}

// 状态
const trades = ref<TradeRecord[]>([])
const statistics = ref<TradeStatistics | null>(null)
const dailySummary = ref<DailySummary[]>([])
const loading = ref(false)
const loadError = ref(false)  // 成交查询后端接口不可用(404=功能未实现)
const selectedAccount = ref<string | null>(null)
const accounts = ref<Array<{ uuid: string; name: string; exchange: string }>>([])
const dateFilter = reactive({
  start_date: '',
  end_date: ''
})

const showFilterDialog = ref(false)

// 计算属性
const totalVolume = computed(() => {
  return trades.value.reduce((sum, t) => sum + t.quantity, 0)
})

const totalValue = computed(() => {
  return trades.value.reduce((sum, t) => sum + (t.quote_quantity || 0), 0)
})

const totalFees = computed(() => {
  return trades.value.reduce((sum, t) => sum + (t.fee || 0), 0)
})

// 格式化函数
const formatNumber = (num: number | string | null, decimals = 2) => {
  if (num === null) return '-'
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return '-'
  return n.toFixed(decimals)
}

const getSideBadgeVariant = (side: string) => {
  return side === 'buy' ? 'success' : 'destructive'
}

// 加载账户列表
const loadAccounts = async () => {
  try {
    const result = await liveAccountApi.getAccounts()
    const list = (result as any)?.accounts || []
    accounts.value = list
    // 自动选中第一个账户
    if (list.length > 0 && !selectedAccount.value) {
      selectedAccount.value = list[0].uuid
      await loadTrades()
    }
  } catch (error) {
    console.error('Failed to load accounts:', error)
  }
}

// 加载交易历史
const loadTrades = async () => {
  if (!selectedAccount.value) return

  loading.value = true
  try {
    loadError.value = false
    const params: Record<string, string> = {}
    if (dateFilter.start_date) params.start_date = dateFilter.start_date
    if (dateFilter.end_date) params.end_date = dateFilter.end_date

    const result = await tradeHistoryApi.getTrades(selectedAccount.value, params)
    trades.value = (result as any) || []

    // 同时加载统计数据
    await loadStatistics()
    await loadDailySummary()
  } catch (error) {
    // 后端 /accounts/{id}/trades 待实现(实盘 stub 阶段),诚实标注
    loadError.value = true
    console.warn('成交历史加载失败(后端接口待实现):', error)
  } finally {
    loading.value = false
  }
}

// 加载统计数据
const loadStatistics = async () => {
  if (!selectedAccount.value) return

  try {
    const result = await tradeHistoryApi.getStatistics(selectedAccount.value)
    statistics.value = (result as any) ?? null
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

// 加载每日汇总
const loadDailySummary = async () => {
  if (!selectedAccount.value) return

  try {
    const result = await tradeHistoryApi.getDailySummary(selectedAccount.value)
    dailySummary.value = (result as any) || []
  } catch (error) {
    console.error('Failed to load daily summary:', error)
  }
}

// 导出CSV
const { run: exportCSV } = useAsyncAction(async () => {
  if (!selectedAccount.value) return

  const blob = await tradeHistoryApi.exportCSV(selectedAccount.value) as any
  const url = window.URL.createObjectURL(new Blob([blob], { type: 'text/csv' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `trades_${selectedAccount.value.slice(0, 8)}.csv`
  a.click()
  window.URL.revokeObjectURL(url)
}, { success: false })

// 应用日期筛选
const applyDateFilter = () => {
  showFilterDialog.value = false
  loadTrades()
}

// 切换账户
const onAccountChange = () => {
  trades.value = []
  statistics.value = null
  dailySummary.value = []
  loadTrades()
}

// 组件挂载
onMounted(() => {
  loadAccounts()
})
</script>

<template>
  <PageLayout>
    <template #title>
      交易历史
    </template>
    <template #description>
      查看实盘交易记录和统计数据
    </template>
    <template #actions>
      <select
        v-model="selectedAccount"
        class="px-3 py-1.5 border rounded-md text-sm bg-background"
        @change="onAccountChange"
      >
        <option
          :value="null"
          disabled
        >
          选择账户
        </option>
        <option
          v-for="acc in accounts"
          :key="acc.uuid"
          :value="acc.uuid"
        >
          {{ acc.name }} ({{ acc.exchange.toUpperCase() }})
        </option>
      </select>
      <Button
        variant="outline"
        size="sm"
        @click="showFilterDialog = true"
      >
        <Filter class="w-4 h-4 mr-2" />
        筛选
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="!selectedAccount"
        @click="exportCSV"
      >
        <Download class="w-4 h-4 mr-2" />
        导出CSV
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="!selectedAccount"
        @click="loadTrades"
      >
        <RefreshCw class="w-4 h-4 mr-2" />
        刷新
      </Button>
    </template>

    <Card>
      <CardContent>
        <!-- 统计卡片 -->
        <div
          v-if="statistics"
          class="grid grid-cols-5 gap-4 mb-6"
        >
          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">
                {{ statistics.total_trades }}
              </div>
              <div class="text-sm text-muted-foreground">
                总交易次数
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-success">
                {{ statistics.buy_trades }} / {{ statistics.sell_trades }}
              </div>
              <div class="text-sm text-muted-foreground">
                买入 / 卖出
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">
                {{ formatNumber(totalVolume) }}
              </div>
              <div class="text-sm text-muted-foreground">
                总成交量
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-primary">
                {{ formatNumber(totalValue) }}
              </div>
              <div class="text-sm text-muted-foreground">
                总成交额
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-error">
                {{ formatNumber(totalFees) }}
              </div>
              <div class="text-sm text-muted-foreground">
                总手续费
              </div>
            </CardContent>
          </Card>
        </div>

        <!-- 加载状态 -->
        <div
          v-if="loading"
          class="text-center py-8"
        >
          <p>加载中...</p>
        </div>

        <!-- 未选择账户 -->
        <div
          v-else-if="!selectedAccount"
          class="text-center py-8"
        >
          <p class="text-muted-foreground">
            {{ accounts.length === 0 ? '暂无交易账户，请先在账号配置中添加' : '请选择一个交易账户' }}
          </p>
        </div>

        <!-- 成交查询功能未实现(后端接口 404) -->
        <div
          v-else-if="loadError"
          class="text-center py-8"
        >
          <p class="text-muted-foreground">
            成交查询功能开发中(实盘引擎就绪后启用)
          </p>
        </div>

        <!-- 交易记录表格 -->
        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>成交时间</TableHead>
              <TableHead>交易对</TableHead>
              <TableHead>方向</TableHead>
              <TableHead>价格</TableHead>
              <TableHead>数量</TableHead>
              <TableHead>成交额</TableHead>
              <TableHead>手续费</TableHead>
              <TableHead>订单ID</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="trade in trades"
              :key="trade.uuid"
              @contextmenu="openTradeMenu($event, trade)"
            >
              <TableCell>{{ formatDate(trade.trade_time) }}</TableCell>
              <TableCell class="font-medium">
                {{ trade.symbol }}
              </TableCell>
              <TableCell>
                <Badge :variant="getSideBadgeVariant(trade.side)">
                  {{ trade.side === 'buy' ? '买入' : '卖出' }}
                </Badge>
              </TableCell>
              <TableCell>{{ formatNumber(trade.price) }}</TableCell>
              <TableCell>{{ formatNumber(trade.quantity) }}</TableCell>
              <TableCell>{{ formatNumber(trade.quote_quantity) }}</TableCell>
              <TableCell>{{ formatNumber(trade.fee) }} {{ trade.fee_currency || '' }}</TableCell>
              <TableCell class="text-xs text-muted-foreground">
                {{ trade.exchange_order_id?.slice(0, 8) }}...
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <!-- 每日汇总 -->
        <div
          v-if="dailySummary.length > 0"
          class="mt-6"
        >
          <h3 class="text-lg font-semibold mb-4">
            每日汇总
          </h3>
          <div class="grid grid-cols-7 gap-2">
            <div
              v-for="day in dailySummary"
              :key="day.date"
              class="p-3 border rounded-lg"
            >
              <div class="text-xs text-muted-foreground">
                {{ day.date.slice(5, 10) }}
              </div>
              <div class="text-lg font-bold">
                {{ day.total_trades }}
              </div>
              <div class="text-xs text-muted-foreground">
                笔交易
              </div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 筛选对话框 -->
    <DialogRoot
      :open="showFilterDialog"
      @update:open="showFilterDialog = false"
    >
      <DialogPortal>
        <DialogOverlay />
        <DialogContent>
          <DialogHeader>
            <DialogTitle>日期筛选</DialogTitle>
            <DialogDescription>选择交易记录的时间范围</DialogDescription>
          </DialogHeader>

          <div class="space-y-4 py-4">
            <div>
              <label class="text-sm font-medium">开始日期</label>
              <DateField
                v-model="dateFilter.start_date"
                class="w-full mt-1"
                bordered
                clearable
              />
            </div>
            <div>
              <label class="text-sm font-medium">结束日期</label>
              <DateField
                v-model="dateFilter.end_date"
                class="w-full mt-1"
                bordered
                clearable
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              @click="showFilterDialog = false"
            >
              取消
            </Button>
            <Button @click="applyDateFilter">
              应用
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </PageLayout>
</template>

<style scoped>
</style>
