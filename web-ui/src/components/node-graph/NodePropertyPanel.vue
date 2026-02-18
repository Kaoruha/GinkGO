<template>
  <div class="property-panel">
    <div
      v-if="!node"
      class="empty-panel"
    >
      <p>选择节点查看属性</p>
    </div>
    <div
      v-else
      class="panel-content"
    >
      <h3 class="panel-title">{{ node.name }}</h3>
      <a-tag :color="getTypeColor(node.type)">
        {{ node.type }}
      </a-tag>

      <a-divider />

      <div
        v-if="node.params && node.params.length > 0"
        class="params-section"
      >
        <h4>参数配置</h4>
        <a-form layout="vertical">
          <a-form-item
            v-for="param in node.params"
            :key="param.name"
            :label="param.name"
          >
            <a-input
              v-if="param.type === 'string'"
              :value="param.default"
              @change="updateParam(param.name, $event.target.value)"
            />
            <a-input-number
              v-else-if="param.type === 'number'"
              :value="param.default"
              @change="updateParam(param.name, $event)"
              style="width: 100%"
            />
            <a-switch
              v-else-if="param.type === 'boolean'"
              :checked="param.default"
              @change="updateParam(param.name, $event)"
            />
            <a-input
              v-else
              :value="param.default"
              @change="updateParam(param.name, $event.target.value)"
            />
          </a-form-item>
        </a-form>
      </div>
      <div
        v-else
        class="no-params"
      >
        <p>此组件无可配置参数</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GraphNode } from './types'

const props = defineProps<{
  node: GraphNode | null
}>()

const emit = defineEmits<{
  update: [nodeId: string, updates: Partial<GraphNode>]
}>()

const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    selector: 'green',
    sizer: 'orange',
    risk: 'red'
  }
  return colors[type] || 'default'
}

const updateParam = (paramName: string, value: any) => {
  if (props.node) {
    emit('update', props.node.id, { params: { ...props.node.params, [paramName]: value } })
  }
}
</script>

<style scoped>
.property-panel {
  height: 100%;
  padding: 16px;
  background: #fff;
  border-left: 1px solid #f0f0f0;
}

.empty-panel {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.panel-title {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.params-section h4 {
  margin-bottom: 12px;
  color: #666;
}

.no-params {
  color: #999;
  text-align: center;
  padding: 20px;
}
</style>
