<template>
  <div
    class="empty-state m-scale-in"
    :class="{ 'has-action': hasAction, 'has-title': title }"
  >
    <div
      v-if="image"
      class="empty-image"
    >
      <img
        :src="image"
        :alt="title || description"
      >
    </div>
    <div
      v-else
      class="empty-icon"
    >
      <slot name="icon">
        <!-- 默认中性 inbox 图标:原 X(关闭)图标语义误导,空态 ≠ 关闭 -->
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="64"
          height="64"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1"
        >
          <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
          <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z" />
        </svg>
      </slot>
    </div>
    <p
      v-if="title"
      class="empty-title"
    >
      {{ title }}
    </p>
    <p
      v-if="description"
      class="empty-description"
    >
      {{ description }}
    </p>
    <!-- 终端 hint(ADR-047):mono // 注释风,用于系统状态说明(如 stub 页"后端接口开发中") -->
    <p
      v-if="hint"
      class="empty-hint-mono"
    >
      // {{ hint }}
    </p>
    <slot />
    <button
      v-if="hasAction"
      class="btn-primary"
      @click="handleAction"
    >
      {{ actionText }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  /** 图片 URL(优先于默认图标) */
  image?: string
  /** 标题(foreground 高对比主文字) */
  title?: string
  /** 描述(muted-foreground 次要文字) */
  description?: string
  /** 终端风 hint:mono // 注释行,系统状态类说明(ADR-047) */
  hint?: string
  /** 操作按钮文字(提供 onAction 时显示) */
  actionText?: string
  /** 操作回调 */
  onAction?: () => void
}

const props = defineProps<Props>()

const hasAction = computed(() => !!props.onAction)

const handleAction = () => {
  props.onAction?.()
}
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 8px;
  /* 终端细网格纹理(ADR-047):极淡方格,只在空态卡内,不进数据区 */
  background-image:
    linear-gradient(hsl(var(--border) / 0.35) 1px, transparent 1px),
    linear-gradient(90deg, hsl(var(--border) / 0.35) 1px, transparent 1px);
  background-size: 24px 24px;
  border-radius: var(--radius-lg);
}

.empty-state.has-action {
  padding: 40px 20px;
}

/* 图标:muted-foreground 直接着色,不加 opacity(dark L55% on bg L7% 对比~5:1 可读) */
.empty-icon {
  margin-bottom: 8px;
  color: hsl(var(--muted-foreground));
}

.empty-icon svg {
  width: 64px;
  height: 64px;
}

.empty-image {
  margin-bottom: 8px;
}

.empty-image img {
  max-width: 200px;
  height: auto;
}

.empty-title {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.empty-description {
  margin: 0;
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

.empty-hint-mono {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 12px;
  color: hsl(var(--muted-foreground) / 0.85);
}

.empty-state.has-action .empty-description,
.empty-state:not(.has-title) .empty-description {
  margin-bottom: 8px;
}
</style>
