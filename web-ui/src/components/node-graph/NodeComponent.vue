<template>
  <div class="custom-node" :class="{ selected }">
    <div class="node-header">
      <div class="node-icon">
        <component :is="nodeIcon" />
      </div>
      <span class="node-label">{{ node.data.label }}</span>
    </div>
    <div class="node-body">
      <div v-if="node.data.errors && node.data.errors.length > 0" class="node-errors">
        <a-tooltip v-for="error in node.data.errors" :key="error" :title="error">
          <WarningOutlined class="error-icon" />
        </a-tooltip>
      </div>
      <div v-else class="node-summary">
        {{ getNodeSummary() }}
      </div>
    </div>
    <!-- Handle 输出端口 -->
    <Handle
      v-for="output in outputs"
      :key="output.name"
      :id="output.name"
      type="source"
      :position="Position.Right"
      :class="`handle handle-${output.name}`"
    />
    <!-- Handle 输入端口 -->
    <Handle
      v-for="input in inputs"
      :key="input.name"
      :id="input.name"
      type="target"
      :position="Position.Left"
      :class="`handle handle-${input.name} ${input.required ? 'required' : ''}`"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { WarningOutlined } from '@ant-design/icons-vue'
import type { NodeProps } from '@vue-flow/core'
import type { NodeType, GraphNode, NodePort } from './types'
import { getOutputPorts, getInputPorts, NODE_TYPE_LABELS } from './types'
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

interface Props extends NodeProps {
  data: GraphNode['data']
}

const props = defineProps<Props>()

const selected = computed(() => props.selected)

// 获取节点类型
const nodeType = computed(() => props.type as NodeType)

// 获取节点图标
const nodeIcon = computed(() => {
  const icons: Record<NodeType, any> = {
    [NodeType.ENGINE]: SettingOutlined,
    [NodeType.FEEDER]: DatabaseOutlined,
    [NodeType.BROKER]: BankOutlined,
    [NodeType.PORTFOLIO]: ApartmentOutlined,
    [NodeType.STRATEGY]: BulbOutlined,
    [NodeType.SELECTOR]: FilterOutlined,
    [NodeType.SIZER]: PartitionOutlined,
    [NodeType.RISK_MANAGEMENT]: SafetyOutlined,
    [NodeType.ANALYZER]: BarChartOutlined,
  }
  return icons[nodeType.value] || SettingOutlined
})

// 获取输入端口
const inputs = computed(() => {
  return getInputPorts(nodeType.value)
})

// 获取输出端口
const outputs = computed(() => {
  return getOutputPorts(nodeType.value)
})

// 节点摘要显示
const getNodeSummary = () => {
  const config = props.data.config || {}
  switch (nodeType.value) {
    case NodeType.ENGINE:
      return config.start_date && config.end_date
        ? `${config.start_date} 至 ${config.end_date}`
        : '未配置时间范围'
    case NodeType.BROKER:
      return config.broker_type || '未配置券商'
    case NodeType.PORTFOLIO:
      return config.portfolio_uuid ? '已选择' : '未选择'
    case NodeType.STRATEGY:
    case NodeType.SELECTOR:
    case NodeType.SIZER:
    case NodeType.RISK_MANAGEMENT:
    case NodeType.ANALYZER:
      return config.component_uuid ? '已配置' : '未配置'
    default:
      return ''
  }
}
</script>

<style scoped lang="less">
.custom-node {
  padding: 12px;
  border-radius: 8px;
  background: #fff;
  border: 2px solid #e8e8e8;
  min-width: 150px;
  transition: all 0.2s;

  &.selected {
    border-color: #1890ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }

  .node-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;

    .node-icon {
      width: 20px;
      height: 20px;
      color: #1890ff;
    }

    .node-label {
      font-size: 13px;
      font-weight: 500;
    }
  }

  .node-body {
    .node-errors {
      display: flex;
      gap: 4px;
      color: #ff4d4f;

      .error-icon {
        font-size: 12px;
      }
    }

    .node-summary {
      font-size: 11px;
      color: #666;
    }
  }

  .handle {
    width: 8px;
    height: 8px;
    background: #1890ff;
    border: 2px solid #fff;

    &.required {
      background: #52c41a;
    }

    &.handle-portfolio {
      top: 50%;
    }

    &[class*="source"] {
      right: -4px;
    }

    &[class*="target"] {
      left: -4px;
    }
  }
}
</style>
