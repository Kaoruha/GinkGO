<template>
  <ListPage
    title="投资组合"
    :columns="[]"
    :data-source="displayPortfolios"
    :loading="loading"
    row-key="uuid"
    :searchable="true"
    :search-value="searchKeyword"
    search-placeholder="搜索组合名称..."
    :creatable="true"
    create-label="创建组合"
    empty-text="暂无投资组合"
    empty-action-text="创建第一个组合"
    @update:search-value="onSearch"
    @create="showCreateModal"
  >
    <template #tag>
      <span class="tag tag-purple">{{ total }} 个组合</span>
    </template>

    <template #filters>
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
    </template>

    <template #stats>
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
    </template>

    <!-- 自定义内容: 卡片网格 -->
    <template #default>
      <div v-if="displayPortfolios.length === 0 && !loading" class="empty-state">
        <div class="empty-icon">📊</div>
        <p class="empty-text">暂无投资组合</p>
        <button class="btn-primary" @click="showCreateModal">创建第一个组合</button>
      </div>
      <template v-else>
        <div class="portfolio-grid">
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
        <div v-if="displayPortfolios.length > 0" ref="loadMoreTrigger" class="load-more-trigger">
          <div v-if="loadingMore" class="spinner spinner-small"></div>
          <div v-else-if="!hasMore" class="no-more">没有更多了</div>
        </div>
      </template>
    </template>
  </ListPage>

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
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import { usePortfolioMode, usePortfolioState } from '@/composables'
import { formatMoney } from '@/utils/format'
import ListPage from '@/components/common/ListPage.vue'
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

const { getTagClass: getModeColor, getLabel: getModeLabel } = usePortfolioMode()
const { getTagClass: getStateColor, getLabel: getStateLabel } = usePortfolioState()

const searchKeyword = ref('')
const createModalVisible = ref(false)
const deleteModalVisible = ref(false)
const deletingPortfolio = ref<any>(null)
const formEditorRef = ref()
const loadMoreTrigger = ref<HTMLElement>()
const activeMenu = ref<string | null>(null)

const filterOptions = [
  { value: '', label: '全部' },
  { value: '0', label: '回测' },
  { value: '1', label: '模拟' },
  { value: '2', label: '实盘' }
]

const displayPortfolios = computed(() => filteredPortfolios.value)

const getModeColorClass = (mode: number) => {
  const map: Record<string, string> = { purple: 'purple', blue: 'blue', green: 'green', orange: 'orange' }
  return map[getModeColor(mode)] || 'blue'
}

const getStateColorClass = (state: number) => {
  const map: Record<string, string> = { green: 'green', red: 'red', orange: 'orange', blue: 'blue' }
  return map[getStateColor(state)] || 'blue'
}

let observer: IntersectionObserver | null = null

const setupIntersectionObserver = () => {
  nextTick(() => {
    if (!loadMoreTrigger.value) return
    if (observer) observer.disconnect()
    const scrollableContainer = document.querySelector('.list-content')
    if (!scrollableContainer) return
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore.value && !loading.value && !loadingMore.value) {
          loadMore()
        }
      },
      { root: scrollableContainer as Element, rootMargin: '100px', threshold: 0.1 }
    )
    observer.observe(loadMoreTrigger.value)
  })
}

const loadMore = async () => {
  if (!hasMore.value || loading.value || loadingMore.value) return
  await fetchPortfolios({ append: true })
}

watch(filterMode, () => fetchPortfolios({ page: 0, append: false }))

let searchTimer: ReturnType<typeof setTimeout> | null = null
const onSearch = (val: string) => {
  searchKeyword.value = val
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchPortfolios({ page: 0, append: false, keyword: val || undefined })
  }, 500)
}

watch(displayPortfolios, (newVal) => {
  if (newVal.length > 0 && !observer) setupIntersectionObserver()
})

const formatPercentValue = (val: number | undefined) => ((val || 0) * 100).toFixed(2) + '%'
const formatShortDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const setFilterMode = (value: string) => { filterMode.value = value }
const toggleMenu = (uuid: string) => { activeMenu.value = activeMenu.value === uuid ? null : uuid }
const closeMenus = () => { activeMenu.value = null }

const showCreateModal = () => { createModalVisible.value = true }
const closeCreateModal = () => { createModalVisible.value = false }

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
  if (observer) observer.disconnect()
  document.removeEventListener('click', closeMenus)
})
</script>

<style scoped>
/* Stats */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #fff;
}

.stat-value.stat-success { color: #52c41a; }
.stat-label { font-size: 12px; color: #8a8a9a; margin-top: 4px; }

/* Filter */
.filter-bar { margin-top: 12px; }

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

.radio-button:hover { color: #fff; }
.radio-button.active { background: #1890ff; color: #fff; }

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-purple { background: rgba(114,46,209,0.15); color: #b37feb; }
.tag-blue { background: rgba(24,144,255,0.15); color: #69c0ff; }
.tag-green { background: rgba(82,196,26,0.15); color: #95de64; }
.tag-orange { background: rgba(250,173,20,0.15); color: #ffc53d; }
.tag-red { background: rgba(245,34,45,0.15); color: #ff7875; }

/* Card grid */
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
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  transform: translateY(-2px);
  border-color: #3a3a4e;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
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
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-actions { position: relative; }

.btn-icon {
  padding: 4px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
}

.btn-icon:hover { color: #fff; background: #2a2a3e; }

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
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.dropdown-item {
  width: 100%;
  padding: 8px 12px;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}

.dropdown-item:hover { background: #3a3a4e; }
.dropdown-item.danger { color: #f5222d; }
.dropdown-item.danger:hover { background: rgba(245,34,45,0.1); }
.dropdown-divider { height: 1px; background: #3a3a4e; margin: 4px 0; }

.card-content { display: flex; flex-direction: column; gap: 12px; }
.card-content .desc { color: #8a8a9a; font-size: 13px; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.metrics { display: flex; gap: 24px; }
.metric { display: flex; flex-direction: column; }
.metric .label { font-size: 12px; color: #8a8a9a; }
.metric .value { font-size: 16px; font-weight: 500; color: #fff; }
.metric .value.positive { color: #52c41a; }
.metric .value.negative { color: #f5222d; }

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-footer .date { font-size: 12px; color: #8a8a9a; }

/* Empty */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px;
  color: #8a8a9a;
}

.empty-icon { font-size: 48px; margin-bottom: 16px; }
.empty-text { font-size: 14px; margin: 0 0 16px 0; }

/* Load more */
.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 20px;
  margin-top: 20px;
}

.no-more { color: #8a8a9a; font-size: 14px; }

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
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

.modal-large { width: 700px; }
.modal-small { width: 420px; }

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 { margin: 0; color: #fff; font-size: 16px; }
.btn-close { background: none; border: none; color: #8a8a9a; font-size: 20px; cursor: pointer; }
.btn-close:hover { color: #fff; }

.modal-body { padding: 20px; overflow-y: auto; flex: 1; }
.modal-body p { color: #fff; margin: 0; }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
}

.btn-secondary {
  padding: 8px 16px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.btn-secondary:hover { background: #3a3a4e; }

.btn-danger {
  padding: 8px 16px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #fff;
  cursor: pointer;
}

.btn-danger:hover { background: #ff4d4f; }

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary:hover { background: #40a9ff; }

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
  .portfolio-grid { grid-template-columns: 1fr; }
}
</style>
