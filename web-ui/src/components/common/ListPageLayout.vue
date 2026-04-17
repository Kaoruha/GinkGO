<template>
  <div class="list-page-layout">
    <!-- 固定头部 -->
    <div class="list-header">
      <div class="header-row">
        <div class="header-left">
          <div class="page-header">
            <h1 class="page-title">{{ title }}</h1>
            <p v-if="description" class="page-description">{{ description }}</p>
            <slot name="tag" />
          </div>
          <slot name="stats" />
        </div>
        <div class="header-right">
          <div v-if="showSearch" class="search-input-wrapper">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            <input
              v-model="searchModel"
              type="text"
              :placeholder="searchPlaceholder"
              class="search-input"
            />
            <button
              v-if="searchModel"
              class="clear-btn"
              @click="searchModel = ''"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
          <button v-if="showCreate" class="btn btn-primary" @click="emit('create')">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            {{ createText }}
          </button>
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
        <div class="spinner"></div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="empty" class="empty-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <circle cx="8.5" cy="8.5" r="1.5"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <p>{{ emptyText }}</p>
        <button v-if="showCreate" class="btn btn-primary" @click="emit('create')">{{ emptyActionText }}</button>
      </div>

      <!-- 内容插槽 -->
      <slot v-else />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  title: string
  description?: string
  loading?: boolean
  empty?: boolean
  emptyText?: string
  emptyActionText?: string
  showSearch?: boolean
  searchPlaceholder?: string
  searchValue?: string
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
  get: () => props.searchValue ?? '',
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

/* Page Header */
.page-header {
  margin-bottom: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.page-description {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

/* Search Input */
.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 6px 12px;
  width: 200px;
}

.search-input-wrapper svg {
  color: #8a8a9a;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 14px;
  padding: 0;
  outline: none;
}

.search-input::placeholder {
  color: #8a8a9a;
}

.clear-btn {
  padding: 2px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
}

.clear-btn:hover {
  color: #ffffff;
  background: #2a2a3e;
}

/* Button */

/* Loading */

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: #8a8a9a;
}

.empty-state svg {
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-state p {
  margin: 0 0 16px 0;
  font-size: 14px;
}
</style>
