<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-blue">股票</span>
      股票信息
    </template>
    <template #actions>
      <input
        v-model="searchKeyword"
        type="search"
        placeholder="搜索代码或名称"
        class="search-input"
        @keyup.enter="loadStocks"
      >
      <button
        class="btn-primary"
        :disabled="loading"
        @click="loadStocks"
      >
        刷新
      </button>
      <button
        class="btn-success"
        :disabled="syncing"
        @click="syncStockInfo"
      >
        同步数据
      </button>
    </template>

    <!-- 统计 -->
    <div class="stats-grid-three">
      <div class="stat-card">
        <div class="stat-value">
          {{ pagination.total }}
        </div>
        <div class="stat-label">
          股票总数
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-value">
          {{ exchangeStats.sh }}
        </div>
        <div class="stat-label">
          沪市
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-value">
          {{ exchangeStats.sz }}
        </div>
        <div class="stat-label">
          深市
        </div>
      </div>
    </div>

    <!-- 股票表格 -->
    <div class="card">
      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th
                style="cursor: pointer"
                @click="sortBy('code')"
              >
                代码 {{ sortField === 'code' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th
                style="cursor: pointer"
                @click="sortBy('name')"
              >
                名称 {{ sortField === 'name' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th
                style="cursor: pointer"
                @click="sortBy('exchange')"
              >
                交易所 {{ sortField === 'exchange' ? (sortAsc ? '↑' : '↓') : '' }}
              </th>
              <th>行业</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody v-if="!loading && stockList.length > 0">
            <tr
              v-for="stock in paginatedStocks"
              :key="stock.code"
              class="clickable-row"
              @click="viewStockDetail(stock)"
              @contextmenu="openStockMenu($event, stock)"
            >
              <td class="link">
                {{ stock.code }}
              </td>
              <td>
                {{ stock.name }}
                <span
                  v-if="stock.is_st"
                  class="tag tag-st"
                >ST</span>
              </td>
              <td>
                <span
                  class="tag"
                  :class="stock.exchange === 'SH' ? 'tag-sh' : 'tag-sz'"
                >
                  {{ stock.exchange === 'SH' ? '沪市' : '深市' }}
                </span>
              </td>
              <td>{{ stock.industry || '-' }}</td>
              <td>
                <span
                  class="tag"
                  :class="stock.is_active === false ? 'tag-st' : 'tag-sh'"
                >
                  {{ stock.is_active === false ? '退市' : '上市' }}
                </span>
              </td>
            </tr>
          </tbody>
          <tbody v-else-if="loading">
            <tr>
              <td
                colspan="6"
                class="text-center"
              >
                加载中...
              </td>
            </tr>
          </tbody>
          <tbody v-else>
            <tr>
              <td
                colspan="6"
                class="text-center"
              >
                暂无数据
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div
        v-if="filteredTotal > 0"
        class="pagination"
      >
        <button
          :disabled="pagination.current === 1"
          class="btn-small"
          @click="prevPage"
        >
          上一页
        </button>
        <span class="pagination-info">
          {{ (pagination.current - 1) * pagination.pageSize + 1 }} -
          {{ Math.min(pagination.current * pagination.pageSize, filteredTotal) }} / {{ filteredTotal }}
        </span>
        <button
          :disabled="pagination.current * pagination.pageSize >= filteredTotal"
          class="btn-small"
          @click="nextPage"
        >
          下一页
        </button>
        <select
          v-model="pagination.pageSize"
          class="page-size-select"
          @change="onPageSizeChange"
        >
          <option :value="20">
            20条/页
          </option>
          <option :value="50">
            50条/页
          </option>
          <option :value="100">
            100条/页
          </option>
        </select>
      </div>
    </div>

    <!-- 股票详情抽屉 -->
    <div
      v-if="detailDrawerVisible"
      class="drawer-overlay"
      @click.self="closeDrawer"
    >
      <div class="drawer">
        <div class="drawer-header">
          <h3>{{ currentStock?.name }}</h3>
          <button
            class="btn-close"
            @click="closeDrawer"
          >
            ×
          </button>
        </div>
        <div class="drawer-content">
          <div
            v-if="currentStock"
            class="stock-details"
          >
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
              <span class="detail-label">行业</span>
              <span class="detail-value">{{ currentStock.industry || '-' }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">状态</span>
              <span class="detail-value">{{ currentStock.is_active === false ? '退市' : '上市' }}</span>
            </div>
          </div>
          <div class="drawer-actions">
            <button
              class="btn-success"
              :disabled="syncing"
              @click="syncSingleStock"
            >
              同步K线数据
            </button>
            <button
              class="btn-primary"
              @click="viewBarData"
            >
              查看K线
            </button>
          </div>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { useRouter } from 'vue-router'
import { dataApi } from '@/api/modules/data'
import message from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'

const router = useRouter()
const loading = ref(false)
const searchKeyword = ref('')
const detailDrawerVisible = ref(false)
const currentStock = ref<any>(null)
const syncing = ref(false)

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

// 后端 /api/v1/data/stockinfo 无 exchange 字段(market 是 CHINA/NASDAQ 粗粒度),
// 交易所从代码后缀派生(.SH/.SZ),无后缀时回退 market
const deriveExchange = (stock: any): string => {
  const code = String(stock?.code || '')
  if (code.endsWith('.SH')) return 'SH'
  if (code.endsWith('.SZ')) return 'SZ'
  if (code.endsWith('.BJ')) return 'BJ'
  return stock?.market || '-'
}

// 搜索过滤(本地全量过滤,与分页解耦;分页显示口径用 filteredTotal)
const filteredStocks = computed(() => {
  let stocks = [...stockList.value]
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    stocks = stocks.filter(s =>
      s.code.toLowerCase().includes(keyword) ||
      s.name?.toLowerCase().includes(keyword)
    )
  }
  return stocks
})

const filteredTotal = computed(() => filteredStocks.value.length)

const paginatedStocks = computed(() => {
  const start = (pagination.current - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  const stocks = [...filteredStocks.value]

  // 排序
  stocks.sort((a, b) => {
    const aVal = a[sortField.value] || ''
    const bVal = b[sortField.value] || ''
    const cmp = String(aVal).localeCompare(String(bVal))
    return sortAsc.value ? cmp : -cmp
  })

  return stocks.slice(start, end)
})

// 后端单页上限 500(DEFAULT_MAX_PAGE_SIZE),分页循环拉全量,
// 本地排序/搜索/分页与沪深统计才有全量口径
const loadStocks = async () => {
  loading.value = true
  try {
    const pageSize = 500
    const all: any[] = []
    let page = 1
    // 安全上限 40 页(2 万条),防异常数据量拖死页面
    while (page <= 40) {
      const res = await dataApi.listStocks({ page, page_size: pageSize })
      const items = res?.items ?? []
      all.push(...items.map((s: any) => ({ ...s, exchange: deriveExchange(s) })))
      const total = res?.total ?? all.length
      if (all.length >= total || items.length === 0) break
      page++
    }
    stockList.value = all
    pagination.total = all.length
    pagination.current = 1
    exchangeStats.sh = all.filter(s => s.exchange === 'SH').length
    exchangeStats.sz = all.filter(s => s.exchange === 'SZ').length
  } catch (error: any) {
    console.error('加载股票列表失败:', error)
    message.error(error?.message || '加载股票列表失败')
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
  if (pagination.current * pagination.pageSize < filteredTotal.value) {
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

/** 行右键菜单:详情抽屉内操作的快捷入口 */
const { open: openCtxMenu } = useContextMenu()
const openStockMenu = (e: MouseEvent, stock: any) => {
  openCtxMenu(e, [
    { label: '查看详情', action: () => viewStockDetail(stock) },
    { label: '查看K线', action: () => { currentStock.value = stock; viewBarData() } },
    { label: '复制代码', action: () => { navigator.clipboard.writeText(stock.code); message.success('已复制') } },
    { divider: true },
    { label: '同步K线数据', action: () => { currentStock.value = stock; syncSingleStock() } },
  ])
}

const closeDrawer = () => {
  detailDrawerVisible.value = false
}

const syncStockInfo = async () => {
  if (syncing.value) return
  syncing.value = true
  try {
    await dataApi.syncStockInfo()
    message.success('股票信息同步任务已提交')
  } catch (error: any) {
    console.error('同步股票信息失败:', error)
    message.error(error?.message || '同步股票信息失败')
  } finally {
    syncing.value = false
  }
}

const syncSingleStock = async () => {
  const code = currentStock.value?.code
  if (!code || syncing.value) return
  syncing.value = true
  try {
    await dataApi.syncBars([code])
    message.success(`${code} K线同步任务已提交`)
  } catch (error: any) {
    console.error('同步K线数据失败:', error)
    message.error(error?.message || '同步K线数据失败')
  } finally {
    syncing.value = false
  }
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
.tag-st {
  background: hsl(var(--error));
  color: hsl(var(--foreground));
  margin-left: 4px;
}

.tag-sh {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.tag-sz {
  background: hsl(var(--success));
  color: hsl(var(--foreground));
}

.search-input {
  padding: 8px 12px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 14px;
  width: 200px;
}

.search-input:focus {
  outline: none;
  border-color: hsl(var(--primary));
}

.btn-success {
  padding: 8px 20px;
  background: hsl(var(--success));
  border: none;
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-success:hover {
  background: hsl(var(--success));
}

.stats-grid-three {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.table-wrapper {
  overflow-x: clip;
}

.text-center {
  text-align: center;
  color: hsl(var(--muted-foreground));
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
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}

.btn-small:hover:not(:disabled) {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
}

.btn-small:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-size-select {
  padding: 4px 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
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
  background: hsl(var(--card));
  border-left: 1px solid hsl(var(--border));
  display: flex;
  flex-direction: column;
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.drawer-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: hsl(var(--foreground));
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
  color: hsl(var(--muted-foreground));
}

.detail-value {
  font-size: 14px;
  color: hsl(var(--foreground));
  font-weight: 500;
}

.drawer-actions {
  display: flex;
  gap: 12px;
  padding: 20px;
  border-top: 1px solid hsl(var(--border));
}
</style>
