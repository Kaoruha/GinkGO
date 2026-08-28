<template>
  <div class="page-layout">
    <!-- 固定头部外壳:所有页共享同一结构/尺寸,切换路由不抖动
         (此前 33 页各自写 .page-header 容器:margin-bottom 16/20/24 三派、
          display block/flex 混用、3 页双重 padding,导致标题位置漂移抖动) -->
    <header class="page-layout-header">
      <div class="page-layout-title">
        <!-- 终端 kicker(ADR-047):路由段 mono 大写,`>` 提示符用交互绿。
             全站标题基因,详情页在前缀返回链接左侧 -->
        <span
          v-if="kicker"
          class="page-kicker"
          aria-hidden="true"
        ><span class="kicker-prompt">&gt;</span> {{ kicker }}</span>
        <slot name="title" />
      </div>
      <div
        v-if="$slots.actions"
        class="page-layout-actions"
      >
        <slot name="actions" />
      </div>
    </header>

    <!-- 标题下元信息副行(可选):id / 状态 / 来源等。负 margin 上拉贴标题,
         与 #description 互斥(详情页用 meta,列表/功能页用 description) -->
    <div
      v-if="$slots.meta"
      class="page-layout-meta"
    >
      <slot name="meta" />
    </div>

    <!-- 标题下描述(可选,仅 PaperTrading 等用):负 margin 上拉贴标题 -->
    <div
      v-if="$slots.description"
      class="page-layout-description"
    >
      <slot name="description" />
    </div>

    <!-- 标准 tab 行(可选):概况 / 回测 / 组件。详情页统一槽,不再 body 内各自自写 -->
    <nav
      v-if="$slots.tabs"
      class="page-layout-tabs"
    >
      <slot name="tabs" />
    </nav>

    <!-- 筛选/统计条(可选,header 下方) -->
    <div
      v-if="$slots.filters"
      class="page-layout-filters"
    >
      <slot name="filters" />
    </div>

    <!-- 内容区 -->
    <div class="page-layout-body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// 纯布局外壳组件:固化 header 容器结构,消除跨页标题抖动。
// 外层 padding 由 App.vue .content 统一(24px),此处不再加。
// 标题文字样式走全局 .page-title(main.css @layer components)。

const route = useRoute()
/** 终端 kicker:路由段大写(如 PORTFOLIOS、DATA/BARS),根路由不显示 */
const kicker = computed(() => {
  const segs = route.path.split('/').filter(Boolean)
  if (segs.length === 0) return ''
  return segs.slice(0, 2).join('/').toUpperCase()
})
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
  /* flex-start 非 center:各页 #actions 内容高度不同(2 按钮 / select+3 按钮 / 无),
     center 时 header 高度=max(标题,actions),标题 Y 随 actions 撑高而垂直居中漂移
     (探证实测 16px 抖动);flex-start 让标题恒贴 header 顶,relY 恒 0 不抖 */
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
}

/* 终端 kicker(ADR-047):mono 大写小字,`>` 交互绿;置于标题上方独立一行 */
.page-kicker {
  position: absolute;
  top: -16px;
  left: 0;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 1.5px;
  color: hsl(var(--muted-foreground));
  user-select: none;
  white-space: nowrap;
}

.page-kicker .kicker-prompt {
  color: hsl(var(--primary));
  font-weight: 600;
}

.page-layout-title {
  position: relative;
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

.page-layout-meta {
  /* 上拉抵消 header margin-bottom:24,贴标题下方;留 16 给后续 tab/内容。
     与 #description 同模式负 margin,详情页(id/状态/来源)用 */
  margin: -20px 0 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.page-layout-description {
  /* 上拉抵消 header 的 margin-bottom:24,贴到标题下方 4px */
  margin: -20px 0 24px;
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

.page-layout-tabs {
  /* 标准 tab 行容器:详情页(概况/回测/组件)统一 #tabs 槽,不再各页 body 内自写。
     tab-item 文字样式仍由各页 scoped 提供(slot 内容归属定义页组件) */
  display: flex;
  gap: 0;
  border-bottom: 1px solid hsl(var(--border));
  margin-bottom: 20px;
  flex-shrink: 0;
}

.page-layout-filters {
  margin-bottom: 16px;
}

.page-layout-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  /* 直接子项垂直间距由布局容器统一提供(2026-08-19 收口):
     此前无 gap,靠子项各自 margin(.card 全局有,.stats-grid 等容器类无)→ 页面间贴靠不一 */
  gap: 16px;
  /* 滚动收口在 body(2026-08-19):header/meta/tabs/filters 固定不随滚,
     页面内容在此内部滚动(ListPage .list-content 同款模式上提为全局默认)。
     自持内滚的页面(ListPage)子项不超高 → 本滚动条不触发,无双滚。 */
  overflow-y: auto;
}
</style>
