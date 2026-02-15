<template>
  <div
    v-if="visible"
    class="node-create-menu"
    :style="{ left: `${position.x}px`, top: `${position.y}px` }"
    @click.stop
  >
    <div class="menu-header">
      <span class="menu-title">选择组件类型</span>
      <a-button
        type="text"
        size="small"
        @click="close"
      >
        <CloseOutlined />
      </a-button>
    </div>

    <div class="menu-search">
      <a-input
        v-model:value="searchKeyword"
        placeholder="搜索组件..."
        size="small"
        allow-clear
      >
        <template #prefix>
          <SearchOutlined />
        </template>
      </a-input>
    </div>

    <div class="menu-content">
      <div
        v-for="section in filteredSections"
        :key="section.type"
        class="menu-section"
      >
        <div class="section-header" @click="toggleSection(section.type)">
          <a-tag :color="section.color">
            {{ section.label }}
          </a-tag>
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
            <div class="item-icon">
              <component :is="getSectionIcon(section.type)" />
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

  <!-- Custom -->
  <div
    v-if="visible"
    class="menu-overlay"
    @click="close"
  ></div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message, Tag, Input, Button } from 'ant-design-vue'
import { CloseOutlined, SearchOutlined } from '@ant-design/icons-vue'
import {
  BulbOutlined,
  FilterOutlined,
  PartitionOutlined,
  SafetyOutlined,
  BarChartOutlined,
  DatabaseOutlined,
  BankOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'
import type { ComponentSummary } from '@/api/modules/components'

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
  // 根据端口数据类型判断可以连接的组件类型
  const portDataType = props.sourcePort?.port

  // 定义端口数据类型到组件类型的映射
  const typeMapping: Record<string, string[]> = {
    // Portfolio 的输出端口可以连接的组件
    'strategy': ['strategy'],
    'selector': ['selector'],
    'sizer': ['sizer'],
    'risk': ['risk'],
    'analyzer': ['analyzer'],
    // 其他端口类型...
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
      icon: BulbOutlined,
      items: props.availableComponents.strategies
    },
    {
      type: 'selector',
      label: '选股器',
      color: 'lime',
      icon: FilterOutlined,
      items: props.availableComponents.selectors
    },
    {
      type: 'sizer',
      label: '仓位管理',
      color: 'gold',
      icon: PartitionOutlined,
      items: props.availableComponents.sizers
    },
    {
      type: 'risk',
      label: '风控',
      color: 'red',
      icon: SafetyOutlined,
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

// 获取区域图标
const getSectionIcon = (type: string) => {
  const icons: Record<string, any> = {
    strategy: BulbOutlined,
    selector: FilterOutlined,
    sizer: PartitionOutlined,
    risk: SafetyOutlined,
  }
  return icons[type] || SettingOutlined
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

<style scoped lang="less">
.node-create-menu {
  position: fixed;
  width: 320px;
  max-height: 480px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  overflow: hidden;

  .menu-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;

    .menu-title {
      font-size: 14px;
      font-weight: 600;
      color: #1a1a1a;
    }
  }

  .menu-search {
    padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
  }

  .menu-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .menu-section {
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }
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

    &:hover {
      background: #f5f5f5;
    }

    .section-count {
      margin-left: 2px;
      font-size: 11px;
      color: #999;
    }

    .collapse-icon {
      margin-left: auto;
      font-size: 14px;
      color: #999;
      transition: transform 0.2s;

      &.expanded {
        transform: rotate(90deg);
      }
    }
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

    &:hover {
      background: #f0f9ff;
    }

    .item-icon {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #e6f7ff;
      border-radius: 6px;
      color: #1890ff;
      flex-shrink: 0;
    }

    .item-info {
      flex: 1;
      min-width: 0;

      .item-name {
        font-size: 13px;
        font-weight: 500;
        color: #1a1a1a;
        margin-bottom: 2px;
      }

      .item-desc {
        font-size: 11px;
        color: #999;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .empty-hint {
    padding: 24px;
    text-align: center;
    font-size: 13px;
    color: #999;
  }
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
