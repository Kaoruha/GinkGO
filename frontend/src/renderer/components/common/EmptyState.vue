<template>
  <div class="empty-state" :class="{ 'has-action': hasAction }">
    <div v-if="image" class="empty-image">
      <img :src="image" :alt="description" />
    </div>
    <div v-else class="empty-icon">
      <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <line x1="9" y1="9" x2="15" y2="15"></line>
        <line x1="15" y1="9" x2="9" y2="15"></line>
      </svg>
    </div>
    <div class="empty-description">{{ description }}</div>
    <button v-if="hasAction" class="btn-primary" @click="handleAction">
      {{ actionText }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  image?: string
  description: string
  actionText?: string
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
  color: #8a8a9a;
}

.empty-state.has-action {
  padding: 40px 20px;
}

.empty-icon {
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-icon svg {
  color: #8a8a9a;
}

.empty-image {
  margin-bottom: 16px;
}

.empty-image img {
  max-width: 200px;
  height: auto;
}

.empty-description {
  font-size: 14px;
  margin-bottom: 16px;
}

.btn-primary {
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}
</style>
