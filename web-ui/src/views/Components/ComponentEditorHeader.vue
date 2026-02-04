<template>
  <div class="flex items-center justify-between">
    <div class="flex items-center space-x-4">
      <a-button type="text" @click="goBack" class="text-gray-600 hover:text-gray-900">
        <template #icon><ArrowLeftOutlined /></template>
        返回列表
      </a-button>
      <div class="h-6 w-px bg-gray-300"></div>
      <div>
        <h1 class="text-lg font-semibold text-gray-900">组件编辑器</h1>
        <p class="text-sm text-gray-500">编辑策略、分析器、风控等组件代码</p>
      </div>
    </div>
    <div class="flex items-center space-x-2 text-sm text-gray-500">
      <span v-if="componentInfo">{{ componentInfo.name }}</span>
      <a-tag v-if="componentInfo" :color="getComponentTypeColor(componentInfo.component_type)">
        {{ getComponentTypeLabel(componentInfo.component_type) }}
      </a-tag>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeftOutlined } from '@ant-design/icons-vue'
import { componentsApi, type ComponentDetail } from '@/api/modules/components'

const router = useRouter()
const route = useRoute()
const componentUuid = route.params.uuid as string

const componentInfo = ref<ComponentDetail | null>(null)

const getComponentTypeColor = (type?: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    analyzer: 'green',
    risk: 'orange',
    sizer: 'purple',
    selector: 'cyan'
  }
  return colors[type || ''] || 'default'
}

const getComponentTypeLabel = (type?: string) => {
  const labels: Record<string, string> = {
    strategy: '策略',
    analyzer: '分析器',
    risk: '风控',
    sizer: '仓位管理',
    selector: '选择器'
  }
  return labels[type || ''] || type || ''
}

const loadComponent = async () => {
  try {
    const detail = await componentsApi.get(componentUuid)
    componentInfo.value = detail
  } catch (error) {
    // Ignore error
  }
}

const goBack = () => {
  router.push('/components')
}

onMounted(() => {
  loadComponent()
})
</script>
