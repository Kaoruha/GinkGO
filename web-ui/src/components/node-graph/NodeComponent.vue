<template>
  <div
    class="custom-node"
    :class="[
      `node-${nodeType}`,
      { selected, 'is-root': isRootNode }
    ]"
  >
    <!-- 输入端口 -->
    <div class="ports-left" v-if="inputs.length > 0">
      <div
        v-for="input in inputs"
        :key="input.name"
        class="port port-input"
        :class="{ required: input.required }"
        :title="input.label"
        @mousedown.stop="startConnection(input, 'target')"
      >
        <div class="port-dot"></div>
        <span class="port-label">{{ input.label }}</span>
      </div>
    </div>

    <!-- 节点内容 -->
    <div class="node-content">
      <div class="node-header">
        <div class="node-icon" :class="`icon-${nodeType}`">
          <svg v-if="nodeType === 'ENGINE'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6"></path>
            <path d="m19 21-7-5 7-5"></path>
            <path d="m22 9-7-5 7-5"></path>
          </svg>
          <svg v-else-if="nodeType === 'FEEDER'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
            <path d="M21 12c0 1.66-4 3-9 3-3s-9 1.34-9 3"></path>
            <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"></path>
          </svg>
          <svg v-else-if="nodeType === 'BROKER'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
            <path d="M12 7V4"></path>
          </svg>
          <svg v-else-if="nodeType === 'PORTFOLIO'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <path d="M9 9V4.5a2.5 2.5 0 0 1 5 0V9"></path>
          </svg>
          <svg v-else-if="nodeType === 'STRATEGY'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 18h6"></path>
            <path d="M10 22h4"></path>
            <path d="M12 2v1"></path>
            <path d="M12 7v4"></path>
            <path d="M12 18v-3"></path>
          </svg>
          <svg v-else-if="nodeType === 'SELECTOR'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="22 3 2 22 12 12 22"></polygon>
            <path d="M12 16v4"></path>
            <path d="M12 12v4"></path>
          </svg>
          <svg v-else-if="nodeType === 'SIZER'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="4" y="4" width="16" height="16" rx="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
            <line x1="9" y1="12" x2="15" y2="12"></line>
          </svg>
          <svg v-else-if="nodeType === 'RISK_MANAGEMENT'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 22s8-4 8-10V5l-8-4v8s8 4 8 10Z"></path>
            <path d="M12 8v4"></path>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="18" rx="2" ry="2"></rect>
            <line x1="8" y1="12" x2="16" y2="12"></line>
            <line x1="12" y1="16" x2="12" y2="12"></line>
          </svg>
        </div>
        <span class="node-label">{{ data.label }}</span>
        <span
          v-if="!isRootNode"
          class="tag node-type-tag"
          :class="`tag-${getNodeTypeColor(nodeType)}`"
        >
          {{ NODE_TYPE_LABELS[nodeType] }}
        </span>
      </div>
      <div class="node-body" v-if="!isRootNode">
        <div
          v-if="data.errors && data.errors.length > 0"
          class="node-errors"
        >
          <span v-for="error in data.errors" :key="error" class="error-icon" :title="error">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.16L6 14h12l2.47-7.84a2 2 0 0 0 .71-3.16L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="17"></line>
              <line x1="8" y1="13" x2="16" y2="13"></line>
            </svg>
          </span>
        </div>
        <div v-else class="node-summary">
          {{ getNodeSummary() }}
        </div>
      </div>
      <!-- 根节点配置 -->
      <div class="node-config" v-else>
        <div class="config-row">
          <span class="config-label">初始资金:</span>
          <span class="config-value">¥{{ formatNumber(rootConfig.initial_cash || 100000) }}</span>
        </div>
        <div class="config-row">
          <span class="config-label">运行模式:</span>
          <span class="tag" :class="`tag-${getModeColor(rootConfig.mode)}`">
            {{ rootConfig.mode || 'BACKTEST' }}
          </span>
        </div>
      </div>
    </div>

    <!-- 输出端口 -->
    <div class="ports-right" v-if="outputs.length > 0">
      <div
        v-for="output in outputs"
        :key="output.name"
        class="port port-output"
        :title="output.label"
        @mousedown.stop="startConnection(output, 'source')"
      >
        <span class="port-label">{{ output.label }}</span>
        <div class="port-dot"></div>
      </div>
    </div>

    <!-- VueFlow Handle components (hidden) -->
    <div
      v-for="input in inputs"
      :key="`in-${input.name}`"
      class="hidden-handle"
      :data-handleid="input.name"
      data-handlepos="left"
    ></div>
    <div
      v-for="output in outputs"
      :key="`out-${output.name}`"
      class="hidden-handle"
      :data-handleid="output.name"
      data-handlepos="right"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { NodeProps } from '@vue-flow/core'
import type { NodeType, GraphNode, NodePort } from './types'
import { getOutputPorts, getInputPorts, NODE_TYPE_LABELS, NodeType as NodeTypeEnum } from './types'

// VueFlow会将节点数据作为props传递
const props = defineProps<NodeProps>()
const emit = defineEmits(['connection-start'])

const selected = computed(() => props.selected || false)

// 获取节点类型
const nodeType = computed(() => props.type as NodeType)

// 判断是否是根节点（Portfolio起始节点）
const isRootNode = computed(() => {
  return props.id === 'portfolio-root' || nodeType.value === NodeTypeEnum.PORTFOLIO
})

// 根节点配置（从表单数据或组件数据获取）
const rootConfig = computed(() => {
  return props.data.config || {}
})

// 获取输入端口
const inputs = computed(() => {
  // 根节点只有输出端口，过滤掉输入端口
  if (isRootNode.value) return []
  return getInputPorts(nodeType.value)
})

// 获取输出端口
const outputs = computed(() => {
  return getOutputPorts(nodeType.value)
})

// 获取节点类型颜色
const getNodeTypeColor = (type: NodeType): string => {
  const colors: Record<NodeType, string> = {
    [NodeTypeEnum.ENGINE]: 'blue',
    [NodeTypeEnum.FEEDER]: 'green',
    [NodeTypeEnum.BROKER]: 'purple',
    [NodeTypeEnum.PORTFOLIO]: 'orange',
    [NodeTypeEnum.STRATEGY]: 'cyan',
    [NodeTypeEnum.SELECTOR]: 'lime',
    [NodeTypeEnum.SIZER]: 'gold',
    [NodeTypeEnum.RISK_MANAGEMENT]: 'red',
    [NodeTypeEnum.ANALYZER]: 'magenta',
  }
  return colors[type] || 'gray'
}

// 获取运行模式颜色
const getModeColor = (mode: string): string => {
  const colors: Record<string, string> = {
    'BACKTEST': 'blue',
    'PAPER': 'orange',
    'LIVE': 'green',
  }
  return colors[mode] || 'gray'
}

// 格式化数字
const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN')
}

// 节点摘要显示
const getNodeSummary = (): string => {
  const config = props.data.config || {}
  switch (nodeType.value) {
    case NodeTypeEnum.ENGINE:
      return config.start_date && config.end_date
        ? `${config.start_date} 至 ${config.end_date}`
        : '未配置时间范围'
    case NodeTypeEnum.BROKER:
      return config.broker_type || '未配置券商'
    case NodeTypeEnum.STRATEGY:
    case NodeTypeEnum.SELECTOR:
    case NodeTypeEnum.SIZER:
    case NodeTypeEnum.RISK_MANAGEMENT:
    case NodeTypeEnum.ANALYZER:
      return config.component_uuid ? '已配置组件' : '点击选择组件'
    default:
      return ''
  }
}

// 开始连接（从端口拖拽）
const startConnection = (port: NodePort, handleType: 'source' | 'target') => {
  emit('connection-start', {
    nodeId: props.id,
    port,
    handleType,
    nodeType: nodeType.value
  })

  // 同时发送到全局事件总线（通过VueFlow）
  const event = new CustomEvent('node-connection-start', {
    detail: {
      nodeId: props.id,
      port,
      handleType,
      nodeType: nodeType.value
    },
    bubbles: true
  })
  document.dispatchEvent(event)
}
</script>

<style scoped>
.custom-node {
  position: relative;
  display: flex;
  align-items: stretch;
  min-width: 320px;
  max-width: 400px;
  background: #1a1a2e;
  border-radius: 12px;
  border: 2px solid #2a2a3e;
  transition: all 0.2s;
}

.custom-node.selected {
  border-color: #1890ff;
  box-shadow: 0 4px 20px rgba(24, 144, 255, 0.2);
}

.custom-node.is-root {
  border-color: #faad14;
  background: linear-gradient(135deg, rgba(250, 173, 20, 0.1) 0%, #1a1a2e 100%);
}

.custom-node.is-root .node-icon {
  background: linear-gradient(135deg, rgba(250, 173, 20, 0.2) 0%, rgba(250, 173, 20, 0.1) 100%) !important;
  color: #face15 !important;
}

/* 端口区域 */
.ports-left,
.ports-right {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
  padding: 8px;
  z-index: 10;
}

.ports-left {
  border-right: 1px solid #2a2a3e;
  padding-right: 12px;
}

.ports-right {
  border-left: 1px solid #2a2a3e;
  padding-left: 12px;
}

/* 端口样式 */
.port {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: crosshair;
  padding: 4px 6px;
  border-radius: 4px;
  transition: all 0.2s;
}

.port:hover {
  background: rgba(24, 144, 255, 0.1);
}

.port:hover .port-dot {
  transform: scale(1.3);
  box-shadow: 0 0 8px rgba(24, 144, 255, 0.5);
}

.port.required .port-label {
  color: #52c41a;
  font-weight: 500;
}

.port.required .port-dot {
  background: #52c41a;
  border-color: #389e0d;
}

.port-label {
  font-size: 11px;
  color: #8a8a9a;
  white-space: nowrap;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.port-dot {
  width: 12px;
  height: 12px;
  background: #1890ff;
  border: 2px solid #1a1a2e;
  border-radius: 50%;
  flex-shrink: 0;
  transition: all 0.2s;
}

.port-input {
  flex-direction: row-reverse;
}

.port-input .port-label {
  text-align: right;
}

/* 节点内容 */
.node-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px;
  min-width: 0;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #2a2a3e;
}

.node-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 16px;
  flex-shrink: 0;
}

.icon-ENGINE {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.icon-FEEDER {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.icon-BROKER {
  background: rgba(114, 46, 209, 0.2);
  color: #722ed1;
}

.icon-PORTFOLIO {
  background: rgba(250, 173, 20, 0.2);
  color: #face15;
}

.icon-STRATEGY {
  background: rgba(19, 194, 194, 0.2);
  color: #13c2c2;
}

.icon-SELECTOR {
  background: rgba(160, 217, 17, 0.2);
  color: #a0d911;
}

.icon-SIZER {
  background: rgba(250, 173, 14, 0.2);
  color: #faad14;
}

.icon-RISK_MANAGEMENT {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.node-label {
  font-size: 15px;
  font-weight: 600;
  color: #ffffff;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-type-tag {
  flex-shrink: 0;
  font-size: 11px;
}

.node-body .node-errors {
  display: flex;
  gap: 4px;
  color: #f5222d;
  flex-wrap: wrap;
}

.error-icon {
  display: flex;
  align-items: center;
}

.node-summary {
  font-size: 12px;
  color: #8a8a9a;
  line-height: 1.6;
}

.node-config .config-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 12px;
}

.config-label {
  color: #8a8a9a;
  font-weight: 500;
}

.config-value {
  color: #ffffff;
  font-weight: 600;
}

/* Tag 样式 */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-orange {
  background: rgba(250, 173, 20, 0.2);
  color: #faad14;
}

.tag-purple {
  background: rgba(114, 46, 209, 0.2);
  color: #722ed1;
}

.tag-cyan {
  background: rgba(19, 194, 194, 0.2);
  color: #13c2c2;
}

.tag-lime {
  background: rgba(160, 217, 17, 0.2);
  color: #a0d911;
}

.tag-gold {
  background: rgba(250, 173, 14, 0.2);
  color: #faad14;
}

.tag-red {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}

.tag-gray {
  background: #2a2a3e;
  color: #8a8a9a;
}

.tag-magenta {
  background: rgba(235, 47, 150, 0.2);
  color: #eb2f96;
}

/* 隐藏VueFlow默认Handle */
.hidden-handle {
  display: none !important;
  opacity: 0;
  width: 0;
  height: 0;
}
</style>
