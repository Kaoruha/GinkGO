<template>
  <div
    class="custom-node"
    :class="[
      `node-${nodeType}`,
      { selected, 'is-root': isRootNode }
    ]"
  >
    <!-- Custom -->
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

    <!-- Custom -->
    <div class="node-content">
      <div class="node-header">
        <div class="node-icon" :class="`icon-${nodeType}`">
          <component :is="nodeIcon" />
        </div>
        <span class="node-label">{{ data.label }}</span>
        <a-tag
          v-if="!isRootNode"
          size="small"
          :color="getNodeTypeColor(nodeType)"
          class="node-type-tag"
        >
          {{ NODE_TYPE_LABELS[nodeType] }}
        </a-tag>
      </div>
      <div class="node-body" v-if="!isRootNode">
        <div
          v-if="data.errors && data.errors.length > 0"
          class="node-errors"
        >
          <a-tooltip
            v-for="error in data.errors"
            :key="error"
            :title="error"
          >
            <WarningOutlined class="error-icon" />
          </a-tooltip>
        </div>
        <div v-else class="node-summary">
          {{ getNodeSummary() }}
        </div>
      </div>
      <!-- Custom -->
      <div class="node-config" v-else>
        <div class="config-row">
          <span class="config-label">初始资金:</span>
          <span class="config-value">¥{{ formatNumber(rootConfig.initial_cash || 100000) }}</span>
        </div>
        <div class="config-row">
          <span class="config-label">运行模式:</span>
          <a-tag :color="getModeColor(rootConfig.mode)">
            {{ rootConfig.mode || 'BACKTEST' }}
          </a-tag>
        </div>
      </div>
    </div>

    <!-- Custom -->
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

    <!--  HandleVueFlow -->
    <Handle
      v-for="input in inputs"
      :id="input.name"
      :key="`in-${input.name}`"
      type="target"
      :position="Position.Left"
      class="hidden-handle"
    />
    <Handle
      v-for="output in outputs"
      :id="output.name"
      :key="`out-${output.name}`"
      type="source"
      :position="Position.Right"
      class="hidden-handle"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { Tag } from 'ant-design-vue'
import { WarningOutlined } from '@ant-design/icons-vue'
import type { Node, NodeProps } from '@vue-flow/core'
import type { NodeType, GraphNode, NodePort } from './types'
import { getOutputPorts, getInputPorts, NODE_TYPE_LABELS, NodeType as NodeTypeEnum } from './types'
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

// 获取节点图标
const nodeIcon = computed(() => {
  const icons: Record<NodeType, any> = {
    [NodeTypeEnum.ENGINE]: SettingOutlined,
    [NodeTypeEnum.FEEDER]: DatabaseOutlined,
    [NodeTypeEnum.BROKER]: BankOutlined,
    [NodeTypeEnum.PORTFOLIO]: ApartmentOutlined,
    [NodeTypeEnum.STRATEGY]: BulbOutlined,
    [NodeTypeEnum.SELECTOR]: FilterOutlined,
    [NodeTypeEnum.SIZER]: PartitionOutlined,
    [NodeTypeEnum.RISK_MANAGEMENT]: SafetyOutlined,
    [NodeTypeEnum.ANALYZER]: BarChartOutlined,
  }
  return icons[nodeType.value] || SettingOutlined
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
  return colors[type] || 'default'
}

// 获取运行模式颜色
const getModeColor = (mode: string): string => {
  const colors: Record<string, string> = {
    'BACKTEST': 'blue',
    'PAPER': 'orange',
    'LIVE': 'green',
  }
  return colors[mode] || 'default'
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
  // @ts-ignore
  document.dispatchEvent(event)
}
</script>

<style scoped lang="less">
.custom-node {
  position: relative;
  display: flex;
  align-items: stretch;
  min-width: 320px;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  border: 2px solid #e8e8e8;
  transition: all 0.2s;

  &.selected {
    border-color: #1890ff;
    box-shadow: 0 4px 20px rgba(24, 144, 255, 0.2);
  }

  &.is-root {
    border-color: #faad14;
    background: linear-gradient(135deg, #fff7e6 0%, #ffffff 100%);

    .node-icon {
      background: linear-gradient(135deg, #ffe7ba 0%, #ffd591 100%) !important;
      color: #d46b08 !important;
    }
  }

  // 端口区域
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
    border-right: 1px solid #f0f0f0;
    padding-right: 12px;
  }

  .ports-right {
    border-left: 1px solid #f0f0f0;
    padding-left: 12px;
  }

  // 端口样式
  .port {
    display: flex;
    align-items: center;
    gap: 6px;
    cursor: crosshair;
    padding: 4px 6px;
    border-radius: 4px;
    transition: all 0.2s;

    &:hover {
      background: #f0f9ff;

      .port-dot {
        transform: scale(1.3);
        box-shadow: 0 0 8px rgba(24, 144, 255, 0.5);
      }
    }

    &.required {
      .port-label {
        color: #52c41a;
        font-weight: 500;
      }

      .port-dot {
        background: #52c41a;
        border-color: #389e0d;
      }
    }

    .port-label {
      font-size: 11px;
      color: #666;
      white-space: nowrap;
      max-width: 80px;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .port-dot {
      width: 12px;
      height: 12px;
      background: #1890ff;
      border: 2px solid #fff;
      border-radius: 50%;
      box-shadow: 0 0 0 2px #e6f7ff;
      flex-shrink: 0;
      transition: all 0.2s;
    }
  }

  .port-input {
    flex-direction: row-reverse;

    .port-label {
      text-align: right;
    }
  }

  .port-output {
    flex-direction: row;
  }

  // 节点内容
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
    border-bottom: 1px solid #f0f0f0;

    .node-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #e6f7ff;
      border-radius: 8px;
      color: #1890ff;
      font-size: 16px;
      flex-shrink: 0;
    }

    .node-label {
      font-size: 15px;
      font-weight: 600;
      color: #1a1a1a;
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .node-type-tag {
      flex-shrink: 0;
      font-size: 11px;
    }
  }

  .node-body {
    .node-errors {
      display: flex;
      gap: 4px;
      color: #ff4d4f;
      flex-wrap: wrap;

      .error-icon {
        font-size: 14px;
      }
    }

    .node-summary {
      font-size: 12px;
      color: #666;
      line-height: 1.6;
    }
  }

  .node-config {
    .config-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 0;
      font-size: 12px;

      .config-label {
        color: #666;
        font-weight: 500;
      }

      .config-value {
        color: #1a1a1a;
        font-weight: 600;
      }
    }
  }

  // 不同类型节点的图标颜色
  .icon-ENGINE {
    background: #e6f7ff;
    color: #1890ff;
  }

  .icon-FEEDER {
    background: #f6ffed;
    color: #52c41a;
  }

  .icon-BROKER {
    background: #f9f0ff;
    color: #722ed1;
  }

  .icon-PORTFOLIO {
    background: #fff7e6;
    color: #fa8c16;
  }

  .icon-STRATEGY {
    background: #e6fffb;
    color: #13c2c2;
  }

  .icon-SELECTOR {
    background: #fcffe6;
    color: #a0d911;
  }

  .icon-SIZER {
    background: #fffbe6;
    color: #faad14;
  }

  .icon-RISK {
    background: #fff1f0;
    color: #f5222d;
  }

  .icon-ANALYZER {
    background: #f9f0ff;
    color: #eb2f96;
  }

  // 隐藏VueFlow默认Handle
  .hidden-handle {
    display: none !important;
    opacity: 0;
    width: 0;
    height: 0;
  }
}
</style>
