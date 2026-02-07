<template>
  <div class="node-palette">
    <div class="palette-header">
      <h3>节点库</h3>
    </div>
    <div class="palette-content">
      <div
        v-for="nodeType in nodeTypes"
        :key="nodeType.type"
        class="palette-item"
        draggable="true"
        @dragstart="handleDragStart(nodeType.type, $event)"
      >
        <div
          class="node-icon"
          :class="`icon-${nodeType.type}`"
        >
          <component :is="nodeType.icon" />
        </div>
        <span class="node-label">{{ nodeType.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NodeType, NODE_TYPE_LABELS } from './types'
import {
  SettingOutlined,
  DatabaseOutlined,
  BankOutlined,
  ApartmentOutlined,
  BulbOutlined,
  FilterOutlined,
  PartitionOutlined,
  SafetyOutlined,
  BarChartOutlined,
} from '@ant-design/icons-vue'

interface NodeType {
  type: NodeType
  label: string
  icon: any
}

const emit = defineEmits(['node-drag-start'])

// 节点类型列表
const nodeTypes: NodeType[] = [
  { type: NodeType.ENGINE, label: NODE_TYPE_LABELS[NodeType.ENGINE], icon: SettingOutlined },
  { type: NodeType.FEEDER, label: NODE_TYPE_LABELS[NodeType.FEEDER], icon: DatabaseOutlined },
  { type: NodeType.BROKER, label: NODE_TYPE_LABELS[NodeType.BROKER], icon: BankOutlined },
  { type: NodeType.PORTFOLIO, label: NODE_TYPE_LABELS[NodeType.PORTFOLIO], icon: ApartmentOutlined },
  { type: NodeType.STRATEGY, label: NODE_TYPE_LABELS[NodeType.STRATEGY], icon: BulbOutlined },
  { type: NodeType.SELECTOR, label: NODE_TYPE_LABELS[NodeType.SELECTOR], icon: FilterOutlined },
  { type: NodeType.SIZER, label: NODE_TYPE_LABELS[NodeType.SIZER], icon: PartitionOutlined },
  { type: NodeType.RISK_MANAGEMENT, label: NODE_TYPE_LABELS[NodeType.RISK_MANAGEMENT], icon: SafetyOutlined },
  { type: NodeType.ANALYZER, label: NODE_TYPE_LABELS[NodeType.ANALYZER], icon: BarChartOutlined },
]

// 处理拖拽开始
const handleDragStart = (nodeType: NodeType, event: DragEvent) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vue-flow', nodeType)
  }
  emit('node-drag-start', nodeType)
}
</script>

<style scoped lang="less">
.node-palette {
  height: 100%;
  display: flex;
  flex-direction: column;

  .palette-header {
    padding: 16px;
    border-bottom: 1px solid #e8e8e8;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
    }
  }

  .palette-content {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }

  .palette-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    margin-bottom: 8px;
    background: #fff;
    border: 1px solid #e8e8e8;
    border-radius: 4px;
    cursor: grab;
    transition: all 0.2s;

    &:hover {
      border-color: #1890ff;
      box-shadow: 0 2px 4px rgba(24, 144, 255, 0.1);
    }

    &:active {
      cursor: grabbing;
    }

    .node-icon {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #1890ff;
    }

    .node-label {
      font-size: 12px;
    }
  }
}
</style>
