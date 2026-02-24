<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">系统状态</div>
      <div class="page-actions">
        <a-switch v-model:checked="autoRefresh" @change="toggleAutoRefresh" />
        <span style="margin-left: 8px">自动刷新</span>
        <a-button style="margin-left: 16px" @click="fetchStatus">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </div>
    </div>

    <!-- 系统概览 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="4">
        <a-card>
          <a-statistic title="服务状态" :value="systemStatus.status === 'running' ? '运行中' : '异常'">
            <template #prefix>
              <CheckCircleOutlined v-if="systemStatus.status === 'running'" style="color: #52c41a" />
              <CloseCircleOutlined v-else style="color: #ff4d4f" />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card>
          <a-statistic title="版本" :value="systemStatus.version" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card>
          <a-statistic title="运行时间" :value="systemStatus.uptime" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card>
          <a-statistic title="调试模式" :value="systemStatus.debug_mode ? '开启' : '关闭'">
            <template #suffix>
              <a-tag :color="systemStatus.debug_mode ? 'orange' : 'green'">
                {{ systemStatus.debug_mode ? 'DEBUG' : 'PROD' }}
              </a-tag>
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card>
          <a-statistic title="在线组件" :value="componentCounts.total" suffix="个" />
        </a-card>
      </a-col>
      <a-col :span="4">
        <a-card>
          <a-statistic title="最后更新" :value="lastUpdate" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 基础设施状态 -->
    <a-card title="基础设施" style="margin-bottom: 16px">
      <a-row :gutter="16">
        <a-col :span="6" v-for="(info, name) in infrastructure" :key="name">
          <a-card size="small">
            <template #title>
              <span style="text-transform: capitalize">{{ getInfraName(name) }}</span>
            </template>
            <a-tag :color="getInfraColor(info.status)">
              {{ getInfraStatusText(info.status) }}
            </a-tag>
            <div v-if="info.error" style="margin-top: 8px; font-size: 12px; color: #999">
              {{ info.error }}
            </div>
            <div v-if="info.latency_ms !== undefined" style="margin-top: 8px; font-size: 12px">
              延迟: {{ info.latency_ms }}ms
            </div>
            <div v-if="info.topics !== undefined" style="margin-top: 8px; font-size: 12px">
              Topics: {{ info.topics }}
            </div>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- 组件统计 -->
    <a-card title="组件统计" style="margin-bottom: 16px">
      <a-row :gutter="16">
        <a-col :span="4" v-for="(count, type) in componentTypeMap" :key="type">
          <a-card size="small" :bordered="false" class="component-stat-card">
            <a-statistic :title="count.label" :value="getComponentCount(type)" :value-style="{ color: count.color }">
              <template #suffix>
                <span style="font-size: 12px; color: #999">/ {{ count.total }} 在线</span>
              </template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- Worker 状态 -->
    <a-card title="组件详情" :loading="workerLoading">
      <a-table
        :columns="workerColumns"
        :dataSource="workers"
        :rowKey="(record: WorkerInfo) => `${record.type}-${record.id}`"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="getStatusColor(record.status)">
              {{ getStatusText(record.status) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'type'">
            <a-tag :color="getTypeColor(record.type)">
              {{ getTypeText(record.type) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'details'">
            <span class="detail-text">
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
            </span>
          </template>
        </template>
      </a-table>
      <a-empty v-if="workers.length === 0" description="暂无组件" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons-vue'
import { useSystemStore } from '@/stores'
import type { WorkerInfo } from '@/api'

// ========== Store ==========
const systemStore = useSystemStore()

// ========== 计算属性（从 Store 获取） ==========
const autoRefresh = computed({
  get: () => systemStore.autoRefresh,
  set: () => systemStore.toggleAutoRefresh()
})

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

const workerColumns = [
  { title: '组件 ID', dataIndex: 'id', width: 180 },
  { title: '类型', key: 'type', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '详情', key: 'details', width: 180 },
  { title: '最后心跳', dataIndex: 'last_heartbeat', width: 180 },
]

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

const getInfraColor = (status: string): string => {
  const colors: Record<string, string> = {
    ok: 'green',
    connected: 'green',
    error: 'red',
    not_configured: 'default',
  }
  return colors[status] || 'default'
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

const getStatusColor = (status: string): string => {
  const colors: Record<string, string> = {
    running: 'green',
    active: 'green',
    stopped: 'default',
    stale: 'orange',
    error: 'red',
  }
  return colors[status?.toLowerCase()] || 'default'
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

const getTypeColor = (type: string): string => {
  const colors: Record<string, string> = {
    data_worker: 'purple',
    backtest_worker: 'blue',
    execution_node: 'green',
    scheduler: 'orange',
    task_timer: 'magenta',
  }
  return colors[type] || 'default'
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
    message.error('获取系统状态失败')
    console.error(e)
  }
}

const toggleAutoRefresh = (checked: boolean) => {
  if (checked) {
    systemStore.enableAutoRefresh(5000)
  } else {
    systemStore.disableAutoRefresh()
  }
}

// ========== 生命周期 ==========
onMounted(() => {
  fetchStatus()
})

onUnmounted(() => {
  systemStore.disableAutoRefresh()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.component-stat-card {
  background: #fafafa;
}

.component-stat-card :deep(.ant-statistic-title) {
  font-size: 12px;
}

.detail-text {
  font-size: 12px;
  color: #666;
}
</style>
