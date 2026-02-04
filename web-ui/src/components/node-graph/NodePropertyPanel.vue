<template>
  <div class="node-property-panel">
    <div class="panel-header">
      <h3>节点属性</h3>
      <a-button type="text" size="small" @click="$emit('close')">
        <CloseOutlined />
      </a-button>
    </div>

    <div class="panel-content">
      <!-- 基本信息 -->
      <div class="section">
        <div class="section-title">基本信息</div>
        <a-form-item label="节点名称">
          <a-input v-model:value="localNode.data.label" @change="handleUpdate" />
        </a-form-item>
        <a-form-item label="节点类型">
          <a-tag :color="getNodeTypeColor(node.type)">
            {{ NODE_TYPE_LABELS[node.type] }}
          </a-tag>
        </a-form-item>
      </div>

      <!-- 配置项 -->
      <div class="section">
        <div class="section-title">配置参数</div>

        <!-- ENGINE 节点配置 -->
        <template v-if="node.type === NodeType.ENGINE">
          <a-form-item label="开始日期">
            <a-date-picker
              v-model:value="engineConfig.start_date"
              format="YYYY-MM-DD"
              @change="handleUpdate"
            />
          </a-form-item>
          <a-form-item label="结束日期">
            <a-date-picker
              v-model:value="engineConfig.end_date"
              format="YYYY-MM-DD"
              @change="handleUpdate"
            />
          </a-form-item>
        </template>

        <!-- BROKER 节点配置 -->
        <template v-if="node.type === NodeType.BROKER">
          <a-form-item label="券商类型">
            <a-select v-model:value="brokerConfig.broker_type" @change="handleUpdate">
              <a-select-option value="simulated">模拟券商</a-select-option>
              <a-select-option value="real">实盘券商</a-select-option>
            </a-select>
          </a-form-item>
          <a-form-item label="初始资金">
            <a-input-number
              v-model:value="brokerConfig.initial_cash"
              :min="0"
              :precision="2"
              @change="handleUpdate"
            />
          </a-form-item>
          <a-form-item label="手续费率">
            <a-input-number
              v-model:value="brokerConfig.commission_rate"
              :min="0"
              :max="1"
              :precision="4"
              :step="0.0001"
              @change="handleUpdate"
            />
          </a-form-item>
        </template>

        <!-- PORTFOLIO 节点配置 -->
        <template v-if="node.type === NodeType.PORTFOLIO">
          <a-form-item label="投资组合">
            <a-select
              v-model:value="portfolioConfig.portfolio_uuid"
              show-search
              placeholder="选择投资组合"
              :options="portfolioOptions"
              @change="handleUpdate"
            />
          </a-form-item>
        </template>

        <!-- STRATEGY/SELECTOR/SIZER/RISK_MANAGEMENT/ANALYZER 节点配置 -->
        <template v-if="isComponentNode">
          <a-form-item label="选择组件">
            <a-select
              v-model:value="componentConfig.component_uuid"
              show-search
              :placeholder="`选择${NODE_TYPE_LABELS[node.type]}组件`"
              :options="componentOptions"
              @change="handleUpdate"
            />
          </a-form-item>
        </template>
      </div>

      <!-- 端口信息 -->
      <div class="section">
        <div class="section-title">端口信息</div>
        <div class="ports-info">
          <div class="port-group">
            <div class="port-label">输入端口</div>
            <div class="port-list">
              <a-tag v-for="port in inputPorts" :key="port.name" :color="port.required ? 'green' : 'default'">
                {{ port.label }}
              </a-tag>
            </div>
          </div>
          <div class="port-group">
            <div class="port-label">输出端口</div>
            <div class="port-list">
              <a-tag v-for="port in outputPorts" :key="port.name">
                {{ port.label }}
              </a-tag>
            </div>
          </div>
        </div>
      </div>

      <!-- 删除按钮 -->
      <div class="section danger">
        <a-button danger block @click="handleDelete">
          <DeleteOutlined />
          删除节点
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { CloseOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import type { GraphNode, NodeType } from './types'
import { NODE_TYPE_LABELS, getInputPorts, getOutputPorts, NodeType as NodeTypeEnum } from './types'

// 导出NodeType供模板使用
const NodeType = NodeTypeEnum

interface Props {
  node: GraphNode
}

const props = defineProps<Props>()
const emit = defineEmits(['node-update', 'close', 'node-delete'])

// 本地节点副本
const localNode = ref<GraphNode>({ ...props.node })

// 监听props变化
watch(
  () => props.node,
  (newNode) => {
    localNode.value = { ...newNode }
  },
  { deep: true }
)

// 节点类型
const nodeType = computed(() => props.node.type as NodeType)

// 是否是组件节点
const isComponentNode = computed(() => {
  return [
    NodeTypeEnum.STRATEGY,
    NodeTypeEnum.SELECTOR,
    NodeTypeEnum.SIZER,
    NodeTypeEnum.RISK_MANAGEMENT,
    NodeTypeEnum.ANALYZER,
  ].includes(nodeType.value)
})

// 配置访问器
const engineConfig = computed({
  get: () => localNode.value.data.config || {},
  set: (val) => {
    localNode.value.data.config = { ...localNode.value.data.config, ...val }
  }
})

const brokerConfig = computed({
  get: () => localNode.value.data.config || {},
  set: (val) => {
    localNode.value.data.config = { ...localNode.value.data.config, ...val }
  }
})

const portfolioConfig = computed({
  get: () => localNode.value.data.config || {},
  set: (val) => {
    localNode.value.data.config = { ...localNode.value.data.config, ...val }
  }
})

const componentConfig = computed({
  get: () => localNode.value.data.config || {},
  set: (val) => {
    localNode.value.data.config = { ...localNode.value.data.config, ...val }
  }
})

// 端口信息
const inputPorts = computed(() => getInputPorts(nodeType.value))
const outputPorts = computed(() => getOutputPorts(nodeType.value))

// 选项数据（TODO: 从API获取）
const portfolioOptions = ref([
  { value: 'portfolio-1', label: '投资组合 1' },
  { value: 'portfolio-2', label: '投资组合 2' },
])

const componentOptions = ref([
  { value: 'component-1', label: '组件 1' },
  { value: 'component-2', label: '组件 2' },
])

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

// 处理更新
const handleUpdate = () => {
  emit('node-update', localNode.value)
}

// 处理删除
const handleDelete = () => {
  emit('node-delete', props.node.id)
}
</script>

<style scoped lang="less">
.node-property-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    border-bottom: 1px solid #e8e8e8;

    h3 {
      margin: 0;
      font-size: 16px;
      font-weight: 500;
    }
  }

  .panel-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;

    .section {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }

      &.danger {
        margin-top: 32px;
      }

      .section-title {
        font-size: 14px;
        font-weight: 500;
        margin-bottom: 12px;
        color: #333;
      }
    }

    .ports-info {
      display: flex;
      flex-direction: column;
      gap: 12px;

      .port-group {
        .port-label {
          font-size: 12px;
          color: #666;
          margin-bottom: 8px;
        }

        .port-list {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
      }
    }
  }
}
</style>
