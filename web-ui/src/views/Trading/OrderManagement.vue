<template>
  <div class="order-management">
    <div class="card">
      <div class="card-header">
        <span>订单管理</span>
        <div class="header-actions">
          <select v-model="statusFilter" class="form-select">
            <option value="all">全部</option>
            <option value="active">活跃</option>
            <option value="filled">已成交</option>
            <option value="cancelled">已撤销</option>
          </select>
          <input v-model="dateRangeText" type="text" placeholder="选择日期范围" class="form-input" />
          <button class="btn-primary" @click="queryOrders">查询</button>
        </div>
      </div>

      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>订单号</th>
                <th>策略</th>
                <th>代码</th>
                <th>名称</th>
                <th>方向</th>
                <th>价格</th>
                <th>数量</th>
                <th>已成交</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in orders" :key="record.orderId">
                <td>{{ record.orderId }}</td>
                <td>{{ record.strategy }}</td>
                <td>{{ record.code }}</td>
                <td>{{ record.name }}</td>
                <td>
                  <span class="tag" :class="record.side === 'buy' ? 'tag-red' : 'tag-green'">
                    {{ record.side === 'buy' ? '买入' : '卖出' }}
                  </span>
                </td>
                <td>{{ record.price }}</td>
                <td>{{ record.volume }}</td>
                <td>{{ record.filled }}</td>
                <td>
                  <span class="tag" :class="getStatusTagClass(record.status)">
                    {{ getStatusText(record.status) }}
                  </span>
                </td>
                <td>{{ formatTime(record.time) }}</td>
                <td>
                  <button
                    v-if="['pending', 'partial'].includes(record.status)"
                    class="btn-link text-danger"
                    @click="cancelOrder(record)"
                  >
                    撤单
                  </button>
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

const statusFilter = ref('all')
const dateRangeText = ref('')

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

const getStatusTagClass = (status: string) => {
  const classes: Record<string, string> = {
    pending: 'tag-orange',
    partial: 'tag-blue',
    filled: 'tag-green',
    cancelled: 'tag-red',
    rejected: 'tag-red',
  }
  return classes[status] || 'tag-gray'
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
  console.log('查询订单历史...')
}

const cancelOrder = (order: any) => {
  console.log(`撤单: ${order.orderId}`)
}
</script>

<style scoped>
.order-management {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.btn-primary {
  padding: 6px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-link {
  background: none;
  border: none;
  color: inherit;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.btn-link:hover {
  text-decoration: underline;
}

.text-danger {
  color: #f5222d;
}

.form-select,
.form-input {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-select:focus,
.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }
.tag-orange { background: rgba(250, 140, 22, 0.2); color: #fa8c16; }
.tag-gray { background: rgba(140, 140, 140, 0.2); color: #8c8c8c; }

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .form-select,
  .form-input {
    width: 100%;
  }
}
</style>
