<template>
  <div class="page-header">
    <div class="page-title">
      <slot name="tag" />
      <span>{{ title }}</span>
    </div>
    <div v-if="description" class="page-desc">{{ description }}</div>
    <div v-if="$slots.actions" class="page-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>
