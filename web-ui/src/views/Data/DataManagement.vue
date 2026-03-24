<template>
  <div class="data-management-container">
    <div class="page-header">
      <div>
        <h1 class="page-title">数据管理</h1>
        <p class="page-subtitle">管理股票信息、K线数据、Tick数据等市场数据</p>
      </div>
      <button class="btn-secondary" :disabled="refreshing" @click="refreshStats">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
        </svg>
        刷新统计
      </button>
    </div>

    <div class="stats-grid">
      <div class="stat-card stat-blue">
        <div class="stat-label">股票总数</div>
        <div class="stat-value">{{ dataStats.totalStocks }}</div>
      </div>
      <div class="stat-card stat-green">
        <div class="stat-label">K线数据量</div>
        <div class="stat-value">{{ formatNumber(dataStats.totalBars) }}</div>
      </div>
      <div class="stat-card stat-orange">
        <div class="stat-label">Tick数据量</div>
        <div class="stat-value">{{ formatNumber(dataStats.totalTicks) }}</div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-label">复权因子</div>
        <div class="stat-value">{{ formatNumber(dataStats.totalAdjustFactors) }}</div>
      </div>
    </div>

    <div class="card">
      <div class="card-body data-type-selector">
        <div class="radio-group-vertical">
          <label class="radio-label" :class="{ active: dataType === 'stockinfo' }">
            <input v-model="dataType" type="radio" value="stockinfo" @change="handleDataTypeChange" />
            股票信息
          </label>
          <label class="radio-label" :class="{ active: dataType === 'bars' }">
            <input v-model="dataType" type="radio" value="bars" @change="handleDataTypeChange" />
            K线数据
          </label>
          <label class="radio-label" :class="{ active: dataType === 'ticks' }">
            <input v-model="dataType" type="radio" value="ticks" @change="handleDataTypeChange" />
            Tick数据
          </label>
          <label class="radio-label" :class="{ active: dataType === 'adjustfactors' }">
            <input v-model="dataType" type="radio" value="adjustfactors" @change="handleDataTypeChange" />
            复权因子
          </label>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span>{{ dataTypeTitle }}</span>
        <div class="header-actions">
          <input v-model="searchCode" type="text" placeholder="搜索股票代码" class="form-input" @keyup.enter="loadData" />
          <button class="btn-secondary" @click="loadData">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            刷新
          </button>
        </div>
      </div>

      <div class="card-body">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th v-for="col in currentColumns" :key="col.dataIndex">{{ col.title }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in tableData" :key="record.uuid">
                <td v-for="col in currentColumns" :key="col.dataIndex">
                  <a v-if="col.dataIndex === 'code'" class="link" @click="viewDetail(record)">
                    {{ record[col.dataIndex] }}
                  </a>
                  <span v-else>{{ record[col.dataIndex] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="pagination">
          <div class="pagination-info">共 {{ pagination.total }} 条</div>
          <div class="pagination-controls">
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(1)">首页</button>
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(pagination.current - 1)">上一页</button>
            <span class="pagination-current">{{ pagination.current }} / {{ totalPages }}</span>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(pagination.current + 1)">下一页</button>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(totalPages)">末页</button>
            <select v-model="pagination.pageSize" @change="loadData" class="pagination-size">
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
import { ref, reactive, computed, onMounted } from 'vue'

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
  total: 0
})

const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize))

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

const formatNumber = (num: number) => {
  if (num >= 100000000) return (num / 100000000).toFixed(1) + '亿'
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  return num.toString()
}

const refreshStats = async () => {
  refreshing.value = true
  try {
    // TODO: 调用API获取统计数据
    dataStats.totalStocks = 5000
    dataStats.totalBars = 10000000
    dataStats.totalTicks = 100000000
    dataStats.totalAdjustFactors = 50000
    console.log('统计已刷新')
  } catch (error: any) {
    console.error(`刷新失败: ${error.message}`)
  } finally {
    refreshing.value = false
  }
}

const handleDataTypeChange = () => {
  pagination.current = 1
  loadData()
}

const goToPage = (page: number) => {
  pagination.current = page
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取数据
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
    console.error(`加载数据失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const viewDetail = (record: any) => {
  console.log(`查看 ${record.code} 详情`)
}

onMounted(() => {
  refreshStats()
  loadData()
})
</script>

<style scoped>
.data-management-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.btn-primary {
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #ffffff;
}

.stat-blue .stat-value { color: #1890ff; }
.stat-green .stat-value { color: #52c41a; }
.stat-orange .stat-value { color: #fa8c16; }
.stat-purple .stat-value { color: #722ed1; }

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 24px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header span {
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.data-type-selector {
  display: flex;
  justify-content: center;
}

.radio-group-vertical {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}

.radio-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-label:hover {
  border-color: #1890ff;
}

.radio-label.active {
  background: #1890ff;
  border-color: #1890ff;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.form-input {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  min-width: 200px;
}

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.table-wrapper {
  overflow-x: auto;
  margin-bottom: 16px;
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

.link {
  color: #1890ff;
  cursor: pointer;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
}

.pagination-btn {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  color: #ffffff;
  font-size: 14px;
  padding: 0 8px;
}

.pagination-size {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .radio-group-vertical {
    flex-direction: column;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
    align-items: stretch;
  }

  .form-input {
    width: 100%;
    min-width: unset;
  }

  .pagination {
    flex-direction: column;
    align-items: stretch;
  }

  .pagination-controls {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
