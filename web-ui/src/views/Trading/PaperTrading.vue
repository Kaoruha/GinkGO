<template>
  <div class="paper-trading-container">
    <div class="page-header">
      <h1 class="page-title">模拟盘交易</h1>
      <a-button type="primary" @click="showSelectPortfolio = true">
        <PlusOutlined /> 添加Portfolio
      </a-button>
    </div>

    <a-row :gutter="16">
      <!-- 左侧：Portfolio列表 -->
      <a-col :span="8">
        <a-card title="运行中的Portfolio" :loading="loading">
          <div v-if="portfolios.length === 0" class="empty-tip">
            暂无运行中的模拟盘Portfolio
          </div>
          <div v-else class="portfolio-list">
            <div
              v-for="p in portfolios"
              :key="p.uuid"
              :class="['portfolio-item', { active: selectedPortfolio?.uuid === p.uuid }]"
              @click="selectPortfolio(p)"
            >
              <div class="portfolio-header">
                <span class="portfolio-name">{{ p.name }}</span>
                <a-tag :color="getStateColor(p.state)">{{ getStateLabel(p.state) }}</a-tag>
              </div>
              <div class="portfolio-stats">
                <span>净值: {{ p.net_value?.toFixed(4) || '-' }}</span>
              </div>
              <div class="portfolio-actions">
                <a-button
                  v-if="p.state === 'RUNNING'"
                  size="small"
                  @click.stop="pausePortfolio(p)"
                >暂停</a-button>
                <a-button
                  v-else-if="p.state === 'PAUSED'"
                  size="small"
                  type="primary"
                  @click.stop="resumePortfolio(p)"
                >恢复</a-button>
                <a-button
                  v-else
                  size="small"
                  type="primary"
                  @click.stop="startPortfolio(p)"
                >启动</a-button>
                <a-button size="small" danger @click.stop="removePortfolio(p)">移除</a-button>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：选中Portfolio详情 -->
      <a-col :span="16">
        <template v-if="selectedPortfolio">
          <!-- 账户信息 -->
          <a-card title="账户信息" class="mb-4">
            <a-row :gutter="16">
              <a-col :span="6">
                <a-statistic title="初始资金" :value="portfolioDetail?.initial_cash || 0" :precision="2" prefix="¥" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="可用资金" :value="portfolioDetail?.current_cash || 0" :precision="2" prefix="¥" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="持仓市值" :value="positionValue" :precision="2" prefix="¥" />
              </a-col>
              <a-col :span="6">
                <a-statistic
                  title="累计盈亏"
                  :value="totalPnl"
                  :precision="2"
                  prefix="¥"
                  :value-style="{ color: totalPnl >= 0 ? '#f5222d' : '#52c41a' }"
                />
              </a-col>
            </a-row>
          </a-card>

          <!-- 当前持仓 -->
          <a-card title="当前持仓" class="mb-4">
            <a-table
              :columns="positionColumns"
              :data-source="portfolioDetail?.positions || []"
              :pagination="false"
              size="small"
              row-key="code"
            >
              <template #bodyCell="{ column, record }">
                <span v-if="column.dataIndex === 'pnl'" :style="{ color: record.pnl >= 0 ? '#f5222d' : '#52c41a' }">
                  {{ record.pnl >= 0 ? '+' : '' }}{{ record.pnl?.toFixed(2) || '0.00' }}%
                </span>
              </template>
            </a-table>
          </a-card>

          <!-- 风控预警 -->
          <a-card v-if="portfolioDetail?.risk_alerts?.length" title="风控预警">
            <a-list :data-source="portfolioDetail.risk_alerts" size="small">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-alert
                    :type="item.level === 'high' ? 'error' : 'warning'"
                    :message="item.message"
                    show-icon
                  />
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </template>

        <a-card v-else>
          <a-empty description="请选择一个Portfolio查看详情" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 选择Portfolio弹窗 -->
    <a-modal v-model:open="showSelectPortfolio" title="选择Portfolio" @ok="confirmAddPortfolio">
      <a-form layout="vertical">
        <a-form-item label="选择已有Portfolio">
          <a-select v-model:value="selectedPortfolioUuid" placeholder="选择要添加到模拟盘的Portfolio">
            <a-select-option v-for="p in availablePortfolios" :key="p.uuid" :value="p.uuid">
              {{ p.name }} ({{ p.mode }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="或创建新的模拟盘Portfolio">
          <a-button @click="$router.push('/portfolio/create')">新建Portfolio</a-button>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { portfolioApi, type Portfolio, type PortfolioDetail } from '@/api/modules/portfolio'

const loading = ref(false)
const portfolios = ref<Portfolio[]>([])
const selectedPortfolio = ref<Portfolio | null>(null)
const portfolioDetail = ref<PortfolioDetail | null>(null)
const showSelectPortfolio = ref(false)
const selectedPortfolioUuid = ref('')
const availablePortfolios = ref<Portfolio[]>([])

const positionColumns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '持仓量', dataIndex: 'volume', width: 100 },
  { title: '成本价', dataIndex: 'cost_price', width: 100 },
  { title: '现价', dataIndex: 'current_price', width: 100 },
  { title: '盈亏%', dataIndex: 'pnl', width: 100 }
]

const positionValue = computed(() => {
  if (!portfolioDetail.value?.positions) return 0
  return portfolioDetail.value.positions.reduce((sum, p) => sum + p.volume * p.current_price, 0)
})

const totalPnl = computed(() => {
  if (!portfolioDetail.value) return 0
  const init = portfolioDetail.value.initial_cash || 0
  const current = portfolioDetail.value.current_cash + positionValue.value
  return current - init
})

const getStateColor = (state: string) => {
  const colors: Record<string, string> = {
    RUNNING: 'green',
    PAUSED: 'orange',
    STOPPED: 'default',
    INITIALIZED: 'blue'
  }
  return colors[state] || 'default'
}

const getStateLabel = (state: string) => {
  const labels: Record<string, string> = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    STOPPED: '已停止',
    INITIALIZED: '已初始化'
  }
  return labels[state] || state
}

const loadPortfolios = async () => {
  loading.value = true
  try {
    const res = await portfolioApi.list({ mode: 'PAPER' })
    portfolios.value = res.data || []
    if (portfolios.value.length > 0 && !selectedPortfolio.value) {
      selectPortfolio(portfolios.value[0])
    }
  } catch (e) {
    message.error('加载Portfolio列表失败')
  } finally {
    loading.value = false
  }
}

const loadAvailablePortfolios = async () => {
  try {
    const res = await portfolioApi.list({})
    availablePortfolios.value = (res.data || []).filter(p => p.mode !== 'PAPER')
  } catch (e) {
    // ignore
  }
}

const selectPortfolio = async (p: Portfolio) => {
  selectedPortfolio.value = p
  try {
    const res = await portfolioApi.get(p.uuid)
    portfolioDetail.value = res.data || null
  } catch (e) {
    message.error('加载Portfolio详情失败')
  }
}

const startPortfolio = async (p: Portfolio) => {
  message.success(`启动Portfolio: ${p.name}`)
  p.state = 'RUNNING'
}

const pausePortfolio = async (p: Portfolio) => {
  message.success(`暂停Portfolio: ${p.name}`)
  p.state = 'PAUSED'
}

const resumePortfolio = async (p: Portfolio) => {
  message.success(`恢复Portfolio: ${p.name}`)
  p.state = 'RUNNING'
}

const removePortfolio = async (p: Portfolio) => {
  portfolios.value = portfolios.value.filter(item => item.uuid !== p.uuid)
  if (selectedPortfolio.value?.uuid === p.uuid) {
    selectedPortfolio.value = null
    portfolioDetail.value = null
  }
  message.success('已移除')
}

const confirmAddPortfolio = async () => {
  if (!selectedPortfolioUuid.value) {
    message.warning('请选择一个Portfolio')
    return
  }
  // 将选中的Portfolio切换为PAPER模式
  try {
    await portfolioApi.update(selectedPortfolioUuid.value, { mode: 'PAPER' as any })
    message.success('添加成功')
    showSelectPortfolio.value = false
    selectedPortfolioUuid.value = ''
    loadPortfolios()
  } catch (e) {
    message.error('添加失败')
  }
}

onMounted(() => {
  loadPortfolios()
  loadAvailablePortfolios()
})
</script>

<style scoped>
.paper-trading-container {
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

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.mb-4 {
  margin-bottom: 16px;
}

.empty-tip {
  text-align: center;
  color: #999;
  padding: 24px;
}

.portfolio-list {
  max-height: 400px;
  overflow-y: auto;
}

.portfolio-item {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.portfolio-item:hover {
  border-color: #1890ff;
}

.portfolio-item.active {
  border-color: #1890ff;
  background: #e6f7ff;
}

.portfolio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.portfolio-name {
  font-weight: 500;
}

.portfolio-stats {
  color: #666;
  font-size: 12px;
  margin-bottom: 8px;
}

.portfolio-actions {
  display: flex;
  gap: 8px;
}
</style>
