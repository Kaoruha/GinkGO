<template>
  <ListPage
    title="回测中心"
    :columns="columns"
    :data-source="tasks"
    :loading="loading && tasks.length === 0"
    row-key="uuid"
    :searchable="false"
    :creatable="false"
    :infinite-scroll="true"
    clickable
    @sort="onSort"
    @row-click="goDetail"
  >
    <template #filters>
      <select v-model="statusFilter" class="filter-select" @change="resetAndFetch">
        <option value="">全部状态</option>
        <option value="completed">已完成</option>
        <option value="running">进行中</option>
        <option value="pending">排队中</option>
        <option value="failed">失败</option>
        <option value="stopped">已停止</option>
        <option value="created">待调度</option>
      </select>
    </template>

    <template #name="{ record }">
      <router-link
        :to="`/portfolios/${record.portfolio_id}/backtests/${record.uuid}`"
        class="task-link"
        @click.stop
      >
        {{ record.name || record.uuid?.slice(0, 8) }}
      </router-link>
    </template>

    <template #portfolio_name="{ record }">
      <router-link
        v-if="record.portfolio_id"
        :to="`/portfolios/${record.portfolio_id}`"
        class="portfolio-link"
        @click.stop
      >
        {{ record.portfolio_name || record.portfolio_id?.slice(0, 8) }}
      </router-link>
      <span v-else class="val-muted">-</span>
    </template>

    <template #status="{ record }">
      <StatusTag :status="record.status" type="backtest" />
    </template>

    <template #annual_return="{ record }">
      <span :class="Number(record.annual_return) >= 0 ? 'val-green' : 'val-red'">
        {{ formatPct(record.annual_return) }}
      </span>
    </template>

    <template #sharpe_ratio="{ record }">
      <span :class="Number(record.sharpe_ratio) >= 0 ? 'val-green' : 'val-red'">
        {{ formatNum(record.sharpe_ratio, 2) }}
      </span>
    </template>

    <template #max_drawdown="{ record }">
      <span class="val-red">{{ formatPct(record.max_drawdown) }}</span>
    </template>

    <template #win_rate="{ record }">
      {{ formatPct(record.win_rate) }}
    </template>

    <template #total_signals="{ record }">
      <span class="val-muted">{{ record.total_signals ?? '-' }}</span>
      <span class="val-divider">/</span>
      <span class="val-muted">{{ record.total_orders ?? '-' }}</span>
    </template>

    <template #created_at="{ record }">
      <span class="val-muted">{{ formatTime(record.created_at) }}</span>
    </template>

    <!-- 无限滚动触发器 -->
    <template #afterTable>
      <div v-if="tasks.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
        <div v-if="loadingMore" class="spinner spinner-small"></div>
        <div v-else-if="!hasMore" class="no-more">没有更多了</div>
        <div v-else class="load-more-sentinel"></div>
      </div>
    </template>
  </ListPage>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import ListPage from '@/components/common/ListPage.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { backtestApi } from '@/api/modules/backtest'

const router = useRouter()

const tasks = ref<any[]>([])
const loading = ref(false)
const loadingMore = ref(false)
const total = ref(0)
const currentPage = ref(0)
const pageSize = 20
const statusFilter = ref('')
const sortBy = ref('annual_return')
const sortOrder = ref<'asc' | 'desc'>('desc')

const hasMore = computed(() => tasks.value.length < total.value)

const columns = [
  { title: '任务名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '组合', dataIndex: 'portfolio_name', key: 'portfolio_name', width: 150 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 90 },
  { title: '收益率', dataIndex: 'annual_return', key: 'annual_return', width: 100, sortable: true },
  { title: '夏普', dataIndex: 'sharpe_ratio', key: 'sharpe_ratio', width: 80, sortable: true },
  { title: '最大回撤', dataIndex: 'max_drawdown', key: 'max_drawdown', width: 100, sortable: true },
  { title: '胜率', dataIndex: 'win_rate', key: 'win_rate', width: 80, sortable: true },
  { title: '信号/订单', dataIndex: 'total_signals', key: 'total_signals', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160 },
]

const formatPct = (v: any) => v != null && v !== '' ? (Number(v) * 100).toFixed(2) + '%' : '-'
const formatNum = (v: any, d: number) => v != null && v !== '' ? Number(v).toFixed(d) : '-'
const formatTime = (t: string) => {
  if (!t) return '-'
  return t.replace('T', ' ').slice(0, 19)
}

function goDetail(record: any) {
  router.push(`/portfolios/${record.portfolio_id}/backtests/${record.uuid}`)
}

function onSort(field: string, order: 'asc' | 'desc') {
  sortBy.value = field
  sortOrder.value = order
  resetAndFetch()
}

async function resetAndFetch() {
  currentPage.value = 0
  tasks.value = []
  total.value = 0
  // 断开旧 observer，首次 fetch 完成后重建
  if (observer) { observer.disconnect(); observer = null }
  await fetchTasks(false)
  nextTick(() => setupObserver())
}

async function fetchTasks(append: boolean) {
  if (append) {
    if (!hasMore.value || loading.value || loadingMore.value) return
    loadingMore.value = true
    currentPage.value += 1
  } else {
    loading.value = true
    currentPage.value = 1
  }

  try {
    const params: any = { page: currentPage.value, page_size: pageSize }
    if (statusFilter.value) params.status = statusFilter.value
    if (sortBy.value) {
      params.sort_by = sortBy.value
      params.sort_order = sortOrder.value
    }
    const res: any = await backtestApi.list(params)
    const newData = res?.data || []
    if (append) {
      tasks.value.push(...newData)
    } else {
      tasks.value = newData
    }
    total.value = res?.meta?.total || 0
  } catch {
    if (!append) {
      tasks.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => fetchTasks(true)

// IntersectionObserver — 只建一次，靠 loadingMore/hasMore 守卫防重入
const loadMoreTrigger = ref<HTMLElement>()
let observer: IntersectionObserver | null = null

const setupObserver = () => {
  if (!loadMoreTrigger.value || observer) return
  const scrollableContainer = document.querySelector('.list-content')
  if (!scrollableContainer) return
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loading.value && !loadingMore.value) {
        loadMore()
      }
    },
    { root: scrollableContainer as Element, rootMargin: '200px', threshold: 0.1 }
  )
  observer.observe(loadMoreTrigger.value)
}

onMounted(async () => {
  await fetchTasks(false)
  nextTick(() => setupObserver())
})

onUnmounted(() => {
  if (observer) observer.disconnect()
})
</script>

<style scoped>
.task-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
}
.task-link:hover { text-decoration: underline; }

.portfolio-link {
  color: #8a8a9a;
  text-decoration: none;
  font-size: 12px;
}
.portfolio-link:hover { color: #1890ff; }

.val-green { color: #52c41a; font-weight: 500; }
.val-red { color: #f5222d; font-weight: 500; }
.val-muted { color: #8a8a9a; }
.val-divider { color: #3a3a4e; margin: 0 2px; }

.filter-select {
  padding: 6px 12px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.filter-select:focus { outline: none; border-color: #1890ff; }

.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.no-more {
  color: #5a5a6e;
  font-size: 12px;
}

.load-more-sentinel {
  height: 1px;
}
</style>
