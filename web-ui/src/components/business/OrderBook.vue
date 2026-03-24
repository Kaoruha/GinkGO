<template>
  <div class="order-book">
    <div class="card">
      <div class="card-header">
        <h4>订单簿</h4>
      </div>
      <div class="card-body">
        <div v-if="orders.length === 0" class="empty-state">
          <p>暂无订单</p>
        </div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th width="100">代码</th>
                <th width="80">方向</th>
                <th width="100">数量</th>
                <th width="100">价格</th>
                <th width="120">金额</th>
                <th width="100">状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(record, index) in orders" :key="index">
                <td>{{ record.code }}</td>
                <td>
                  <span class="tag" :class="record.direction === 'buy' ? 'tag-green' : 'tag-red'">
                    {{ record.direction === 'buy' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>{{ record.quantity }}</td>
                <td>{{ record.price?.toFixed(2) || '-' }}</td>
                <td>{{ record.amount?.toFixed(2) || '-' }}</td>
                <td>
                  <span class="status-badge" :class="`status-${record.status}`">
                    {{ getStatusLabel(record.status) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
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

const getStatusLabel = (status: string) => {
  const labels: Record<string, string> = {
    pending: '待提交',
    filled: '已成交',
    cancelled: '已取消'
  }
  return labels[status] || status
}

const orders = ref<Order[]>([
  { code: '000001', direction: 'buy', quantity: 1000, price: 10.5, amount: 10500, status: 'pending' },
  { code: '000001', direction: 'sell', quantity: 500, price: 11.2, amount: 5600, status: 'pending' }
])
</script>

<style scoped>
.order-book {
  min-width: 400px;
}

.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 0;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
  font-size: 13px;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }

.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-pending { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.status-filled { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.status-cancelled { background: rgba(140, 140, 140, 0.2); color: #8a8a9a; }
</style>
