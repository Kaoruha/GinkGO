<template>
  <div
    v-if="visible"
    class="node-create-menu"
    :style="{ left: `${position.x}px`, top: `${position.y}px` }"
    @click.stop
  >
    <div class="menu-header">
      <span class="menu-title">选择组件类型</span>
      <button class="btn-icon" @click="close">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="menu-search">
      <div class="search-input-wrapper">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <input
          v-model="searchKeyword"
          type="text"
          placeholder="搜索组件..."
          class="search-input"
        />
        <button
          v-if="searchKeyword"
          class="clear-btn"
          @click="searchKeyword = ''"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <div class="menu-content">
      <div
        v-for="section in filteredSections"
        :key="section.type"
        class="menu-section"
      >
        <div class="section-header" @click="toggleSection(section.type)">
          <span class="tag" :class="`tag-${section.color}`">
            {{ section.label }}
          </span>
          <span class="section-count">({{ section.items.length }})</span>
          <span class="collapse-icon" :class="{ expanded: expandedSections[section.type] }">
            ‹
          </span>
        </div>
        <div v-show="expandedSections[section.type]" class="section-list">
          <div
            v-for="item in section.items"
            :key="item.uuid"
            class="menu-item"
            @click="selectComponent(item, section.type)"
          >
            <div class="item-icon" :class="`icon-${section.color}`">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M12 1v6m0 6v6"></path>
              </svg>
            </div>
            <div class="item-info">
              <div class="item-name">{{ item.name }}</div>
              <div class="item-desc">{{ item.description || item.type }}</div>
            </div>
          </div>
          <div
            v-if="section.items.length === 0"
            class="empty-hint"
          >
            暂无组件
          </div>
        </div>
      </div>

      <div
        v-if="filteredSections.length === 0"
        class="empty-hint"
      >
        未找到匹配的组件
      </div>
    </div>
  </div>

  <div
    v-if="visible"
    class="menu-overlay"
    @click="close"
  ></div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

interface ComponentSummary {
  uuid: string
  name: string
  type: string
  description?: string
  component_type: string
}

interface Props {
  visible: boolean
  position: { x: number; y: number }
  sourcePort?: {
    nodeId: string
    port: string
    portType: 'source' | 'target'
  }
  availableComponents: {
    strategies: ComponentSummary[]
    selectors: ComponentSummary[]
    sizers: ComponentSummary[]
    risks: ComponentSummary[]
  }
}

const props = defineProps<Props>()
const emit = defineEmits(['close', 'select'])

const searchKeyword = ref('')
const expandedSections = ref({
  strategy: true,
  selector: true,
  sizer: true,
  risk: true,
})

// 根据端口类型过滤可用的组件类型
const availableTypes = computed(() => {
  const portDataType = props.sourcePort?.port

  // 定义端口数据类型到组件类型的映射
  const typeMapping: Record<string, string[]> = {
    'strategy': ['strategy'],
    'selector': ['selector'],
    'sizer': ['sizer'],
    'risk': ['risk'],
    'analyzer': ['analyzer'],
  }

  return typeMapping[portDataType || ''] || ['strategy', 'selector', 'sizer', 'risk']
})

// 菜单区域定义
const menuSections = computed(() => {
  const sections = [
    {
      type: 'strategy',
      label: '策略',
      color: 'cyan',
      items: props.availableComponents.strategies
    },
    {
      type: 'selector',
      label: '选股器',
      color: 'lime',
      items: props.availableComponents.selectors
    },
    {
      type: 'sizer',
      label: '仓位管理',
      color: 'gold',
      items: props.availableComponents.sizers
    },
    {
      type: 'risk',
      label: '风控',
      color: 'red',
      items: props.availableComponents.risks
    },
  ]

  // 根据可用类型过滤
  return sections.filter(section =>
    availableTypes.value.includes(section.type) && section.items.length > 0
  )
})

// 过滤后的区域
const filteredSections = computed(() => {
  if (!searchKeyword.value) return menuSections.value

  const keyword = searchKeyword.value.toLowerCase()
  return menuSections.value
    .map(section => ({
      ...section,
      items: section.items.filter(item =>
        item.name.toLowerCase().includes(keyword) ||
        item.type?.toLowerCase().includes(keyword) ||
        item.description?.toLowerCase().includes(keyword)
      )
    }))
    .filter(section => section.items.length > 0)
})

// 切换区域展开/收起
const toggleSection = (type: string) => {
  expandedSections.value[type as keyof typeof expandedSections.value] =
    !expandedSections.value[type as keyof typeof expandedSections.value]
}

// 选择组件
const selectComponent = (component: ComponentSummary, nodeType: string) => {
  emit('select', {
    component,
    nodeType,
    sourcePort: props.sourcePort
  })
  close()
}

// 关闭菜单
const close = () => {
  emit('close')
  searchKeyword.value = ''
}

// 监听可见性变化，搜索时展开所有区域
watch(searchKeyword, (newVal) => {
  if (newVal) {
    Object.keys(expandedSections.value).forEach(key => {
      expandedSections.value[key as keyof typeof expandedSections.value] = true
    })
  }
})
</script>

<style scoped>
.node-create-menu {
  position: fixed;
  width: 320px;
  max-height: 480px;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a3e;
}

.menu-title {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.btn-icon {
  padding: 4px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.menu-search {
  padding: 8px 12px;
  border-bottom: 1px solid #2a2a3e;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  padding: 6px 10px;
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
  font-size: 13px;
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
  background: #3a3a4e;
}

.menu-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.menu-section {
  margin-bottom: 8px;
}

.menu-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  cursor: pointer;
  user-select: none;
  border-radius: 6px;
  transition: background 0.2s;
}

.section-header:hover {
  background: #2a2a3e;
}

.section-count {
  margin-left: 2px;
  font-size: 11px;
  color: #8a8a9a;
}

.collapse-icon {
  margin-left: auto;
  font-size: 14px;
  color: #8a8a9a;
  transition: transform 0.2s;
}

.collapse-icon.expanded {
  transform: rotate(90deg);
}

.section-list {
  padding: 4px 0 8px 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.menu-item:hover {
  background: #2a2a3e;
}

.item-icon {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  flex-shrink: 0;
}

.item-icon.icon-cyan {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.item-icon.icon-lime {
  background: rgba(153, 204, 51, 0.2);
  color: #99cc33;
}

.item-icon.icon-gold {
  background: rgba(250, 204, 21, 0.2);
  color: #face15;
}

.item-icon.icon-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 2px;
}

.item-desc {
  font-size: 11px;
  color: #8a8a9a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-hint {
  padding: 24px;
  text-align: center;
  font-size: 13px;
  color: #8a8a9a;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-cyan {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-lime {
  background: rgba(153, 204, 51, 0.2);
  color: #99cc33;
}

.tag-gold {
  background: rgba(250, 204, 21, 0.2);
  color: #face15;
}

.tag-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 999;
}
</style>
