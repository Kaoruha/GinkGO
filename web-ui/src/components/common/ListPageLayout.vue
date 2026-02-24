<template>
  <div class="list-page-layout">
    <!-- 固定头部 -->
    <div class="list-header">
      <div class="header-row">
        <div class="header-left">
          <PageHeader :title="title" :description="description">
            <template v-if="$slots.tag" #tag><slot name="tag" /></template>
          </PageHeader>
          <slot name="stats" />
        </div>
        <div class="header-right">
          <a-input-search
            v-if="showSearch"
            v-model:value="searchModel"
            :placeholder="searchPlaceholder"
            style="width: 200px"
            allow-clear
          />
          <a-button v-if="showCreate" type="primary" @click="emit('create')">
            <template #icon><PlusOutlined /></template>
            {{ createText }}
          </a-button>
          <slot name="actions" />
        </div>
      </div>

      <!-- 筛选栏插槽 -->
      <div v-if="$slots.filters" class="filter-bar">
        <slot name="filters" />
      </div>
    </div>

    <!-- 可滚动内容区 -->
    <div class="list-content">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <a-spin size="large" />
      </div>

      <!-- 空状态 -->
      <a-empty v-else-if="empty" :description="emptyText">
        <a-button v-if="showCreate" type="primary" @click="emit('create')">{{ emptyActionText }}</a-button>
      </a-empty>

      <!-- 内容插槽 -->
      <slot v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import PageHeader from '@/components/layout/PageHeader.vue'

const props = withDefaults(defineProps<{
  title: string
  description?: string
  loading?: boolean
  empty?: boolean
  emptyText?: string
  emptyActionText?: string
  showSearch?: boolean
  searchPlaceholder?: string
  showCreate?: boolean
  createText?: string
}>(), {
  loading: false,
  empty: false,
  emptyText: '暂无数据',
  emptyActionText: '创建第一个',
  showSearch: true,
  searchPlaceholder: '搜索...',
  showCreate: true,
  createText: '新建',
})

const emit = defineEmits<{
  create: []
  'update:search': [value: string]
}>()

const searchModel = computed({
  get: () => '',
  set: (val) => emit('update:search', val),
})
</script>

<style scoped>
.list-page-layout {
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
  align-items: flex-start;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.filter-bar {
  margin-top: 12px;
}

.list-content {
  flex: 1;
  overflow-y: auto;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
}
</style>
