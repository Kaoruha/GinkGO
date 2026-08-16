<template>
  <PageLayout>
    <template #title>
      系统状态
      <StatusTag
        type="system"
        :status="systemStore.systemHealth"
      />
    </template>
    <template #meta>
      <!-- 低价值元信息降级到副行:不再占统计卡 -->
      <span>v{{ systemStore.version }}</span>
      <span>调试模式 {{ systemStore.debugMode ? '开' : '关' }}</span>
      <span>最后更新 {{ lastUpdate }}</span>
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
        @click="fetchStatus"
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

    <!-- 异常横幅:降级/异常时置顶,健康时不占空间 -->
    <div
      v-if="healthIssues.length"
      class="alert-banner"
      :class="`alert-${systemStore.systemHealth}`"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line
          x1="12"
          y1="9"
          x2="12"
          y2="13"
        />
        <line
          x1="12"
          y1="17"
          x2="12.01"
          y2="17"
        />
      </svg>
      <div class="alert-body">
        <div class="alert-title">
          {{ systemStore.systemHealth === 'unhealthy' ? '系统异常' : '系统降级' }}
        </div>
        <ul class="alert-list">
          <li
            v-for="(issue, i) in healthIssues"
            :key="i"
          >
            {{ issue }}
          </li>
        </ul>
      </div>
    </div>

    <!-- 核心指标:4 张数值卡(复用全局 .stats-grid + StatCard) -->
    <div class="stats-grid">
      <StatCard
        title="基础设施"
        :value="okInfraCount"
        suffix="/ 4 已连接"
        :color="okInfraCount === infraTotal ? 'neutral' : 'negative'"
      />
      <StatCard
        title="在线组件"
        :value="onlineWorkerCount"
        :suffix="`/ ${systemStore.totalWorkerCount}`"
        :color="onlineWorkerCount === systemStore.totalWorkerCount ? 'neutral' : 'negative'"
      />
      <StatCard
        title="异常组件"
        :value="anomalyWorkerCount"
        :color="anomalyWorkerCount > 0 ? 'negative' : 'positive'"
      />
      <StatCard
        title="运行中任务"
        :value="runningTaskCount"
      />
    </div>

    <!-- 基础设施状态 -->
    <div class="card">
      <div class="card-header">
        <h3>基础设施</h3>
      </div>
      <div class="infra-grid">
        <div
          v-for="(info, name) in infrastructure"
          :key="name"
          class="infra-card"
        >
          <div class="infra-header">
            <span class="infra-name">{{ INFRA_NAMES[name] || name }}</span>
            <StatusTag
              type="infra"
              :status="info.status"
            />
          </div>
          <div
            v-if="info.error"
            class="infra-error"
          >
            {{ info.error }}
          </div>
          <div
            v-if="info.latency_ms !== undefined"
            class="infra-info"
          >
            延迟: {{ info.latency_ms }}ms
          </div>
          <div
            v-if="info.topics !== undefined"
            class="infra-info"
          >
            Topics: {{ info.topics }}
          </div>
        </div>
      </div>
    </div>

    <!-- 组件详情:统计 chips 兼作类型筛选,异常组件排序置顶 -->
    <div class="card">
      <div class="card-header">
        <h3>组件详情</h3>
        <div class="type-chips">
          <button
            class="type-chip"
            :class="{ active: typeFilter === 'all' }"
            @click="typeFilter = 'all'"
          >
            全部 {{ systemStore.totalWorkerCount }}
          </button>
          <button
            v-for="t in visibleComponentTypes"
            :key="t.key"
            class="type-chip"
            :class="{ active: typeFilter === t.key }"
            @click="typeFilter = t.key"
          >
            {{ t.label }} <span :class="onlineCount(t.key) < totalCount(t.key) ? 'chip-warn' : ''">{{ onlineCount(t.key) }}/{{ totalCount(t.key) }}</span>
          </button>
        </div>
      </div>
      <div
        v-if="workerLoading"
        class="loading-container"
      >
        <div class="spinner" />
      </div>
      <div
        v-else-if="filteredWorkers.length > 0"
        class="table-wrapper"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th>组件 ID</th>
              <th>类型</th>
              <th>状态</th>
              <th>详情</th>
              <th>最后心跳</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="record in filteredWorkers"
              :key="`${record.type}-${record.id}`"
            >
              <td class="monospace">
                {{ record.id }}
              </td>
              <td>
                <span
                  class="tag"
                  :class="workerTypeTagClass(record.type)"
                >
                  {{ workerTypeLabel(record.type) }}
                </span>
              </td>
              <td>
                <StatusTag
                  type="worker"
                  :status="record.status"
                />
              </td>
              <td class="detail-text">
                <template v-if="record.type === 'backtest_worker'">
                  任务: {{ record.task_count || 0 }}/{{ record.max_tasks || 5 }}
                </template>
                <template v-else-if="record.type === 'execution_node'">
                  Portfolio: {{ record.portfolio_count || 0 }}
                </template>
                <template v-else-if="record.type === 'scheduler'">
                  运行: {{ record.running_tasks || 0 }} / 待处理: {{ record.pending_tasks || 0 }}
                </template>
                <template v-else-if="record.type === 'task_timer'">
                  定时任务: {{ record.jobs_count || 0 }}
                </template>
                <template v-else>
                  已处理: {{ record.task_count || 0 }}
                </template>
              </td>
              <td
                class="monospace"
                :class="{ 'heartbeat-stale': isHeartbeatStale(record) }"
              >
                {{ formatRelativeTime(record.last_heartbeat) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        :description="typeFilter === 'all' ? '暂无组件' : '该类型暂无组件'"
      />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { formatRelativeTime } from '@/utils/format'
import { WORKER_TYPES, workerTypeTagClass, workerTypeLabel } from '@/constants/statusConfig'
import { useSystemStore } from '@/stores'
import type { WorkerInfo } from '@/api'

// ========== Store ==========
const systemStore = useSystemStore()

// ========== 本地状态 ==========
const autoRefreshModel = ref(systemStore.autoRefresh)
/** 组件类型筛选('all' | 组件 type) */
const typeFilter = ref('all')

// ========== 常量 ==========
const INFRA_NAMES: Record<string, string> = {
  mysql: 'MySQL',
  redis: 'Redis',
  kafka: 'Kafka',
  clickhouse: 'ClickHouse',
}

const COMPONENT_TYPES = WORKER_TYPES

/** 异常严重度:越小越靠前(error > stale > stopped/idle > 其他) */
const SEVERITY_RANK: Record<string, number> = {
  error: 0,
  stale: 1,
  stopped: 2,
  idle: 2,
}

const isOnline = (status: string) =>
  status === 'running' || status === 'healthy' || status === 'active'

const isAnomaly = (status: string) => status === 'error' || status === 'stale'

// ========== 计算属性 ==========
const workerLoading = computed(() => systemStore.loading)

const lastUpdate = computed(() => {
  if (!systemStore.lastUpdate) return '-'
  return new Date(systemStore.lastUpdate).toLocaleTimeString()
})

const infrastructure = computed(() => {
  const infra = systemStore.infrastructure
  if (!infra) return {}
  return {
    mysql: infra.mysql || { status: 'unknown' },
    redis: infra.redis || { status: 'unknown' },
    kafka: infra.kafka || { status: 'unknown' },
    clickhouse: infra.clickhouse || { status: 'unknown' },
  } as Record<string, { status: string; error?: string; latency_ms?: number; topics?: number }>
})

const workers = computed(() => systemStore.workers)

const infraTotal = computed(() => Object.keys(infrastructure.value).length || 4)

const okInfraCount = computed(() =>
  Object.values(infrastructure.value).filter(
    info => info.status === 'ok' || info.status === 'connected',
  ).length,
)

const onlineWorkerCount = computed(() =>
  workers.value.filter(w => isOnline(w.status)).length,
)

const anomalyWorkerCount = computed(() =>
  workers.value.filter(w => isAnomaly(w.status)).length,
)

const runningTaskCount = computed(() =>
  workers.value.reduce((sum, w) => {
    if (w.type === 'backtest_worker') return sum + (w.task_count || 0)
    if (w.type === 'scheduler') return sum + (w.running_tasks || 0)
    return sum
  }, 0),
)

/** 横幅异常清单:基础设施错误 + 异常组件 */
const healthIssues = computed(() => {
  const issues: string[] = []
  for (const [name, info] of Object.entries(infrastructure.value)) {
    if (info.status === 'error') {
      issues.push(`${INFRA_NAMES[name] || name} 连接错误${info.error ? `：${info.error}` : ''}`)
    }
  }
  for (const w of workers.value) {
    if (isAnomaly(w.status)) {
      issues.push(`${workerTypeLabel(w.type)} ${w.id} 状态异常（${w.status}）`)
    }
  }
  return issues
})

/** 只显示有注册组件的类型 chip */
const visibleComponentTypes = computed(() =>
  COMPONENT_TYPES.filter(t => (systemStore.componentCounts as any)[t.countsKey] > 0),
)

/** 异常置顶,同级按类型 + ID 稳定排序 */
const filteredWorkers = computed(() =>
  workers.value
    .filter(w => typeFilter.value === 'all' || w.type === typeFilter.value)
    .slice()
    .sort((a, b) => {
      const rank = (SEVERITY_RANK[a.status] ?? 3) - (SEVERITY_RANK[b.status] ?? 3)
      if (rank !== 0) return rank
      if (a.type !== b.type) return a.type.localeCompare(b.type)
      return a.id.localeCompare(b.id)
    }),
)

// ========== 方法 ==========
const onlineCount = (type: string): number =>
  workers.value.filter(w => w.type === type && isOnline(w.status)).length

const totalCount = (type: string): number => {
  const t = COMPONENT_TYPES.find(t => t.key === type)
  if (!t) return 0
  return (systemStore.componentCounts as any)[t.countsKey] || 0
}

/** 心跳超过 60s 视为过期,标橙提示 */
const isHeartbeatStale = (record: WorkerInfo): boolean => {
  if (!record.last_heartbeat) return false
  const ts = new Date(record.last_heartbeat).getTime()
  if (isNaN(ts)) return false
  return Date.now() - ts > 60_000
}

const fetchStatus = async () => {
  try {
    await systemStore.fetchStatus()
  } catch (e: any) {
    console.error('获取系统状态失败', e)
  }
}

const toggleAutoRefresh = () => {
  if (autoRefreshModel.value) {
    systemStore.enableAutoRefresh(5000)
  } else {
    systemStore.disableAutoRefresh()
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  fetchStatus()
  autoRefreshModel.value = systemStore.autoRefresh
})

onUnmounted(() => {
  systemStore.disableAutoRefresh()
})
</script>

<style scoped>

/* 密度覆盖:紧凑 12px + 表头底色(公共基线见 styles/tables.less) */
.data-table th,
.data-table td {
  padding: 10px 12px;
  font-size: 12px;
}

.data-table th {
  background: hsl(var(--muted));
}

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

/* 异常横幅 */
.alert-banner {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid transparent;
  margin-bottom: 16px;
}

.alert-banner > svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-degraded {
  background: hsl(var(--warning) / 0.1);
  border-color: hsl(var(--warning) / 0.4);
  color: hsl(var(--warning-fg));
}

.alert-unhealthy {
  background: hsl(var(--error) / 0.1);
  border-color: hsl(var(--error) / 0.4);
  color: hsl(var(--error-fg));
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alert-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* 统计卡片间距(列数/间距走全局 .stats-grid) */
.stats-grid {
  margin-bottom: 16px;
}

/* 基础设施卡片 */
.infra-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 20px;
}

.infra-card {
  background: hsl(var(--muted));
  border-radius: var(--radius);
  padding: 12px;
}

.infra-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.infra-name {
  font-size: 13px;
  font-weight: 500;
  color: hsl(var(--foreground));
  text-transform: capitalize;
}

.infra-error,
.infra-info {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-top: 4px;
}

.infra-error {
  color: hsl(var(--error-fg));
  word-break: break-all;
}

/* 类型 chips(chips 与 card-header 同行,窄屏换行) */
.type-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-chip {
  padding: 4px 10px;
  border-radius: 9999px;
  border: 1px solid hsl(var(--border));
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.type-chip:hover {
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--foreground));
}

.type-chip.active {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
  font-weight: 500;
}

.chip-warn {
  color: hsl(var(--warning-fg));
}

/* 表格 */
.table-wrapper {
  padding: 20px;
  overflow-x: clip;
}

.monospace {
  font-family: monospace;
  font-size: 11px;
}

.detail-text {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.heartbeat-stale {
  color: hsl(var(--warning-fg));
  font-weight: 600;
}

/* 响应式 */
@media (max-width: 1200px) {
  .infra-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .infra-grid {
    grid-template-columns: 1fr;
  }
}
</style>
