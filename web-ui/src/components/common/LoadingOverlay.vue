<template>
  <div v-if="visible" class="loading-overlay" @click="handleMaskClick">
    <div class="loading-spinner">
      <div class="spinner-icon"></div>
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

.spinner-icon {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.2);
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  color: #ffffff;
  font-size: 14px;
}
</style>
