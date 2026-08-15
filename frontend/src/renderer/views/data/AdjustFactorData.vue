<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-purple">复权</span>
      复权因子
    </template>
    <template #actions>
      <input v-model="selectedCode" type="text" placeholder="股票代码 (可选)" class="control-input" />
      <button class="btn-primary" @click="loadData" :disabled="loading">查询</button>
    </template>

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
            <tr v-for="f in factors" :key="f.uuid" @contextmenu="openFactorMenu($event, f)">
              <td>{{ formatDate(f.timestamp) }}</td>
              <td>{{ f.code }}</td>
              <td class="num">{{ f.foreadjustfactor?.toFixed(6) }}</td>
              <td class="num">{{ f.backadjustfactor?.toFixed(6) }}</td>
              <td class="num">{{ f.adjustfactor?.toFixed(6) }}</td>
            </tr>
          </tbody>
        </table>
        <!-- 加载失败:区别于空态,提供重试 -->
        <div v-else-if="!loading && loadError" class="empty-state-small">
          <p class="error-text">{{ loadError }}</p>
          <button class="btn-primary btn-retry" @click="loadData">重试</button>
        </div>
        <div v-else-if="!loading && hasSearched" class="empty-state-small">查询无结果，请调整股票代码或分页</div>
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
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { useRoute } from 'vue-router'
import { dataApi } from '@/api/modules/data'
import type { AdjustFactorData } from '@/api/modules/data'
import dayjs from 'dayjs'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'

/** 行右键菜单(本页无行操作,给复制类) */
const { open: openCtxMenu } = useContextMenu()
const openFactorMenu = (e: MouseEvent, f: AdjustFactorData) => {
  openCtxMenu(e, [
    { label: '复制日期', action: () => { navigator.clipboard.writeText(formatDate(f.timestamp)); toast.success('已复制') } },
    { label: '复制代码', action: () => { navigator.clipboard.writeText(f.code); toast.success('已复制') } },
    { label: '复制前复权因子', action: () => { navigator.clipboard.writeText(String(f.foreadjustfactor ?? '')); toast.success('已复制') } },
  ])
}

const route = useRoute()

const selectedCode = ref((route.query.code as string) || '')
const loading = ref(false)
const factors = ref<AdjustFactorData[]>([])
// 查询失败(后端 5xx/网络断):须与"查询无结果"区分,否则误导用户以为无数据
const loadError = ref('')
const hasSearched = ref(false)

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
  loadError.value = ''
  hasSearched.value = true
  try {
    const params: any = {
      page: pagination.value.current,
      page_size: pagination.value.pageSize,
    }
    if (selectedCode.value) params.code = selectedCode.value

    const res: any = await dataApi.getAdjustFactors(params)
    factors.value = res?.items || []
    pagination.value.total = res?.total || 0
  } catch (e: any) {
    factors.value = []
    pagination.value.total = 0
    const st = e?.response?.status
    loadError.value = st ? `复权因子加载失败（HTTP ${st}）` : '复权因子加载失败，请检查网络后重试'
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
.control-input { padding: 6px 12px; background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 13px; }
.control-input:focus { outline: none; border-color: hsl(var(--primary)); }
.control-input[type="date"] { width: 140px; }

.tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card-small { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); padding: 16px; }
.stat-value-small { font-size: 20px; font-weight: 600; color: hsl(var(--foreground)); }
.stat-label-small { font-size: 12px; color: hsl(var(--muted-foreground)); margin-top: 4px; }

/* Table */
.card { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); }
.card-header-simple { padding: 12px 16px; font-size: 14px; font-weight: 600; color: hsl(var(--foreground)); border-bottom: 1px solid hsl(var(--border)); }
.table-wrapper { overflow-x: clip; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { position: sticky; top: 0; z-index: 1; padding: 10px 12px; text-align: left; color: hsl(var(--foreground)); background: hsl(var(--border)); font-weight: 600; white-space: nowrap; }
.data-table td { padding: 10px 12px; color: hsl(var(--foreground)); border-bottom: 1px solid hsl(var(--border)); }
.data-table tbody tr:hover { background: hsl(var(--secondary)); }
.data-table .num { font-variant-numeric: tabular-nums; font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }

.empty-state-small { padding: 40px; text-align: center; color: hsl(var(--muted-foreground)); }
.empty-state-small .error-text { color: hsl(var(--error)); margin: 0 0 12px; }
.btn-retry { padding: 6px 16px; background: transparent; border: 1px solid hsl(var(--border)); }
.btn-retry:hover { border-color: hsl(var(--primary)); color: hsl(var(--primary)); }

/* Pagination */
.pagination { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; border-top: 1px solid hsl(var(--border)); }
.pagination-info { font-size: 13px; color: hsl(var(--muted-foreground)); }
.pagination-controls { display: flex; gap: 4px; }
.pg-btn { min-width: 28px; height: 28px; padding: 0 6px; background: hsl(var(--border)); border: 1px solid hsl(var(--secondary)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.pg-btn:hover:not(:disabled) { background: hsl(var(--secondary)); border-color: hsl(var(--primary)); }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid hsl(var(--border)); border-top-color: hsl(var(--primary)); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
