<template>
  <div class="data-table">
    <div class="table-wrapper">
      <table class="pro-table">
        <thead>
          <tr>
            <th
              v-for="column in columns"
              :key="column.key || column.dataIndex"
              :style="{ width: column.width }"
            >
              {{ column.title }}
            </th>
          </tr>
        </thead>
        <tbody v-if="!loading">
          <tr
            v-for="(record, rowIndex) in displayData"
            :key="record[rowKey] || rowIndex"
            :class="{ 'table-row-hover': hoveredRow === rowIndex }"
            @mouseenter="hoveredRow = rowIndex"
            @mouseleave="hoveredRow = -1"
          >
            <td
              v-for="column in columns"
              :key="column.key || column.dataIndex"
            >
              <slot
                v-if="column.slotName"
                :name="column.slotName"
                :record="record"
                :index="rowIndex"
              >
                <component :is="column.customRender" v-bind="{ record, index: rowIndex }" />
              </slot>
              <template v-else>
                {{ record[column.dataIndex] }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="table-loading">
      <div class="spinner"></div>
    </div>

    <!-- Pagination -->
    <div v-if="paginationConfig && total > 0" class="table-pagination">
      <div class="pagination-info">
        共 {{ total }} 条，第 {{ page }} / {{ totalPages }} 页
      </div>
      <div class="pagination-controls">
        <button
          class="pagination-btn"
          :disabled="page === 1"
          @click="handlePageChange(1)"
        >
          首页
        </button>
        <button
          class="pagination-btn"
          :disabled="page === 1"
          @click="handlePageChange(page - 1)"
        >
          上一页
        </button>
        <input
          v-model.number="jumpPage"
          type="number"
          :min="1"
          :max="totalPages"
          class="pagination-input"
          @keyup.enter="handlePageChange(jumpPage)"
        />
        <button
          class="pagination-btn"
          @click="handlePageChange(jumpPage)"
        >
          跳转
        </button>
        <button
          class="pagination-btn"
          :disabled="page === totalPages"
          @click="handlePageChange(page + 1)"
        >
          下一页
        </button>
        <button
          class="pagination-btn"
          :disabled="page === totalPages"
          @click="handlePageChange(totalPages)"
        >
          末页
        </button>
        <select v-model.number="localPageSize" class="pagination-select">
          <option :value="10">10 条/页</option>
          <option :value="20">20 条/页</option>
          <option :value="50">50 条/页</option>
          <option :value="100">100 条/页</option>
        </select>
      </div>
    </div>

    <!-- Custom Toolbar -->
    <div v-if="showToolbar" class="table-toolbar">
      <div class="toolbar-left">
        <slot name="toolbar" />
      </div>
      <div class="toolbar-right">
        <div class="toolbar-actions">
          <button class="btn-icon" title="刷新" @click="handleRefresh" :disabled="loading">
            <svg v-if="!loading" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M12 2a10 10 0 0 1 10 10"></path>
            </svg>
          </button>
          <button v-if="showExport" class="btn-icon" title="导出" @click="handleExport">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </button>
          <slot name="toolbarActions" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, useAttrs, watch } from 'vue'

/**
 * 通用数据表格组件
 * 提供统一的分页、筛选、排序功能
 */

interface Column {
  title: string
  dataIndex: string
  key?: string
  width?: number
  slotName?: string
  customRender?: any
}

interface Props {
  columns: Column[]
  dataSource: any[]
  loading?: boolean
  rowKey?: string
  scrollX?: number
  showToolbar?: boolean
  showExport?: boolean
  page?: number
  pageSize?: number
  total?: number
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  rowKey: 'id',
  scrollX: 1200,
  showToolbar: true,
  showExport: true,
  page: 1,
  pageSize: 20
})

const emit = defineEmits<{
  refresh: [event?: any]
  export: []
  'update:page': [value: number]
  'update:pageSize': [value: number]
}>()

const attrs = useAttrs()
const hoveredRow = ref(-1)
const jumpPage = ref(props.page)
const localPageSize = ref(props.pageSize)

// 计算总页数
const totalPages = computed(() => {
  return Math.ceil((props.total || props.dataSource.length) / props.pageSize)
})

// 当前页数据
const displayData = computed(() => {
  if (!props.total) {
    // 如果没有total，使用客户端分页
    const start = (props.page - 1) * props.pageSize
    const end = start + props.pageSize
    return props.dataSource.slice(start, end)
  }
  return props.dataSource
})

// 分页配置
const paginationConfig = computed(() => ({
  current: props.page,
  pageSize: props.pageSize,
  total: props.total || props.dataSource.length,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`
}))

// 监听页码变化更新跳转输入框
watch(() => props.page, (newPage) => {
  jumpPage.value = newPage
})

// 监听每页条数变化
watch(localPageSize, (newSize) => {
  emit('update:pageSize', newSize)
  emit('refresh')
})

// 页码变化处理
const handlePageChange = (newPage: number) => {
  if (newPage < 1 || newPage > totalPages.value) return
  jumpPage.value = newPage
  emit('update:page', newPage)
  emit('refresh', { page: newPage, pageSize: localPageSize.value })
}

// 刷新
const handleRefresh = () => {
  emit('refresh')
}

// 导出
const handleExport = () => {
  emit('export')
}
</script>

<style scoped>
.data-table {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.table-wrapper {
  overflow-x: auto;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

.pro-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  background: #1a1a2e;
}

.pro-table thead {
  background: #2a2a3e;
}

.pro-table th {
  padding: 12px;
  text-align: left;
  font-weight: 600;
  color: #ffffff;
  border-bottom: 1px solid #3a3a4e;
  white-space: nowrap;
}

.pro-table td {
  padding: 12px;
  color: #ffffff;
  border-bottom: 1px solid #2a2a3e;
}

.pro-table tbody tr {
  transition: background 0.2s;
}

.pro-table tbody tr.table-row-hover {
  background: #2a2a3e;
}

.pro-table tbody tr:hover {
  background: #2a2a3e;
}

/* Loading */
.table-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Pagination */
.table-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

.pagination-info {
  font-size: 13px;
  color: #8a8a9a;
}

.pagination-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.pagination-btn {
  padding: 4px 10px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-input {
  width: 50px;
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  text-align: center;
}

.pagination-input:focus {
  outline: none;
  border-color: #1890ff;
}

.pagination-select {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

.pagination-select:focus {
  outline: none;
  border-color: #1890ff;
}

/* Toolbar */
.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

.toolbar-left {
  flex: 1;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.btn-icon {
  padding: 6px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.btn-icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
