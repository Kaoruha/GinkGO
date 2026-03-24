<template>
  <div class="page-container">
    <div class="not-found-content">
      <h1 class="error-code">404</h1>
      <p class="error-message">页面未找到</p>
      <button @click="$router.push('/')" class="back-button">
        返回首页
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.page-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0f;
}

.not-found-content {
  text-align: center;
  padding: 100px 0;
}

.error-code {
  font-size: 72px;
  color: #00ff88;
  margin: 0 0 16px 0;
  font-family: 'Silkscreen', monospace;
  text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
}

.error-message {
  font-size: 18px;
  color: #8a8a9a;
  margin: 0 0 32px 0;
}

.back-button {
  padding: 12px 32px;
  background: linear-gradient(135deg, #00ff88, #00cc6a);
  border: none;
  border-radius: 4px;
  color: #0a0a0f;
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover {
  background: linear-gradient(135deg, #00cc6a, #00aa55);
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
}

.back-button:active {
  transform: translateY(0);
}
</style>
