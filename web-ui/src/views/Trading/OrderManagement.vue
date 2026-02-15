<template>
  <div class="order-management">
    <a-card title="订单管理">
      <template #extra>
        <a-space>
          <a-select v-model:value="statusFilter" placeholder="状态筛选" style="width: 120px" allow-clear>
            <a-select-option value="all">全部</a-select-option>
            <a-select-option value="active">活跃</a-select-option>
            <a-select-option value="filled">已成交</a-select-option>
            <a-select-option value="cancelled">已撤销</a-select-option>
          </a-select>
          <a-range-picker v-model:value="dateRange" />
          <a-button type="primary" @click="queryOrders">查询</a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data-source="orders"
        :pagination="{ pageSize: 50, showSizeChanger: true }"
        size="small"
        :scroll="{ y: 500 }"
      >
        <template #bodyCell="{ column, record }">
          <a-tag v-if="column.dataIndex === 'side'" :color="record.side === 'buy' ? 'red' : 'green'">
            {{ record.side === 'buy' ? '买入' : '卖出' }}
          </a-tag>
          <a-tag v-if="column.dataIndex === 'status'" :color="getStatusColor(record.status)">
            {{ getStatusText(record.status) }}
          </a-tag>
          <span v-if="column.dataIndex === 'time'">{{ formatTime(record.time) }}</span>
          <template v-if="column.key === 'action'">
            <a-button v-if="['pending', 'partial'].includes(record.status)" type="link" size="small" danger @click="cancelOrder(record)">
              撤单
            </a-button>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { message } from 'ant-design-vue'

const statusFilter = ref('all')
const dateRange = ref<any[]>([])

const columns = [
  { title: '订单号', dataIndex: 'orderId', width: 120, fixed: 'left' },
  { title: '策略', dataIndex: 'strategy', width: 100 },
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '名称', dataIndex: 'name', width: 120 },
  { title: '方向', dataIndex: 'side', width: 80 },
  { title: '价格', dataIndex: 'price', width: 100 },
  { title: '数量', dataIndex: 'volume', width: 100 },
  { title: '已成交', dataIndex: 'filled', width: 100 },
  { title: '状态', dataIndex: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'time', width: 160 },
  { key: 'action', title: '操作', width: 80, fixed: 'right' },
]

const orders = ref([
  {
    orderId: 'O20250210001',
    strategy: '双均线',
    code: '000001.SZ',
    name: '平安银行',
    side: 'buy',
    price: 13.20,
    volume: 1000,
    filled: 1000,
    status: 'filled',
    time: '2025-02-10 09:32:15'
  },
  {
    orderId: 'O20250210002',
    strategy: '双均线',
    code: '600519.SH',
    name: '贵州茅台',
    side: 'buy',
    price: 1750.00,
    volume: 100,
    filled: 0,
    status: 'pending',
    time: '2025-02-10 09:35:22'
  },
])

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    pending: 'orange',
    partial: 'blue',
    filled: 'green',
    cancelled: 'red',
    rejected: 'red',
  }
  return colors[status] || 'default'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    pending: '待报',
    partial: '部成',
    filled: '已成交',
    cancelled: '已撤销',
    rejected: '已拒绝',
  }
  return texts[status] || status
}

const formatTime = (time: string) => {
  return time
}

const queryOrders = () => {
  message.info('查询订单历史...')
}

const cancelOrder = (order: any) => {
  message.warning(`撤单: ${order.orderId}`)
}
</script>

<style scoped>
.order-management {
  padding: 16px;
}
</style>
