<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">股票</span>
        股票信息
      </div>
      <div class="header-controls">
        <input
          v-model="searchKeyword"
          type="search"
          placeholder="搜索代码或名称"
          class="search-input"
          @keyup.enter="loadStocks"
        />
        <button class="btn-primary" :disabled="loading" @click="loadStocks">
          刷新
        </button>
        <button class="btn-success" @click="syncStockInfo">
          同步数据
        </button>
      </div>
    </div>

    <!-- 统计 -->
    <div class="stats-grid-three">
      <div class="stat-card">
        <div class="stat-value">{{ pagination.total }}</div>
        <div class="stat-label">股票总数</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ exchangeStats.sh }}</div>
        <div class="stat-label">沪市</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ exchangeStats.sz }}</div>
        <div class="stat-label">深市</div>
      </div>
    </div>

    <!-- 股票表格 -->
    <div class="card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th @click="sortBy('code')" style="cursor: pointer">
                代码 {{ sortField === 'code' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th @click="sortBy('name')" style="cursor: pointer">
                名称 {{ sortField === 'name' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th @click="sortBy('exchange')" style="cursor: pointer">
                交易所 {{ sortField === 'exchange' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th>类型</th>
              <th>行业</th>
              <th @click="sortBy('list_date')" style="cursor: pointer">
                上市日期 {{ sortField === 'list_date' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
            </tr>
          </thead>
          <tbody v-if="!loading && stockList.length > 0">
            <tr
              v-for="stock in paginatedStocks"
              :key="stock.code"
              @click="viewStockDetail(stock)"
              class="clickable-row"
            >
              <td class="link">{{ stock.code }}</td>
              <td>
                {{ stock.name }}
                <span v-if="stock.is_st" class="tag tag-st">ST</span>
              </td>
              <td>
                <span class="tag" :class="stock.exchange === 'SH' ? 'tag-sh' : 'tag-sz'">
                  {{ stock.exchange === 'SH' ? '沪市' : '深市' }}
                </span>
              </td>
              <td>{{ stock.type || '-' }}</td>
              <td>{{ stock.industry || '-' }}</td>
              <td>{{ stock.list_date || '-' }}</td>
            </tr>
          </tbody>
          <tbody v-else-if="loading">
            <tr>
              <td colspan="6" class="text-center">加载中...</td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td colspan="6" class="text-center">暂无数据</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-if="stockList.length > 0" class="pagination">
        <button @click="prevPage" :disabled="pagination.current === 1" class="btn-small">上一页</button>
        <span class="pagination-info">
          {{ (pagination.current - 1) * pagination.pageSize + 1 }} -
          {{ Math.min(pagination.current * pagination.pageSize, pagination.total) }} / {{ pagination.total }}
        </span>
        <button @click="nextPage" :disabled="pagination.current * pagination.pageSize >= pagination.total" class="btn-small">下一页</button>
        <select v-model="pagination.pageSize" @change="onPageSizeChange" class="page-size-select">
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 股票详情抽屉 -->
    <div v-if="detailDrawerVisible" class="drawer-overlay" @click.self="closeDrawer">
      <div class="drawer">
        <div class="drawer-header">
          <h3>{{ currentStock?.name }}</h3>
          <button @click="closeDrawer" class="btn-close">×</button>
        </div>
        <div class="drawer-content">
          <div v-if="currentStock" class="stock-details">
            <div class="detail-row">
              <span class="detail-label">代码</span>
              <span class="detail-value">{{ currentStock.code }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">名称</span>
              <span class="detail-value">{{ currentStock.name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">交易所</span>
              <span class="detail-value">{{ currentStock.exchange }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">类型</span>
              <span class="detail-value">{{ currentStock.type || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">行业</span>
              <span class="detail-value">{{ currentStock.industry || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">上市日期</span>
              <span class="detail-value">{{ currentStock.list_date || '-' }}</span>
            </div>
          </div>
          <div class="drawer-actions">
            <button class="btn-success" @click="syncSingleStock">
              同步K线数据
            </button>
            <button class="btn-primary" @click="viewBarData">
              查看K线
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const searchKeyword = ref('')
const detailDrawerVisible = ref(false)
const currentStock = ref<any>(null)

const stockList = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

const sortField = ref('code')
const sortAsc = ref(true)

const exchangeStats = reactive({
  sh: 0,
  sz: 0
})

const paginatedStocks = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  let stocks = [...stockList.value]

  // 排序
  stocks.sort((a, b) => {
    const aVal = a[sortField.value] || ''
    const bVal = b[sortField.value] || ''
    const cmp = String(aVal).localeCompare(String(bVal))
    return sortAsc.value ? cmp : -cmp
  })

  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    stocks = stocks.filter(s =>
      s.code.toLowerCase().includes(keyword) ||
      s.name?.toLowerCase().includes(keyword)
    )
  }

  pagination.total = stocks.length
  return stocks.slice(start, end)
})

const loadStocks = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取股票列表
    stockList.value = [
      { code: '000001.SZ', name: '平安银行', exchange: 'SZ', type: 'A股', industry: '银行', list_date: '1991-04-03' },
      { code: '000002.SZ', name: '万科A', exchange: 'SZ', type: 'A股', industry: '房地产', list_date: '1991-01-29' },
      { code: '600000.SH', name: '浦发银行', exchange: 'SH', type: 'A股', industry: '银行', list_date: '1999-11-10' },
      { code: '600519.SH', name: '贵州茅台', exchange: 'SH', type: 'A股', industry: '白酒', list_date: '2001-08-27' },
    ]
    pagination.total = stockList.value.length
    exchangeStats.sh = stockList.value.filter(s => s.exchange === 'SH').length
    exchangeStats.sz = stockList.value.filter(s => s.exchange === 'SZ').length
  } catch (error: any) {
    console.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const prevPage = () => {
  if (pagination.current > 1) {
    pagination.current--
  }
}

const nextPage = () => {
  if (pagination.current * pagination.pageSize < pagination.total) {
    pagination.current++
  }
}

const onPageSizeChange = () => {
  pagination.current = 1
}

const sortBy = (field: string) => {
  if (sortField.value === field) {
    sortAsc.value = !sortAsc.value
  } else {
    sortField.value = field
    sortAsc.value = true
  }
}

const viewStockDetail = (stock: any) => {
  currentStock.value = stock
  detailDrawerVisible.value = true
}

const closeDrawer = () => {
  detailDrawerVisible.value = false
}

const syncStockInfo = () => {
  console.log('同步股票信息...')
}

const syncSingleStock = () => {
  console.log(`同步 ${currentStock.value?.code} K线数据...`)
}

const viewBarData = () => {
  if (currentStock.value) {
    router.push(`/data/bars?code=${currentStock.value.code}`)
  }
}

onMounted(() => {
  loadStocks()
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
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tag-st {
  background: #f5222d;
  color: #ffffff;
  margin-left: 4px;
}

.tag-sh {
  background: #1890ff;
  color: #ffffff;
}

.tag-sz {
  background: #52c41a;
  color: #ffffff;
}

.search-input {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  width: 200px;
}

.search-input:focus {
  outline: none;
  border-color: #1890ff;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-success {
  padding: 8px 20px;
  background: #52c41a;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-success:hover {
  background: #73d13d;
}

.stats-grid-three {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
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

.data-table tbody tr {
  cursor: pointer;
  transition: background-color 0.2s;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.data-table .link {
  color: #1890ff;
  text-decoration: none;
}

.data-table .link:hover {
  text-decoration: underline;
}

.text-center {
  text-align: center;
  color: #8a8a9a;
  padding: 20px;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  padding: 16px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 13px;
}

.btn-small:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-size-select {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

/* 抽屉 */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.drawer {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 400px;
  background: #1a1a2e;
  border-left: 1px solid #2a2a3e;
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #2a2a3e;
}

.drawer-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.drawer-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}

.stock-details {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 14px;
  color: #8a8a9a;
}

.detail-value {
  font-size: 14px;
  color: #ffffff;
  font-weight: 500;
}

.drawer-actions {
  display: flex;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid #2a2a3e;
}
</style>
