<template>
  <PageLayout>
    <template #title>
      Worker 管理
    </template>
    <template #actions>
      <label class="switch-label">
        <input type="checkbox" v-model="autoRefreshModel" @change="toggleAutoRefresh" class="switch-input" />
        <span class="switch-slider"></span>
        <span class="switch-text">自动刷新</span>
      </label>
      <button class="btn-secondary" @click="refreshData">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
          <path d="M3 3v5h5"></path>
          <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
          <path d="M16 21h5v-5"></path>
        </svg>
        刷新
      </button>
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">总 Worker</div>
        <div class="stat-value">{{ workers.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">运行中</div>
        <div class="stat-value stat-success">{{ runningCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已停止</div>
        <div class="stat-value stat-muted">{{ stoppedCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">异常</div>
        <div class="stat-value stat-danger">{{ errorCount }}</div>
      </div>
    </div>

    <!-- Worker 列表 -->
    <div class="card">
      <div class="card-header">
        <h3>Worker 列表</h3>
        <select v-model="typeFilter" class="filter-select">
          <option value="">全部类型</option>
          <option value="data_worker">数据 Worker</option>
          <option value="backtest_worker">回测 Worker</option>
          <option value="execution_node">执行节点</option>
          <option value="scheduler">调度器</option>
          <option value="task_timer">定时器</option>
        </select>
      </div>
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else-if="filteredWorkers.length > 0" class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Worker ID</th>
              <th>类型</th>
              <th>状态</th>
              <th>详情</th>
              <th>最后心跳</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredWorkers" :key="`${record.type}-${record.id}`">
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
              <td class="monospace">{{ record.last_heartbeat || '-' }}</td>
              <td>
                <div class="action-buttons">
                  <button
                    v-if="record.status !== 'running'"
                    class="btn-icon btn-start"
                    @click="handleStart(record)"
                    title="启动"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                  </button>
                  <button
                    v-if="record.status === 'running'"
                    class="btn-icon btn-stop"
                    @click="handleStop(record)"
                    title="停止"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                      <rect x="6" y="4" width="4" height="16"></rect>
                      <rect x="14" y="4" width="4" height="16"></rect>
                    </svg>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else description="暂无 Worker" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { useSystemStore } from '@/stores'
import type { WorkerInfo } from '@/api'
import { message as toast } from '@/utils/toast'

const systemStore = useSystemStore()
const autoRefreshModel = ref(false)
const typeFilter = ref('')

const loading = computed(() => systemStore.loading)
const workers = computed(() => systemStore.workers)

const filteredWorkers = computed(() => {
  if (!typeFilter.value) return workers.value
  return workers.value.filter(w => w.type === typeFilter.value)
})

const runningCount = computed(() => workers.value.filter(w => w.status === 'running' || w.status === 'active').length)
const stoppedCount = computed(() => workers.value.filter(w => w.status === 'stopped' || w.status === 'idle').length)
const errorCount = computed(() => workers.value.filter(w => w.status === 'error' || w.status === 'stale').length)

const getTypeColorClass = (type: string) => {
  const colors: Record<string, string> = { data_worker: 'purple', backtest_worker: 'blue', execution_node: 'green', scheduler: 'orange', task_timer: 'magenta' }
  return colors[type] || 'gray'
}

const getTypeText = (type: string) => {
  const texts: Record<string, string> = { data_worker: '数据Worker', backtest_worker: '回测Worker', execution_node: '执行节点', scheduler: '调度器', task_timer: '定时器' }
  return texts[type] || type
}

const getStatusColorClass = (status: string) => {
  const colors: Record<string, string> = { running: 'green', active: 'green', stopped: 'gray', idle: 'gray', stale: 'orange', error: 'red' }
  return colors[status?.toLowerCase()] || 'gray'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = { running: '运行中', active: '活跃', stopped: '已停止', idle: '空闲', stale: '过期', error: '错误' }
  return texts[status?.toLowerCase()] || status
}

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

const handleStart = async (worker: WorkerInfo) => {
  try {
    await systemStore.startWorker(worker.id)
    toast.success(`Worker ${worker.id} 已启动`)
    await refreshData()
  } catch (e: any) {
    toast.error(e.message || '启动失败')
  }
}

const handleStop = async (worker: WorkerInfo) => {
  if (!confirm(`确定要停止 Worker "${worker.id}" 吗？`)) return
  try {
    await systemStore.stopWorker(worker.id)
    toast.success(`Worker ${worker.id} 已停止`)
    await refreshData()
  } catch (e: any) {
    toast.error(e.message || '停止失败')
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

/* 统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

/* stat-* 字色由全局 cards.less 统一收口(*-fg token) */

/* 卡片 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.card-header h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.filter-select {
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: 4px;
  padding: 6px 12px;
  color: hsl(var(--foreground));
  font-size: 13px;
}

/* 标签 */

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
  border-bottom: 1px solid hsl(var(--border));
}

.data-table th {
  background: hsl(var(--border));
  color: hsl(var(--foreground));
  font-weight: 500;
  font-size: 12px;
  white-space: nowrap;
}

.data-table td {
  color: hsl(var(--foreground));
  font-size: 12px;
}

.monospace {
  font-family: monospace;
  font-size: 11px;
}

.detail-text {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 8px;
}

.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-start {
  background: hsl(var(--success) / 0.2);
  color: hsl(var(--success));
}

.btn-start:hover {
  background: hsl(var(--success) / 0.3);
}

.btn-stop {
  background: hsl(var(--error) / 0.2);
  color: hsl(var(--error));
}

.btn-stop:hover {
  background: hsl(var(--error) / 0.3);
}

/* 响应式 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
