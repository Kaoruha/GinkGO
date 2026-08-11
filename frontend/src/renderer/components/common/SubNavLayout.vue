<template>
  <!-- 二级导航统一壳:容器页(admin/components/trading/research/live 等)的子导航。
       variant=auto 时按子项数量自适应:≤4 顶部 tab、≥5 左侧栏。
       替代此前 AdminLayout/AdminPage(侧栏) 与 TradingPage/ResearchPage/LivePage(tab)
       五份逐字复制的实现,并修文字色 rgba(255,255,255) 硬编码(亮色主题不可见)。
       active 判定:item.exact 精确匹配,否则前缀匹配(route 或 route+'/')。 -->
  <div class="sub-nav-layout" :class="`is-${effectiveVariant}`">
    <nav class="sub-nav">
      <div v-if="title && effectiveVariant === 'sidebar'" class="sub-nav-title">{{ title }}</div>
      <router-link
        v-for="item in items"
        :key="item.route"
        :to="item.route"
        class="sub-nav-item"
        :class="{ active: isActive(item) }"
      >
        {{ item.label }}
      </router-link>
    </nav>
    <div class="sub-nav-content" :class="{ 'is-padded': padded }">
      <slot />
    </div>
  </div>
</template>

<script lang="ts">
/** 子导航项;SubNavItem 在独立 script 块导出(<script setup> 内不允许 export) */
export interface SubNavItem {
  label: string
  route: string
  /** 精确匹配高亮(模块根路由,如 '/admin',避免在所有子页都亮) */
  exact?: boolean
}
</script>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = withDefaults(defineProps<{
  items: SubNavItem[]
  /** auto: ≤4 项 → tabs,≥5 项 → sidebar;可强制指定 */
  variant?: 'auto' | 'tabs' | 'sidebar'
  /** 侧栏形态顶部小标题(如「系统管理」「组件库」);tab 形态不显示 */
  title?: string
  /** 内容区是否加 24px padding(各壳沿用原行为,避免子页双层/贴边回归) */
  padded?: boolean
}>(), {
  variant: 'auto',
  padded: false,
})

const route = useRoute()

const effectiveVariant = computed(() => {
  if (props.variant !== 'auto') return props.variant
  return props.items.length <= 4 ? 'tabs' : 'sidebar'
})

const isActive = (item: SubNavItem) => {
  if (item.exact) return route.path === item.route
  return route.path === item.route || route.path.startsWith(item.route + '/')
}
</script>

<style scoped>
/* ---- 公共 ---- */
.sub-nav-item {
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
}

/* ---- 顶部 tab 形态(≤4 项) ---- */
.sub-nav-layout.is-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.sub-nav-layout.is-tabs .sub-nav {
  display: flex;
  gap: 0;
  border-bottom: 1px solid hsl(var(--border));
  padding: 0 24px;
  flex-shrink: 0;
}
.sub-nav-layout.is-tabs .sub-nav-item {
  padding: 10px 16px;
  color: hsl(var(--muted-foreground));
  font-size: 14px;
  border-bottom: 2px solid transparent;
}
.sub-nav-layout.is-tabs .sub-nav-item:hover {
  color: hsl(var(--foreground));
}
.sub-nav-layout.is-tabs .sub-nav-item.active {
  color: hsl(var(--primary));
  border-bottom-color: hsl(var(--primary));
  font-weight: 600;
}

/* ---- 左侧栏形态(≥5 项) ---- */
.sub-nav-layout.is-sidebar {
  display: flex;
  height: 100%;
}
.sub-nav-layout.is-sidebar .sub-nav {
  width: 180px;
  background: hsl(var(--card));
  border-right: 1px solid hsl(var(--border));
  padding: 16px 0;
  overflow-y: auto;
  flex-shrink: 0;
}
.sub-nav-title {
  padding: 6px 20px;
  font-size: 11px;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground));
  letter-spacing: 0.5px;
}
.sub-nav-layout.is-sidebar .sub-nav-item {
  display: block;
  padding: 8px 20px;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
}
.sub-nav-layout.is-sidebar .sub-nav-item:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent));
}
.sub-nav-layout.is-sidebar .sub-nav-item.active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  border-right: 2px solid hsl(var(--primary));
}

/* ---- 内容区 ---- */
.sub-nav-content {
  flex: 1;
  min-width: 0;
  overflow: auto;
}
.sub-nav-content.is-padded {
  padding: 24px;
}
</style>
