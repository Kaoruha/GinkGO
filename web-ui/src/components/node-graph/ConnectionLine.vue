<template>
  <svg
    class="connection-line"
    :style="{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 0 }"
  >
    <path
      v-if="isValid"
      :d="path"
      fill="none"
      stroke="#1890ff"
      stroke-width="2"
    />
    <path
      v-else
      :d="path"
      fill="none"
      stroke="#ff4d4f"
      stroke-width="2"
      stroke-dasharray="5,5"
    />
  </svg>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getBezierPath } from '@vue-flow/core'
import type { EdgeProps } from '@vue-flow/core'

interface Props extends EdgeProps {}

const props = defineProps<Props>()

// 计算贝塞尔曲线路径
const path = computed(() => {
  const [d] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    sourcePosition: props.sourcePosition,
    targetX: props.targetX,
    targetY: props.targetY,
    targetPosition: props.targetPosition,
  })
  return d
})

// 验证连接是否有效
const isValid = computed(() => {
  // 可以根据连接规则验证
  // 暂时返回true，后续可以集成canConnect逻辑
  return true
})
</script>

<style scoped lang="less">
.connection-line {
  path {
    transition: stroke 0.2s;
  }
}
</style>
