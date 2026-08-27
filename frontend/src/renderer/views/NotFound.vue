<template>
  <PageLayout>
    <div class="not-found-content">
      <h1 class="error-code">
        404
      </h1>
      <p class="error-message">
        页面未找到
      </p>
      <button
        class="back-button"
        @click="$router.push('/')"
      >
        返回首页
      </button>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import PageLayout from '@/components/common/PageLayout.vue'
</script>

<style scoped>
.not-found-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 100px 0;
  background: hsl(var(--background));
}

.error-code {
  font-size: 72px;
  /* 中性:错误页不承担涨跌/成功语义,绿色数字+绿按钮双绿刺眼 */
  color: hsl(var(--foreground));
  margin: 0 0 16px 0;
  font-family: 'Silkscreen', monospace;
}

.error-message {
  font-size: 18px;
  color: hsl(var(--muted-foreground));
  margin: 0 0 32px 0;
}

.back-button {
  padding: 12px 32px;
  background: hsl(var(--primary));
  border: none;
  border-radius: var(--radius-sm);
  color: hsl(var(--primary-foreground));
  font-family: 'Silkscreen', monospace;
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
}

.back-button:hover {
  opacity: 0.85;
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.back-button:active {
  transform: translateY(0);
}
</style>
