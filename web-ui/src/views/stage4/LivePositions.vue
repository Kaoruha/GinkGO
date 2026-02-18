<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="red">实盘</a-tag>
        持仓管理
      </div>
      <div class="page-actions">
        <a-space>
          <a-input v-model:value="filterCode" placeholder="股票代码" style="width: 150px" allowClear />
          <a-button type="primary" @click="loadPositions">
            <template #icon><SearchOutlined /></template>
            搜索
          </a-button>
          <a-button @click="loadPositions">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- 汇总信息 -->
    <a-row :gutter="16" style="margin-bottom: 16px" v-if="summary">
      <a-col :span="6">
        <a-card>
          <a-statistic title="持仓数量" :value="summary.position_count" suffix="只" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="总市值" :value="summary.total_market_value" :precision="2" prefix="¥" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="总盈亏"
            :value="summary.total_profit"
            :precision="2"
            prefix="¥"
            :value-style="{ color: summary.total_profit >= 0 ? '#cf1322' : '#3f8600' }"
          />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="总手续费" :value="summary.total_fee" :precision="2" prefix="¥" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 持仓表格 -->
    <a-card :loading="loading">
      <a-table
        :columns="columns"
        :dataSource="positions"
        :rowKey="(record: Position) => record.uuid"
        :pagination="pagination"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'code'">
            <span style="font-weight: 600">{{ record.code }}</span>
          </template>
          <template v-else-if="column.key === 'profit'">
            <span :style="{ color: record.profit >= 0 ? '#cf1322' : '#3f8600' }">
              {{ record.profit.toFixed(2) }} ({{ record.profit_pct >= 0 ? '+' : '' }}{{ record.profit_pct }}%)
            </span>
          </template>
          <template v-else-if="column.key === 'market_value'">
            {{ record.market_value.toFixed(2) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" danger>卖出</a-button>
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
import { positionApi, type Position, type PositionSummary } from '@/api/modules/order'

const loading = ref(false)
const positions = ref<Position[]>([])
const summary = ref<PositionSummary | null>(null)

const filterCode = ref<string>('')

const pagination = reactive({
  current: 1,
  pageSize: 100,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (t: number) => `共 ${t} 条`,
})

const columns = [
  { title: '代码', key: 'code', dataIndex: 'code', width: 120 },
  { title: '持仓量', dataIndex: 'volume', width: 100 },
  { title: '可用量', dataIndex: 'frozen_volume', width: 100, customRender: ({ record }: { record: Position }) => {
    return record.volume - (record.frozen_volume || 0)
  }},
  { title: '成本价', dataIndex: 'cost', width: 100, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '现价', dataIndex: 'price', width: 100, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '市值', key: 'market_value', width: 120 },
  { title: '盈亏', key: 'profit', width: 160 },
  { title: '手续费', dataIndex: 'fee', width: 100, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '操作', key: 'action', width: 80 },
]

const loadPositions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current - 1,
      size: pagination.pageSize,
    }
    if (filterCode.value) {
      params.code = filterCode.value
    }

    const result = await positionApi.list(params)
    positions.value = result.data
    pagination.total = result.total
    summary.value = result.summary
  } catch (e: any) {
    message.error('加载持仓失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadPositions()
}

onMounted(() => {
  loadPositions()
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
