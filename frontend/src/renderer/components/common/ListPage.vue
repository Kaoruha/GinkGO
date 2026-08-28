<template>
  <!-- 列表页壳:基于 PageLayout 组合(header/title/actions/filters 复用统一外壳),
       自持滚动容器 list-content(表头 sticky 恒贴 header 下,不随整页滚)。
       表格+分页渲染委托 ProTable(全站唯一表格实现);
       infiniteScroll 时自渲染 sentinel,页面只传 loadingMore/hasMore + @load-more -->
  <PageLayout>
    <template #title>
      {{ title }}
      <slot name="tag" />
    </template>

    <template #actions>
      <div
        v-if="searchable"
        class="search-box"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <circle
            cx="11"
            cy="11"
            r="8"
          />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          :value="searchValue"
          type="text"
          :placeholder="searchPlaceholder"
          class="search-input"
          @input="$emit('update:searchValue', ($event.target as HTMLInputElement).value)"
        >
        <button
          v-if="searchValue"
          class="clear-btn"
          @click="$emit('update:searchValue', '')"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line
              x1="18"
              y1="6"
              x2="6"
              y2="18"
            />
            <line
              x1="6"
              y1="6"
              x2="18"
              y2="18"
            />
          </svg>
        </button>
      </div>
      <button
        v-if="creatable"
        class="btn-primary"
        @click="$emit('create')"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <line
            x1="12"
            y1="5"
            x2="12"
            y2="19"
          />
          <line
            x1="5"
            y1="12"
            x2="19"
            y2="12"
          />
        </svg>
        {{ createLabel }}
      </button>
      <slot name="header-actions" />
    </template>

    <template
      v-if="$slots.filters"
      #filters
    >
      <slot name="filters" />
    </template>

    <!-- 统计条(固定不随表格滚动,PortfolioList 在用) -->
    <div
      v-if="$slots.stats"
      class="list-stats"
    >
      <slot name="stats" />
    </div>

    <!-- 可滚动内容区 -->
    <div
      ref="listContentEl"
      class="list-content"
    >
      <!-- 加载状态 -->
      <div
        v-if="loading"
        class="loading-state"
      >
        <div class="spinner" />
      </div>

      <!-- 列表加载失败:区别于空态,提供重试 -->
      <div
        v-else-if="errorText"
        class="empty-state"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1"
        >
          <circle
            cx="12"
            cy="12"
            r="10"
          />
          <line
            x1="12"
            y1="8"
            x2="12"
            y2="12"
          />
          <line
            x1="12"
            y1="16"
            x2="12.01"
            y2="16"
          />
        </svg>
        <p class="error-text">
          {{ errorText }}
        </p>
        <button
          class="btn-primary"
          @click="$emit('retry')"
        >
          重试
        </button>
      </div>

      <!-- 空状态 -->
      <div
        v-else-if="isEmpty && !$slots.default"
        class="empty-state"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1"
        >
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
          />
          <circle
            cx="8.5"
            cy="8.5"
            r="1.5"
          />
          <path d="m21 15-5-5L5 21" />
        </svg>
        <p>{{ emptyText }}</p>
        <button
          v-if="creatable"
          class="btn-primary"
          @click="$emit('create')"
        >
          {{ emptyActionText }}
        </button>
      </div>

      <!-- 自定义内容 (替换表格) -->
      <slot v-else-if="$slots.default" />

      <!-- 数据表格 (默认) -->
      <ProTable
        v-else
        :columns="columns"
        :data-source="dataSource"
        :row-key="rowKey"
        :clickable="clickable"
        :context-menu="contextMenu"
        :total="total"
        :page="page"
        :page-size="pageSize"
        :page-sizes="pageSizes"
        :server-pagination="serverPagination"
        :infinite-scroll="infiniteScroll"
        :show-actions="showActions"
        :default-sort-by="defaultSortBy"
        :default-sort-order="defaultSortOrder"
        @update:page="$emit('update:page', $event)"
        @update:page-size="$emit('update:pageSize', $event)"
        @sort="(field, order) => $emit('sort', field, order)"
        @row-click="$emit('rowClick', $event)"
      >
        <template
          v-if="$slots.actions"
          #actions="slotProps"
        >
          <slot
            name="actions"
            v-bind="slotProps"
          />
        </template>
        <template
          v-for="col in slotColumns"
          :key="col.key"
          #[col.key]="slotProps"
        >
          <slot
            :name="col.key"
            v-bind="slotProps"
          />
        </template>
      </ProTable>

      <!-- 无限滚动触发器(仅 infiniteScroll 且已有数据;observer root=list-content) -->
      <div
        v-if="infiniteScroll && !loading && !errorText && dataSource.length > 0"
        ref="sentinelEl"
        class="load-more-trigger"
      >
        <div
          v-if="loadingMore"
          class="spinner spinner-small"
        />
        <div
          v-else-if="!hasMore"
          class="no-more"
        >
          没有更多了
        </div>
        <div
          v-else
          class="load-more-sentinel"
        />
      </div>

      <!-- 兼容插槽:表格之后自定义内容 -->
      <slot name="afterTable" />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, useSlots, watch } from 'vue'
import PageLayout from './PageLayout.vue'
import ProTable, { type Column } from './ProTable.vue'
import type { MenuItem } from '@/composables/useContextMenu'

export type { Column }

const props = withDefaults(defineProps<{
  title: string
  columns: Column[]
  dataSource: any[]
  loading?: boolean
  /** 无限滚动:加载更多中(驱动 sentinel spinner) */
  loadingMore?: boolean
  /** 无限滚动:是否还有更多(=false 显示"没有更多了") */
  hasMore?: boolean
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
  /** 页面持有的排序字段:loading 分支会卸载 ProTable,重挂载时靠它恢复排序态 */
  defaultSortBy?: string
  defaultSortOrder?: 'asc' | 'desc'
  /** 行右键菜单构建器:返回菜单项数组;不传则不接管行右键 */
  contextMenu?: (record: any, index: number) => MenuItem[]
}>(), {
  loading: false,
  loadingMore: false,
  hasMore: true,
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
  loadMore: []
  'update:searchValue': [value: string]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  sort: [field: string, order: 'asc' | 'desc']
  rowClick: [record: any]
}>()

const isEmpty = computed(() => !props.loading && props.dataSource.length === 0)

// 列 slot 转发名单(排除 __actions,它走独立 #actions 转发)。
// 只转发页面实际提供的 slot:ProTable 以 $slots[col.key] 判定自定义渲染,
// 若给未提供内容的列也转发空壳,会遮蔽其 formatValue 默认渲染(列显示空白)
const slots = useSlots()
const slotColumns = computed(() =>
  props.columns
    .map(c => ({ ...c, key: c.key || c.dataIndex }))
    .filter(c => c.key !== '__actions' && !!slots[c.key])
)

// ===== 无限滚动 sentinel(此前 PortfolioList/BacktestListPage 各写一份 observer) =====
const listContentEl = ref<HTMLElement>()
const sentinelEl = ref<HTMLElement>()
let observer: IntersectionObserver | null = null

watch(sentinelEl, (el) => {
  if (!el) return
  nextTick(() => {
    if (!observer && listContentEl.value) {
      observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting && props.hasMore && !props.loading && !props.loadingMore) {
            emit('loadMore')
          }
        },
        // root 必须显式指向 list-content 滚动容器,否则视口相交判定永不触发
        { root: listContentEl.value, rootMargin: '200px', threshold: 0.1 }
      )
    }
    observer?.observe(el)
  })
})

onUnmounted(() => {
  observer?.disconnect()
  observer = null
})
</script>

<style scoped>
/* header/title/actions/filters 外壳样式由 PageLayout 统一提供;
   表格/分页样式由 ProTable 持有,此处仅列表壳特有样式 */

.list-stats {
  flex-shrink: 0;
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

.spinner-small {
  width: 20px;
  height: 20px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
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

/* Load more sentinel */
.load-more-trigger {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.no-more { color: hsl(var(--muted-foreground)); font-size: 12px; }

.load-more-sentinel { height: 1px; }
</style>
