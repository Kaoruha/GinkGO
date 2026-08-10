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
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  margin-bottom: 16px;
}

.config-card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.config-card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.config-card-body {
  padding: 20px;
}
</style>
