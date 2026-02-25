<template>
  <a-card :title="title" class="config-card">
    <slot />
  </a-card>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<style scoped>
.config-card {
  margin-bottom: 16px;
}
</style>
