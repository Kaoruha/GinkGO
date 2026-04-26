<template>
  <div class="list-page">
    <!-- 固定头部 -->
    <div class="list-header">
      <div class="header-row">
        <div class="header-left">
          <h1 class="page-title">{{ title }}</h1>
          <slot name="tag" />
        </div>
        <div class="header-right">
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
        </div>
      </div>

      <div v-if="$slots.filters" class="filter-bar">
        <slot name="filters" />
      </div>

      <div v-if="$slots.stats" class="stats-area">
        <slot name="stats" />
      </div>
    </div>

    <!-- 可滚动内容区 -->
    <div class="list-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="spinner"></div>
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
                  <template v-if="sortBy === col.dataIndex">
                    {{ sortOrder === 'asc' ? '↑' : '↓' }}
                  </template>
                  <template v-else>⇅</template>
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(record, idx) in pageData"
              :key="record[rowKey] || idx"
              :class="{ clickable: clickable }"
              @click="$emit('rowClick', record)"
            >
              <td v-for="col in resolvedColumns" :key="col.key">
                <!-- 操作列 -->
                <template v-if="col.key === '__actions'">
                  <slot name="actions" :record="record" :index="idx" />
                </template>
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
        <div v-if="totalCount > 0" class="pagination-bar">
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
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

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
  clickable?: boolean
  showActions?: boolean
  total?: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
  serverPagination?: boolean
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
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
  clickable: false,
  showActions: false,
  page: 1,
  pageSize: 20,
  pageSizes: () => [10, 20, 50, 100],
  serverPagination: false,
  sortBy: '',
  sortOrder: 'desc',
})

const emit = defineEmits<{
  create: []
  'update:searchValue': [value: string]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  'update:sortBy': [field: string]
  'update:sortOrder': [order: 'asc' | 'desc']
  sort: [field: string, order: 'asc' | 'desc']
  rowClick: [record: any]
}>()

const innerPage = ref(props.page)
const innerPageSize = ref(props.pageSize)

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

// Client-side pagination
const pageData = computed(() => {
  if (props.serverPagination || props.total != null) return props.dataSource
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
  const newOrder = props.sortBy === field && props.sortOrder === 'desc' ? 'asc' : 'desc'
  emit('update:sortBy', field)
  emit('update:sortOrder', newOrder)
  emit('sort', field, newOrder)
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
.list-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.list-header {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-bar {
  margin-top: 12px;
}

.stats-area {
  margin-top: 16px;
}

/* Search */
.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 6px 12px;
  width: 220px;
}

.search-box svg { color: #8a8a9a; flex-shrink: 0; }

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 14px;
  outline: none;
}

.search-input::placeholder { color: #8a8a9a; }

.clear-btn {
  padding: 2px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  display: flex;
  align-items: center;
}

.clear-btn:hover { color: #fff; }

/* Buttons */
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
  transition: background 0.2s;
}

.btn-primary:hover { background: #40a9ff; }

/* Content */
.list-content {
  flex: 1;
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
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  color: #8a8a9a;
}

.empty-state svg { opacity: 0.3; margin-bottom: 16px; }
.empty-state p { margin: 0 0 16px; font-size: 14px; }

/* Table */
.table-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  overflow: hidden;
}

.pro-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.pro-table thead { background: #2a2a3e; }

.pro-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #fff;
  border-bottom: 1px solid #3a3a4e;
  white-space: nowrap;
}

.pro-table th.sortable {
  cursor: pointer;
  user-select: none;
}

.pro-table th.sortable:hover {
  color: #1890ff;
}

.sort-icon {
  margin-left: 4px;
  font-size: 11px;
  opacity: 0.6;
}

.pro-table td {
  padding: 12px;
  color: #fff;
  border-bottom: 1px solid #2a2a3e;
}

.pro-table tbody tr { transition: background 0.2s; }
.pro-table tbody tr:hover { background: #22223a; }
.pro-table tbody tr.clickable { cursor: pointer; }

/* Pagination */
.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid #2a2a3e;
}

.pagination-info { font-size: 13px; color: #8a8a9a; }

.pagination-controls {
  display: flex;
  gap: 4px;
  align-items: center;
}

.pg-btn {
  min-width: 28px;
  height: 28px;
  padding: 0 6px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pg-btn:hover:not(:disabled):not(.active) { background: #3a3a4e; border-color: #1890ff; }
.pg-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.pg-btn.active { background: #1890ff; border-color: #1890ff; }

.pg-ellipsis { padding: 0 4px; color: #8a8a9a; font-size: 12px; }

.pg-size {
  margin-left: 8px;
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}

.pg-size:focus { outline: none; border-color: #1890ff; }
</style>
