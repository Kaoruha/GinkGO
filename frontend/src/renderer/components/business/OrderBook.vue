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
  background: hsl(var(--card));
  border-radius: 8px;
  border: 1px solid hsl(var(--border));
}

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid hsl(var(--border));
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.card-body {
  padding: 0;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: hsl(var(--muted-foreground));
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
  border-bottom: 1px solid hsl(var(--border));
}

.data-table th {
  background: hsl(var(--border));
  color: hsl(var(--foreground));
  font-weight: 500;
}

.data-table td {
  color: hsl(var(--foreground));
}

.data-table tbody tr:hover {
  background: hsl(var(--border));
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}


.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.status-pending { background: hsl(var(--primary) / 0.2); color: hsl(var(--primary)); }
.status-filled { background: hsl(var(--success) / 0.2); color: hsl(var(--success)); }
.status-cancelled { background: hsl(var(--muted-foreground) / 0.2); color: hsl(var(--muted-foreground)); }
</style>
