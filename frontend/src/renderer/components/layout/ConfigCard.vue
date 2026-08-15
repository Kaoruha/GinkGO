<template>
  <div class="config-card">
    <div v-if="title" class="config-card-header">
      <h4>{{ title }}</h4>
    </div>
    <div class="config-card-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<style scoped>
.config-card {
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  border: 1px solid hsl(var(--border));
  margin-bottom: 16px;
}

.config-card-header {
  padding: 16px 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.config-card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.config-card-body {
  padding: 20px;
}
</style>
