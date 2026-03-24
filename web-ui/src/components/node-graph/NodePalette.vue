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
          v-html="nodeType.icon"
        ></div>
        <span class="node-label">{{ nodeType.label }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { NodeType, NODE_TYPE_LABELS } from './types'

interface NodeTypeItem {
  type: NodeType
  label: string
  icon: string
}

const emit = defineEmits(['node-drag-start'])

// SVG 图标定义
const icons: Record<NodeType, string> = {
  [NodeType.ENGINE]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M12 1v6m0 6v6"></path>
    <path d="m19 21-7-5 7-5"></path>
    <path d="m22 9-7-5 7-5"></path>
  </svg>`,
  [NodeType.FEEDER]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
    <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path>
  </svg>`,
  [NodeType.BROKER]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
    <path d="M12 7V4"></path>
  </svg>`,
  [NodeType.PORTFOLIO]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
    <path d="M9 9V4.5a2.5 2.5 0 0 1 5 0V9"></path>
  </svg>`,
  [NodeType.STRATEGY]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M9 18h6"></path>
    <path d="M10 22h4"></path>
    <path d="M12 2v1"></path>
    <path d="M12 7v4"></path>
    <path d="M12 18v-3"></path>
  </svg>`,
  [NodeType.SELECTOR]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <polygon points="22 3 2 3 12 21 22 3"></polygon>
    <line x1="12" y1="16" x2="12" y2="20"></line>
    <line x1="12" y1="12" x2="12" y2="16"></line>
  </svg>`,
  [NodeType.SIZER]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="4" y="4" width="16" height="16" rx="2"></rect>
    <line x1="9" y1="9" x2="15" y2="9"></line>
    <line x1="9" y1="15" x2="15" y2="15"></line>
    <line x1="9" y1="12" x2="15" y2="12"></line>
  </svg>`,
  [NodeType.RISK_MANAGEMENT]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
  </svg>`,
  [NodeType.ANALYZER]: `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="18" y1="20" x2="18" y2="10"></line>
    <line x1="12" y1="20" x2="12" y2="4"></line>
    <line x1="6" y1="20" x2="6" y2="14"></line>
  </svg>`,
}

// 节点类型列表
const nodeTypes: NodeTypeItem[] = [
  { type: NodeType.ENGINE, label: NODE_TYPE_LABELS[NodeType.ENGINE], icon: icons[NodeType.ENGINE] },
  { type: NodeType.FEEDER, label: NODE_TYPE_LABELS[NodeType.FEEDER], icon: icons[NodeType.FEEDER] },
  { type: NodeType.BROKER, label: NODE_TYPE_LABELS[NodeType.BROKER], icon: icons[NodeType.BROKER] },
  { type: NodeType.PORTFOLIO, label: NODE_TYPE_LABELS[NodeType.PORTFOLIO], icon: icons[NodeType.PORTFOLIO] },
  { type: NodeType.STRATEGY, label: NODE_TYPE_LABELS[NodeType.STRATEGY], icon: icons[NodeType.STRATEGY] },
  { type: NodeType.SELECTOR, label: NODE_TYPE_LABELS[NodeType.SELECTOR], icon: icons[NodeType.SELECTOR] },
  { type: NodeType.SIZER, label: NODE_TYPE_LABELS[NodeType.SIZER], icon: icons[NodeType.SIZER] },
  { type: NodeType.RISK_MANAGEMENT, label: NODE_TYPE_LABELS[NodeType.RISK_MANAGEMENT], icon: icons[NodeType.RISK_MANAGEMENT] },
  { type: NodeType.ANALYZER, label: NODE_TYPE_LABELS[NodeType.ANALYZER], icon: icons[NodeType.ANALYZER] },
]

// 处理拖拽开始
const handleDragStart = (nodeType: NodeType, event: DragEvent) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vue-flow', nodeType)
  }
  emit('node-drag-start', nodeType)
}
</script>

<style scoped>
.node-palette {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.palette-header {
  padding: 16px;
  border-bottom: 1px solid #2a2a3e;
}

.palette-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
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
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;
}

.palette-item:hover {
  border-color: #1890ff;
  background: #3a3a4e;
}

.palette-item:active {
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

.node-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.node-label {
  font-size: 12px;
  color: #ffffff;
}

.icon-ENGINE { color: #1890ff; }
.icon-FEEDER { color: #52c41a; }
.icon-BROKER { color: #722ed1; }
.icon-PORTFOLIO { color: #faad14; }
.icon-STRATEGY { color: #13c2c2; }
.icon-SELECTOR { color: #a0d911; }
.icon-SIZER { color: #faad14; }
.icon-RISK_MANAGEMENT { color: #f5222d; }
.icon-ANALYZER { color: #eb2f96; }
</style>
