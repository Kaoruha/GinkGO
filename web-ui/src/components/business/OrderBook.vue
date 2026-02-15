<template>
  <a-card title="订单簿" size="small">
    <a-table :columns="columns" :data-source="orders" size="small" :pagination="false">
      <template #bodyCell="{ column }">
        <span v-if="column.key === 'code'">{{ record.code }}</span>
        <span v-else-if="column.key === 'direction'">
          <a-tag :color="record.direction === 'buy' ? 'success' : 'error'">
            {{ record.direction === 'buy' ? '买入' : '卖出' }}
          </a-tag>
        </span>
        <span v-else-if="column.key === 'quantity'">{{ record.quantity }}</span>
        <span v-else-if="column.key === 'price'">{{ record.price?.toFixed(2) }}</span>
        <span v-else-if="column.key === 'amount'">{{ record.amount?.toFixed(2) }}</span>
        <span v-else-if="column.key === 'status'">
          <a-badge :status="record.status" />
        </span>
      </template>
    </a-table>
  </a-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

/**
 * 订单簿组件
 * 展示和管理交易订单
 */

interface Order {
  code: string
  direction: 'buy' | 'sell'
  quantity: number
  price?: number
  amount?: number
  status: 'pending' | 'filled' | 'cancelled'
}

const columns = [
  { title: '代码', key: 'code', width: 100 },
  { title: '方向', key: 'direction', width: 80 },
  { title: '数量', key: 'quantity', width: 100 },
  { title: '价格', key: 'price', width: 100 },
  { title: '金额', key: 'amount', width: 120 },
  { title: '状态', key: 'status', width: 100 }
]

const orders = ref<Order[]>([
  { code: '000001', direction: 'buy', quantity: 1000, price: 10.5, amount: 10500, status: 'pending' },
  { code: '000001', direction: 'sell', quantity: 500, price: 11.2, amount: 5600, status: 'pending' }
])
</script>

<style scoped>
</style>
