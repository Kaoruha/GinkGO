<template>
  <div class="component-list-header">
    <div class="header-info">
      <h1>组件管理</h1>
      <p>管理系统中的策略、分析器、风控等组件</p>
    </div>
    <button class="btn btn-primary" @click="openCreateModal">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="12" y1="5" x2="12" y2="19"></line>
        <line x1="5" y1="12" x2="19" y2="12"></line>
      </svg>
      新建组件
    </button>
  </div>
</template>

<script setup lang="ts">
import { useComponentList } from '@/composables/useComponentList'

const { openCreateModal } = useComponentList()
</script>

<style scoped>
.component-list-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.header-info h1 {
  margin: 0 0 4px 0;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

.header-info p {
  margin: 0;
  font-size: 13px;
  color: #8a8a9a;
}

.btn-primary svg {
  flex-shrink: 0;
}
</style>
