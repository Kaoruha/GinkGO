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
          v-model:value="filterState"
          button-style="solid"
          size="large"
          @change="handleFilterChange"
        >
          <a-radio-button value="">
            全部
          </a-radio-button>
          <a-radio-button value="PENDING">
            等待中
          </a-radio-button>
          <a-radio-button value="RUNNING">
            运行中
          </a-radio-button>
          <a-radio-button value="COMPLETED">
            已完成
          </a-radio-button>
        </a-radio-group>
        <a-button
          type="primary"
          size="large"
          @click="goToCreate"
        >
          <PlusOutlined /> 创建回测
        </a-button>
      </div>
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
      v-else-if="filteredBacktests.length === 0"
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
      :data-source="filteredBacktests"
      :pagination="{ pageSize: 10, showSizeChanger: true, showQuickJumper: true }"
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
        <template v-if="column.key === 'state'">
          <a-tag :color="getBacktestStateColor(record.state)">
            <a-badge :status="getBacktestStateStatus(record.state)" />
            {{ getBacktestStateLabel(record.state) }}
          </a-tag>
        </template>
        <template v-if="column.key === 'progress'">
          <div class="progress-cell">
            <a-progress
              :percent="record.progress"
              :status="record.state === 'FAILED' ? 'exception' : record.state === 'COMPLETED' ? 'success' : 'active'"
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
            <a
              v-if="record.state === 'COMPLETED'"
              @click="viewResult(record)"
            >查看结果</a>
            <a
              v-if="record.state === 'PENDING'"
              @click="handleStart(record)"
            >启动</a>
            <a
              v-if="record.state === 'RUNNING'"
              @click="handleStop(record)"
            >停止</a>
            <a
              v-if="record.state !== 'RUNNING'"
              @click="handleDelete(record)"
            >删除</a>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import dayjs from 'dayjs'
import {
  PlusOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined
} from '@ant-design/icons-vue'
import { backtestApi, type BacktestTask, type BacktestTaskDetail } from '@/api/modules/backtest'
import {
  getBacktestStateLabel,
  getBacktestStateColor,
  getBacktestStateStatus
} from '@/constants'
import { formatDate } from '@/utils/format'

const router = useRouter()

// 状态管理
const loading = ref(false)
const backtests = ref<BacktestTask[]>([])
const filterState = ref('')
const showResultModal = ref(false)
const selectedBacktest = ref<BacktestTaskDetail | null>(null)

// 表格列
const columns = [
  { title: '任务名称', key: 'name', width: 250 },
  { title: '状态', key: 'state', width: 120 },
  { title: '进度', key: 'progress', width: 150 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '运行时长', key: 'duration', width: 120 },
  { title: '操作', key: 'actions', width: 150, fixed: 'right' }
]

// 统计数据
const stats = computed(() => {
  const filtered = filterState.value
    ? backtests.value.filter(t => t.state === filterState.value)
    : backtests.value

  return {
    total: filtered.length,
    completed: filtered.filter(t => t.state === 'COMPLETED').length,
    running: filtered.filter(t => t.state === 'RUNNING').length,
    failed: filtered.filter(t => t.state === 'FAILED').length
  }
})

// 筛选后的列表
const filteredBacktests = computed(() => {
  if (!filterState.value) return backtests.value
  return backtests.value.filter(t => t.state === filterState.value)
})

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const data = await backtestApi.list({ state: filterState.value as any })
    backtests.value = data
  } catch (error: any) {
    message.error(`加载失败: ${error.message || '未知错误'}`)
  } finally {
    loading.value = false
  }
}

// 筛选变化
const handleFilterChange = () => {
  loadData()
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

// 跳转创建页面
const goToCreate = () => {
  router.push('/backtest/create')
}

// 查看结果
const viewResult = async (task: BacktestTask) => {
  try {
    const detail = await backtestApi.get(task.uuid)
    selectedBacktest.value = detail
    showResultModal.value = true
  } catch (error: any) {
    message.error(`加载详情失败: ${error.message || '未知错误'}`)
  }
}

// 启动任务
const handleStart = (task: BacktestTask) => {
  Modal.confirm({
    title: '确认启动',
    content: `确定要启动回测任务"${task.name}"吗？`,
    onOk: async () => {
      try {
        await backtestApi.start(task.uuid)
        message.success('启动成功')
        loadData()
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
        await backtestApi.stop(task.uuid)
        message.success('已停止')
        loadData()
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
        await backtestApi.delete(task.uuid)
        message.success('删除成功')
        loadData()
      } catch (error: any) {
        message.error(`删除失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

onMounted(() => {
  loadData()
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
