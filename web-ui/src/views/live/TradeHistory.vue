<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Download, Filter } from 'lucide-vue-next'
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
const loading = ref(true)
const selectedAccount = ref<string | null>(null)
const dateFilter = reactive({
  start_date: '',
  end_date: ''
})

const showFilterDialog = ref(false)
const csvContent = ref('')

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

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleString()
}

const getSideBadgeVariant = (side: string) => {
  return side === 'buy' ? 'success' : 'destructive'
}

// 加载交易历史
const loadTrades = async () => {
  if (!selectedAccount.value) return

  loading.value = true
  try {
    let url = `/api/v1/accounts/${selectedAccount.value}/trades`
    const params = new URLSearchParams()
    if (dateFilter.start_date) params.append('start_date', dateFilter.start_date)
    if (dateFilter.end_date) params.append('end_date', dateFilter.end_date)
    if (params.toString()) url += '?' + params.toString()

    const response = await fetch(url)
    if (response.ok) {
      const result = await response.json()
      trades.value = result.data || []

      // 同时加载统计数据
      await loadStatistics()
      await loadDailySummary()
    }
  } catch (error) {
    console.error('Failed to load trades:', error)
  } finally {
    loading.value = false
  }
}

// 加载统计数据
const loadStatistics = async () => {
  if (!selectedAccount.value) return

  try {
    let url = `/api/v1/accounts/${selectedAccount.value}/trades/statistics`
    const params = new URLSearchParams()
    if (dateFilter.start_date) params.append('start_date', dateFilter.start_date)
    if (dateFilter.end_date) params.append('end_date', dateFilter.end_date)
    if (params.toString()) url += '?' + params.toString()

    const response = await fetch(url)
    if (response.ok) {
      const result = await response.json()
      statistics.value = result.data
    }
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

// 加载每日汇总
const loadDailySummary = async () => {
  if (!selectedAccount.value) return

  try {
    const response = await fetch(`/api/v1/accounts/${selectedAccount.value}/trades/daily-summary?days=30`)
    if (response.ok) {
      const result = await response.json()
      dailySummary.value = result.data || []
    }
  } catch (error) {
    console.error('Failed to load daily summary:', error)
  }
}

// 导出CSV
const exportCSV = async () => {
  if (!selectedAccount.value) return

  try {
    let url = `/api/v1/accounts/${selectedAccount.value}/trades/export`
    const params = new URLSearchParams()
    if (dateFilter.start_date) params.append('start_date', dateFilter.start_date)
    if (dateFilter.end_date) params.append('end_date', dateFilter.end_date)
    if (params.toString()) url += '?' + params.toString()

    const response = await fetch(url)
    if (response.ok) {
      const result = await response.json()
      csvContent.value = result.data.content

      // 下载CSV文件
      const blob = new Blob([result.data.content], { type: 'text/csv' })
      const url_download = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url_download
      a.download = result.data.filename
      a.click()
      window.URL.revokeObjectURL(url_download)
    }
  } catch (error) {
    console.error('Failed to export CSV:', error)
  }
}

// 应用日期筛选
const applyDateFilter = () => {
  showFilterDialog.value = false
  loadTrades()
}

// 组件挂载
onMounted(() => {
  // 默认选择第一个账号（如果有）
  // 实际应用中应该从路由参数或用户选择获取
  loadTrades()
})
</script>

<template>
  <div class="trade-history">
    <Card>
      <CardHeader>
        <div class="flex justify-between items-center">
          <div>
            <CardTitle>交易历史</CardTitle>
            <CardDescription>查看实盘交易记录和统计数据</CardDescription>
          </div>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" @click="showFilterDialog = true">
              <Filter class="w-4 h-4 mr-2" />
              筛选
            </Button>
            <Button variant="outline" size="sm" @click="exportCSV">
              <Download class="w-4 h-4 mr-2" />
              导出CSV
            </Button>
            <Button variant="outline" size="sm" @click="loadTrades">
              <RefreshCw class="w-4 h-4 mr-2" />
              刷新
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <!-- 统计卡片 -->
        <div v-if="statistics" class="grid grid-cols-5 gap-4 mb-6">
          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">{{ statistics.total_trades }}</div>
              <div class="text-sm text-muted-foreground">总交易次数</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-green-600">
                {{ statistics.buy_trades }} / {{ statistics.sell_trades }}
              </div>
              <div class="text-sm text-muted-foreground">买入 / 卖出</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">{{ formatNumber(totalVolume) }}</div>
              <div class="text-sm text-muted-foreground">总成交量</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-blue-600">{{ formatNumber(totalValue) }}</div>
              <div class="text-sm text-muted-foreground">总成交额</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-red-600">{{ formatNumber(totalFees) }}</div>
              <div class="text-sm text-muted-foreground">总手续费</div>
            </CardContent>
          </Card>
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="text-center py-8">
          <p>加载中...</p>
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
            >
              <TableCell>{{ formatDate(trade.trade_time) }}</TableCell>
              <TableCell class="font-medium">{{ trade.symbol }}</TableCell>
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
        <div v-if="dailySummary.length > 0" class="mt-6">
          <h3 class="text-lg font-semibold mb-4">每日汇总</h3>
          <div class="grid grid-cols-7 gap-2">
            <div
              v-for="day in dailySummary"
              :key="day.date"
              class="p-3 border rounded-lg"
            >
              <div class="text-xs text-muted-foreground">{{ day.date.slice(5, 10) }}</div>
              <div class="text-lg font-bold">{{ day.total_trades }}</div>
              <div class="text-xs text-muted-foreground">笔交易</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>

    <!-- 筛选对话框 -->
    <DialogRoot :open="showFilterDialog" @update:open="showFilterDialog = false">
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
              <input
                type="date"
                v-model="dateFilter.start_date"
                class="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </div>
            <div>
              <label class="text-sm font-medium">结束日期</label>
              <input
                type="date"
                v-model="dateFilter.end_date"
                class="w-full mt-1 px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" @click="showFilterDialog = false">取消</Button>
            <Button @click="applyDateFilter">应用</Button>
          </DialogFooter>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </div>
</template>

<style scoped>
.trade-history {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>
