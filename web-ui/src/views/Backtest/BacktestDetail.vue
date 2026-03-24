<template>
  <div class="backtest-detail-container">
    <div class="page-header">
      <div class="header-left">
        <button class="btn-text" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
          返回
        </button>
        <h1 class="page-title">{{ backtest?.name || '回测详情' }}</h1>
        <p class="page-subtitle">{{ backtest?.portfolio_name || '-' }}</p>
      </div>
      <div class="header-actions">
        <div v-if="!canOperate" class="permission-hint">无权限操作</div>
        <template v-else>
          <button v-if="canStart" class="btn-primary" @click="handleStart">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polygon points="10 8 16 12 10 16"/>
            </svg>
            重新运行
          </button>
          <button v-if="canStop" class="btn-danger" @click="handleStop">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
            停止回测
          </button>
          <button v-if="canCancel" class="btn-secondary" @click="handleCancel">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            取消
          </button>
          <button v-if="canDelete" class="btn-secondary" @click="handleDelete">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            删除
          </button>
        </template>
      </div>
    </div>

    <div v-if="loading" class="loading-container">
      <div class="spinner"></div>
    </div>

    <div v-else-if="backtest" class="detail-content">
      <div class="info-section">
        <div class="info-grid">
          <div class="info-card">
            <div class="status-display">
              <div class="status-label">状态</div>
              <StatusTag v-if="backtest" :status="backtest.status" type="backtest" />
            </div>
          </div>

          <div class="info-card">
            <div class="progress-section">
              <div class="progress-header">
                <span class="progress-label">回测进度</span>
                <span class="progress-value">{{ progress.toFixed(1) }}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" :class="getProgressStatus()" :style="{ width: progress + '%', backgroundColor: getProgressColor() }"></div>
              </div>
              <div v-if="currentDate" class="progress-footer">
                <span class="current-date">当前日期: {{ currentDate }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="config-grid">
        <div class="card">
          <div class="card-header">
            <h4>回测配置</h4>
          </div>
          <div class="card-body">
            <div class="descriptions">
              <div class="description-item">
                <span class="description-label">开始日期</span>
                <span class="description-value">{{ backtest.config?.start_date }}</span>
              </div>
              <div class="description-item">
                <span class="description-label">结束日期</span>
                <span class="description-value">{{ backtest.config?.end_date }}</span>
              </div>
              <div class="description-item">
                <span class="description-label">Broker 类型</span>
                <span class="description-value">{{ backtest.config?.broker_type }}</span>
              </div>
              <div class="description-item">
                <span class="description-label">手续费率</span>
                <span class="description-value">{{ (backtest.config?.commission_rate * 100).toFixed(4) }}%</span>
              </div>
              <div class="description-item">
                <span class="description-label">滑点率</span>
                <span class="description-value">{{ (backtest.config?.slippage_rate * 100).toFixed(4) }}%</span>
              </div>
              <div class="description-item">
                <span class="description-label">创建时间</span>
                <span class="description-value">{{ formatDate(backtest.created_at) }}</span>
              </div>
              <div v-if="backtest.started_at" class="description-item">
                <span class="description-label">启动时间</span>
                <span class="description-value">{{ formatDate(backtest.started_at) }}</span>
              </div>
              <div v-if="backtest.completed_at" class="description-item">
                <span class="description-label">完成时间</span>
                <span class="description-value">{{ formatDate(backtest.completed_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <h4>回测结果</h4>
          </div>
          <div class="card-body">
            <div v-if="backtest.result" class="result-content">
              <div class="result-grid">
                <div class="result-item">
                  <span class="result-label">总收益率</span>
                  <span class="result-value" :class="getChangeClass(backtest.result.total_return)">
                    {{ (backtest.result.total_return * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="result-item">
                  <span class="result-label">年化收益率</span>
                  <span class="result-value" :class="getChangeClass(backtest.result.annual_return)">
                    {{ (backtest.result.annual_return * 100).toFixed(2) }}%
                  </span>
                </div>
                <div class="result-item">
                  <span class="result-label">夏普比率</span>
                  <span class="result-value">{{ backtest.result.sharpe_ratio.toFixed(2) }}</span>
                </div>
                <div class="result-item">
                  <span class="result-label">最大回撤</span>
                  <span class="result-value value-down">{{ (backtest.result.max_drawdown * 100).toFixed(2) }}%</span>
                </div>
                <div class="result-item">
                  <span class="result-label">胜率</span>
                  <span class="result-value">{{ (backtest.result.win_rate * 100).toFixed(2) }}%</span>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p>回测尚未完成</p>
            </div>
          </div>
        </div>
      </div>

      <div v-if="backtest.error_message" class="card error-card">
        <div class="card-header">
          <h4>错误信息</h4>
        </div>
        <div class="card-body">
          <div class="alert alert-error">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>{{ backtest.error_message }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { storeToRefs } from 'pinia'
import { useBacktestStore } from '@/stores/backtest'
import StatusTag from '@/components/common/StatusTag.vue'
import { formatDate } from '@/utils/format'
import type { BacktestTask } from '@/api'

const route = useRoute()
const router = useRouter()
const taskUuid = route.params.uuid as string

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

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
  if (backtest.value?.status === 'failed') return 'progress-exception'
  if (backtest.value?.status === 'completed') return 'progress-success'
  return 'progress-active'
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

// 自定义确认对话框
const showConfirm = (title: string, content: string, onOk: () => void) => {
  if (confirm(`${title}\n\n${content}`)) {
    onOk()
  }
}

// 返回
const goBack = () => {
  router.push('/backtest')
}

// 启动回测（重新运行，创建新任务）
const handleStart = async () => {
  if (!backtest.value) return

  showConfirm(
    '确认重新运行',
    `确定要重新运行回测任务"${backtest.value.name}"吗？这将创建一个新的回测任务。`,
    async () => {
      try {
        const result = await startTask(backtest.value.uuid)
        showToast('启动成功，正在跳转到新任务...')
        if (result?.uuid) {
          router.push(`/backtest/${result.uuid}`)
        } else {
          await fetchTask(taskUuid)
        }
      } catch (error: any) {
        showToast(`操作失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 停止回测
const handleStop = async () => {
  if (!backtest.value) return

  showConfirm(
    '确认停止',
    `确定要停止回测任务"${backtest.value.name}"吗？`,
    async () => {
      try {
        await stopTask(backtest.value.uuid)
        showToast('已停止')
        stopSSE()
        await fetchTask(taskUuid)
      } catch (error: any) {
        showToast(`操作失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 取消任务
const handleCancel = async () => {
  if (!backtest.value) return

  showConfirm(
    '确认取消',
    `确定要取消回测任务"${backtest.value.name}"吗？`,
    async () => {
      try {
        await cancelTask(backtest.value.uuid)
        showToast('已取消')
        stopSSE()
        await fetchTask(taskUuid)
      } catch (error: any) {
        showToast(`操作失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 删除任务
const handleDelete = async () => {
  if (!backtest.value) return

  showConfirm(
    '确认删除',
    `确定要删除回测任务"${backtest.value.name}"吗？此操作不可恢复。`,
    async () => {
      try {
        await deleteTask(backtest.value.uuid)
        showToast('删除成功')
        router.push('/backtest')
      } catch (error: any) {
        showToast(`删除失败: ${error.message || '未知错误'}`, 'error')
      }
    }
  )
}

// 启动 SSE 监听
const startSSE = () => {
  if (eventSource.value) {
    eventSource.value.close()
  }
  // SSE 实现待完成
}

// 停止 SSE
const stopSSE = () => {
  if (eventSource.value) {
    eventSource.value.close()
    eventSource.value = null
  }
}

// 加载详情
const loadDetail = async () => {
  const detail = await fetchTask(taskUuid)
  if (detail) {
    progress.value = detail.progress || 0
    if (detail.status === 'running' || detail.status === 'pending') {
      startSSE()
    }
  } else {
    showToast('加载详情失败', 'error')
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
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-text:hover {
  background: #2a2a3e;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.permission-hint {
  color: #8a8a9a;
  font-size: 14px;
  padding: 8px 12px;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-danger {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #ff4d4f;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-section {
  margin-bottom: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.info-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.status-display {
  text-align: center;
  padding: 16px 0;
}

.status-label {
  font-size: 14px;
  color: #8a8a9a;
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
  color: #8a8a9a;
}

.progress-value {
  font-size: 24px;
  font-weight: 600;
  color: #1890ff;
}

.progress-bar {
  height: 12px;
  background: #2a2a3e;
  border-radius: 6px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease;
  border-radius: 6px;
}

.progress-active {
  background: #1890ff;
}

.progress-success {
  background: #52c41a;
}

.progress-exception {
  background: #f5222d;
}

.progress-footer {
  margin-top: 12px;
}

.current-date {
  font-size: 12px;
  color: #8a8a9a;
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.descriptions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.description-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
}

.description-label {
  font-size: 14px;
  color: #8a8a9a;
}

.description-value {
  font-size: 14px;
  color: #ffffff;
  font-weight: 500;
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
  background: #2a2a3e;
  border-radius: 8px;
  text-align: center;
}

.result-label {
  display: block;
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.result-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}

.value-flat {
  color: #8a8a9a;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.error-card {
  border-color: #f5222d;
}

.alert {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 4px;
}

.alert-error {
  background: rgba(245, 34, 45, 0.1);
  border: 1px solid #f5222d;
  color: #f5222d;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .config-grid {
    grid-template-columns: 1fr;
  }

  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
