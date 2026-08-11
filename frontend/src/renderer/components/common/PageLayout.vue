<template>
  <div class="page-layout">
    <!-- 固定头部外壳:所有页共享同一结构/尺寸,切换路由不抖动
         (此前 33 页各自写 .page-header 容器:margin-bottom 16/20/24 三派、
          display block/flex 混用、3 页双重 padding,导致标题位置漂移抖动) -->
    <header class="page-layout-header">
      <div class="page-layout-title">
        <slot name="title" />
      </div>
      <div v-if="$slots.actions" class="page-layout-actions">
        <slot name="actions" />
      </div>
    </header>

    <!-- 标题下描述(可选,仅 PaperTrading 等用):负 margin 上拉贴标题 -->
    <div v-if="$slots.description" class="page-layout-description">
      <slot name="description" />
    </div>

    <!-- 筛选/统计条(可选,header 下方) -->
    <div v-if="$slots.filters" class="page-layout-filters">
      <slot name="filters" />
    </div>

    <!-- 内容区 -->
    <div class="page-layout-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
// 纯布局外壳组件:固化 header 容器结构,消除跨页标题抖动。
// 外层 padding 由 App.vue .content 统一(24px),此处不再加。
// 标题文字样式走全局 .page-title(main.css @layer components)。
</script>

<style scoped>
.page-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.page-layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

.page-layout-title {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  /* 标题字号/字重内聚于此:slot 内容(纯文本或 tag+文字)统一 20px,
     不依赖全局 .page-title class(避免 scoped/layer 优先级漂移) */
  font-size: 20px;
  font-weight: 600;
  line-height: 1.4;
  color: hsl(var(--foreground));
}

.page-layout-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.page-layout-description {
  /* 上拉抵消 header 的 margin-bottom:24,贴到标题下方 4px */
  margin: -20px 0 24px;
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

.page-layout-filters {
  margin-bottom: 16px;
}

.page-layout-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
</style>
