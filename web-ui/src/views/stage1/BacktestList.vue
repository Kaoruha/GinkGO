<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-1">第一阶段</span>
        回测列表
      </div>
      <div class="page-actions">
        <a-button type="primary" @click="$router.push('/stage1/backtest/create')">
          <template #icon><PlusOutlined /></template>
          创建回测
        </a-button>
      </div>
    </div>

    <a-card>
      <a-table :columns="columns" :data-source="backtests" :loading="loading" row-key="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ record.status }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'return'">
            <span :style="{ color: record.totalReturn >= 0 ? '#52c41a' : '#f5222d' }">
              {{ (record.totalReturn * 100).toFixed(2) }}%
            </span>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="viewDetail(record)">
                详情
              </a-button>
              <a-button type="link" size="small" @click="compareSelect(record)">
                对比
              </a-button>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlusOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const loading = ref(false)
const backtests = ref([])

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
  { title: '策略名称', dataIndex: 'strategyName', key: 'strategyName' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '总收益', dataIndex: 'totalReturn', key: 'return', width: 120 },
  { title: '夏普比率', dataIndex: 'sharpeRatio', key: 'sharpeRatio', width: 120 },
  { title: '最大回撤', dataIndex: 'maxDrawdown', key: 'maxDrawdown', width: 120 },
  { title: '开始日期', dataIndex: 'startDate', key: 'startDate', width: 120 },
  { title: '结束日期', dataIndex: 'endDate', key: 'endDate', width: 120 },
  { title: '操作', key: 'action', width: 150 },
]

const getStatusColor = (status: string) => {
  const colors: Record<string, string> = {
    completed: 'green',
    running: 'blue',
    failed: 'red',
    pending: 'default',
  }
  return colors[status] || 'default'
}

const viewDetail = (record: any) => {
  router.push(`/stage1/backtest/${record.id}`)
}

const compareSelect = (record: any) => {
  // TODO: 实现对比选择逻辑
}

onMounted(() => {
  // TODO: 加载回测列表
})
</script>
