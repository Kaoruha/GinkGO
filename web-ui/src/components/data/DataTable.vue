<template>
  <div class="data-table">
    <a-table
      v-bind="$attrs"
      :columns="columns"
      :data-source="dataSource"
      :pagination="paginationConfig"
      :loading="loading"
      :row-key="rowKey"
      :scroll="{ x: scrollX }"
      @change="handleTableChange"
      class="pro-table"
    >
      <!-- Custom -->
      <template v-for="column in columns" :#[column.slotName]="slotProps"]="slotProps">
        <slot :name="column.slotName />>
          <template v-if="column.customRender" #default="slotProps">
</template>
            <component :is="column.customRender" v-bind="slotProps" />
          </template>
        </template>
        </slot>
      </template>

      <!-- Custom -->
      <template #expandIcon="slotProps">
        <slot name="expandIcon" v-bind="slotProps" />
      </template>
    </a-table>

    <!-- Custom -->
    <div v-if="showToolbar" class="table-toolbar">
      <div class="toolbar-left">
        <slot name="toolbar" />
      </div>
      <div class="toolbar-right">
        <a-space>
          <a-tooltip title="刷新">
            <a-button @click="handleRefresh" :loading="loading">
              <ReloadOutlined />
            </a-button>
          </a-tooltip>
          <a-tooltip v-if="showExport" title="导出">
            <a-button @click="handleExport">
              <DownloadOutlined />
            </a-button>
          </a-tooltip>
          <slot name="toolbarActions" />
        </a-space>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useAttrs } from 'vue'
import { ReloadOutlined, DownloadOutlined } from '@ant-design/icons-vue'

/**
 * 通用数据表格组件
 * 提供统一的分页、筛选、排序功能
 */

interface Props {
  columns: any[]
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
  refresh: []
  export: []
}>()

const attrs = useAttrs()

// 分页配置
const paginationConfig = computed(() => ({
  current: props.page,
  pageSize: props.pageSize,
  total: props.total,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total) => `共 ${total} 条`
}))

// 表格变化处理
const handleTableChange = (pagination: any, filters: any, sorter: any) => {
  emit('refresh', { pagination, filters, sorter })
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

.table-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border-radius: 8px;
}

.toolbar-left {
  flex: 1;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.pro-table :deep(.ant-table) {
  font-size: 13px;
}

.pro-table :deep(.ant-table-thead > tr > th) {
  font-weight: 600;
  background: #fafafa;
}

.pro-table :deep(.ant-table-tbody > tr:hover) {
  background: #f5f7fa;
}
</style>
