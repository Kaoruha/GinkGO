<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-purple">复权</span>
      复权因子
    </template>
    <template #actions>
      <input
        v-model="selectedCode"
        type="text"
        placeholder="股票代码 (可选)"
        class="control-input"
      >
      <button
        class="btn-primary"
        :disabled="loading"
        @click="loadData"
      >
        查询
      </button>
    </template>

    <!-- 统计卡片 -->
    <div
      v-if="factors.length > 0"
      class="stats-grid"
    >
      <div class="stat-card-small">
        <div class="stat-value-small">
          {{ formatNumber(pagination.total) }}
        </div>
        <div class="stat-label-small">
          记录数
        </div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">
          {{ stats.codeCount }}
        </div>
        <div class="stat-label-small">
          股票数
        </div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">
          {{ stats.latestFore }}
        </div>
        <div class="stat-label-small">
          最新前复权因子
        </div>
      </div>
      <div class="stat-card-small">
        <div class="stat-value-small">
          {{ stats.latestBack }}
        </div>
        <div class="stat-label-small">
          最新后复权因子
        </div>
      </div>
    </div>

    <!-- 数据表格:ProTable(服务端分页+右键菜单) -->
    <ProTable
      v-if="factors.length > 0"
      :columns="columns"
      :data-source="factors"
      row-key="uuid"
      server-pagination
      :total="pagination.total"
      :page="pagination.current"
      :page-size="pagination.pageSize"
      :page-sizes="[pagination.pageSize]"
      :context-menu="factorMenu"
      @update:page="goPage"
    >
      <template #timestamp="{ record }">
        {{ formatDay(record.timestamp) }}
      </template>
      <template #foreadjustfactor="{ record }">
        {{ record.foreadjustfactor?.toFixed(6) }}
      </template>
      <template #backadjustfactor="{ record }">
        {{ record.backadjustfactor?.toFixed(6) }}
      </template>
      <template #adjustfactor="{ record }">
        {{ record.adjustfactor?.toFixed(6) }}
      </template>
    </ProTable>
    <!-- 加载失败:区别于空态,提供重试 -->
    <div
      v-else-if="!loading && loadError"
      class="card"
    >
      <div class="empty-state-small">
        <p class="error-text">
          {{ loadError }}
        </p>
        <button
          class="btn-primary btn-retry"
          @click="loadData"
        >
          重试
        </button>
      </div>
    </div>
    <div
      v-else-if="!loading && hasSearched"
      class="card"
    >
      <div class="empty-state-small">
        查询无结果，请调整股票代码或分页
      </div>
    </div>
    <div
      v-else-if="!loading"
      class="card"
    >
      <div class="empty-state-small">
        点击查询加载数据
      </div>
    </div>

    <div
      v-if="loading"
      class="loading-overlay"
    >
      <div class="spinner" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import ProTable from '@/components/common/ProTable.vue'
import { useRoute } from 'vue-router'
import { dataApi } from '@/api/modules/data'
import type { AdjustFactorData } from '@/api/modules/data'
import { message as toast } from '@/utils/toast'
import type { MenuItem } from '@/composables/useContextMenu'
import { formatDay, formatNumber } from '@/utils/format'

const columns = [
  { title: '日期', dataIndex: 'timestamp' },
  { title: '代码', dataIndex: 'code' },
  { title: '前复权因子', dataIndex: 'foreadjustfactor', num: true },
  { title: '后复权因子', dataIndex: 'backadjustfactor', num: true },
  { title: '原始因子', dataIndex: 'adjustfactor', num: true },
]

/** 行右键菜单(本页无行操作,给复制类) */
const factorMenu = (f: AdjustFactorData): MenuItem[] => [
  { label: '复制日期', action: () => { navigator.clipboard.writeText(formatDay(f.timestamp)); toast.success('已复制') } },
  { label: '复制代码', action: () => { navigator.clipboard.writeText(f.code); toast.success('已复制') } },
  { label: '复制前复权因子', action: () => { navigator.clipboard.writeText(String(f.foreadjustfactor ?? '')); toast.success('已复制') } },
]

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
/* 表格/分页由 ProTable 持有;此处仅页面特有样式 */

.control-input { padding: 6px 12px; background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-sm); color: hsl(var(--foreground)); font-size: 13px; }
.control-input:focus { outline: none; border-color: hsl(var(--primary)); }
.control-input[type="date"] { width: 140px; }

.tag { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }

/* Stats */
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 16px; }
.stat-card-small { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); padding: 16px; }
.stat-value-small { font-size: 20px; font-weight: 600; color: hsl(var(--foreground)); }
.stat-label-small { font-size: 12px; color: hsl(var(--muted-foreground)); margin-top: 4px; }

.card { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius-lg); }

.empty-state-small { padding: 40px; text-align: center; color: hsl(var(--muted-foreground)); }
.empty-state-small .error-text { color: hsl(var(--error)); margin: 0 0 12px; }
.btn-retry { padding: 6px 16px; background: transparent; border: 1px solid hsl(var(--border)); }
.btn-retry:hover { border-color: hsl(var(--primary)); color: hsl(var(--primary)); }

/* Loading */
.loading-overlay { display: flex; justify-content: center; padding: 40px; }
.spinner { width: 32px; height: 32px; border: 3px solid hsl(var(--border)); border-top-color: hsl(var(--primary)); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
