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
  background: hsl(var(--background));
}

.not-found-content {
  text-align: center;
  padding: 100px 0;
}

.error-code {
  font-size: 72px;
  color: hsl(var(--success));
  margin: 0 0 16px 0;
  font-family: 'Silkscreen', monospace;
  text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
}

.error-message {
  font-size: 18px;
  color: hsl(var(--muted-foreground));
  margin: 0 0 32px 0;
}

.back-button {
  padding: 12px 32px;
  background: linear-gradient(135deg, hsl(var(--success)), hsl(var(--success)));
  border: none;
  border-radius: 4px;
  color: hsl(var(--background));
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover {
  background: linear-gradient(135deg, hsl(var(--success)), hsl(var(--success)));
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(0, 255, 136, 0.3);
}

.back-button:active {
  transform: translateY(0);
}
</style>
