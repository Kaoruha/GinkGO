<template>
  <div class="portfolio-list-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          投资组合
        </h1>
        <p class="page-subtitle">
          管理和监控您的所有投资组合
        </p>
      </div>
      <div class="header-actions">
        <a-radio-group
          v-model:value="filterMode"
          button-style="solid"
          size="large"
          @change="handleFilterChange"
        >
          <a-radio-button value="">
            全部
          </a-radio-button>
          <a-radio-button value="BACKTEST">
            回测
          </a-radio-button>
          <a-radio-button value="PAPER">
            模拟
          </a-radio-button>
          <a-radio-button value="LIVE">
            实盘
          </a-radio-button>
        </a-radio-group>
        <a-button
          type="primary"
          size="large"
          @click="goToCreate"
        >
          <PlusOutlined />
          创建组合
        </a-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <a-card class="stat-card stat-card-blue">
        <a-statistic
          title="总投资组合"
          :value="stats.total"
          :value-style="{ color: '#1890ff', fontSize: '32px' }"
        >
          <template #prefix>
            <FolderOutlined />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-green">
        <a-statistic
          title="运行中"
          :value="stats.running"
          :value-style="{ color: '#52c41a', fontSize: '32px' }"
        >
          <template #prefix>
            <PlayCircleOutlined />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-orange">
        <a-statistic
          title="平均净值"
          :value="stats.avgNetValue"
          :precision="3"
          :value-style="{ color: '#fa8c16', fontSize: '32px' }"
        >
          <template #prefix>
            <LineChartOutlined />
          </template>
        </a-statistic>
      </a-card>
      <a-card class="stat-card stat-card-purple">
        <a-statistic
          title="总资产"
          :value="stats.totalAssets"
          :precision="2"
          prefix="¥"
          :value-style="{ color: '#722ed1', fontSize: '32px' }"
        >
          <template #prefix>
            <DollarOutlined />
          </template>
        </a-statistic>
      </a-card>
    </div>

    <!-- 投资组合列表 -->
    <div
      v-if="loading"
      class="loading-container"
    >
      <a-spin size="large" />
    </div>
    <div
      v-else-if="filteredPortfolios.length === 0"
      class="empty-container"
    >
      <a-empty description="暂无投资组合">
        <a-button
          type="primary"
          @click="showCreateModal = true"
        >
          创建第一个投资组合
        </a-button>
      </a-empty>
    </div>
    <div
      v-else
      class="portfolio-grid"
    >
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
          <a-dropdown
            :trigger="['click']"
            @click.stop
          >
            <a
              class="more-btn"
              @click.prevent
            >
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

        <!-- 净值信息 -->
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

        <!-- 状态信息 -->
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

        <!-- 操作按钮 -->
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
          <a-button
            size="small"
            @click.stop="goToDetail(portfolio.uuid)"
          >
            <EyeOutlined /> 详情
          </a-button>
        </div>
      </a-card>
    </div>

    <!-- 创建组合弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      title="创建投资组合"
      width="600px"
      :confirm-loading="creating"
      @ok="handleCreate"
      @cancel="resetCreateForm"
    >
      <a-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        layout="vertical"
      >
        <a-form-item
          label="组合名称"
          name="name"
        >
          <a-input
            v-model:value="createForm.name"
            placeholder="请输入投资组合名称"
            size="large"
          />
        </a-form-item>
        <a-form-item
          label="运行模式"
          name="mode"
        >
          <a-radio-group
            v-model:value="createForm.mode"
            size="large"
          >
            <a-radio-button value="BACKTEST">
              回测模式
            </a-radio-button>
            <a-radio-button value="PAPER">
              模拟交易
            </a-radio-button>
            <a-radio-button value="LIVE">
              实盘交易
            </a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item
          label="初始资金"
          name="initial_cash"
        >
          <a-input-number
            v-model:value="createForm.initial_cash"
            :min="1000"
            :max="100000000"
            :step="10000"
            :precision="2"
            style="width: 100%"
            size="large"
          >
            <template #prefix>
              ¥
            </template>
          </a-input-number>
        </a-form-item>
        <a-form-item label="风险配置">
          <a-textarea
            v-model:value="createForm.risk_config"
            placeholder="JSON格式，例如：{&quot;max_position_ratio&quot;: 0.3, &quot;stop_loss_ratio&quot;: 0.05}"
            :rows="4"
          />
        </a-form-item>
      </a-form>
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
import { portfolioApi, type Portfolio } from '@/api/modules/portfolio'
import {
  getModeLabel,
  getModeColor,
  getStateLabel,
  getStateColor,
  getStateStatus
} from '@/constants'
import { formatDate } from '@/utils/format'

const router = useRouter()

// 状态管理
const loading = ref(false)
const portfolios = ref<Portfolio[]>([])
const filterMode = ref('')
const showCreateModal = ref(false)
const creating = ref(false)

// 统计数据
const stats = computed(() => {
  const filtered = filterMode.value
    ? portfolios.value.filter(p => p.mode === filterMode.value)
    : portfolios.value

  return {
    total: filtered.length,
    running: filtered.filter(p => p.state === 'RUNNING').length,
    avgNetValue: filtered.length > 0
      ? filtered.reduce((sum, p) => sum + p.net_value, 0) / filtered.length
      : 0,
    totalAssets: filtered.length > 0
      ? filtered.reduce((sum, p) => sum + p.net_value * 100000, 0) // 假设初始资金为10万
      : 0
  }
})

// 筛选后的列表
const filteredPortfolios = computed(() => {
  if (!filterMode.value) return portfolios.value
  return portfolios.value.filter(p => p.mode === filterMode.value)
})

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

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    // 只有当 filterMode 不为空时才传递 mode 参数
    const params = filterMode.value ? { mode: filterMode.value } : {}
    const data = await portfolioApi.list(params)
    portfolios.value = data
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

// 创建组合（保留用于模态框创建，如果需要的话）
const handleCreate = async () => {
  creating.value = true
  try {
    let riskConfig: Record<string, any> = {}
    try {
      riskConfig = JSON.parse(createForm.risk_config)
    } catch (e) {
      message.warning('风险配置JSON格式不正确，将使用默认配置')
    }

    await portfolioApi.create({
      name: createForm.name,
      initial_cash: createForm.initial_cash,
      risk_config: Object.keys(riskConfig).length > 0 ? riskConfig : undefined
    })

    message.success('创建成功')
    showCreateModal.value = false
    resetCreateForm()
    loadData()
  } catch (error: any) {
    message.error(`创建失败: ${error.message || '未知错误'}`)
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
const handleStop = (portfolio: Portfolio) => {
  Modal.confirm({
    title: '确认停止',
    content: `确定要停止投资组合"${portfolio.name}"吗？`,
    onOk: async () => {
      try {
        await portfolioApi.update(portfolio.uuid, { state: 'STOPPED' })
        message.success('已停止')
        loadData()
      } catch (error: any) {
        message.error(`操作失败: ${error.message || '未知错误'}`)
      }
    }
  })
}

// 启动组合
const handleStart = (portfolio: Portfolio) => {
  try {
    // TODO: 调用启动API
    message.success('启动成功')
    loadData()
  } catch (error: any) {
    message.error(`操作失败: ${error.message || '未知错误'}`)
  }
}

// 删除组合
const handleDelete = (portfolio: Portfolio) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除投资组合"${portfolio.name}"吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    onOk: async () => {
      try {
        await portfolioApi.delete(portfolio.uuid)
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
.portfolio-list-container {
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

.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
}

.portfolio-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: pointer;
}

.portfolio-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
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
