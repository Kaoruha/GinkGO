<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-purple">复权</span>
        复权因子
      </div>
      <div class="header-controls">
        <input v-model="selectedCode" type="text" placeholder="股票代码 (可选)" class="control-input" />
        <input v-model="startDate" type="date" class="control-input" />
        <input v-model="endDate" type="date" class="control-input" />
        <button class="btn-primary" @click="loadData" :disabled="loading">查询</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid" v-if="factors.length > 0">
      <div class="stat-card-small">
        <div class="stat-value-small">{{ pagination.total.toLocaleString() }}</div>
        <div class="stat-label-small">记录数</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ stats.codeCount }}</div>
        <div class="stat-label-small">股票数</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ stats.latestFore }}</div>
        <div class="stat-label-small">最新前复权因子</div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">{{ stats.latestBack }}</div>
        <div class="stat-label-small">最新后复权因子</div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="card">
      <div class="card-header-simple">复权因子数据</div>
      <div class="table-wrapper">
        <table class="data-table" v-if="factors.length > 0">
          <thead>
            <tr>
              <th>日期</th>
              <th>代码</th>
              <th>前复权因子</th>
              <th>后复权因子</th>
              <th>原始因子</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in factors" :key="f.uuid">
              <td>{{ formatDate(f.timestamp) }}</td>
              <td>{{ f.code }}</td>
              <td class="num">{{ f.foreadjustfactor?.toFixed(6) }}</td>
              <td class="num">{{ f.backadjustfactor?.toFixed(6) }}</td>
              <td class="num">{{ f.adjustfactor?.toFixed(6) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else-if="!loading" class="empty-state-small">点击查询加载数据</div>
      </div>

      <!-- 分页 -->
      <div class="pagination" v-if="pagination.total > 0">
        <span class="pagination-info">
          共 {{ pagination.total.toLocaleString() }} 条，第 {{ pagination.current }} / {{ totalPages }} 页
        </span>
        <div class="pagination-controls">
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(1)">«</button>
          <button class="pg-btn" :disabled="pagination.current <= 1" @click="goPage(pagination.current - 1)">‹</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(pagination.current + 1)">›</button>
          <button class="pg-btn" :disabled="pagination.current >= totalPages" @click="goPage(totalPages)">»</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-overlay"><div class="spinner"></div></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { dataApi } from '@/api/modules/data'
import type { AdjustFactorData } from '@/api/modules/data'
import dayjs from 'dayjs'

const route = useRoute()

const selectedCode = ref((route.query.code as string) || '')
const startDate = ref(dayjs().subtract(30, 'day').format('YYYY-MM-DD'))
const endDate = ref(dayjs().format('YYYY-MM-DD'))
const loading = ref(false)
const factors = ref<AdjustFactorData[]>([])

const pagination = ref({ current: 1, pageSize: 50, total: 0 })
const totalPages = computed(() => Math.max(1, Math.ceil(pagination.value.total / pagination.value.pageSize)))

const stats = computed(() => {
  if (factors.value.length === 0) return { codeCount: 0, latestFore: '-', latestBack: '-' }
  const codes = new Set(factors.value.map(f => f.code))
  const latest = factors.value[factors.value.length - 1]
  return {
    codeCount: codes.size,
    latestFore: latest?.foreadjustfactor?.toFixed(6) || '-',
    latestBack: latest?.backadjustfactor?.toFixed(6) || '-',
  }
})

function formatDate(t: string) {
  if (!t) return '-'
  return dayjs(t).format('YYYY-MM-DD')
}

async function loadData() {
  loading.value = true
  try {
    const params: any = {
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    }
    if (selectedCode.value) params.code = selectedCode.value
    if (startDate.value) params.start_date = startDate.value
    if (endDate.value) params.end_date = endDate.value

    const res: any = await dataApi.getAdjustFactors(params)
    factors.value = res?.data || []
    pagination.value.total = res?.meta?.total || 0
  } catch {
    factors.value = []
    pagination.value.total = 0
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  pagination.value.current = p
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.page-container { position: relative; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
.page-title { font-size: 20px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 8px; }
.header-controls { display: flex; gap: 10px; align-items: center; }
.control-input { padding: 6px 12px; background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 4px; color: #fff; font-size: 13px; }
.control-input:focus { outline: none; border-color: #1890ff; }
.control-input[type="date"] { width: 140px; }

.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
.tag-purple { background: rgba(114,46,209,0.15); color: #b37feb; }

.btn-primary { display: inline-flex; align-items: center; padding: 7px 16px; background: #1890ff; border: none; border-radius: 4px; color: #fff; font-size: 13px; cursor: pointer; }
.btn-primary:hover { background: #40a9ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card-small { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; padding: 16px; }
.stat-value-small { font-size: 20px; font-weight: 600; color: #fff; }
.stat-label-small { font-size: 12px; color: #8a8a9a; margin-top: 4px; }

/* Table */
.card { background: #1a1a2e; border: 1px solid #2a2a3e; border-radius: 8px; overflow: hidden; }
.card-header-simple { padding: 12px 16px; font-size: 14px; font-weight: 600; color: #fff; border-bottom: 1px solid #2a2a3e; }
.table-wrapper { overflow-x: auto; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { padding: 10px 12px; text-align: left; color: #fff; background: #2a2a3e; font-weight: 600; white-space: nowrap; }
.data-table td { padding: 10px 12px; color: #fff; border-bottom: 1px solid #2a2a3e; }
.data-table tbody tr:hover { background: #22223a; }
.data-table .num { font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

.empty-state-small { padding: 40px; text-align: center; color: #8a8a9a; }

/* Pagination */
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid #2a2a3e; }
.pagination-info { font-size: 13px; color: #8a8a9a; }
.pagination-controls { display: flex; gap: 4px; }
.pg-btn { min-width: 28px; height: 28px; padding: 0 6px; background: #2a2a3e; border: 1px solid #3a3a4e; border-radius: 4px; color: #fff; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.pg-btn:hover:not(:disabled) { background: #3a3a4e; border-color: #1890ff; }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid #2a2a3e; border-top-color: #1890ff; border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .header-controls { flex-wrap: wrap; }
}
</style>
