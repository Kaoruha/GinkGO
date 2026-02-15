<template>
  <div v-if="visible" class="loading-overlay" @click="handleMaskClick">
    <div class="loading-spinner">
      <a-spin size="large" />
      <span class="loading-text">{{ text }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  visible: boolean
  text?: string
}

withDefaults(defineProps<Props>(), {
  text: '加载中...'
})

const emit = defineEmits<{
  close: []
}>()

const handleMaskClick = () => {
  emit('close')
}
</script>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.loading-text {
  margin-top: 12px;
  color: white;
}
</style>
