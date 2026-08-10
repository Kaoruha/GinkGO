<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-orange">模拟</span>
        订单记录
      </h1>
      <div class="page-actions">
        <div class="filter-group">
          <select v-model="filterStatus" class="form-select">
            <option value="">全部状态</option>
            <option value="0">待成交</option>
            <option value="1">已成交</option>
            <option value="2">已取消</option>
            <option value="3">部分成交</option>
          </select>
          <input v-model="filterCode" type="text" placeholder="股票代码" class="form-input" />
          <input v-model="startDate" type="date" class="form-input" />
          <input v-model="endDate" type="date" class="form-input" />
          <button class="btn-primary" @click="loadOrders">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            搜索
          </button>
          <button class="btn-secondary" @click="loadOrders">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
              <path d="M3 3v5h5"></path>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
              <path d="M16 21h5v-5"></path>
            </svg>
            刷新
          </button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-body" :style="{ padding: loading ? '20px' : '0' }">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>代码</th>
                <th>方向</th>
                <th>数量</th>
                <th>成交价</th>
                <th>成交金额</th>
                <th>手续费</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in orders" :key="record.uuid">
                <td>{{ formatTime(record.timestamp) }}</td>
                <td>{{ record.code }}</td>
                <td>
                  <span class="tag" :class="getDirectionClass(record.direction)">
                    {{ getDirectionText(record.direction) }}
                  </span>
                </td>
                <td>{{ record.volume }}</td>
                <td>{{ record.transaction_price?.toFixed(2) || '-' }}</td>
                <td>{{ ((record.transaction_price || 0) * (record.transaction_volume || 0)).toFixed(2) }}</td>
                <td>{{ record.fee?.toFixed(2) || '-' }}</td>
                <td>
                  <span class="tag" :class="getStatusClass(record.status)">
                    {{ getStatusText(record.status) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="orders.length === 0" class="empty-state">
            <p>暂无订单数据</p>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="!loading && orders.length > 0" class="pagination">
          <div class="pagination-info">共 {{ total }} 条</div>
          <div class="pagination-controls">
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(1)">
              首页
            </button>
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(pagination.current - 1)">
              上一页
            </button>
            <span class="pagination-current">第 {{ pagination.current }} 页</span>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(pagination.current + 1)">
              下一页
            </button>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(totalPages)">
              末页
            </button>
            <select v-model="pagination.pageSize" @change="loadOrders" class="pagination-size">
              <option :value="20">20条/页</option>
              <option :value="50">50条/页</option>
              <option :value="100">100条/页</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'

const loading = ref(false)
const orders = ref<any[]>([])
const total = ref(0)

const filterStatus = ref<string>('')
const filterCode = ref<string>('')
const startDate = ref<string>('')
const endDate = ref<string>('')

const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
})

const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize))

const loadOrders = async () => {
  loading.value = true
  try {
    const params: any = {
      mode: 'paper',
      page: pagination.current - 1,
      size: pagination.pageSize,
    }
    if (filterStatus.value !== '') {
      params.status = filterStatus.value
    }
    if (filterCode.value) {
      params.code = filterCode.value
    }
    if (startDate.value) {
      params.start_date = startDate.value
    }
    if (endDate.value) {
      params.end_date = endDate.value
    }

    // TODO: Replace with actual API call
    // const result = await orderApi.list(params)
    // Mock data for now
    await new Promise(resolve => setTimeout(resolve, 500))
    orders.value = []
    total.value = 0
    pagination.total = 0
  } catch (e: any) {
    console.error('加载订单失败:', e)
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  pagination.current = page
  loadOrders()
}

const getDirectionText = (direction: number) => {
  const map: Record<number, string> = {
    1: '买入',
    2: '卖出',
  }
  return map[direction] || '未知'
}

const getDirectionClass = (direction: number) => {
  const map: Record<number, string> = {
    1: 'tag-red',
    2: 'tag-green',
  }
  return map[direction] || 'tag-gray'
}

const getStatusText = (status: number) => {
  const map: Record<number, string> = {
    0: '待成交',
    1: '已成交',
    2: '已取消',
    3: '部分成交',
  }
  return map[status] || '未知'
}

const getStatusClass = (status: number) => {
  const map: Record<number, string> = {
    0: 'tag-orange',
    1: 'tag-green',
    2: 'tag-gray',
    3: 'tag-blue',
  }
  return map[status] || 'tag-gray'
}

const formatTime = (timestamp: string) => {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

onMounted(() => {
  loadOrders()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

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
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
  flex-wrap: wrap;
  gap: 16px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  color: #8a8a9a;
  font-size: 14px;
  padding: 0 8px;
}

.pagination-size {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-group {
    width: 100%;
  }

  .form-input,
  .form-select {
    flex: 1;
    min-width: 120px;
  }

  .pagination {
    flex-direction: column;
    align-items: center;
  }
}
</style>
