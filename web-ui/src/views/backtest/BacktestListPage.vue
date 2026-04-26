<template>
  <ListPage
    title="回测中心"
    :columns="columns"
    :data-source="tasks"
    :loading="loading"
    row-key="uuid"
    :searchable="false"
    :creatable="false"
    :total="total"
    :page="currentPage"
    :page-size="pageSize"
    :server-pagination="true"
    clickable
    @update:page="onPageChange"
    @update:page-size="onPageSizeChange"
    @sort="onSort"
    @row-click="goDetail"
  >
    <template #filters>
      <select v-model="statusFilter" class="filter-select" @change="fetchTasks">
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
  </ListPage>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import ListPage from '@/components/common/ListPage.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { backtestApi } from '@/api/modules/backtest'

const router = useRouter()

const tasks = ref<any[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)
const statusFilter = ref('')
const sortBy = ref('annual_return')
const sortOrder = ref<'asc' | 'desc'>('desc')

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

function onPageChange(p: number) {
  currentPage.value = p
  fetchTasks()
}

function onPageSizeChange(s: number) {
  pageSize.value = s
  currentPage.value = 1
  fetchTasks()
}

function onSort(field: string, order: 'asc' | 'desc') {
  sortBy.value = field
  sortOrder.value = order
  fetchTasks()
}

async function fetchTasks() {
  loading.value = true
  try {
    const params: any = { page: currentPage.value, page_size: pageSize.value }
    if (statusFilter.value) params.status = statusFilter.value
    if (sortBy.value) {
      params.sort_by = sortBy.value
      params.sort_order = sortOrder.value
    }
    const res: any = await backtestApi.list(params)
    tasks.value = res?.data || []
    total.value = res?.meta?.total || 0
  } catch {
    tasks.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(() => fetchTasks())
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
</style>
