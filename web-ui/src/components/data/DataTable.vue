<template>
  <div class="data-table">
    <div class="table-wrapper">
      <table class="pro-table">
        <thead>
          <tr>
            <th
              v-for="column in computedColumns"
              :key="column.key"
              :style="{ width: column.width + 'px' }"
            >
              {{ column.title }}
            </th>
          </tr>
        </thead>
        <tbody v-if="!loading">
          <tr
            v-for="(record, rowIndex) in displayData"
            :key="record[rowKey] || rowIndex"
            :class="{ clickable: $attrs.onRowClick }"
            @click="$emit('rowClick', record)"
          >
            <td
              v-for="column in computedColumns"
              :key="column.key"
            >
              <slot
                v-if="$slots[column.slotName]"
                :name="column.slotName"
                :record="record"
                :index="rowIndex"
              />
              <template v-else-if="column.dataIndex">
                {{ formatCellValue(record[column.dataIndex]) }}
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="table-loading">
      <div class="spinner"></div>
    </div>

    <!-- Pagination -->
    <div v-if="showPagination && totalCount > 0" class="table-pagination">
      <div class="pagination-info">
        共 {{ totalCount }} 条{{ totalPages > 1 ? `，第 ${currentPage} / ${totalPages} 页` : '' }}
      </div>
      <div v-if="totalPages > 1" class="pagination-controls">
        <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(1)">首页</button>
        <button class="pagination-btn" :disabled="currentPage === 1" @click="changePage(currentPage - 1)">上一页</button>
        <input
          v-model.number="jumpInput"
          type="number"
          :min="1"
          :max="totalPages"
          class="pagination-input"
          @keyup.enter="changePage(jumpInput)"
        />
        <button class="pagination-btn" @click="changePage(jumpInput)">跳转</button>
        <button class="pagination-btn" :disabled="currentPage === totalPages" @click="changePage(currentPage + 1)">下一页</button>
        <button class="pagination-btn" :disabled="currentPage === totalPages" @click="changePage(totalPages)">末页</button>
        <select v-model.number="innerPageSize" class="pagination-select">
          <option :value="10">10 条/页</option>
          <option :value="20">20 条/页</option>
          <option :value="50">50 条/页</option>
          <option :value="100">100 条/页</option>
        </select>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

export interface Column {
  title: string
  dataIndex?: string
  width?: number
  slotName?: string
}

export interface ActionConfig {
  key: string
  label?: string
  to?: ((record: any) => RouteLocationRaw) | RouteLocationRaw
  confirm?: string
  danger?: boolean
  show?: ((record: any) => boolean) | boolean
}

const props = withDefaults(defineProps<{
  columns: Column[]
  dataSource: any[]
  loading?: boolean
  rowKey?: string
  actions?: (string | ActionConfig)[]
  total?: number
  page?: number
  pageSize?: number
  showToolbar?: boolean
  showExport?: boolean
}>(), {
  loading: false,
  rowKey: 'id',
  page: 1,
  pageSize: 20,
  showToolbar: false,
  showExport: false,
})

const emit = defineEmits<{
  action: [key: string, record: any]
  rowClick: [record: any]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  refresh: []
  export: []
}>()

const jumpInput = ref(props.page)
const innerPageSize = ref(props.pageSize)

watch(() => props.page, v => { jumpInput.value = v })
watch(innerPageSize, v => {
  emit('update:pageSize', v)
})

const totalCount = computed(() => props.total ?? props.dataSource.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / innerPageSize.value)))
const currentPage = computed(() => Math.min(props.page, totalPages.value))

const showPagination = computed(() => totalCount.value > 0)

// Auto-add action column
const computedColumns = computed(() => {
  const cols = props.columns.map(c => ({
    ...c,
    key: c.slotName || c.dataIndex || c.title,
  }))
  if (props.actions && props.actions.length > 0) {
    cols.push({ title: '操作', slotName: '__actions', width: 120, key: '__actions' })
  }
  return cols
})

// Client-side pagination when total is not provided
const displayData = computed(() => {
  if (props.total != null) return props.dataSource
  const start = (currentPage.value - 1) * innerPageSize.value
  return props.dataSource.slice(start, start + innerPageSize.value)
})

function changePage(p: number) {
  p = Math.max(1, Math.min(p, totalPages.value))
  if (p === currentPage.value) return
  jumpInput.value = p
  emit('update:page', p)
}

function formatCellValue(val: any): string {
  if (val == null) return '-'
  if (typeof val === 'string' && val.match(/^\d{4}-\d{2}-\d{2}T/)) {
    return new Date(val).toLocaleString('zh-CN')
  }
  return String(val)
}
</script>

<style scoped>
.data-table {
  display: flex;
  flex-direction: column;
}

.table-wrapper {
  overflow-x: auto;
  border-radius: 8px 8px 0 0;
  border: 1px solid #2a2a3e;
  border-bottom: none;
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

.pro-table tbody tr:hover {
  background: #2a2a3e;
}

.pro-table tbody tr.clickable {
  cursor: pointer;
}

/* Loading */
.table-loading {
  display: flex;
  justify-content: center;
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
  to { transform: rotate(360deg); }
}

/* Pagination */
.table-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 0 0 8px 8px;
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
</style>
