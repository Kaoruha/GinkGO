<template>
  <div class="trade-records-panel">
    <a-tabs v-model:activeKey="activeTab">
      <!-- 信号记录 -->
      <a-tab-pane key="signals" tab="信号记录">
        <a-table
          :columns="signalColumns"
          :data-source="signals"
          :loading="signalsLoading"
          :pagination="{ pageSize: 20, total: signalsTotal }"
          size="small"
          row-key="uuid"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'direction'">
              <a-tag :color="(record.direction === 'LONG' || record.direction === '1' || record.direction === 1) ? 'green' : 'red'">
                {{ (record.direction === 'LONG' || record.direction === '1' || record.direction === 1) ? '买入' : '卖出' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'weight'">
              {{ (record.weight * 100)?.toFixed(1) || '-' }}%
            </template>
            <template v-else-if="column.key === 'strength'">
              {{ record.strength?.toFixed(2) || '-' }}
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- 订单记录 - 按 order_id 聚合 -->
      <a-tab-pane key="orders" tab="订单记录">
        <a-table
          :columns="orderColumns"
          :data-source="groupedOrders"
          :loading="ordersLoading"
          :pagination="{ pageSize: 20, total: groupedOrdersTotal }"
          size="small"
          row-key="order_id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'direction'">
              <a-tag :color="(record.direction === 'LONG' || record.direction === '1' || record.direction === 1) ? 'green' : 'red'">
                {{ (record.direction === 'LONG' || record.direction === '1' || record.direction === 1) ? '买入' : '卖出' }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'order_type'">
              {{ (record.order_type === '1' || record.order_type === 1) ? '市价' : (record.order_type === '2' || record.order_type === 2) ? '限价' : '-' }}
            </template>
            <template v-else-if="column.key === 'status'">
              <a-tag :color="getOrderStatusColor(record.finalStatus)">
                {{ getOrderStatusLabel(record.finalStatus) }}
                <span v-if="record.statusCount > 1" style="margin-left: 4px; opacity: 0.7">
                  ({{ record.statusCount }}次变更)
                </span>
              </a-tag>
            </template>
            <template v-else-if="column.key === 'limit_price'">
              ¥{{ record.limit_price?.toFixed(2) || '-' }}
            </template>
            <template v-else-if="column.key === 'transaction_price'">
              ¥{{ record.transaction_price?.toFixed(2) || '-' }}
            </template>
            <template v-else-if="column.key === 'order_id'">
              <span style="font-family: monospace; font-size: 12px">{{ record.order_id?.slice(0, 16) }}...</span>
            </template>
          </template>

          <!-- 展开行：显示状态变化历史 -->
          <template #expandedRowRender="{ record }">
            <div style="padding: 8px 16px; background: #fafafa">
              <div style="margin-bottom: 8px; font-weight: 500; color: #666">状态变更历史：</div>
              <a-timeline mode="left">
                <a-timeline-item v-for="(hist, index) in record.statusHistory" :key="index" :color="getTimelineColor(hist.status)">
                  <div style="display: flex; gap: 24px; align-items: center">
                    <a-tag :color="getOrderStatusColor(hist.status)">
                      {{ getOrderStatusLabel(hist.status) }}
                    </a-tag>
                    <span v-if="hist.transaction_price > 0">
                      成交价: ¥{{ hist.transaction_price?.toFixed(2) }}
                    </span>
                    <span v-if="hist.transaction_volume > 0">
                      成交量: {{ hist.transaction_volume }}
                    </span>
                    <span v-if="hist.fee > 0">
                      手续费: ¥{{ hist.fee?.toFixed(2) }}
                    </span>
                    <span style="color: #999; font-size: 12px">
                      {{ hist.timestamp }}
                    </span>
                  </div>
                </a-timeline-item>
              </a-timeline>
            </div>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- 持仓记录 -->
      <a-tab-pane key="positions" tab="持仓记录">
        <a-table
          :columns="positionColumns"
          :data-source="positions"
          :loading="positionsLoading"
          :pagination="{ pageSize: 20, total: positionsTotal }"
          size="small"
          row-key="uuid"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'profit'">
              <span :style="{ color: record.profit >= 0 ? '#52c41a' : '#f5222d' }">
                ¥{{ record.profit?.toFixed(2) || '-' }}
              </span>
            </template>
            <template v-else-if="column.key === 'profit_pct'">
              <span :style="{ color: record.profit_pct >= 0 ? '#52c41a' : '#f5222d' }">
                {{ (record.profit_pct * 100)?.toFixed(2) || '-' }}%
              </span>
            </template>
            <template v-else-if="column.key === 'market_value'">
              ¥{{ record.market_value?.toFixed(2) || '-' }}
            </template>
          </template>
        </a-table>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { backtestApi, type SignalRecord, type OrderRecord, type PositionRecord } from '@/api/modules/backtest'

interface Props {
  taskId: string
}

const props = defineProps<Props>()

const activeTab = ref('signals')

// 信号数据
const signals = ref<SignalRecord[]>([])
const signalsTotal = ref(0)
const signalsLoading = ref(false)

// 订单数据（原始）
const rawOrders = ref<OrderRecord[]>([])
const ordersLoading = ref(false)

// 持仓数据
const positions = ref<PositionRecord[]>([])
const positionsTotal = ref(0)
const positionsLoading = ref(false)

// 聚合后的订单数据
interface GroupedOrder {
  order_id: string
  code: string
  direction: number | string
  order_type: number | string
  volume: number
  limit_price: number
  transaction_price: number
  transaction_volume: number
  fee: number
  finalStatus: number | string
  statusCount: number
  statusHistory: OrderRecord[]
  timestamp: string
}

const groupedOrders = computed(() => {
  const groups: Map<string, GroupedOrder> = new Map()

  // 按 order_id 分组
  for (const order of rawOrders.value) {
    const orderId = order.order_id
    if (!orderId) continue

    if (!groups.has(orderId)) {
      groups.set(orderId, {
        order_id: orderId,
        code: order.code,
        direction: order.direction,
        order_type: order.order_type,
        volume: order.volume,
        limit_price: order.limit_price,
        transaction_price: 0,
        transaction_volume: 0,
        fee: 0,
        finalStatus: order.status,
        statusCount: 0,
        statusHistory: [],
        timestamp: order.timestamp,
      })
    }

    const group = groups.get(orderId)!
    group.statusCount++
    group.statusHistory.push(order)

    // 更新最终状态和成交信息
    const statusNum = typeof order.status === 'string' ? parseInt(order.status) : order.status
    if (statusNum === 4) { // FILLED
      group.finalStatus = order.status
      group.transaction_price = order.transaction_price
      group.transaction_volume = order.transaction_volume
      group.fee = order.fee
    } else if (statusNum === 5 || statusNum === 6) { // CANCELED or REJECTED
      group.finalStatus = order.status
    }
  }

  // 按时间倒序排列
  const result = Array.from(groups.values())
  result.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

  // 状态历史也按时间排序
  for (const group of result) {
    group.statusHistory.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }

  return result
})

const groupedOrdersTotal = computed(() => groupedOrders.value.length)

// 表格列定义
const signalColumns = [
  { title: '代码', dataIndex: 'code', width: 100 },
  { title: '方向', key: 'direction', width: 80 },
  { title: '数量', dataIndex: 'volume', width: 80 },
  { title: '权重', dataIndex: 'weight', width: 80 },
  { title: '强度', dataIndex: 'strength', width: 80 },
  { title: '原因', dataIndex: 'reason', ellipsis: true },
  { title: '时间', dataIndex: 'timestamp', width: 160 },
]

const orderColumns = [
  { title: '代码', dataIndex: 'code', width: 100 },
  { title: '方向', key: 'direction', width: 80 },
  { title: '类型', key: 'order_type', width: 80 },
  { title: '委托价', key: 'limit_price', width: 100 },
  { title: '成交量', dataIndex: 'transaction_volume', width: 80 },
  { title: '成交价', key: 'transaction_price', width: 100 },
  { title: '状态', key: 'status', width: 140 },
  { title: '手续费', dataIndex: 'fee', width: 80 },
  { title: '时间', dataIndex: 'timestamp', width: 160 },
]

const positionColumns = [
  { title: '代码', dataIndex: 'code', width: 100 },
  { title: '数量', dataIndex: 'volume', width: 80 },
  { title: '成本', dataIndex: 'cost', width: 100 },
  { title: '市值', key: 'market_value', width: 120 },
  { title: '盈亏', key: 'profit', width: 100 },
  { title: '盈亏%', key: 'profit_pct', width: 100 },
  { title: '时间', dataIndex: 'timestamp', width: 160 },
]

// 状态颜色和标签
const getOrderStatusColor = (status: string | number) => {
  const statusNum = typeof status === 'string' ? parseInt(status) : status
  const colors: Record<number, string> = {
    1: 'processing',  // NEW
    2: 'processing',  // SUBMITTED
    3: 'warning',     // PARTIAL_FILLED
    4: 'success',     // FILLED
    5: 'error',       // CANCELED
    6: 'error',       // REJECTED
  }
  return colors[statusNum] || 'default'
}

const getOrderStatusLabel = (status: string | number) => {
  const statusNum = typeof status === 'string' ? parseInt(status) : status
  const labels: Record<number, string> = {
    1: '新建',
    2: '已提交',
    3: '部分成交',
    4: '已成交',
    5: '已撤销',
    6: '已拒绝',
  }
  return labels[statusNum] || String(status)
}

const getTimelineColor = (status: string | number) => {
  const statusNum = typeof status === 'string' ? parseInt(status) : status
  const colors: Record<number, string> = {
    1: 'gray',      // NEW
    2: 'blue',      // SUBMITTED
    3: 'orange',    // PARTIAL_FILLED
    4: 'green',     // FILLED
    5: 'red',       // CANCELED
    6: 'red',       // REJECTED
  }
  return colors[statusNum] || 'gray'
}

// 加载数据
const loadSignals = async () => {
  if (!props.taskId) return
  signalsLoading.value = true
  try {
    const result = await backtestApi.getSignals(props.taskId)
    signals.value = result.data || []
    signalsTotal.value = result.total || 0
  } catch (e) {
    console.error('Failed to load signals:', e)
  } finally {
    signalsLoading.value = false
  }
}

const loadOrders = async () => {
  if (!props.taskId) return
  ordersLoading.value = true
  try {
    const result = await backtestApi.getOrders(props.taskId)
    rawOrders.value = result.data || []
  } catch (e) {
    console.error('Failed to load orders:', e)
  } finally {
    ordersLoading.value = false
  }
}

const loadPositions = async () => {
  if (!props.taskId) return
  positionsLoading.value = true
  try {
    const result = await backtestApi.getPositions(props.taskId)
    positions.value = result.data || []
    positionsTotal.value = result.total || 0
  } catch (e) {
    console.error('Failed to load positions:', e)
  } finally {
    positionsLoading.value = false
  }
}

onMounted(() => {
  loadSignals()
  loadOrders()
  loadPositions()
})
</script>

<style scoped>
.trade-records-panel {
  padding: 0;
}
</style>
