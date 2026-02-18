<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="red">实盘</a-tag>
        订单管理
      </div>
      <div class="page-actions">
        <a-space>
          <a-select v-model:value="filterStatus" style="width: 120px" placeholder="状态筛选" allowClear>
            <a-select-option value="0">待成交</a-select-option>
            <a-select-option value="1">已成交</a-select-option>
            <a-select-option value="2">已取消</a-select-option>
            <a-select-option value="3">部分成交</a-select-option>
          </a-select>
          <a-input v-model:value="filterCode" placeholder="股票代码" style="width: 150px" allowClear />
          <a-range-picker v-model:value="filterDateRange" />
          <a-button type="primary" @click="loadOrders">
            <template #icon><SearchOutlined /></template>
            搜索
          </a-button>
          <a-button @click="loadOrders">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </div>
    </div>

    <a-card :loading="loading">
      <a-table
        :columns="columns"
        :dataSource="orders"
        :rowKey="(record: Order) => record.uuid"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'direction'">
            <a-tag :color="getDirectionColor(record.direction)">
              {{ getDirectionText(record.direction) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'timestamp'">
            {{ formatTime(record.timestamp) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" v-if="record.status === 0" danger>撤单</a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { orderApi, ORDER_STATUS_MAP, ORDER_DIRECTION_MAP, type Order } from '@/api/modules/order'

const loading = ref(false)
const orders = ref<Order[]>([])
const total = ref(0)

const filterStatus = ref<string | undefined>(undefined)
const filterCode = ref<string>('')
const filterDateRange = ref<any[]>([])

const pagination = reactive({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (t: number) => `共 ${t} 条`,
})

const columns = [
  { title: '委托时间', key: 'timestamp', dataIndex: 'timestamp', width: 180 },
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '方向', key: 'direction', width: 80 },
  { title: '委托量', dataIndex: 'volume', width: 100 },
  { title: '成交量', dataIndex: 'transaction_volume', width: 100 },
  { title: '委托价', dataIndex: 'limit_price', width: 100 },
  { title: '成交价', dataIndex: 'transaction_price', width: 100 },
  { title: '手续费', dataIndex: 'fee', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '操作', key: 'action', width: 80 },
]

const loadOrders = async () => {
  loading.value = true
  try {
    const params: any = {
      mode: 'live',
      page: pagination.current - 1,
      size: pagination.pageSize,
    }
    if (filterStatus.value !== undefined) {
      params.status = filterStatus.value
    }
    if (filterCode.value) {
      params.code = filterCode.value
    }
    if (filterDateRange.value && filterDateRange.value.length === 2) {
      params.start_date = filterDateRange.value[0].format('YYYY-MM-DD')
      params.end_date = filterDateRange.value[1].format('YYYY-MM-DD')
    }

    const result = await orderApi.list(params)
    orders.value = result.data
    total.value = result.total
    pagination.total = result.total
  } catch (e: any) {
    message.error('加载订单失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadOrders()
}

const getDirectionText = (direction: number) => {
  return ORDER_DIRECTION_MAP[direction]?.text || '未知'
}

const getDirectionColor = (direction: number) => {
  return ORDER_DIRECTION_MAP[direction]?.color || 'default'
}

const getStatusText = (status: number) => {
  return ORDER_STATUS_MAP[status]?.text || '未知'
}

const getStatusColor = (status: number) => {
  return ORDER_STATUS_MAP[status]?.color || 'default'
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
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
