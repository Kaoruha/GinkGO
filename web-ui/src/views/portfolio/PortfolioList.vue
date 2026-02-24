<template>
  <div class="portfolio-list-page">
    <!-- 固定的页面头部区域 -->
    <div class="fixed-header">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1>投资组合</h1>
          <a-tag color="purple">{{ total }} 个组合</a-tag>
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
      <a-empty v-else-if="displayPortfolios.length === 0" description="暂无投资组合">
        <a-button type="primary" @click="showCreateModal">创建第一个组合</a-button>
      </a-empty>

      <!-- 卡片列表 -->
      <div v-else class="portfolio-grid">
      <a-card
        v-for="portfolio in displayPortfolios"
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

          <!-- 回测模式指标 -->
          <div v-if="portfolio.mode === 0" class="metrics">
            <div class="metric">
              <span class="label">回测次数</span>
              <span class="value">{{ portfolio.backtest_count || 0 }}</span>
            </div>
            <div class="metric">
              <span class="label">平均收益</span>
              <span class="value" :class="{ positive: portfolio.avg_return >= 0, negative: portfolio.avg_return < 0 }">
                {{ formatPercentValue(portfolio.avg_return) }}
              </span>
            </div>
          </div>

          <!-- 模拟/实盘模式指标 -->
          <div v-else class="metrics">
            <div class="metric">
              <span class="label">净值</span>
              <span class="value" :class="{ positive: portfolio.net_value >= 1, negative: portfolio.net_value < 1 }">
                {{ (portfolio.net_value || 1).toFixed(4) }}
              </span>
            </div>
            <div class="metric">
              <span class="label">初始资金</span>
              <span class="value">{{ formatMoney(portfolio.initial_cash) }}</span>
            </div>
          </div>

          <div class="card-footer">
            <a-tag :color="getStateColor(portfolio.state)" size="small">
              {{ getStateLabel(portfolio.state) }}
            </a-tag>
            <span class="date">{{ formatShortDate(portfolio.created_at) }}</span>
          </div>
        </div>
      </a-card>
      </div>

      <!-- 滚动加载触发器 -->
      <div v-if="displayPortfolios.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
        <a-spin v-if="loadingMore" size="small" />
        <div v-else-if="!hasMore" class="no-more">没有更多了</div>
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
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { PlusOutlined, MoreOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import { usePortfolioMode, usePortfolioState } from '@/composables'
import { formatMoney } from '@/utils/format'
import PortfolioFormEditor from './PortfolioFormEditor.vue'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const {
  portfolios,
  loading,
  loadingMore,
  filterMode,
  stats,
  filteredPortfolios,
  hasMore,
  total
} = storeToRefs(portfolioStore)
const { fetchPortfolios, fetchStats, deletePortfolio } = portfolioStore

// 状态格式化
const { getColor: getModeColor, getLabel: getModeLabel } = usePortfolioMode()
const { getColor: getStateColor, getLabel: getStateLabel } = usePortfolioState()

const searchKeyword = ref('')
const createModalVisible = ref(false)
const formEditorRef = ref()
const loadMoreTrigger = ref<HTMLElement>()

// 显示的投资组合（后端搜索，前端只做筛选过滤）
const displayPortfolios = computed(() => {
  return filteredPortfolios.value
})

// Intersection Observer 用于滚动加载
let observer: IntersectionObserver | null = null

const setupIntersectionObserver = () => {
  // 等待 DOM 更新后设置 observer
  nextTick(() => {
    if (!loadMoreTrigger.value) {
      console.log('⚠️ loadMoreTrigger 元素不存在，跳过 observer 设置')
      return
    }

    if (observer) {
      observer.disconnect()
    }

    // 获取滚动容器
    const scrollableContainer = document.querySelector('.scrollable-content')
    if (!scrollableContainer) {
      console.log('⚠️ .scrollable-content 元素不存在，跳过 observer 设置')
      return
    }

    observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0]
        if (entry.isIntersecting && hasMore.value && !loading.value && !loadingMore.value) {
          console.log(`📜 触发加载更多 - 当前: ${portfolios.value.length}, total: ${total.value}`)
          loadMore()
        }
      },
      {
        root: scrollableContainer as Element,
        rootMargin: '100px',
        threshold: 0.1
      }
    )

    observer.observe(loadMoreTrigger.value)
    console.log('✅ Intersection Observer 已设置 (root: .scrollable-content)')
  })
}

const loadMore = async () => {
  if (!hasMore.value || loading.value || loadingMore.value) return
  await fetchPortfolios({ append: true })
}

// 监听筛选模式变化，重置加载
watch(filterMode, () => {
  fetchPortfolios({ page: 0, append: false })
})

// 监听搜索关键词变化，后端搜索（带防抖）
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchKeyword, (newVal) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchPortfolios({ page: 0, append: false, keyword: newVal || undefined })
  }, 500)
})

// 当数据加载后，设置滚动监听
watch(displayPortfolios, (newVal) => {
  if (newVal.length > 0 && !observer) {
    console.log(`📦 数据加载完成，设置滚动监听 (${newVal.length} 条)`)
    setupIntersectionObserver()
  }
})

// 格式化百分比（用于平均收益）
const formatPercentValue = (val: number | undefined) => {
  return ((val || 0) * 100).toFixed(2) + '%'
}

// 格式化短日期（用于卡片底部）
const formatShortDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`
}

const handleFilterChange = () => {
  // filterMode 变化会触发 watch，这里不需要额外处理
}

const showCreateModal = () => {
  createModalVisible.value = true
}

const closeCreateModal = () => {
  createModalVisible.value = false
}

const handleCreated = (uuid: string) => {
  createModalVisible.value = false
  fetchPortfolios({ page: 0, append: false })
  fetchStats()  // 刷新统计数据
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

onMounted(() => {
  fetchPortfolios({ page: 0, append: false })
  fetchStats()  // 获取统计数据
  setupIntersectionObserver()
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})
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

.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 20px;
  margin-top: 20px;
}

.load-more-trigger .no-more {
  color: #999;
  font-size: 14px;
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
