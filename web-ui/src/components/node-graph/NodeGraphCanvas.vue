<template>
  <div
    class="node-canvas"
    @dragover.prevent
    @drop="handleDrop"
  >
    <div
      v-if="nodes.length === 0"
      class="empty-canvas"
    >
      <p>拖拽组件到此处开始配置</p>
    </div>
    <div
      v-for="node in nodes"
      :key="node.id"
      class="node-item"
      :class="{ selected: selectedNodeId === node.id }"
      :style="{ left: node.x + 'px', top: node.y + 'px' }"
      @click="$emit('select', node)"
    >
      <div class="node-header">
        <span class="node-type">{{ node.type }}</span>
        <span class="node-name">{{ node.name }}</span>
      </div>
      <button
        class="node-delete"
        @click.stop="$emit('delete', node.id)"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { GraphNode } from './types'

defineProps<{
  nodes: GraphNode[]
  selectedNodeId?: string
}>()

const emit = defineEmits<{
  drop: [event: DragEvent]
  select: [node: GraphNode]
  delete: [nodeId: string]
}>()

const handleDrop = (event: DragEvent) => {
  emit('drop', event)
}
</script>

<style scoped>
.node-canvas {
  width: 100%;
  height: 100%;
  background: #fafafa;
  border: 1px dashed #d9d9d9;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}

.empty-canvas {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
}

.node-item {
  position: absolute;
  background: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 8px;
  padding: 12px;
  min-width: 150px;
  cursor: move;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.node-item.selected {
  border-color: #1890ff;
  box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
}

.node-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.node-type {
  font-size: 12px;
  color: #8c8c8c;
}

.node-name {
  font-weight: 500;
}

.node-delete {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border: none;
  background: #ff4d4f;
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}
</style>
