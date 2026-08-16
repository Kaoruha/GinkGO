<template>
  <PageLayout>
    <template #title>
      Worker 管理
    </template>
    <template #actions>
      <label class="switch-label">
        <input
          v-model="autoRefreshModel"
          type="checkbox"
          class="switch-input"
          @change="toggleAutoRefresh"
        >
        <span class="switch-slider" />
        <span class="switch-text">自动刷新</span>
      </label>
      <button
        class="btn-secondary"
        @click="refreshData"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
          <path d="M3 3v5h5" />
          <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
          <path d="M16 21h5v-5" />
        </svg>
        刷新
      </button>
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatCard
        title="总 Worker"
        :value="filteredWorkers.length"
      />
      <StatCard
        title="运行中"
        :value="runningCount"
        :color="runningCount > 0 ? 'positive' : 'neutral'"
      />
      <StatCard
        title="已停止"
        :value="stoppedCount"
        color="neutral"
      />
      <StatCard
        title="异常"
        :value="errorCount"
        :color="errorCount > 0 ? 'negative' : 'positive'"
      />
    </div>

    <!-- Worker 列表 -->
    <div class="card">
      <div class="card-header">
        <h3>Worker 列表</h3>
        <select
          v-model="typeFilter"
          class="filter-select"
        >
          <option value="">
            全部类型
          </option>
          <option
            v-for="t in WORKER_TYPES"
            :key="t.key"
            :value="t.key"
          >
            {{ t.label }}
          </option>
        </select>
      </div>
      <WorkerTable
        :workers="filteredWorkers"
        :loading="loading"
        expandable
        :heartbeat-tick="systemStore.lastUpdate"
        @row-contextmenu="openWorkerMenu"
      />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import StatCard from '@/components/common/StatCard.vue'
import WorkerTable from '@/components/admin/WorkerTable.vue'
import { useContextMenu } from '@/composables/useContextMenu'
import { useSystemStore } from '@/stores'
import { WORKER_TYPES } from '@/constants/statusConfig'

/** 行右键菜单(纯监控:仅刷新) */
const { open: openCtxMenu } = useContextMenu()
const openWorkerMenu = (e: MouseEvent) => {
  openCtxMenu(e, [
    { label: '刷新', action: refreshData },
  ])
}

const systemStore = useSystemStore()
const autoRefreshModel = ref(false)
const typeFilter = ref('')

const loading = computed(() => systemStore.loading)
const workers = computed(() => systemStore.workers)

const filteredWorkers = computed(() => {
  if (!typeFilter.value) return workers.value
  return workers.value.filter(w => w.type === typeFilter.value)
})

const runningCount = computed(() => filteredWorkers.value.filter(w => w.status === 'running' || w.status === 'active').length)
const stoppedCount = computed(() => filteredWorkers.value.filter(w => w.status === 'stopped' || w.status === 'idle').length)
const errorCount = computed(() => filteredWorkers.value.filter(w => w.status === 'error' || w.status === 'stale').length)

const refreshData = () => {
  systemStore.fetchWorkers()
}

const toggleAutoRefresh = () => {
  if (autoRefreshModel.value) {
    systemStore.enableAutoRefresh(5000)
  } else {
    systemStore.disableAutoRefresh()
  }
}

onMounted(() => {
  refreshData()
})

onUnmounted(() => {
  systemStore.disableAutoRefresh()
})
</script>

<style scoped>
/* 开关 */
.switch-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.switch-input {
  position: relative;
  width: 40px;
  height: 20px;
  appearance: none;
  background: hsl(var(--secondary));
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
  transition: background 0.3s;
}

.switch-input::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  background: hsl(var(--card));
  border-radius: 50%;
  transition: transform 0.3s;
}

.switch-input:checked {
  background: hsl(var(--primary));
}

.switch-input:checked::after {
  transform: translateX(20px);
}

.switch-text {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

/* 统计卡片:StatCard + 全局 .stats-grid/.stat-card(间距需页内补) */
.stats-grid {
  margin-bottom: 16px;
}

/* 筛选下拉 */
.filter-select {
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  color: hsl(var(--foreground));
  font-size: 13px;
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
