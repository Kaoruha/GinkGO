<template>
  <div class="data-management-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">数据管理</h1>
        <p class="page-subtitle">管理股票信息、K线数据、Tick数据等市场数据</p>
      </div>
      <a-button :loading="refreshing" @click="refreshStats">
        <ReloadOutlined /> 刷新统计
      </a-button>
    </div>

    <a-row :gutter="16" class="stats-row">
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="股票总数" :value="dataStats.totalStocks" :value-style="{ color: '#1890ff' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="K线数据量" :value="dataStats.totalBars" :value-style="{ color: '#52c41a' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="Tick数据量" :value="dataStats.totalTicks" :value-style="{ color: '#fa8c16' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="复权因子" :value="dataStats.totalAdjustFactors" :value-style="{ color: '#722ed1' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-card class="data-type-card">
      <a-radio-group v-model:value="dataType" button-style="solid" size="large" @change="handleDataTypeChange">
        <a-radio-button value="stockinfo">股票信息</a-radio-button>
        <a-radio-button value="bars">K线数据</a-radio-button>
        <a-radio-button value="ticks">Tick数据</a-radio-button>
        <a-radio-button value="adjustfactors">复权因子</a-radio-button>
      </a-radio-group>
    </a-card>

    <a-card class="table-card">
      <template #title>
        <span>{{ dataTypeTitle }}</span>
      </template>
      <template #extra>
        <a-space>
          <a-input-search
            v-model:value="searchCode"
            placeholder="搜索股票代码"
            style="width: 200px"
            @search="loadData"
          />
          <a-button @click="loadData">
            <ReloadOutlined /> 刷新
          </a-button>
        </a-space>
      </template>

      <a-table
        :columns="currentColumns"
        :data-source="tableData"
        :loading="loading"
        :pagination="pagination"
        row-key="uuid"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'code'">
            <a @click="viewDetail(record)">{{ record.code }}</a>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined } from '@ant-design/icons-vue'

const loading = ref(false)
const refreshing = ref(false)
const dataType = ref('stockinfo')
const searchCode = ref('')
const tableData = ref<any[]>([])

const dataStats = reactive({
  totalStocks: 0,
  totalBars: 0,
  totalTicks: 0,
  totalAdjustFactors: 0
})

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const dataTypeTitle = computed(() => {
  const titles: Record<string, string> = {
    stockinfo: '股票信息',
    bars: 'K线数据',
    ticks: 'Tick数据',
    adjustfactors: '复权因子'
  }
  return titles[dataType.value] || '数据'
})

const stockColumns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '名称', dataIndex: 'name', width: 150 },
  { title: '交易所', dataIndex: 'exchange', width: 100 },
  { title: '类型', dataIndex: 'type', width: 100 },
  { title: '上市日期', dataIndex: 'list_date', width: 120 }
]

const barColumns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: '开盘价', dataIndex: 'open', width: 100 },
  { title: '最高价', dataIndex: 'high', width: 100 },
  { title: '最低价', dataIndex: 'low', width: 100 },
  { title: '收盘价', dataIndex: 'close', width: 100 },
  { title: '成交量', dataIndex: 'volume', width: 120 }
]

const tickColumns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '时间', dataIndex: 'timestamp', width: 180 },
  { title: '价格', dataIndex: 'price', width: 100 },
  { title: '成交量', dataIndex: 'volume', width: 100 }
]

const adjustColumns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: '因子', dataIndex: 'factor', width: 100 }
]

const currentColumns = computed(() => {
  const columnsMap: Record<string, any[]> = {
    stockinfo: stockColumns,
    bars: barColumns,
    ticks: tickColumns,
    adjustfactors: adjustColumns
  }
  return columnsMap[dataType.value] || stockColumns
})

const refreshStats = async () => {
  refreshing.value = true
  try {
    // TODO: 调用API获取统计数据
    dataStats.totalStocks = 5000
    dataStats.totalBars = 10000000
    dataStats.totalTicks = 100000000
    dataStats.totalAdjustFactors = 50000
    message.success('统计已刷新')
  } catch (error: any) {
    message.error(`刷新失败: ${error.message}`)
  } finally {
    refreshing.value = false
  }
}

const handleDataTypeChange = () => {
  pagination.current = 1
  loadData()
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取数据
    // 临时模拟数据
    if (dataType.value === 'stockinfo') {
      tableData.value = [
        { uuid: '1', code: '000001.SZ', name: '平安银行', exchange: '深交所', type: 'A股', list_date: '1991-04-03' },
        { uuid: '2', code: '000002.SZ', name: '万科A', exchange: '深交所', type: 'A股', list_date: '1991-01-29' }
      ]
    } else {
      tableData.value = []
    }
    pagination.total = tableData.value.length
  } catch (error: any) {
    message.error(`加载数据失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const viewDetail = (record: any) => {
  message.info(`查看 ${record.code} 详情`)
}

onMounted(() => {
  refreshStats()
  loadData()
})
</script>

<style scoped>
.data-management-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 8px;
}

.data-type-card,
.table-card {
  margin-bottom: 24px;
  border-radius: 8px;
}
</style>
