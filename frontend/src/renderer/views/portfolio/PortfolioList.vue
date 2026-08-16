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
    :infinite-scroll="true"
    :loading-more="loadingMore"
    :has-more="hasMore"
    @update:search-value="onSearch"
    @create="showCreateModal"
    @load-more="loadMore"
  >
    <template #tag>
      <span class="tag tag-purple">{{ total }} 个组合</span>
    </template>

    <template #filters>
      <div class="filter-bar">
        <SegmentedControl
          :model-value="filterMode"
          :options="filterOptions"
          @update:model-value="setFilterMode"
        />
        <SegmentedControl
          :model-value="viewMode"
          :options="viewOptions"
          @update:model-value="setViewMode"
        />
      </div>
    </template>

    <template #stats>
      <div class="stats-inline">
        <span class="stat-item">共 <strong>{{ stats.total }}</strong> 个组合</span>
        <span class="stat-sep">·</span>
        <span class="stat-item">运行中 <strong class="text-success">{{ stats.running }}</strong></span>
        <span class="stat-sep">·</span>
        <span class="stat-item">平均净值 <strong>{{ stats.avgNetValue?.toFixed(3) || '-' }}</strong></span>
        <span class="stat-sep">·</span>
        <span class="stat-item">总资产 <strong>{{ formatMoney(stats.totalAssets) }}</strong></span>
        <template v-if="showCtxHint">
          <span class="stat-sep">·</span>
          <span class="stat-item ctx-hint">💡 右键卡片/行可操作</span>
        </template>
      </div>
    </template>

    <!-- 自定义内容: 卡片网格 -->
    <template #default>
      <EmptyState
        v-if="displayPortfolios.length === 0 && !loading"
        title="暂无投资组合"
        description="创建第一个组合,开始回测验证策略"
        action-text="创建第一个组合"
        :on-action="showCreateModal"
      />
      <!-- 列表视图:复用全局 .pro-table(styles/tables.less),与其他列表页视觉一致 -->
      <div
        v-else-if="viewMode === 'table'"
        class="table-card"
      >
        <table class="pro-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>模式</th>
              <th>状态</th>
              <th class="col-num">
                {{ firstMetricLabel }}
              </th>
              <th class="col-num">
                Sharpe
              </th>
              <th class="col-num">
                最大回撤
              </th>
              <th class="col-num">
                胜率
              </th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody class="m-stagger">
            <tr
              v-for="portfolio in displayPortfolios"
              :key="portfolio.uuid"
              data-testid="portfolio-row"
              class="clickable"
              :title="portfolio.uuid"
              @click="viewDetail(portfolio)"
              @contextmenu="openPortfolioMenu($event, portfolio)"
            >
              <td class="cell-name">
                {{ portfolio.name }}
              </td>
              <td>
                <span
                  class="tag"
                  :class="`tag-${getModeColorClass(portfolio.mode)}`"
                >{{ formatMode(portfolio.mode) }}</span>
              </td>
              <td>
                <span
                  class="status-dot"
                  :class="getStateDotClass(portfolio.state)"
                />
                {{ formatState(portfolio.state) }}
              </td>
              <td
                class="col-num"
                :class="getValueClass(portfolio.annual_return)"
              >
                {{ formatPercent(portfolio.annual_return) }}
              </td>
              <td
                class="col-num"
                :class="getSharpeClass(portfolio.sharpe_ratio)"
              >
                {{ formatDecimal(portfolio.sharpe_ratio) }}
              </td>
              <td class="col-num negative">
                {{ formatDrawdown(portfolio.max_drawdown) }}
              </td>
              <td
                class="col-num"
                :class="getWinRateClass(portfolio.win_rate)"
              >
                {{ formatPercent(portfolio.win_rate) }}
              </td>
              <td @click.stop>
                <div class="actions-cell">
                  <button
                    v-if="portfolio.mode === 0 || portfolio.mode === 'BACKTEST'"
                    class="deploy-link"
                    @click="openDeploy(portfolio)"
                  >
                    部署
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <template v-else>
        <div class="portfolio-grid">
          <div
            v-for="portfolio in displayPortfolios"
            :key="portfolio.uuid"
            class="portfolio-card"
            data-testid="portfolio-card"
            :title="portfolio.uuid"
            @click="viewDetail(portfolio)"
            @contextmenu="openPortfolioMenu($event, portfolio)"
          >
            <div class="card-header">
              <div class="card-title">
                <span class="name">{{ portfolio.name }}</span>
                <div class="card-tags">
                  <span
                    class="tag"
                    :class="`tag-${getModeColorClass(portfolio.mode)}`"
                  >{{ formatMode(portfolio.mode) }}</span>
                  <span
                    class="tag"
                    :class="`tag-${getStateColorClass(portfolio.state)}`"
                  >{{ formatState(portfolio.state) }}</span>
                </div>
              </div>
            </div>

            <div class="card-body">
              <div class="metric-primary">
                <span class="label">{{ getReturnLabel(portfolio.mode) }}</span>
                <span
                  class="value"
                  :class="getValueClass(portfolio.annual_return)"
                >
                  {{ formatPercent(portfolio.annual_return) }}
                </span>
              </div>
              <div class="metrics-grid">
                <div class="metric">
                  <span class="label">Sharpe</span>
                  <span
                    class="value"
                    :class="getSharpeClass(portfolio.sharpe_ratio)"
                  >
                    {{ formatDecimal(portfolio.sharpe_ratio) }}
                  </span>
                </div>
                <div class="metric">
                  <span class="label">最大回撤</span>
                  <span class="value negative">
                    {{ formatDrawdown(portfolio.max_drawdown) }}
                  </span>
                </div>
                <div class="metric">
                  <span class="label">胜率</span>
                  <span
                    class="value"
                    :class="getWinRateClass(portfolio.win_rate)"
                  >
                    {{ formatPercent(portfolio.win_rate) }}
                  </span>
                </div>
              </div>
              <div class="info-row">
                <span class="info-item">净值 <strong>{{ portfolio.net_value?.toFixed(4) ?? '--' }}</strong></span>
                <span class="info-item">初始资金 <strong>{{ formatMoney(portfolio.initial_cash) }}</strong></span>
              </div>
            </div>
            <div class="card-footer">
              <button
                v-if="portfolio.mode === 0 || portfolio.mode === 'BACKTEST'"
                class="deploy-link"
                @click.stop="openDeploy(portfolio)"
              >
                部署 →
              </button>
              <span
                v-else
                class="footer-spacer"
              />
              <span class="date">{{ formatShortDate(portfolio.created_at) }}</span>
            </div>
            <div
              v-if="portfolio.related && portfolio.related.length > 0"
              class="related-bar"
            >
              <div
                v-for="rel in portfolio.related"
                :key="rel.uuid"
                class="related-card"
                :class="`related-${rel.mode.toLowerCase()}`"
                @click.stop="viewDetail({ uuid: rel.uuid })"
              >
                <div class="related-header">
                  <span class="related-mode">{{ formatRelatedMode(rel.mode) }}</span>
                  <span
                    v-if="rel.state"
                    class="related-state"
                  >{{ rel.state }}</span>
                </div>
                <div class="related-metrics">
                  <span>收益 <strong :class="getValueClass(rel.annual_return)">{{ formatPercent(rel.annual_return) }}</strong></span>
                  <span>回撤 <strong class="negative">{{ formatDrawdown(rel.max_drawdown) }}</strong></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </ListPage>

  <!-- 创建组合模态框 -->
  <FormModal
    v-model:open="createModalVisible"
    title="创建投资组合"
    size="xl"
    hide-footer
    :close-on-overlay="false"
  >
    <div data-testid="create-portfolio-modal">
      <PortfolioFormEditor
        ref="formEditorRef"
        :is-modal-mode="true"
        @created="handleCreated"
        @cancel="closeCreateModal"
      />
    </div>
  </FormModal>

  <!-- 删除确认模态框 -->
  <FormModal
    v-model:open="deleteModalVisible"
    title="确认删除"
    size="sm"
    :loading="deleting"
    loading-text="删除中..."
    @cancel="closeDeleteModal"
    @submit="handleDelete"
  >
    <p>确定要删除组合「{{ deletingPortfolio?.name }}」吗？此操作不可恢复。</p>
    <template #footer>
      <button
        type="button"
        class="btn-secondary"
        :disabled="deleting"
        @click="closeDeleteModal"
      >
        取消
      </button>
      <button
        type="submit"
        class="btn-danger"
        :disabled="deleting"
      >
        {{ deleting ? '删除中...' : '删除' }}
      </button>
    </template>
  </FormModal>

  <!-- 部署模态框 -->
  <DeployModal
    v-if="deployingPortfolio"
    v-model:visible="showDeployModal"
    :portfolio-id="deployingPortfolio.uuid"
    @success="onDeploySuccess"
  />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePortfolioStore } from '@/stores/portfolio'
import { storeToRefs } from 'pinia'
import { usePortfolioMode, usePortfolioState, useContextMenu, useAsyncAction } from '@/composables'
import { formatMoney } from '@/utils/format'
import ListPage from '@/components/common/ListPage.vue'
import FormModal from '@/components/common/FormModal.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import PortfolioFormEditor from './PortfolioFormEditor.vue'
import DeployModal from '@/components/business/DeployModal.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { message } from '@/utils/toast'

const router = useRouter()
const portfolioStore = usePortfolioStore()
const {
  loading,
  loadingMore,
  filterMode,
  stats,
  filteredPortfolios,
  hasMore,
  total
} = storeToRefs(portfolioStore)
const { fetchPortfolios, fetchStats, deletePortfolio } = portfolioStore

const { getTagClass: getModeColor, getLabel: _getModeLabel } = usePortfolioMode()
const { getTagClass: getStateColor, getLabel: _getStateLabel } = usePortfolioState()

const formatMode = (mode: number | string) => _getModeLabel(mode as number)
const formatState = (state: number | string) => _getStateLabel(state as number)

const searchKeyword = ref('')
const createModalVisible = ref(false)
const deleteModalVisible = ref(false)
const deletingPortfolio = ref<any>(null)
const formEditorRef = ref()

const showDeployModal = ref(false)
const deployingPortfolio = ref<any>(null)

// 右键菜单(OS 风格,替代原三点 dropdown);首次使用前给一次性可发现性提示
const { open: openCtx } = useContextMenu()
const showCtxHint = ref(!localStorage.getItem('ginkgo_ctx_hint_done'))

const openDeploy = (portfolio: any) => {
  deployingPortfolio.value = portfolio
  showDeployModal.value = true
}

const onDeploySuccess = (newPortfolioId: string) => {
  fetchPortfolios({ page: 0, append: false })
  fetchStats()
  if (newPortfolioId) {
    router.push(`/portfolios/${newPortfolioId}`)
  }
}

const filterOptions = [
  { key: '', label: '全部' },
  { key: 'BACKTEST', label: '回测' },
  { key: 'PAPER', label: '模拟' },
  { key: 'LIVE', label: '实盘' }
]

/** 视图切换:卡片网格 / 表格行 */
const viewMode = ref<'card' | 'table'>('card')
const viewOptions = [
  { key: 'card', label: '卡片' },
  { key: 'table', label: '列表' }
]
const setViewMode = (v: string) => { viewMode.value = v as 'card' | 'table' }

/** 列表视图首列收益指标文案:混合模式下取通用词 */
const firstMetricLabel = computed(() =>
  displayPortfolios.value.some(p => String(p.mode).toUpperCase() !== 'BACKTEST' && p.mode !== 0)
    ? '收益'
    : '年化收益'
)

/** 状态点样式(复用全局 .status-dot 呼吸动画) */
const getStateDotClass = (state: number | string) => {
  const s = String(state).toUpperCase()
  if (s === 'RUNNING' || s === '1') return 'running'
  if (s === 'ERROR' || s === '4') return 'error'
  return 'stopped'
}

const displayPortfolios = computed(() => filteredPortfolios.value)

const getModeColorClass = (mode: number | string) => {
  const map: Record<string, string> = { purple: 'purple', blue: 'blue', green: 'green', orange: 'orange' }
  return map[getModeColor(mode as any)] || 'blue'
}

const getStateColorClass = (state: number | string) => {
  const map: Record<string, string> = { green: 'green', red: 'red', orange: 'orange', blue: 'blue' }
  return map[getStateColor(state as any)] || 'blue'
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

const formatShortDate = (dateStr: string) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const getReturnLabel = (mode: any) => {
  const m = typeof mode === 'string' ? mode.toUpperCase() : mode
  return m === 'BACKTEST' || m === 0 || m === '0' ? '年化收益' : '累计收益'
}

// 0 是有效值须显示(原实现 val===0 返回 '--',0% 收益被吞);仅 null/undefined/NaN 显示占位
const formatPercent = (val: any) => {
  if (val === null || val === undefined) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  const sign = n > 0 ? '+' : ''
  return `${sign}${(n * 100).toFixed(2)}%`
}

const formatDecimal = (val: any) => {
  if (val === null || val === undefined) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  return n.toFixed(2)
}

const formatDrawdown = (val: any) => {
  if (val === null || val === undefined) return '--'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n)) return '--'
  return `-${(Math.abs(n) * 100).toFixed(1)}%`
}

const getValueClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  return n > 0 ? 'positive' : 'negative'
}

const getSharpeClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  if (n < 0.5) return 'warning'
  return n > 0 ? 'positive' : 'negative'
}

const getWinRateClass = (val: any) => {
  if (val === null || val === undefined) return 'neutral'
  const n = typeof val === 'string' ? parseFloat(val) : val
  if (isNaN(n) || n === 0) return 'neutral'
  return n >= 0.5 ? 'positive' : 'warning'
}

const formatRelatedMode = (mode: string) => {
  const map: Record<string, string> = {
    'BACKTEST': '来源回测',
    'PAPER': '模拟',
    'LIVE': '实盘',
  }
  return map[mode] || mode
}

const setFilterMode = (value: string) => { filterMode.value = value }

/** 卡片/表格行右键菜单:详情/部署/删除(替代三点菜单交互) */
const openPortfolioMenu = (e: MouseEvent, portfolio: any) => {
  if (!localStorage.getItem('ginkgo_ctx_hint_done')) {
    localStorage.setItem('ginkgo_ctx_hint_done', '1')
    showCtxHint.value = false
  }
  const isBacktest = portfolio.mode === 0 || portfolio.mode === 'BACKTEST'
  openCtx(e, [
    { label: '详情', action: () => viewDetail(portfolio) },
    ...(isBacktest ? [{ label: '部署', action: () => openDeploy(portfolio) }] : []),
    { divider: true },
    { label: '删除', danger: true, action: () => confirmDelete(portfolio) },
  ])
}

const showCreateModal = () => { createModalVisible.value = true }
const closeCreateModal = () => { createModalVisible.value = false }

const handleCreated = (uuid: string) => {
  createModalVisible.value = false
  fetchPortfolios({ page: 0, append: false })
  fetchStats()
  router.push(`/portfolios/${uuid}`)
}

const viewDetail = (record: any) => {
  router.push(`/portfolios/${record.uuid}`)
}

const confirmDelete = (record: any) => {
  const mode = record.mode
  const state = record.state
  if ((mode === 1 || mode === 2) && (state === 1 || state === 3)) {
    message.warning('请先停止该组合后再删除')
    return
  }
  deletingPortfolio.value = record
  deleteModalVisible.value = true
}

const closeDeleteModal = () => {
  deleteModalVisible.value = false
  deletingPortfolio.value = null
}

const handleDelete = () => {
  if (!deletingPortfolio.value) return
  runDelete()
}

const { running: deleting, run: runDelete } = useAsyncAction(async () => {
  const target = deletingPortfolio.value
  if (!target) return
  await deletePortfolio(target.uuid)
}, {
  success: '删除成功',
  onSuccess: () => {
    deleteModalVisible.value = false
    deletingPortfolio.value = null
    fetchPortfolios({ page: 0, append: false })
    fetchStats()
  },
})

onMounted(() => {
  fetchPortfolios({ page: 0, append: false })
  fetchStats()
})
</script>

<style scoped>
/* Stats: 单行内联统计(原 4 张大卡与 Dashboard 重复且占屏 30%) */
.stats-inline {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.stats-inline strong {
  color: hsl(var(--foreground));
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stats-inline .text-success { color: hsl(var(--success-fg)); }
.stats-inline .stat-sep { opacity: 0.5; }

/* Filter:模式筛选居左,视图切换居右 */
.filter-bar {
  margin-top: 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* 列表视图:结构/样式复用全局 .pro-table,此处仅页面特有细节 */
.pro-table .cell-name {
  font-weight: 600;
  max-width: 260px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pro-table td.negative { color: hsl(var(--error-fg)); }
.pro-table td.positive { color: hsl(var(--success-fg)); }
.pro-table td.warning { color: hsl(var(--warning-fg)); }
.pro-table td.neutral { color: hsl(var(--muted-foreground)); }

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}


/* Card grid */
.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.portfolio-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  flex-direction: column;
}

.portfolio-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
  border-color: hsl(var(--secondary));
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.card-title {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}

.card-title .name {
  font-size: 15px;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-tags {
  display: flex;
  gap: 6px;
}

/* 右键交互一次性提示(首次右键后消失,localStorage 记忆) */
.ctx-hint { color: hsl(var(--primary)); }

.card-body { display: flex; flex-direction: column; gap: 10px; flex: 1; }

/* 主指标:收益大号突出 */
.metric-primary { display: flex; flex-direction: column; gap: 2px; }
.metric-primary .label { font-size: 11px; color: hsl(var(--muted-foreground)); }
.metric-primary .value { font-size: 22px; font-weight: 700; line-height: 1.2; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px 12px;
  padding: 8px 10px;
  background: hsl(var(--muted) / 0.4);
  border-radius: var(--radius);
}

.metrics-grid .metric { display: flex; flex-direction: column; gap: 2px; }
.metrics-grid .metric .label { font-size: 11px; color: hsl(var(--muted-foreground)); }
.metrics-grid .metric .value { font-size: 15px; font-weight: 700; }

.info-row {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.info-row .info-item strong {
  color: hsl(var(--foreground));
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.value.positive { color: hsl(var(--success-fg)); }
.value.negative { color: hsl(var(--error-fg)); }
.value.warning { color: hsl(var(--warning-fg)); }
.value.neutral { color: hsl(var(--muted-foreground)); }

.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid hsl(var(--border));
}

/* 部署是回测组合的高频主操作,从三点菜单提升为卡上入口 */
.deploy-link {
  background: transparent;
  border: none;
  padding: 0;
  color: hsl(var(--primary));
  font-size: 13px;
  cursor: pointer;
}

.deploy-link:hover { text-decoration: underline; }

.footer-spacer { flex: 1; }

.card-footer .date { font-size: 12px; color: hsl(var(--muted-foreground)); margin-left: auto; }

.related-bar {
  display: flex;
  gap: 8px;
  padding: 8px 0 0;
  border-top: 1px solid hsl(var(--secondary));
  margin-top: 8px;
}

.related-card {
  flex: 1;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: opacity 0.2s;
}

.related-card:hover { opacity: 0.8; }

.related-backtest { background: hsl(var(--background)); border: 1px solid hsl(var(--border)); }
.related-paper { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); }
.related-live { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); }

.related-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.related-mode { font-size: 12px; font-weight: 600; }
.related-backtest .related-mode { color: hsl(var(--primary)); }
.related-paper .related-mode { color: hsl(var(--warning-fg)); }
.related-live .related-mode { color: hsl(var(--success-fg)); }

.related-state { font-size: 11px; color: hsl(var(--success-fg)); }

.related-metrics {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.related-metrics strong { font-size: 12px; }

/* 弹窗/按钮走全局 modals.less + buttons.less;加载态/sentinel 由 ListPage 持有 */

@media (max-width: 768px) {
  .portfolio-grid { grid-template-columns: 1fr; }
}
</style>
