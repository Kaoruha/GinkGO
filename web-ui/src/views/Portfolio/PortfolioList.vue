<template>
  <div class="portfolio-list-container">
    <!-- Custom -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">投资组合</h1>
        <p class="page-subtitle">管理和监控您的所有投资组合</p>
      </div>
      <div class="header-actions">
        <a-radio-group
          v-model:value="filterMode"
          button-style="solid"
          size="large"
          @change="handleFilterChange"
        >
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="BACKTEST">回测</a-radio-button>
          <a-radio-button value="PAPER">模拟</a-radio-button>
          <a-radio-button value="LIVE">实盘</a-radio-button>
        </a-radio-group>
        <a-button type="primary" size="large" @click="goToCreate">
          <PlusOutlined /> 创建组合
        </a-button>
      </div>
    </div>

    <!-- Custom -->
    <div class="stats-row">
      <StatisticCard
        title="总投资组合"
        :value="stats.total"
        :icon="FolderOutlined"
        icon-color="#1890ff"
        type="primary"
      />
      <StatisticCard
        title="运行中"
        :value="stats.running"
        :icon="PlayCircleOutlined"
        icon-color="#52c41a"
        type="success"
      />
      <StatisticCard
        title="平均净值"
        :value="stats.avgNetValue"
        :precision="3"
        :icon="LineChartOutlined"
        icon-color="#fa8c16"
        type="warning"
      />
      <StatisticCard
        title="总资产"
        :value="stats.totalAssets"
        :precision="2"
        prefix="¥"
        :icon="DollarOutlined"
        icon-color="#722ed1"
      />
    </div>

    <!-- Custom -->
    <div v-if="isPortfolioLoading()" class="loading-container">
      <a-spin size="large" />
    </div>
    <div v-else-if="filteredPortfolios.length === 0" class="empty-container">
      <EmptyState
        description="暂无投资组合"
        action-text="创建第一个投资组合"
        :on-action="() => showCreateModal = true"
      />
    </div>
    <div v-else class="portfolio-grid">
      <a-card
        v-for="portfolio in filteredPortfolios"
        :key="portfolio.uuid"
        class="portfolio-card"
        hoverable
        @click="goToDetail(portfolio.uuid)"
      >
        <template #title>
          <div class="card-title">
            <span class="portfolio-name">{{ portfolio.name }}</span>
            <a-tag :color="getModeColor(portfolio.mode)">
              {{ getModeLabel(portfolio.mode) }}
            </a-tag>
          </div>
        </template>
        <template #extra>
          <a-dropdown :trigger="['click']" @click.stop>
            <a class="more-btn" @click.prevent>
              <MoreOutlined />
            </a>
            <template #overlay>
              <a-menu>
                <a-menu-item @click="goToDetail(portfolio.uuid)">
                  <EyeOutlined /> 查看详情
                </a-menu-item>
                <a-menu-item @click="handleDelete(portfolio)">
                  <DeleteOutlined /> 删除
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </template>

        <!-- Custom -->
        <div class="net-value-section">
          <div class="net-value-main">
            <span class="net-value-value">{{ portfolio.net_value.toFixed(3) }}</span>
            <span class="net-value-label">净值</span>
          </div>
          <div
            class="net-value-change"
            :class="getNetValueChangeClass(portfolio.net_value)"
          >
            <ArrowUpOutlined v-if="portfolio.net_value > 1" />
            <ArrowDownOutlined v-else-if="portfolio.net_value < 1" />
            <MinusOutlined v-else />
            {{ Math.abs((portfolio.net_value - 1) * 100).toFixed(2) }}%
          </div>
        </div>

        <!-- Custom -->
        <div class="info-row">
          <span class="info-label">状态:</span>
          <a-tag :color="getStateColor(portfolio.state)">
            <a-badge :status="getStateStatus(portfolio.state)" />
            {{ getStateLabel(portfolio.state) }}
          </a-tag>
        </div>
        <div class="info-row">
          <span class="info-label">创建时间:</span>
          <span class="info-value">{{ formatDate(portfolio.created_at) }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">配置锁定:</span>
          <a-tag :color="portfolio.config_locked ? 'orange' : 'green'">
            {{ portfolio.config_locked ? '是' : '否' }}
          </a-tag>
        </div>

        <!-- Custom -->
        <div class="action-buttons">
          <a-button
            v-if="portfolio.state === 'RUNNING'"
            danger
            size="small"
            @click.stop="handleStop(portfolio)"
          >
            <PauseOutlined /> 停止
          </a-button>
          <a-button
            v-else-if="portfolio.state === 'PAUSED' || portfolio.state === 'STOPPED'"
            type="primary"
            size="small"
            @click.stop="handleStart(portfolio)"
          >
            <PlayCircleOutlined /> 启动
          </a-button>
          <a-button size="small" @click.stop="goToDetail(portfolio.uuid)">
            <EyeOutlined /> 详情
          </a-button>
        </div>
      </a-card>
    </div>

    <!-- Custom -->
    <a-modal
      v-model:open="showCreateModal"
      title="创建投资组合"
      width="600px"
      :confirm-loading="creating"
      @ok="handleCreate"
      @cancel="resetCreateForm"
    >
      <ProForm
        :model="createForm"
        :rules="createRules"
        @submit="handleCreate"
        @cancel="resetCreateForm"
      >
        <a-form-item label="组合名称" name="name">
          <a-input
            v-model:value="createForm.name"
            placeholder="请输入投资组合名称"
            size="large"
          />
        </a-form-item>

        <a-form-item label="运行模式" name="mode">
          <a-radio-group v-model:value="createForm.mode" size="large">
            <a-radio-button value="BACKTEST">回测模式</a-radio-button>
            <a-radio-button value="PAPER">模拟交易</a-radio-button>
            <a-radio-button value="LIVE">实盘交易</a-radio-button>
          </a-radio-group>
        </a-form-item>

        <a-form-item label="初始资金" name="initial_cash">
          <a-input-number
            v-model:value="createForm.initial_cash"
            :min="1000"
            :max="100000000"
            :step="10000"
            :precision="2"
            style="width: 100%"
            size="large"
          >
            <template #prefix>¥</template>
          </a-input-number>
        </a-form-item>

        <a-form-item label="风险配置">
          <a-textarea
            v-model:value="createForm.risk_config"
            placeholder='JSON格式，例如：{"max_position_ratio": 0.3, "stop_loss_ratio": 0.05}'
            :rows="4"
          />
        </a-form-item>
      </ProForm>
    </a-modal>

    <!-- Loading Overlay -->
    <LoadingOverlay
      :visible="creating"
      :text="'创建投资组合中...'"
      @close="creating = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import {
  PlusOutlined,
  FolderOutlined,
  PlayCircleOutlined,
  LineChartOutlined,
  DollarOutlined,
  MoreOutlined,
  EyeOutlined,
  DeleteOutlined,
  PauseOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined
} from '@ant-design/icons-vue'
import StatisticCard from '@/components/data/StatisticCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import ProForm from '@/components/form/ProForm.vue'
import LoadingOverlay from '@/components/common/LoadingOverlay.vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import {
  getModeLabel,
  getModeColor,
  getStateLabel,
  getStateColor,
  getStateStatus
} from '@/constants'
import { formatDate } from '@/utils/format'
import { useErrorHandler, useLoading } from '@/composables'

const router = useRouter()

// 使用 Store
const portfolioStore = usePortfolioStore()
const {
  portfolios,
  filterMode,
  filteredPortfolios,
  stats
} = storeToRefs(portfolioStore)
const {
  fetchPortfolios,
  deletePortfolio,
  updatePortfolio
} = portfolioStore

// 使用统一错误处理
const { execute } = useErrorHandler()

// 使用统一 loading 管理
const { isLoading: isPortfolioLoading } = useLoading({
  key: 'portfolio-list'
})

// 本地状态
const showCreateModal = ref(false)
const creating = ref(false)

// 创建表单
const createForm = reactive({
  name: '',
  mode: 'BACKTEST',
  initial_cash: 100000,
  risk_config: '{}'
})

const createRules = {
  name: [{ required: true, message: '请输入组合名称', trigger: 'blur' }],
  mode: [{ required: true, message: '请选择运行模式', trigger: 'change' }],
  initial_cash: [{ required: true, message: '请输入初始资金', trigger: 'blur' }]
}

// 筛选变化
const handleFilterChange = () => {
  fetchPortfolios(filterMode.value ? { mode: filterMode.value } : undefined)
}

// 净值变化样式
const getNetValueChangeClass = (netValue: number) => {
  if (netValue > 1) return 'value-up'
  if (netValue < 1) return 'value-down'
  return 'value-flat'
}

// 跳转详情
const goToDetail = (uuid: string) => {
  router.push(`/portfolio/${uuid}`)
}

// 跳转创建页面
const goToCreate = () => {
  router.push('/portfolio/create')
}

// 创建组合
const handleCreate = async () => {
  creating.value = true
  try {
    let riskConfig: Record<string, any> = {}
    try {
      riskConfig = JSON.parse(createForm.risk_config)
    } catch {
      message.warning('风险配置JSON格式不正确，将使用默认配置')
    }

    const result = await execute(async () => {
      return await portfolioStore.createPortfolio({
        name: createForm.name,
        initial_cash: createForm.initial_cash,
        risk_config: Object.keys(riskConfig).length > 0 ? riskConfig : undefined
      })
    })

    if (result) {
      message.success('创建成功')
      showCreateModal.value = false
      resetCreateForm()
    }
  } finally {
    creating.value = false
  }
}

// 重置创建表单
const resetCreateForm = () => {
  createForm.name = ''
  createForm.mode = 'BACKTEST'
  createForm.initial_cash = 100000
  createForm.risk_config = '{}'
}

// 停止组合
const handleStop = (portfolio: any) => {
  Modal.confirm({
    title: '确认停止',
    content: `确定要停止投资组合"${portfolio.name}"吗？`,
    onOk: async () => {
      const result = await execute(async () => {
        return await updatePortfolio(portfolio.uuid, { state: 'STOPPED' })
      })
      if (result) {
        message.success('已停止')
      }
    }
  })
}

// 启动组合
const handleStart = (portfolio: any) => {
  Modal.confirm({
    title: '确认启动',
    content: `确定要启动投资组合"${portfolio.name}"吗？`,
    onOk: async () => {
      const result = await execute(async () => {
        return await updatePortfolio(portfolio.uuid, { state: 'RUNNING' })
      })
      if (result) {
        message.success('启动成功')
      }
    }
  })
}

// 删除组合
const handleDelete = (portfolio: any) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除投资组合"${portfolio.name}"吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      const result = await execute(async () => {
        return await deletePortfolio(portfolio.uuid)
      })
      if (result) {
        message.success('删除成功')
      }
    }
  })
}

onMounted(() => {
  fetchPortfolios()
})
</script>

<style scoped>
.portfolio-list-container {
  padding: 24px;
  background: #f5f7fa;
  height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-shrink: 0;
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
  flex-shrink: 0;
}

/* 滚动内容区域 */
.loading-container,
.empty-container,
.portfolio-grid {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px;
}

/* 滚动条样式 */
.portfolio-grid::-webkit-scrollbar,
.loading-container::-webkit-scrollbar,
.empty-container::-webkit-scrollbar {
  width: 8px;
}

.portfolio-grid::-webkit-scrollbar-track,
.loading-container::-webkit-scrollbar-track,
.empty-container::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 4px;
}

.portfolio-grid::-webkit-scrollbar-thumb,
.loading-container::-webkit-scrollbar-thumb,
.empty-container::-webkit-scrollbar-thumb {
  background: #bfbfbf;
  border-radius: 4px;
}

.portfolio-grid::-webkit-scrollbar-thumb:hover,
.loading-container::-webkit-scrollbar-thumb:hover,
.empty-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}

.loading-container,
.empty-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
}

.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  align-content: start;
}

.portfolio-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: box-shadow 0.2s;
  cursor: pointer;
}

.portfolio-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.portfolio-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
  padding: 16px 20px;
}

.portfolio-card :deep(.ant-card-body) {
  padding: 20px;
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

.portfolio-name {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.more-btn {
  color: #8c8c8c;
  font-size: 18px;
}

.more-btn:hover {
  color: #1890ff;
}

.net-value-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  margin-bottom: 16px;
  border-bottom: 1px solid #f0f0f0;
}

.net-value-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.net-value-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a1a;
}

.net-value-label {
  font-size: 12px;
  color: #8c8c8c;
}

.net-value-change {
  font-size: 16px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 4px;
}

.value-up {
  color: #f5222d;
  background: #fff1f0;
}

.value-down {
  color: #52c41a;
  background: #f6ffed;
}

.value-flat {
  color: #8c8c8c;
  background: #fafafa;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 14px;
}

.info-label {
  color: #8c8c8c;
}

.info-value {
  color: #1a1a1a;
}

.action-buttons {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.action-buttons .ant-btn {
  flex: 1;
}

/* 响应式 */
@media (max-width: 1400px) {
  .stats-row {
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

  .portfolio-grid {
    grid-template-columns: 1fr;
  }
}
</style>
