<template>
  <div class="component-editor-header">
    <div class="header-left">
      <button class="btn btn-text" @click="goBack">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="19" y1="12" x2="5" y2="12"></line>
          <polyline points="12 19 5 12 12 5"></polyline>
        </svg>
        返回列表
      </button>
      <div class="divider"></div>
      <div class="header-info">
        <h1>组件编辑器</h1>
        <p>编辑策略、分析器、风控等组件代码</p>
      </div>
    </div>
    <div class="header-right">
      <span v-if="componentInfo" class="component-name">{{ componentInfo.name }}</span>
      <span v-if="componentInfo" class="tag" :class="`tag-${getComponentTypeColorClass(componentInfo.component_type)}`">
        {{ getComponentTypeLabel(componentInfo.component_type) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { componentsApi, type ComponentDetail } from '@/api/modules/components'

const router = useRouter()
const route = useRoute()
const componentUuid = route.params.uuid as string

const componentInfo = ref<ComponentDetail | null>(null)

const getComponentTypeColorClass = (type?: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    analyzer: 'green',
    risk: 'orange',
    sizer: 'purple',
    selector: 'cyan'
  }
  return colors[type || ''] || 'gray'
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

<style scoped>
.component-editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #8a8a9a;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-text:hover {
  color: #ffffff;
  background: #2a2a3e;
}

.btn-text svg {
  flex-shrink: 0;
}

.divider {
  width: 1px;
  height: 24px;
  background: #2a2a3e;
}

.header-info h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.header-info p {
  margin: 2px 0 0 0;
  font-size: 13px;
  color: #8a8a9a;
}

.component-name {
  font-size: 13px;
  color: #8a8a9a;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-purple { background: rgba(114, 46, 209, 0.2); color: #722ed1; }
.tag-cyan { background: rgba(19, 194, 194, 0.2); color: #13c2c2; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }
</style>
