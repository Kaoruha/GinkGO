<template>
  <!-- 表格+分页统一封装:全站唯一表格实现(退役 DataTable 与各页手写 «‹›» 分页条)。
       ListPage 内部复用本组件;图表+表格混排的详情页(BarData/TickData 等)直接使用。
       分页语义:total 未传 = 客户端切页;total/serverPagination 传入 = 服务端分页(仅 emit)。
       滚动语义:默认靠外层滚动容器(ListPage .list-content)吸顶;maxHeight 传入时表格自滚。 -->
  <div class="table-card">
    <div
      class="table-scroll"
      :style="scrollStyle"
    >
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
              <span
                v-if="col.sortable"
                class="sort-icon"
              >
                <template v-if="innerSortBy === col.dataIndex">
                  {{ innerSortOrder === 'asc' ? '↑' : '↓' }}
                </template>
                <template v-else>⇅</template>
              </span>
            </th>
          </tr>
        </thead>
        <tbody class="m-stagger">
          <!-- 加载态:保留表头,行区显示 spinner -->
          <tr v-if="loading">
            <td
              :colspan="resolvedColumns.length"
              class="state-cell"
            >
              <div class="spinner" />
            </td>
          </tr>
          <tr v-else-if="pageData.length === 0">
            <td
              :colspan="resolvedColumns.length"
              class="state-cell"
            >
              {{ emptyText }}
            </td>
          </tr>
          <template v-else>
            <tr
              v-for="(record, idx) in pageData"
              :key="record[rowKey] || idx"
              :class="{ clickable: clickable }"
              @click="$emit('rowClick', record)"
              @contextmenu="onRowContextMenu($event, record, idx)"
            >
              <td
                v-for="col in resolvedColumns"
                :key="col.key"
                :class="{ 'col-num': col.num }"
              >
                <!-- 操作列:flex 容器给按钮间距,避免多按钮紧贴 -->
                <div
                  v-if="col.key === '__actions'"
                  class="actions-cell"
                >
                  <slot
                    name="actions"
                    :record="record"
                    :index="idx"
                  />
                </div>
                <!-- 自定义列:slot 名 = col.key || col.dataIndex -->
                <template v-else-if="$slots[col.key]">
                  <slot
                    :name="col.key"
                    :record="record"
                    :index="idx"
                  />
                </template>
                <!-- 默认渲染 -->
                <template v-else>
                  {{ formatValue(record[col.dataIndex]) }}
                </template>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div
      v-if="totalCount > 0 && !infiniteScroll"
      class="pagination-bar"
    >
      <div class="pagination-info">
        共 {{ totalCount }} 条{{ totalPages > 1 ? `，第 ${innerPage} / ${totalPages} 页` : '' }}
      </div>
      <div
        v-if="totalPages > 1"
        class="pagination-controls"
      >
        <button
          class="pg-btn"
          :disabled="innerPage <= 1"
          @click="goPage(1)"
        >
          «
        </button>
        <button
          class="pg-btn"
          :disabled="innerPage <= 1"
          @click="goPage(innerPage - 1)"
        >
          ‹
        </button>
        <template
          v-for="p in visiblePages"
          :key="p"
        >
          <span
            v-if="p === '...'"
            class="pg-ellipsis"
          >…</span>
          <button
            v-else
            class="pg-btn"
            :class="{ active: p === innerPage }"
            @click="goPage(p as number)"
          >
            {{ p }}
          </button>
        </template>
        <button
          class="pg-btn"
          :disabled="innerPage >= totalPages"
          @click="goPage(innerPage + 1)"
        >
          ›
        </button>
        <button
          class="pg-btn"
          :disabled="innerPage >= totalPages"
          @click="goPage(totalPages)"
        >
          »
        </button>
        <select
          v-model.number="innerPageSize"
          class="pg-size"
        >
          <option
            v-for="s in pageSizes"
            :key="s"
            :value="s"
          >
            {{ s }} 条/页
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useContextMenu, type MenuItem } from '@/composables/useContextMenu'
import { formatDate } from '@/utils/format'

export interface Column {
  title: string
  dataIndex: string
  key?: string
  width?: number
  sortable?: boolean
  /** 数字列:右对齐 + 等宽数字(挂全局 .col-num) */
  num?: boolean
}

const props = withDefaults(defineProps<{
  columns: Column[]
  dataSource: any[]
  loading?: boolean
  rowKey?: string
  clickable?: boolean
  /** 总数。传入即视为外部管分页(仅 emit 翻页,不本地切页) */
  total?: number
  page?: number
  pageSize?: number
  pageSizes?: number[]
  /** 服务端分页别名(total 之外再显式声明,语义自文档) */
  serverPagination?: boolean
  /** 无限滚动模式:隐藏分页条,数据全量渲染 */
  infiniteScroll?: boolean
  /** 表格自滚高度(图表+表格混排页用);不传靠外层滚动容器 */
  maxHeight?: number | string
  emptyText?: string
  /** 行右键菜单构建器:返回菜单项数组;不传则不接管行右键 */
  contextMenu?: (record: any, index: number) => MenuItem[]
  /** 追加操作列(配合 #actions slot) */
  showActions?: boolean
  /** 初始排序(非受控:仅表头指示器;实际排序由 @sort 消费方执行) */
  defaultSortBy?: string
  /** 默认排序方向:初始 + 首次点击新列时(文本列页面传 asc) */
  defaultSortOrder?: 'asc' | 'desc'
}>(), {
  loading: false,
  rowKey: 'id',
  page: 1,
  pageSize: 20,
  pageSizes: () => [10, 20, 50, 100],
  serverPagination: false,
  infiniteScroll: false,
  emptyText: '暂无数据',
  showActions: false,
  defaultSortBy: '',
  defaultSortOrder: 'desc',
})

const emit = defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
  sort: [field: string, order: 'asc' | 'desc']
  rowClick: [record: any]
}>()

const innerPage = ref(props.page)
const innerPageSize = ref(props.pageSize)
const innerSortBy = ref(props.defaultSortBy)
const innerSortOrder = ref<'asc' | 'desc'>(props.defaultSortOrder)

const { open: openCtx } = useContextMenu()
function onRowContextMenu(e: MouseEvent, record: any, idx: number) {
  if (!props.contextMenu) return
  openCtx(e, props.contextMenu(record, idx))
}

watch(() => props.page, v => { innerPage.value = v })

const totalCount = computed(() => props.total ?? props.dataSource.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / innerPageSize.value)))

const resolvedColumns = computed(() => {
  const cols = props.columns.map(c => ({ ...c, key: c.key || c.dataIndex }))
  if (props.showActions) {
    cols.push({ title: '操作', dataIndex: '', key: '__actions', width: 120 })
  }
  return cols
})

// 客户端切页:仅当外部未声明 total/serverPagination/infiniteScroll 时本地分片
const pageData = computed(() => {
  if (props.serverPagination || props.total != null || props.infiniteScroll) return props.dataSource
  const start = (innerPage.value - 1) * innerPageSize.value
  return props.dataSource.slice(start, start + innerPageSize.value)
})

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

const scrollStyle = computed(() => {
  if (!props.maxHeight) return undefined
  const raw = props.maxHeight
  const h = typeof raw === 'number' || /^\d+$/.test(String(raw)) ? `${raw}px` : raw
  return { maxHeight: h, overflowY: 'auto' as const }
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
    innerSortOrder.value = props.defaultSortOrder
  }
  innerPage.value = 1
  emit('update:page', 1)
  emit('sort', field, innerSortOrder.value)
}

function formatValue(val: any): string {
  if (val == null) return '-'
  if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T/)) {
    // 走统一 formatter(toLocaleString 产出 "2026/8/17 2:49:43" 不补零,列内不对齐)
    return formatDate(val)
  }
  return String(val)
}
</script>

<style scoped>
/* 表格样式全局权威在 styles/tables.less(.table-card/.pro-table),此处仅分页/状态 */

.table-scroll { overflow-x: auto; }

.state-cell {
  text-align: center;
  padding: 40px 16px;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}

.spinner {
  width: 28px;
  height: 28px;
  border: 3px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto;
}

@keyframes spin { to { transform: rotate(360deg); } }

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
