<template>
  <div class="backtest-detail-container">
    <!-- Custom -->
    <div class="page-header">
      <div class="header-left">
        <a-button
          type="text"
          @click="goBack"
        >
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h1 class="page-title">
          {{ backtest?.name || '回测详情' }}
        </h1>
        <p class="page-subtitle">
          {{ backtest?.portfolio_name || '-' }}
        </p>
      </div>
      <div class="header-actions">
        <a-space>
          <a-tooltip v-if="!canOperate" title="仅创建者可操作">
            <span style="color: #ccc;">无权限操作</span>
          </a-tooltip>
          <template v-else>
            <!-- 重新运行按钮（已完成/失败/已停止） -->
            <a-button
              v-if="canStart"
              type="primary"
              @click="handleStart"
            >
              <PlayCircleOutlined /> 重新运行
            </a-button>
            <!-- 停止按钮（进行中） -->
            <a-button
              v-if="canStop"
              danger
              @click="handleStop"
            >
              <StopOutlined /> 停止回测
            </a-button>
            <!-- 取消按钮（待调度/排队中） -->
            <a-button
              v-if="canCancel"
              @click="handleCancel"
            >
              <CloseCircleOutlined /> 取消
            </a-button>
            <!-- 删除按钮（非运行中） -->
            <a-button
              v-if="canDelete"
              @click="handleDelete"
            >
              <DeleteOutlined /> 删除
            </a-button>
          </template>
        </a-space>
      </div>
    </div>

    <!-- Custom -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <a-spin size="large" />
    </div>

    <!-- Custom -->
    <div
      v-else-if="backtest"
      class="detail-content"
    >
      <!-- Custom -->
      <div class="info-section">
        <a-row :gutter="16">
          <!-- Custom -->
          <a-col :span="6">
            <a-card class="info-card">
              <div class="status-display">
                <div class="status-label">状态</div>
                <StatusTag v-if="backtest" :status="backtest.status" type="backtest" />
              </div>
            </a-card>
          </a-col>

          <!-- Custom -->
          <a-col :span="18">
            <a-card class="info-card">
              <div class="progress-section">
                <div class="progress-header">
                  <span class="progress-label">回测进度</span>
                  <span class="progress-value">{{ progress.toFixed(1) }}%</span>
                </div>
                <a-progress
                  :percent="progress"
                  :status="getProgressStatus()"
                  :stroke-color="getProgressColor()"
                  size="large"
                />
                <div
                  v-if="currentDate"
                  class="progress-footer"
                >
                  <span class="current-date">当前日期: {{ currentDate }}</span>
                </div>
              </div>
            </a-card>
          </a-col>
        </a-row>
      </div>

      <!-- Custom -->
      <a-row
        :gutter="16"
        style="margin-top: 16px"
      >
        <!-- Custom -->
        <a-col :span="12">
          <a-card title="回测配置">
            <a-descriptions
              bordered
              :column="1"
              size="small"
            >
              <a-descriptions-item label="开始日期">
                {{ backtest.config?.start_date }}
              </a-descriptions-item>
              <a-descriptions-item label="结束日期">
                {{ backtest.config?.end_date }}
              </a-descriptions-item>
              <a-descriptions-item label="Broker 类型">
                {{ backtest.config?.broker_type }}
              </a-descriptions-item>
              <a-descriptions-item label="手续费率">
                {{ (backtest.config?.commission_rate * 100).toFixed(4) }}%
              </a-descriptions-item>
              <a-descriptions-item label="滑点率">
                {{ (backtest.config?.slippage_rate * 100).toFixed(4) }}%
              </a-descriptions-item>
              <a-descriptions-item label="创建时间">
                {{ formatDate(backtest.created_at) }}
              </a-descriptions-item>
              <a-descriptions-item
                v-if="backtest.started_at"
                label="启动时间"
              >
                {{ formatDate(backtest.started_at) }}
              </a-descriptions-item>
              <a-descriptions-item
                v-if="backtest.completed_at"
                label="完成时间"
              >
                {{ formatDate(backtest.completed_at) }}
              </a-descriptions-item>
            </a-descriptions>
          </a-card>
        </a-col>

        <!-- Custom -->
        <a-col :span="12">
          <a-card title="回测结果">
            <div
              v-if="backtest.result"
              class="result-content"
            >
              <div class="result-grid">
                <div class="result-item">
                  <span class="result-label">总收益率</span>
                  <span
                    class="result-value"
                    :class="getChangeClass(backtest.result.total_return)"
                  >
                    {{ (backtest.result.total_return * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="result-item">
                  <span class="result-label">年化收益率</span>
                  <span
                    class="result-value"
                    :class="getChangeClass(backtest.result.annual_return)"
                  >
                    {{ (backtest.result.annual_return * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="result-item">
                  <span class="result-label">夏普比率</span>
                  <span class="result-value">{{ backtest.result.sharpe_ratio.toFixed(2) }}</span>
                </div>
                <div class="result-item">
                  <span class="result-label">最大回撤</span>
                  <span class="result-value value-down">
                    {{ (backtest.result.max_drawdown * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="result-item">
                  <span class="result-label">胜率</span>
                  <span class="result-value">{{ (backtest.result.win_rate * 100).toFixed(2) }}%</span>
                </div>
              </div>
            </div>
            <a-empty
              v-else
              description="回测尚未完成"
              :image="Empty.PRESENTED_IMAGE_SIMPLE"
            />
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-card
        v-if="backtest.error_message"
        style="margin-top: 16px"
        title="错误信息"
      >
        <a-alert
          :message="backtest.error_message"
          type="error"
          show-icon
        />
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message, Modal, Empty } from 'ant-design-vue'
import { storeToRefs } from 'pinia'
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  StopOutlined,
  DeleteOutlined,
  CloseCircleOutlined
} from '@ant-design/icons-vue'
import { useBacktestStore } from '@/stores/backtest'
import StatusTag from '@/components/common/StatusTag.vue'
import { getBacktestStateLabel, getBacktestStateColor } from '@/constants'
import { formatDate } from '@/utils/format'
import type { BacktestTask } from '@/api'

const route = useRoute()
const router = useRouter()
const taskUuid = route.params.uuid as string

// 使用 Store
const backtestStore = useBacktestStore()
const {
  currentTask: backtest,
  detailLoading: loading,
  canOperateTask,
  canStartTask,
  canStopTask,
  canCancelTask,
  canDeleteTask
} = storeToRefs(backtestStore)

const {
  fetchTask,
  startTask,
  stopTask,
  cancelTask,
  deleteTask
} = backtestStore

// 本地状态
const progress = ref(0)
const currentDate = ref('')
const eventSource = ref<EventSource | null>(null)

// 计算属性
const canOperate = computed(() => backtest.value && canOperateTask(backtest.value))
const canStart = computed(() => backtest.value && canStartTask(backtest.value))
const canStop = computed(() => backtest.value && canStopTask(backtest.value))
const canCancel = computed(() => backtest.value && canCancelTask(backtest.value))
const canDelete = computed(() => backtest.value && canDeleteTask(backtest.value))

// 获取进度状态
const getProgressStatus = () => {
  if (backtest.value?.status === 'failed') return 'exception'
  if (backtest.value?.status === 'completed') return 'success'
  return 'active'
}

// 获取进度颜色
const getProgressColor = () => {
  if (backtest.value?.status === 'failed') return '#f5222d'
  if (backtest.value?.status === 'completed') return '#52c41a'
  return '#1890ff'
}

// 获取变化样式
const getChangeClass = (value: number) => {
  if (value > 0) return 'value-up'
  if (value < 0) return 'value-down'
  return 'value-flat'
}

// 加载详情
const loadDetail = async () => {
  loading.value = true
  try {
    const detail = await backtestApi.get(taskUuid)
    backtest.value = detail
    progress.value = detail.progress

    // 如果正在运行，启动 SSE 监听
    if (detail.state === 'RUNNING' || detail.state === 'PENDING') {
      startSSE()
    }
  } catch (error: any) {
    message.error(`加载详情失败: ${error.message || '未知错误'}`)
    router.push('/backtest')
  } finally {
    loading.value = false
  }
}

// 启动 SSE 监听
const startSSE = () => {
  // 关闭之前的连接
  if (eventSource.value) {
    eventSource.value.close()
  }

  // 创建新连接
  eventSource.value = backtestApi.subscribeProgress(
    taskUuid,
    // onProgress
    (data: BacktestProgress) => {
      progress.value = data.progress
      if (data.current_date) {
        currentDate.value = data.current_date
      }
    },
    // onComplete
    async (data: BacktestProgress) => {
      progress.value = data.progress
      // 重新加载详情获取完整数据
      await loadDetail()
      if (eventSource.value) {
        eventSource.value.close()
        eventSource.value = null
      }
    },
    // onError
    (error: string) => {
      console.error('SSE error:', error)
      if (eventSource.value) {
        eventSource.value.close()
        eventSource.value = null
      }
    }
  )
}

// 停止 SSE
const stopSSE = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
}

// 返回
const goBack = () => {
  router.push('/backtest')
}

// 启动回测（重新运行，创建新任务）
const handleStart = async () => {
  if (!backtest.value) return

  Modal.confirm({
    title: '确认重新运行',
    content: `确定要重新运行回测任务"${backtest.value.name}"吗？这将创建一个新的回测任务。`,
    onOk: async () => {
      try {
        const result = await startTask(backtest.value.uuid)
        message.success('启动成功，正在跳转到新任务...')
        // 跳转到新创建的任务详情页
        if (result?.uuid) {
          router.push(`/backtest/${result.uuid}`)
        } else {
          await fetchTask(taskUuid)
        }
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 停止回测
const handleStop = async () => {
  if (!backtest.value) return

  Modal.confirm({
    title: '确认停止',
    content: `确定要停止回测任务"${backtest.value.name}"吗？`,
    onOk: async () => {
      try {
        await stopTask(backtest.value.uuid)
        message.success('已停止')
        stopSSE()
        await fetchTask(taskUuid)
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 取消任务
const handleCancel = async () => {
  if (!backtest.value) return

  Modal.confirm({
    title: '确认取消',
    content: `确定要取消回测任务"${backtest.value.name}"吗？`,
    onOk: async () => {
      try {
        await cancelTask(backtest.value.uuid)
        message.success('已取消')
        stopSSE()
        await fetchTask(taskUuid)
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 删除任务
const handleDelete = async () => {
  if (!backtest.value) return

  Modal.confirm({
    title: '确认删除',
    content: `确定要删除回测任务"${backtest.value.name}"吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      try {
        await deleteTask(backtest.value.uuid)
        message.success('删除成功')
        router.push('/backtest')
      } catch (error: any) {
        message.error(`删除失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 加载详情
const loadDetail = async () => {
  const detail = await fetchTask(taskUuid)
  if (detail) {
    progress.value = detail.progress || 0

    // 如果正在运行，启动 SSE 监听
    if (detail.status === 'running' || detail.status === 'pending') {
      startSSE()
    }
  } else {
    message.error('加载详情失败')
    router.push('/backtest')
  }
}

onMounted(() => {
  loadDetail()
})

onUnmounted(() => {
  stopSSE()
})
</script>

<style scoped>
.backtest-detail-container {
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

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left .page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.header-left .page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.info-section {
  margin-bottom: 16px;
}

.info-card {
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.status-display {
  text-align: center;
  padding: 16px 0;
}

.status-label {
  font-size: 14px;
  color: #8c8c8c;
  margin-bottom: 12px;
}

.progress-section {
  padding: 8px 0;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.progress-label {
  font-size: 14px;
  color: #8c8c8c;
}

.progress-value {
  font-size: 24px;
  font-weight: 600;
  color: #1890ff;
}

.progress-footer {
  margin-top: 12px;
}

.current-date {
  font-size: 12px;
  color: #8c8c8c;
}

.result-content {
  padding: 8px 0;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.result-item {
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  text-align: center;
}

.result-item .result-label {
  display: block;
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 8px;
}

.result-item .result-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
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

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .header-actions {
    width: 100%;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
