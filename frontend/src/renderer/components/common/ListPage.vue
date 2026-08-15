<template>
  <!-- 列表页壳:基于 PageLayout 组合(header/title/actions/filters 复用统一外壳),
       自持滚动容器 list-content(表头 sticky 恒贴 header 下,不随整页滚) -->
  <PageLayout>
    <template #title>
      {{ title }}
      <slot name="tag" />
    </template>

    <template #actions>
      <div v-if="searchable" class="search-box">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <input
          :value="searchValue"
          type="text"
          :placeholder="searchPlaceholder"
          class="search-input"
          @input="$emit('update:searchValue', ($event.target as HTMLInputElement).value)"
        />
        <button v-if="searchValue" class="clear-btn" @click="$emit('update:searchValue', '')">
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <button v-if="creatable" class="btn-primary" @click="$emit('create')">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        {{ createLabel }}
      </button>
      <slot name="header-actions" />
    </template>

    <template v-if="$slots.filters" #filters>
      <slot name="filters" />
    </template>

    <!-- 统计条(固定不随表格滚动,PortfolioList 在用) -->
    <div v-if="$slots.stats" class="list-stats">
      <slot name="stats" />
    </div>

    <!-- 可滚动内容区 -->
    <div class="list-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
      </div>

      <!-- 列表加载失败:区别于空态,提供重试 -->
      <div v-else-if="errorText" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <p class="error-text">{{ errorText }}</p>
        <button class="btn-primary" @click="$emit('retry')">重试</button>
      </div>

      <!-- 空状态 -->
      <div v-else-if="isEmpty && !$slots.default" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <path d="m21 15-5-5L5 21"></path>
        </svg>
        <p>{{ emptyText }}</p>
        <button v-if="creatable" class="btn-primary" @click="$emit('create')">{{ emptyActionText }}</button>
      </div>

      <!-- 自定义内容 (替换表格) -->
      <slot v-else-if="$slots.default" />

      <!-- 数据表格 (默认) -->
      <div v-else class="table-card">
        <table class="pro-table">
          <thead>
            <tr>
              <th
                v-for="col in resolvedColumns"
                :key="col.key"
                :style="{ width: col.width ? col.width + 'px' : undefined }"
                :class="{ sortable: col.sortable }"
                @click="col.sortable && handleSort(col.dataIndex)"
              >
                {{ col.title }}
                <span v-if="col.sortable" class="sort-icon">
                  <template v-if="innerSortBy === col.dataIndex">
                    {{ innerSortOrder === 'asc' ? '↑' : '↓' }}
                  </template>
                  <template v-else>⇅</template>
                </span>
              </th>
            </tr>
          </thead>
          <tbody class="m-stagger">
            <tr
              v-for="(record, idx) in pageData"
              :key="record[rowKey] || idx"
              :class="{ clickable: clickable }"
              @click="$emit('rowClick', record)"
              @contextmenu="onRowContextMenu($event, record, idx)"
            >
              <td v-for="col in resolvedColumns" :key="col.key">
                <!-- 操作列:flex 容器给按钮间距,避免多按钮紧贴 -->
                <div v-if="col.key === '__actions'" class="actions-cell">
                  <slot name="actions" :record="record" :index="idx" />
                </div>
                <!-- 自定义列 -->
                <template v-else-if="$slots[col.key]">
                  <slot :name="col.key" :record="record" :index="idx" />
                </template>
                <!-- 默认渲染 -->
                <template v-else>
                  {{ formatValue(record[col.dataIndex]) }}
                </template>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div v-if="totalCount > 0 && !infiniteScroll" class="pagination-bar">
          <div class="pagination-info">
            共 {{ totalCount }} 条{{ totalPages > 1 ? `，第 ${innerPage} / ${totalPages} 页` : '' }}
          </div>
          <div v-if="totalPages > 1" class="pagination-controls">
            <button class="pg-btn" :disabled="innerPage <= 1" @click="goPage(1)">«</button>
            <button class="pg-btn" :disabled="innerPage <= 1" @click="goPage(innerPage - 1)">‹</button>
            <template v-for="p in visiblePages" :key="p">
              <span v-if="p === '...'" class="pg-ellipsis">…</span>
              <button v-else class="pg-btn" :class="{ active: p === innerPage }" @click="goPage(p as number)">{{ p }}</button>
            </template>
            <button class="pg-btn" :disabled="innerPage >= totalPages" @click="goPage(innerPage + 1)">›</button>
            <button class="pg-btn" :disabled="innerPage >= totalPages" @click="goPage(totalPages)">»</button>
            <select v-model.number="innerPageSize" class="pg-size">
              <option v-for="s in pageSizes" :key="s" :value="s">{{ s }} 条/页</option>
            </select>
          </div>
        </div>

      </div>

      <!-- 无限滚动触发器插槽（在 list-content 内、table-card 外） -->
      <slot name="afterTable" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import PageLayout from './PageLayout.vue'
import { useContextMenu, type MenuItem } from '@/composables/useContextMenu'

export interface Column {
  title: string
  dataIndex: string
  key?: string
  width?: number
  sortable?: boolean
}

const props = withDefaults(defineProps<{
  title: string
  columns: Column[]
  dataSource: any[]
  loading?: boolean
  rowKey?: string
  searchable?: boolean
  searchPlaceholder?: string
  searchValue?: string
  creatable?: boolean
  createLabel?: string
  emptyText?: string
  emptyActionText?: string
  errorText?: string
  clickable?: boolean
  showActions?: boolean
  total?: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
  serverPagination?: boolean
  infiniteScroll?: boolean
  /** 行右键菜单构建器:返回菜单项数组;不传则不接管行右键 */
  contextMenu?: (record: any, index: number) => MenuItem[]
}>(), {
  loading: false,
  rowKey: 'id',
  searchable: true,
  searchPlaceholder: '搜索...',
  searchValue: '',
  creatable: true,
  createLabel: '新建',
  emptyText: '暂无数据',
  emptyActionText: '创建第一个',
  errorText: '',
  clickable: false,
  showActions: false,
  page: 1,
  pageSize: 20,
  pageSizes: () => [10, 20, 50, 100],
  serverPagination: false,
  infiniteScroll: false,
})

const emit = defineEmits<{
  retry: []
  create: []
  'update:searchValue': [value: string]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  sort: [field: string, order: 'asc' | 'desc']
  rowClick: [record: any]
}>()

const innerPage = ref(props.page)
const innerPageSize = ref(props.pageSize)
const innerSortBy = ref('')
const innerSortOrder = ref<'asc' | 'desc'>('desc')

// 行右键:页面传 contextMenu 构建器即可获得 OS 风格菜单(与组合页卡片同套基建)
const { open: openCtx } = useContextMenu()
function onRowContextMenu(e: MouseEvent, record: any, idx: number) {
  if (!props.contextMenu) return
  openCtx(e, props.contextMenu(record, idx))
}

watch(() => props.page, v => { innerPage.value = v })

const totalCount = computed(() => props.total ?? props.dataSource.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / innerPageSize.value)))

const isEmpty = computed(() => !props.loading && props.dataSource.length === 0)

const resolvedColumns = computed(() => {
  const cols = props.columns.map(c => ({ ...c, key: c.key || c.dataIndex }))
  if (props.showActions) {
    cols.push({ title: '操作', dataIndex: '', key: '__actions', width: 120 })
  }
  return cols
})

// Client-side pagination (infiniteScroll always shows all data)
const pageData = computed(() => {
  if (props.serverPagination || props.total != null || props.infiniteScroll) return props.dataSource
  const start = (innerPage.value - 1) * innerPageSize.value
  return props.dataSource.slice(start, start + innerPageSize.value)
})

// Visible page numbers
const visiblePages = computed(() => {
  const pages: (number | string)[] = []
  const tp = totalPages.value
  const cp = innerPage.value
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pages.push(i)
  } else {
    pages.push(1)
    if (cp > 3) pages.push('...')
    for (let i = Math.max(2, cp - 1); i <= Math.min(tp - 1, cp + 1); i++) pages.push(i)
    if (cp < tp - 2) pages.push('...')
    pages.push(tp)
  }
  return pages
})

function goPage(p: number) {
  p = Math.max(1, Math.min(p, totalPages.value))
  if (p === innerPage.value) return
  innerPage.value = p
  emit('update:page', p)
}

watch(innerPageSize, (newSize, oldSize) => {
  if (newSize !== oldSize) {
    innerPage.value = 1
    emit('update:page', 1)
    emit('update:pageSize', newSize)
  }
})

function handleSort(field: string) {
  if (innerSortBy.value === field) {
    innerSortOrder.value = innerSortOrder.value === 'desc' ? 'asc' : 'desc'
  } else {
    innerSortBy.value = field
    innerSortOrder.value = 'desc'
  }
  innerPage.value = 1
  emit('update:page', 1)
  emit('sort', field, innerSortOrder.value)
}

function formatValue(val: any): string {
  if (val == null) return '-'
  if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T/)) {
    return new Date(val).toLocaleString('zh-CN')
  }
  return String(val)
}
</script>

<style scoped>
/* header/title/actions/filters 外壳样式由 PageLayout 统一提供,此处仅列表特有样式 */

.list-stats {
  flex-shrink: 0;
  margin-bottom: 16px;
}

/* Search */
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  /* 与 .btn-primary(buttons.less) 同高同圆角:30px/4px */
  border-radius: var(--radius-sm);
  height: 30px;
  padding: 0 12px;
  box-sizing: border-box;
  width: 220px;
}

.search-box svg { color: hsl(var(--muted-foreground)); flex-shrink: 0; }

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: hsl(var(--foreground));
  font-size: 14px;
  outline: none;
}

.search-input::placeholder { color: hsl(var(--muted-foreground)); }

.clear-btn {
  padding: 2px;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  display: flex;
  align-items: center;
}

.clear-btn:hover { color: hsl(var(--foreground)); }

/* Buttons */

/* Content */
.list-content {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  color: hsl(var(--muted-foreground));
}

.empty-state svg { opacity: 0.3; margin-bottom: 16px; }
.empty-state p { margin: 0 0 16px; font-size: 14px; }
.empty-state .error-text { color: hsl(var(--error)); }

/* Table: 表格样式全局权威在 styles/tables.less(.table-card/.pro-table) */

/* Pagination */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid hsl(var(--border));
}

.pagination-info { font-size: 13px; color: hsl(var(--muted-foreground)); }

.pagination-controls {
  display: flex;
  gap: 4px;
  align-items: center;
}

.pg-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pg-btn:hover:not(:disabled):not(.active) { background: hsl(var(--secondary)); border-color: hsl(var(--primary)); }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pg-btn.active { background: hsl(var(--primary)); border-color: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }

.pg-ellipsis { padding: 0 4px; color: hsl(var(--muted-foreground)); font-size: 12px; }

.pg-size {
  margin-left: 8px;
  padding: 4px 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
  cursor: pointer;
}

.pg-size:focus { outline: none; border-color: hsl(var(--primary)); }
</style>
