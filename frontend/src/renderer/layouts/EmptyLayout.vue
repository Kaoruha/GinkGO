<template>
  <!-- 全屏页面壳(登录页/404 等无侧边栏页面) -->
  <div class="empty-layout">
    <slot />
  </div>
</template>

<style scoped>
.empty-layout {
  height: 100vh;
  background: hsl(var(--background));
}

/* 路由动画 wrapper 保持布局中立（页面依赖 height:100% 链） */
.empty-layout > :deep(.m-page) {
  height: 100%;
}
</style>
