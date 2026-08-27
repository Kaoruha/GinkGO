<template>
  <!-- 全屏页面壳(登录页/404 等无侧边栏页面) -->
  <div class="empty-layout">
    <slot />
  </div>
</template>

<style scoped>
.empty-layout {
  /* dvh 随移动端浏览器工具栏伸缩,100vh 为回退(见 AppLayout 同款注释) */
  height: 100vh;
  height: 100dvh;
  background: hsl(var(--background));
}

/* 路由动画 wrapper 保持布局中立（页面依赖 height:100% 链） */
.empty-layout > :deep(.m-page) {
  height: 100%;
}
</style>
