<template>
  <div class="empty-state" :class="{ 'has-action': hasAction }">
    <a-empty :image="image">
      <template #description>
        <div class="empty-description">{{ description }}</div>
      </template>
      <template #action v-if="hasAction">
        <a-button type="primary" size="small" @click="handleAction">
          {{ actionText }}
        </a-button>
      </template>
    </a-empty>
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
  padding: 40px 0;
}

.empty-state.has-action {
  padding: 24px 0;
}
</style>
