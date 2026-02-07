<template>
  <div class="flex items-center justify-between">
    <div>
      <h1 class="text-lg font-semibold text-gray-900">
        组件管理
      </h1>
      <p class="text-sm text-gray-500">
        管理系统中的策略、分析器、风控等组件
      </p>
    </div>
    <a-button
      type="primary"
      @click="openCreateModal"
    >
      <template #icon>
        <PlusOutlined />
      </template>
      新建组件
    </a-button>
  </div>
</template>

<script setup lang="ts">
import { PlusOutlined } from '@ant-design/icons-vue'
import { useComponentList } from '@/composables/useComponentList'

const { openCreateModal } = useComponentList()
</script>
