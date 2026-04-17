<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">系统状态</h1>
      <div class="page-actions">
        <label class="switch-label">
          <input type="checkbox" v-model="autoRefreshModel" @change="toggleAutoRefresh" class="switch-input" />
          <span class="switch-slider"></span>
          <span class="switch-text">自动刷新</span>
        </label>
        <button class="btn-secondary" @click="fetchStatus">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
            <path d="M16 21h5v-5"></path>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- 系统概览 -->
    <div class="stats-grid-six">
      <div class="stat-card">
        <div class="stat-header">
          <div class="stat-label">服务状态</div>
          <div v-if="systemStatus.status === 'running'" class="stat-icon stat-success">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
              <polyline points="22 4 12 14.01 9 11.01"></polyline>
            </svg>
          </div>
          <div v-else class="stat-icon stat-error">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="15" y1="9" x2="9" y2="15"></line>
              <line x1="9" y1="9" x2="15" y2="15"></line>
            </svg>
          </div>
        </div>
        <div class="stat-value">{{ systemStatus.status === 'running' ? '运行中' : '异常' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">版本</div>
        <div class="stat-value">{{ systemStatus.version }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">运行时间</div>
        <div class="stat-value">{{ systemStatus.uptime }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">调试模式</div>
        <div class="stat-value-with-tag">
          {{ systemStatus.debug_mode ? '开启' : '关闭' }}
          <span class="tag" :class="systemStatus.debug_mode ? 'tag-orange' : 'tag-green'">
            {{ systemStatus.debug_mode ? 'DEBUG' : 'PROD' }}
          </span>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">在线组件</div>
        <div class="stat-value">{{ componentCounts.total }} <span class="stat-unit">个</span></div>
      </div>
      <div class="stat-card">
        <div class="stat-label">最后更新</div>
        <div class="stat-value stat-small">{{ lastUpdate }}</div>
      </div>
    </div>

    <!-- 基础设施状态 -->
    <div class="card">
      <div class="card-header">
        <h3>基础设施</h3>
      </div>
      <div class="infra-grid">
        <div v-for="(info, name) in infrastructure" :key="name" class="infra-card">
          <div class="infra-header">
            <span class="infra-name">{{ getInfraName(name) }}</span>
            <span class="tag" :class="`tag-${getInfraColorClass(info.status)}`">
              {{ getInfraStatusText(info.status) }}
            </span>
          </div>
          <div v-if="info.error" class="infra-error">{{ info.error }}</div>
          <div v-if="info.latency_ms !== undefined" class="infra-info">
            延迟: {{ info.latency_ms }}ms
          </div>
          <div v-if="info.topics !== undefined" class="infra-info">
            Topics: {{ info.topics }}
          </div>
        </div>
      </div>
    </div>

    <!-- 组件统计 -->
    <div class="card">
      <div class="card-header">
        <h3>组件统计</h3>
      </div>
      <div class="component-stats">
        <div v-for="(count, type) in componentTypeMap" :key="type" class="component-stat-card">
          <div class="component-stat-label">{{ count.label }}</div>
          <div class="component-stat-value" :style="{ color: count.color }">
            {{ getComponentCount(type) }}
          </div>
          <div class="component-stat-total">/ {{ count.total }} 在线</div>
        </div>
      </div>
    </div>

    <!-- Worker 状态 -->
    <div class="card">
      <div class="card-header">
        <h3>组件详情</h3>
      </div>
      <div v-if="workerLoading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else-if="workers.length > 0" class="table-wrapper">
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
            <tr v-for="record in workers" :key="`${record.type}-${record.id}`">
              <td class="monospace">{{ record.id }}</td>
              <td>
                <span class="tag" :class="`tag-${getTypeColorClass(record.type)}`">
                  {{ getTypeText(record.type) }}
                </span>
              </td>
              <td>
                <span class="tag" :class="`tag-${getStatusColorClass(record.status)}`">
                  {{ getStatusText(record.status) }}
                </span>
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
              <td class="monospace">{{ record.last_heartbeat }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">
        <p>暂无组件</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores'
import type { WorkerInfo } from '@/api'

// ========== Store ==========
const systemStore = useSystemStore()

// ========== 计算属性（从 Store 获取） ==========
const autoRefreshModel = ref(systemStore.autoRefresh)

const workerLoading = computed(() => systemStore.loading)
const lastUpdate = computed(() => {
  if (!systemStore.lastUpdate) return '-'
  return new Date(systemStore.lastUpdate).toLocaleTimeString()
})

const systemStatus = computed(() => ({
  status: systemStore.systemStatus?.status || 'unknown',
  version: systemStore.version,
  uptime: systemStore.uptime,
  debug_mode: systemStore.debugMode,
}))

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

const componentCounts = computed(() => {
  const counts = systemStore.componentCounts
  const total = Object.values(counts).reduce((sum, count) => sum + (count as number), 0)
  return { ...counts, total }
})

// 组件类型映射
const componentTypeMap: Record<string, { label: string; color: string; total: number }> = {
  data_workers: { label: 'DataWorker', color: '#722ed1', total: 0 },
  backtest_workers: { label: 'BacktestWorker', color: '#1890ff', total: 0 },
  execution_nodes: { label: 'ExecutionNode', color: '#52c41a', total: 0 },
  schedulers: { label: 'Scheduler', color: '#fa8c16', total: 0 },
  task_timers: { label: 'TaskTimer', color: '#eb2f96', total: 0 },
}

// ========== 方法 ==========
const getComponentCount = (type: string): number => {
  return componentCounts.value[type] || 0
}

const getInfraName = (name: string): string => {
  const names: Record<string, string> = {
    mysql: 'MySQL',
    redis: 'Redis',
    kafka: 'Kafka',
    clickhouse: 'ClickHouse',
  }
  return names[name] || name
}

const getInfraColorClass = (status: string): string => {
  const colors: Record<string, string> = {
    ok: 'green',
    connected: 'green',
    error: 'red',
    not_configured: 'gray',
  }
  return colors[status] || 'gray'
}

const getInfraStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    ok: '已连接',
    connected: '已连接',
    error: '错误',
    not_configured: '未配置',
  }
  return texts[status] || status
}

const getStatusColorClass = (status: string): string => {
  const colors: Record<string, string> = {
    running: 'green',
    active: 'green',
    stopped: 'gray',
    stale: 'orange',
    error: 'red',
  }
  return colors[status?.toLowerCase()] || 'gray'
}

const getStatusText = (status: string): string => {
  const texts: Record<string, string> = {
    running: '运行中',
    active: '活跃',
    stopped: '已停止',
    stale: '过期',
    error: '错误',
  }
  return texts[status?.toLowerCase()] || status
}

const getTypeColorClass = (type: string): string => {
  const colors: Record<string, string> = {
    data_worker: 'purple',
    backtest_worker: 'blue',
    execution_node: 'green',
    scheduler: 'orange',
    task_timer: 'magenta',
  }
  return colors[type] || 'gray'
}

const getTypeText = (type: string): string => {
  const texts: Record<string, string> = {
    data_worker: '数据Worker',
    backtest_worker: '回测Worker',
    execution_node: '执行节点',
    scheduler: '调度器',
    task_timer: '定时器',
  }
  return texts[type] || type
}

const fetchStatus = async () => {
  try {
    await systemStore.fetchStatus()
  } catch (e: any) {
    console.error('获取系统状态失败', e)
  }
}

const toggleAutoRefresh = (checked: boolean) => {
  autoRefreshModel.value = checked
  if (checked) {
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
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.page-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
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
  background: #3a3a4e;
  border-radius: 20px;
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
  background: #ffffff;
  border-radius: 50%;
  transition: transform 0.3s;
}

.switch-input:checked {
  background: #1890ff;
}

.switch-input:checked::after {
  transform: translateX(20px);
}

.switch-text {
  font-size: 14px;
  color: #8a8a9a;
}

/* 按钮 */

/* 统计卡片 - 6列 */
.stats-grid-six {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.stat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.stat-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-error {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.stat-value-with-tag {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.stat-small {
  font-size: 14px;
}

.stat-unit {
  font-size: 12px;
  color: #8a8a9a;
  font-weight: normal;
}

/* 卡片 */

/* 基础设施卡片 */
.infra-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  padding: 20px;
}

.infra-card {
  background: #2a2a3e;
  border-radius: 6px;
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
  color: #ffffff;
  text-transform: capitalize;
}

.infra-error,
.infra-info {
  font-size: 12px;
  color: #8a8a9a;
  margin-top: 4px;
}

.infra-error {
  color: #f5222d;
}

/* 组件统计 */
.component-stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  padding: 20px;
}

.component-stat-card {
  background: #2a2a3e;
  border-radius: 6px;
  padding: 12px;
  text-align: center;
}

.component-stat-label {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.component-stat-value {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.component-stat-total {
  font-size: 11px;
  color: #8a8a9a;
}

/* 标签 */

.tag-magenta {
  background: rgba(235, 47, 150, 0.2);
  color: #eb2f96;
}

/* 表格 */
.table-wrapper {
  padding: 20px;
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 12px;
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 12px;
}

.monospace {
  font-family: monospace;
  font-size: 11px;
}

.detail-text {
  font-size: 12px;
  color: #8a8a9a;
}

/* 空状态 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid-six {
    grid-template-columns: repeat(3, 1fr);
  }

  .infra-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid-six {
    grid-template-columns: repeat(2, 1fr);
  }

  .infra-grid {
    grid-template-columns: 1fr;
  }

  .component-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
