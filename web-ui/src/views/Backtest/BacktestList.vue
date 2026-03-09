<template>
  <div class="backtest-list-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          回测任务
        </h1>
        <p class="page-subtitle">
          管理和监控您的所有回测任务
        </p>
      </div>
      <div class="header-actions">
        <a-radio-group
          v-model:value="filterStatus"
          button-style="solid"
          size="large"
          @change="handleFilterChange"
        >
          <a-radio-button value="">
            全部
          </a-radio-button>
          <a-radio-button value="pending">
            排队中
          </a-radio-button>
          <a-radio-button value="running">
            进行中
          </a-radio-button>
          <a-radio-button value="completed">
            已完成
          </a-radio-button>
        </a-radio-group>
        <a-button
          size="large"
          :loading="refreshing"
          @click="handleRefresh"
        >
          <ReloadOutlined />
        </a-button>
        <a-button
          type="primary"
          size="large"
          @click="goToCreate"
        >
          <PlusOutlined /> 创建回测
        </a-button>
      </div>
    </div>

    <!-- 批量操作栏 -->
    <div v-if="selectedIds.size > 0" class="batch-action-bar">
      <div class="batch-info">
        已选择 <strong>{{ selectedIds.size }}</strong> 项
      </div>
      <a-space>
        <a-button
          :disabled="!canBatchStart"
          :loading="batchOperationLoading"
          @click="handleBatchStart"
        >
          <PlayCircleOutlined /> 批量启动
        </a-button>
        <a-button
          :disabled="!canBatchStop"
          :loading="batchOperationLoading"
          @click="handleBatchStop"
        >
          <StopOutlined /> 批量停止
        </a-button>
        <a-button
          :disabled="!canBatchCancel"
          :loading="batchOperationLoading"
          @click="handleBatchCancel"
        >
          <CloseCircleOutlined /> 批量取消
        </a-button>
        <a-button @click="handleClearSelection">
          取消选择
        </a-button>
      </a-space>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <a-card class="stat-card stat-card-blue">
        <a-statistic
          title="总任务数"
          :value="stats.total"
          :value-style="{ color: '#1890ff', fontSize: '32px' }"
        >
          <template #prefix>
            <FileTextOutlined />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-green">
        <a-statistic
          title="已完成"
          :value="stats.completed"
          :value-style="{ color: '#52c41a', fontSize: '32px' }"
        >
          <template #prefix>
            <CheckCircleOutlined />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-orange">
        <a-statistic
          title="运行中"
          :value="stats.running"
          :value-style="{ color: '#fa8c16', fontSize: '32px' }"
        >
          <template #prefix>
            <SyncOutlined :spin="true" />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-red">
        <a-statistic
          title="失败"
          :value="stats.failed"
          :value-style="{ color: '#f5222d', fontSize: '32px' }"
        >
          <template #prefix>
            <CloseCircleOutlined />
          </template>
        </a-statistic>
      </a-card>
    </div>

    <!-- 回测任务列表 -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <a-spin size="large" />
    </div>
    <div
      v-else-if="tasks.length === 0"
      class="empty-container"
    >
      <a-empty description="暂无回测任务">
        <a-button
          type="primary"
          @click="goToCreate"
        >
          创建第一个回测任务
        </a-button>
      </a-empty>
    </div>
    <a-table
      v-else
      :columns="columns"
      :data-source="tasks"
      :pagination="{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }"
      :row-selection="{
        selectedRowKeys: Array.from(selectedIds),
        onChange: handleSelectionChange,
        getCheckboxProps: (record) => ({ disabled: !canOperateTask(record) })
      }"
      row-key="uuid"
      class="backtest-table"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <div class="name-cell">
            <span class="task-name">{{ record.name }}</span>
            <br>
            <span class="portfolio-name">{{ record.portfolio_name }}</span>
          </div>
        </template>
        <template v-if="column.key === 'status'">
          <StatusTag :status="record.status" type="backtest" />
        </template>
        <template v-if="column.key === 'progress'">
          <div class="progress-cell">
            <a-progress
              :percent="record.progress"
              :status="record.status === 'failed' ? 'exception' : record.status === 'completed' ? 'success' : 'active'"
              size="small"
            />
          </div>
        </template>
        <template v-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
        <template v-if="column.key === 'duration'">
          {{ formatDuration(record.started_at, record.completed_at) }}
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <a @click="viewDetail(record)">查看详情</a>
            <a-tooltip v-if="!canOperateTask(record)" title="仅创建者可操作">
              <span style="color: #ccc;">无权限</span>
            </a-tooltip>
            <template v-else>
              <a
                v-if="canStartTask(record)"
                @click="handleStart(record)"
              >启动</a>
              <a
                v-if="canStopTask(record)"
                @click="handleStop(record)"
              >停止</a>
              <a
                v-if="canCancelTask(record)"
                @click="handleCancel(record)"
              >取消</a>
              <a
                v-if="canDeleteTask(record)"
                @click="handleDelete(record)"
              >删除</a>
            </template>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 结果弹窗 -->
    <a-modal
      v-model:open="showResultModal"
      title="回测结果"
      width="800px"
      :footer="null"
    >
      <div
        v-if="selectedBacktest"
        class="result-content"
      >
        <a-descriptions
          bordered
          :column="2"
        >
          <a-descriptions-item label="任务名称">
            {{ selectedBacktest.name }}
          </a-descriptions-item>
          <a-descriptions-item label="投资组合">
            {{ selectedBacktest.portfolio_name }}
          </a-descriptions-item>
          <a-descriptions-item label="开始日期">
            {{ selectedBacktest.config?.start_date }}
          </a-descriptions-item>
          <a-descriptions-item label="结束日期">
            {{ selectedBacktest.config?.end_date }}
          </a-descriptions-item>
        </a-descriptions>

        <div
          v-if="selectedBacktest.result"
          class="result-stats"
        >
          <div class="result-stat">
            <span class="stat-label">总收益率</span>
            <span
              class="stat-value"
              :class="getChangeClass(selectedBacktest.result.total_return)"
            >
              {{ (selectedBacktest.result.total_return * 100).toFixed(2) }}%
            </span>
          </div>
          <div class="result-stat">
            <span class="stat-label">年化收益率</span>
            <span
              class="stat-value"
              :class="getChangeClass(selectedBacktest.result.annual_return)"
            >
              {{ (selectedBacktest.result.annual_return * 100).toFixed(2) }}%
            </span>
          </div>
          <div class="result-stat">
            <span class="stat-label">夏普比率</span>
            <span class="stat-value">{{ selectedBacktest.result.sharpe_ratio.toFixed(2) }}</span>
          </div>
          <div class="result-stat">
            <span class="stat-label">最大回撤</span>
            <span class="stat-value value-down">
              {{ (selectedBacktest.result.max_drawdown * 100).toFixed(2) }}%
            </span>
          </div>
          <div class="result-stat">
            <span class="stat-label">胜率</span>
            <span class="stat-value">{{ (selectedBacktest.result.win_rate * 100).toFixed(2) }}%</span>
          </div>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  PlusOutlined,
  ReloadOutlined,
  PlayCircleOutlined,
  StopOutlined,
  CloseCircleOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  SyncOutlined
} from '@ant-design/icons-vue'
import { useBacktestStore } from '@/stores/backtest'
import { storeToRefs } from 'pinia'
import StatusTag from '@/components/common/StatusTag.vue'
import { formatDate } from '@/utils/format'
import type { BacktestTask } from '@/api'

const router = useRouter()

// 使用 Store
const backtestStore = useBacktestStore()
const {
  loading,
  tasks,
  batchOperationLoading,
  wsConnected,
  pollingMode
} = storeToRefs(backtestStore)

// Store 方法
const {
  fetchList,
  startTask,
  stopTask,
  cancelTask,
  deleteTask,
  batchStart,
  batchStop,
  batchCancel,
  onWebSocketConnected,
  onWebSocketDisconnected,
  canOperateTask,
  canStartTask,
  canStopTask,
  canCancelTask,
  canDeleteTask
} = backtestStore

// 本地状态
const filterStatus = ref<string>('')
const refreshing = ref(false)
const selectedIds = ref<Set<string>>(new Set())
const showResultModal = ref(false)
const selectedBacktest = ref<any>(null)

// 表格列
const columns = [
  { title: '任务名称', key: 'name', width: 250 },
  { title: '状态', key: 'status', width: 120 },
  { title: '进度', key: 'progress', width: 150 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '运行时长', key: 'duration', width: 120 },
  { title: '操作', key: 'actions', width: 200, fixed: 'right' }
]

// 批量操作权限判断
const canBatchStart = computed(() => {
  return Array.from(selectedIds.value)
    .map(uuid => tasks.value.find(t => t.uuid === uuid))
    .filter(Boolean)
    .some(task => canStartTask(task!))
})

const canBatchStop = computed(() => {
  return Array.from(selectedIds.value)
    .map(uuid => tasks.value.find(t => t.uuid === uuid))
    .filter(Boolean)
    .some(task => canStopTask(task!))
})

const canBatchCancel = computed(() => {
  return Array.from(selectedIds.value)
    .map(uuid => tasks.value.find(t => t.uuid === uuid))
    .filter(Boolean)
    .some(task => canCancelTask(task!))
})

// 筛选变化
const handleFilterChange = () => {
  fetchTasks()
}

// 获取任务列表
const fetchTasks = async () => {
  await fetchList({ status: filterStatus.value || undefined })
}

// 格式化时长
const formatDuration = (startAt?: string, endAt?: string) => {
  if (!startAt) return '-'

  const start = dayjs(startAt)
  const end = endAt ? dayjs(endAt) : dayjs()
  const duration = end.diff(start, 'second')

  if (duration < 60) return `${duration}秒`
  if (duration < 3600) return `${Math.floor(duration / 60)}分钟`
  return `${Math.floor(duration / 3600)}小时${Math.floor((duration % 3600) / 60)}分钟`
}

// 获取变化样式
const getChangeClass = (value: number) => {
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return 'value-flat'
}

// 刷新列表
const handleRefresh = async () => {
  refreshing.value = true
  await fetchTasks()
  refreshing.value = false
}

// 选择变化处理
const handleSelectionChange = (selectedKeys: string[]) => {
  selectedIds.value = new Set(selectedKeys)
}

// 清除选择
const handleClearSelection = () => {
  selectedIds.value.clear()
}

// 批量启动
const handleBatchStart = async () => {
  const uuids = Array.from(selectedIds.value).filter(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canStartTask(task)
  })

  if (uuids.length === 0) {
    message.warning('没有可启动的任务')
    return
  }

  Modal.confirm({
    title: '确认批量启动',
    content: `确定要启动 ${uuids.length} 个回测任务吗？`,
    onOk: async () => {
      try {
        const result = await batchStart(uuids)
        message.success(`批量启动完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
        handleClearSelection()
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 批量停止
const handleBatchStop = async () => {
  const uuids = Array.from(selectedIds.value).filter(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canStopTask(task)
  })

  if (uuids.length === 0) {
    message.warning('没有可停止的任务')
    return
  }

  Modal.confirm({
    title: '确认批量停止',
    content: `确定要停止 ${uuids.length} 个回测任务吗？`,
    onOk: async () => {
      try {
        const result = await batchStop(uuids)
        message.success(`批量停止完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
        handleClearSelection()
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 批量取消
const handleBatchCancel = async () => {
  const uuids = Array.from(selectedIds.value).filter(uuid => {
    const task = tasks.value.find(t => t.uuid === uuid)
    return task && canCancelTask(task)
  })

  if (uuids.length === 0) {
    message.warning('没有可取消的任务')
    return
  }

  Modal.confirm({
    title: '确认批量取消',
    content: `确定要取消 ${uuids.length} 个回测任务吗？`,
    onOk: async () => {
      try {
        const result = await batchCancel(uuids)
        message.success(`批量取消完成：成功 ${result.success} 个，失败 ${result.failed} 个`)
        handleClearSelection()
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 跳转创建页面
const goToCreate = () => {
  router.push('/backtest/create')
}

// 查看详情
const viewDetail = (task: BacktestTask) => {
  router.push(`/backtest/${task.uuid}`)
}

// 启动任务
const handleStart = (task: BacktestTask) => {
  Modal.confirm({
    title: '确认启动',
    content: `确定要启动回测任务"${task.name}"吗？`,
    onOk: async () => {
      try {
        await startTask(task.uuid)
        message.success('启动成功')
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 停止任务
const handleStop = (task: BacktestTask) => {
  Modal.confirm({
    title: '确认停止',
    content: `确定要停止回测任务"${task.name}"吗？`,
    onOk: async () => {
      try {
        await stopTask(task.uuid)
        message.success('已停止')
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 取消任务
const handleCancel = (task: BacktestTask) => {
  Modal.confirm({
    title: '确认取消',
    content: `确定要取消回测任务"${task.name}"吗？`,
    onOk: async () => {
      try {
        await cancelTask(task.uuid)
        message.success('已取消')
        await fetchTasks()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 删除任务
const handleDelete = (task: BacktestTask) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除回测任务"${task.name}"吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      try {
        await deleteTask(task.uuid)
        message.success('删除成功')
        await fetchTasks()
      } catch (error: any) {
        message.error(`删除失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 生命周期
onMounted(() => {
  fetchTasks()
  // TODO: 在这里可以初始化 WebSocket 连接
  // onWebSocketConnected()
})

onUnmounted(() => {
  // 清理资源
  // onWebSocketDisconnected()
})
</script>

<style scoped>
.backtest-list-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left .page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.header-left .page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 16px;
  align-items: center;
}

.batch-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  margin-bottom: 16px;
}

.batch-info {
  font-size: 14px;
  color: #1a1a1a;
}

.batch-info strong {
  color: #1890ff;
  font-size: 16px;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.stat-card :deep(.ant-statistic-title) {
  font-size: 14px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.stat-card :deep(.ant-statistic-content) {
  font-size: 32px;
  font-weight: 600;
}

.loading-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.backtest-table {
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.name-cell .task-name {
  font-weight: 600;
  color: #1a1a1a;
}

.name-cell .portfolio-name {
  font-size: 12px;
  color: #8c8c8c;
}

.progress-cell {
  min-width: 120px;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

.value-flat {
  color: #8c8c8c;
}

.result-content {
  padding: 16px 0;
}

.result-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-top: 24px;
}

.result-stat {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  text-align: center;
}

.result-stat .stat-label {
  display: block;
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.result-stat .stat-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

/* 响应式 */
@media (max-width: 1400px) {
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }

  .result-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
    flex-direction: column;
  }

  .header-actions .ant-radio-group {
    width: 100%;
    justify-content: center;
  }

  .stats-row {
    grid-template-columns: 1fr;
  }

  .result-stats {
    grid-template-columns: 1fr;
  }
}
</style>
