<template>
  <div class="portfolio-list-page">
    <!-- 固定的页面头部区域 -->
    <div class="fixed-header">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1>投资组合</h1>
          <span class="tag tag-purple">{{ total }} 个组合</span>
        </div>
        <div class="header-right">
          <div class="search-box">
            <input
              v-model="searchKeyword"
              type="search"
              placeholder="搜索组合名称..."
              class="search-input"
              data-testid="portfolio-search"
            />
            <button class="search-btn" data-testid="portfolio-search-btn" @click="handleSearch">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </button>
          </div>
          <button class="btn-primary" data-testid="btn-create-portfolio" @click="showCreateModal">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            创建组合
          </button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="radio-group">
          <button
            v-for="option in filterOptions"
            :key="option.value"
            class="radio-button"
            :class="{ active: filterMode === option.value }"
            @click="setFilterMode(option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>

      <!-- 统计卡片 -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总投资组合</div>
        </div>
        <div class="stat-card">
          <div class="stat-value stat-success">{{ stats.running }}</div>
          <div class="stat-label">运行中</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ stats.avgNetValue?.toFixed(3) || '-' }}</div>
          <div class="stat-label">平均净值</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">{{ formatMoney(stats.totalAssets) }}</div>
          <div class="stat-label">总资产</div>
        </div>
      </div>
    </div>

    <!-- 可滚动的内容区域 -->
    <div class="scrollable-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="displayPortfolios.length === 0" class="empty-state">
        <div class="empty-icon">📊</div>
        <p class="empty-text">暂无投资组合</p>
        <button class="btn-primary" data-testid="btn-create-portfolio" @click="showCreateModal">创建第一个组合</button>
      </div>

      <!-- 卡片列表 -->
      <div v-else class="portfolio-grid">
        <div
          v-for="portfolio in displayPortfolios"
          :key="portfolio.uuid"
          class="portfolio-card"
              data-testid="portfolio-card"
          @click="viewDetail(portfolio)"
        >
          <div class="card-header">
            <div class="card-title">
              <span class="name">{{ portfolio.name }}</span>
              <span class="tag" :class="`tag-${getModeColorClass(portfolio.mode)}`">
                {{ getModeLabel(portfolio.mode) }}
              </span>
            </div>
            <div class="card-actions" @click.stop>
              <button class="btn-icon" data-testid="card-menu-btn" @click="toggleMenu(portfolio.uuid)">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="1"></circle>
                  <circle cx="12" cy="5" r="1"></circle>
                  <circle cx="12" cy="19" r="1"></circle>
                </svg>
              </button>
              <div v-if="activeMenu === portfolio.uuid" class="dropdown-menu">
                <button class="dropdown-item" @click="viewDetail(portfolio)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                  </svg>
                  详情
                </button>
                <div class="dropdown-divider"></div>
                <button class="dropdown-item danger" data-testid="btn-delete-portfolio" @click="confirmDelete(portfolio)">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 6h18"></path>
                    <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                    <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                  </svg>
                  删除
                </button>
              </div>
            </div>
          </div>

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
              <span class="tag" :class="`tag-${getStateColorClass(portfolio.state)}`">
                {{ getStateLabel(portfolio.state) }}
              </span>
              <span class="date">{{ formatShortDate(portfolio.created_at) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 滚动加载触发器 -->
      <div v-if="displayPortfolios.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
        <div v-if="loadingMore" class="spinner spinner-small"></div>
        <div v-else-if="!hasMore" class="no-more">没有更多了</div>
      </div>
    </div>

    <!-- 创建组合模态框 -->
    <div v-if="createModalVisible" class="modal-overlay" data-testid="create-portfolio-modal" @click.self="closeCreateModal">
      <div class="modal-content modal-large">
        <div class="modal-header">
          <h3>创建投资组合</h3>
          <button class="btn-close" @click="closeCreateModal">×</button>
        </div>
        <div class="modal-body">
          <PortfolioFormEditor ref="formEditorRef" :is-modal-mode="true" @created="handleCreated" @cancel="closeCreateModal" />
        </div>
      </div>
    </div>

    <!-- 删除确认模态框 -->
    <div v-if="deleteModalVisible" class="modal-overlay" @click.self="closeDeleteModal">
      <div class="modal-content modal-small">
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="btn-close" @click="closeDeleteModal">×</button>
        </div>
        <div class="modal-body">
          <p>确定要删除组合「{{ deletingPortfolio?.name }}」吗？此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="closeDeleteModal">取消</button>
          <button class="btn-danger" @click="handleDelete">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
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
const { getTagClass: getModeColor, getLabel: getModeLabel } = usePortfolioMode()
const { getTagClass: getStateColor, getLabel: getStateLabel } = usePortfolioState()

const searchKeyword = ref('')
const createModalVisible = ref(false)
const deleteModalVisible = ref(false)
const deletingPortfolio = ref<any>(null)
const formEditorRef = ref()
const loadMoreTrigger = ref<HTMLElement>()
const activeMenu = ref<string | null>(null)

// 筛选选项
const filterOptions = [
  { value: '', label: '全部' },
  { value: '0', label: '回测' },
  { value: '1', label: '模拟' },
  { value: '2', label: '实盘' }
]

// 显示的投资组合（后端搜索，前端只做筛选过滤）
const displayPortfolios = computed(() => {
  return filteredPortfolios.value
})

// 颜色类名映射
const getModeColorClass = (mode: number) => {
  const color = getModeColor(mode)
  const colorMap: Record<string, string> = {
    'purple': 'purple',
    'blue': 'blue',
    'green': 'green',
    'orange': 'orange'
  }
  return colorMap[color] || 'blue'
}

const getStateColorClass = (state: number) => {
  const color = getStateColor(state)
  const colorMap: Record<string, string> = {
    'green': 'green',
    'red': 'red',
    'orange': 'orange',
    'blue': 'blue'
  }
  return colorMap[color] || 'blue'
}

// Intersection Observer 用于滚动加载
let observer: IntersectionObserver | null = null

const setupIntersectionObserver = () => {
  nextTick(() => {
    if (!loadMoreTrigger.value) {
      console.log('⚠️ loadMoreTrigger 元素不存在，跳过 observer 设置')
      return
    }

    if (observer) {
      observer.disconnect()
    }

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

const handleSearch = () => {
  fetchPortfolios({ page: 0, append: false, keyword: searchKeyword.value || undefined })
}

const setFilterMode = (value: string) => {
  filterMode.value = value
}

const toggleMenu = (uuid: string) => {
  activeMenu.value = activeMenu.value === uuid ? null : uuid
}

// 关闭下拉菜单（点击外部）
const closeMenus = () => {
  activeMenu.value = null
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
  fetchStats()
  router.push(`/portfolios/${uuid}`)
}

const viewDetail = (record: any) => {
  activeMenu.value = null
  router.push(`/portfolios/${record.uuid}`)
}

const confirmDelete = (record: any) => {
  deletingPortfolio.value = record
  deleteModalVisible.value = true
  activeMenu.value = null
}

const closeDeleteModal = () => {
  deleteModalVisible.value = false
  deletingPortfolio.value = null
}

const handleDelete = async () => {
  if (!deletingPortfolio.value) return
  try {
    await deletePortfolio(deletingPortfolio.value.uuid)
    deleteModalVisible.value = false
    deletingPortfolio.value = null
    fetchPortfolios({ page: 0, append: false })
    fetchStats()
  } catch (e) {
    console.error('删除失败', e)
  }
}

onMounted(() => {
  fetchPortfolios({ page: 0, append: false })
  fetchStats()
  setupIntersectionObserver()
  document.addEventListener('click', closeMenus)
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
  document.removeEventListener('click', closeMenus)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

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
  flex-wrap: wrap;
  gap: 16px;
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
  color: #ffffff;
}

.header-right {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 搜索框 */
.search-box {
  display: flex;
  align-items: center;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  overflow: hidden;
  width: 240px;
}

.search-input {
  flex: 1;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 14px;
  outline: none;
}

.search-input::placeholder {
  color: #8a8a9a;
}

.search-btn {
  padding: 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover {
  color: #ffffff;
}

/* 按钮 */

/* 标签 */

/* 筛选栏 */
.filter-bar {
  margin-bottom: 20px;
}

.radio-group {
  display: inline-flex;
  background: #2a2a3e;
  border-radius: 4px;
  padding: 2px;
}

.radio-button {
  padding: 6px 16px;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: #8a8a9a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.radio-button:hover {
  color: #ffffff;
}

.radio-button.active {
  background: #1890ff;
  color: #ffffff;
}

/* 统计卡片 */

/* 滚动内容区 */
.scrollable-content {
  flex: 1;
  overflow-y: auto;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
  color: #8a8a9a;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
  margin: 0 0 16px 0;
}

/* 组合卡片网格 */
.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.portfolio-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.portfolio-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  transform: translateY(-2px);
  border-color: #3a3a4e;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.card-title .name {
  font-weight: 500;
  color: #ffffff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  min-width: 120px;
  z-index: 100;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.dropdown-item {
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: #3a3a4e;
}

.dropdown-item.danger {
  color: #f5222d;
}

.dropdown-item.danger:hover {
  background: rgba(245, 34, 45, 0.1);
}

.dropdown-divider {
  height: 1px;
  background: #3a3a4e;
  margin: 4px 0;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card-content .desc {
  color: #8a8a9a;
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
  color: #8a8a9a;
}

.metric .value {
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
}

.metric .value.positive {
  color: #52c41a;
}

.metric .value.negative {
  color: #f5222d;
}

.card-footer .date {
  font-size: 12px;
  color: #8a8a9a;
}

/* 模态框 */

.modal-body p {
  color: #ffffff;
  margin: 0;
}

/* 加载更多触发器 */
.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 20px;
  margin-top: 20px;
}

.load-more-trigger .no-more {
  color: #8a8a9a;
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-right {
    width: 100%;
  }

  .search-box {
    width: 100%;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .portfolio-grid {
    grid-template-columns: 1fr;
  }

  .modal-large {
    width: 95%;
  }
}
</style>
