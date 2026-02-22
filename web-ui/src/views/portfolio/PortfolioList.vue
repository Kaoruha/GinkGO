<template>
  <div class="portfolio-list-page">
    <!-- 固定的页面头部区域 -->
    <div class="fixed-header">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1>投资组合</h1>
          <a-tag color="purple">{{ stats.total }} 个组合</a-tag>
        </div>
        <div class="header-right">
          <a-input-search
            v-model:value="searchKeyword"
            placeholder="搜索组合名称..."
            style="width: 240px"
            allow-clear
          />
          <a-button type="primary" @click="showCreateModal">
            <PlusOutlined /> 创建组合
          </a-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <a-radio-group v-model:value="filterMode" button-style="solid" size="small" @change="handleFilterChange">
          <a-radio-button value="">全部</a-radio-button>
          <a-radio-button value="0">回测</a-radio-button>
          <a-radio-button value="1">模拟</a-radio-button>
          <a-radio-button value="2">实盘</a-radio-button>
        </a-radio-group>
      </div>

      <!-- 统计卡片 -->
      <a-row :gutter="16" class="stats-row">
        <a-col :span="6">
          <a-card class="stat-card" size="small">
            <a-statistic title="总投资组合" :value="stats.total" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card" size="small">
            <a-statistic title="运行中" :value="stats.running" :value-style="{ color: '#52c41a' }" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card" size="small">
            <a-statistic title="平均净值" :value="stats.avgNetValue" :precision="3" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card" size="small">
            <a-statistic title="总资产" :value="stats.totalAssets" />
          </a-card>
        </a-col>
      </a-row>
    </div>

    <!-- 可滚动的内容区域 -->
    <div class="scrollable-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
      </div>

      <!-- 空状态 -->
      <a-empty v-else-if="filteredAndSearchedPortfolios.length === 0" description="暂无投资组合">
        <a-button type="primary" @click="showCreateModal">创建第一个组合</a-button>
      </a-empty>

      <!-- 卡片列表 -->
      <div v-else class="portfolio-grid">
      <a-card
        v-for="portfolio in filteredAndSearchedPortfolios"
        :key="portfolio.uuid"
        class="portfolio-card"
        hoverable
        @click="viewDetail(portfolio)"
      >
        <template #title>
          <div class="card-title">
            <span class="name">{{ portfolio.name }}</span>
            <a-tag :color="getModeColor(portfolio.mode)" size="small">
              {{ getModeLabel(portfolio.mode) }}
            </a-tag>
          </div>
        </template>
        <template #extra>
          <a-dropdown @click.stop>
            <a-button type="text" size="small">
              <MoreOutlined />
            </a-button>
            <template #overlay>
              <a-menu>
                <a-menu-item @click.stop="viewDetail(portfolio)">
                  <EyeOutlined /> 详情
                </a-menu-item>
                <a-menu-divider />
                <a-menu-item danger @click.stop="confirmDelete(portfolio)">
                  <DeleteOutlined /> 删除
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </template>

        <div class="card-content">
          <p class="desc">{{ portfolio.desc || '暂无描述' }}</p>

          <div class="metrics">
            <div class="metric">
              <span class="label">净值</span>
              <span class="value" :class="{ positive: portfolio.net_value >= 1, negative: portfolio.net_value < 1 }">
                {{ (portfolio.net_value || 1).toFixed(4) }}
              </span>
            </div>
            <div class="metric">
              <span class="label">初始资金</span>
              <span class="value">¥{{ (portfolio.initial_cash || 0).toLocaleString() }}</span>
            </div>
          </div>

          <div class="card-footer">
            <a-tag :color="getStateColor(portfolio.state)" size="small">
              {{ getStateLabel(portfolio.state) }}
            </a-tag>
            <span class="date">{{ formatDate(portfolio.created_at) }}</span>
          </div>
        </div>
      </a-card>
      </div>
    </div>

    <!-- 创建组合模态框 -->
    <a-modal
      v-model:open="createModalVisible"
      title="创建投资组合"
      width="1200px"
      :footer="null"
      :destroyOnClose="true"
      @cancel="closeCreateModal"
    >
      <div class="modal-form-container">
        <PortfolioFormEditor ref="formEditorRef" :is-modal-mode="true" @created="handleCreated" @cancel="closeCreateModal" />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, MoreOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import PortfolioFormEditor from './PortfolioFormEditor.vue'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const { portfolios, loading, filterMode, stats, filteredPortfolios } = storeToRefs(portfolioStore)
const { fetchPortfolios, deletePortfolio } = portfolioStore

const searchKeyword = ref('')
const createModalVisible = ref(false)
const formEditorRef = ref()

const filteredAndSearchedPortfolios = computed(() => {
  if (!searchKeyword.value) return filteredPortfolios.value
  const keyword = searchKeyword.value.toLowerCase()
  return filteredPortfolios.value.filter((p: any) =>
    p.name?.toLowerCase().includes(keyword) ||
    p.desc?.toLowerCase().includes(keyword)
  )
})

const getModeColor = (mode: number) => ({ 0: 'blue', 1: 'orange', 2: 'red' }[mode] || 'default')
const getModeLabel = (mode: number) => ({ 0: '回测', 1: '模拟', 2: '实盘' }[mode] || '未知')
const getStateColor = (state: number) => ({ 0: 'default', 1: 'green', 2: 'blue', 3: 'red' }[state] || 'default')
const getStateLabel = (state: number) => ({ 0: '已停止', 1: '运行中', 2: '已完成', 3: '错误' }[state] || '未知')

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

const handleFilterChange = () => fetchPortfolios()

const showCreateModal = () => {
  createModalVisible.value = true
}

const closeCreateModal = () => {
  createModalVisible.value = false
}

const handleCreated = (uuid: string) => {
  createModalVisible.value = false
  fetchPortfolios()
  router.push(`/portfolio/${uuid}`)
}

const viewDetail = (record: any) => router.push(`/portfolio/${record.uuid}`)

const confirmDelete = (record: any) => {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除组合「${record.name}」吗？此操作不可恢复。`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk: async () => {
      try {
        await deletePortfolio(record.uuid)
        message.success('删除成功')
      } catch (e) {
        message.error('删除失败')
      }
    }
  })
}

onMounted(() => fetchPortfolios())
</script>

<style scoped>
.portfolio-list-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fixed-header {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.header-right {
  display: flex;
  gap: 12px;
}

.filter-bar {
  margin-bottom: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  cursor: default;
}

.scrollable-content {
  flex: 1;
  overflow-y: auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.portfolio-card {
  cursor: pointer;
  transition: all 0.3s;
}

.portfolio-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title .name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-content .desc {
  color: #666;
  font-size: 13px;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metrics {
  display: flex;
  gap: 24px;
}

.metric {
  display: flex;
  flex-direction: column;
}

.metric .label {
  font-size: 12px;
  color: #999;
}

.metric .value {
  font-size: 16px;
  font-weight: 500;
}

.metric .value.positive {
  color: #52c41a;
}

.metric .value.negative {
  color: #f5222d;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.card-footer .date {
  font-size: 12px;
  color: #999;
}

.modal-form-container {
  height: 70vh;
  overflow: hidden;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-right {
    width: 100%;
  }

  .header-right .ant-input-search {
    flex: 1;
  }

  .portfolio-grid {
    grid-template-columns: 1fr;
  }
}
</style>
