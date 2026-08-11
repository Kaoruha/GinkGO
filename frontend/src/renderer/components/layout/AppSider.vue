<template>
  <div class="sider" :class="{ collapsed }">
    <div class="logo">
      <img src="/favicon.svg" alt="Ginkgo" />
      <span v-if="!collapsed">Ginkgo</span>
    </div>
    <nav class="menu">
      <div
        v-for="item in menuConfigs"
        :key="item.key"
        class="menu-section"
        @mouseenter="onHover(item)"
        @mouseleave="onLeave"
      >
        <router-link
          :to="firstChildRoute(item)"
          class="menu-item"
          :class="{ selected: selectedKeys.includes(item.key) }"
          :data-testid="`nav-${item.key}`"
          @click="onSelect(item)"
        >
          <div class="menu-item-content">
            <component :is="item.icon" class="menu-icon" :size="16" v-if="item.icon" />
            <span class="menu-label">{{ item.label }}</span>
          </div>
          <ChevronRight
            v-if="item.children && !collapsed"
            class="chevron"
            :class="{ open: isExpanded(item) }"
            :size="14"
          />
        </router-link>

        <!-- 宽态:就地展开二级(手风琴,一次只展开一个模块) -->
        <div v-if="!collapsed && item.children && isExpanded(item)" class="submenu">
          <router-link
            v-for="(child, i) in item.children"
            :key="i"
            :to="child.route"
            class="submenu-item"
            :class="{ active: isChildActive(child) }"
          >{{ child.label }}</router-link>
        </div>

        <!-- 折叠态:hover 弹出二级 flyout -->
        <div v-if="collapsed && item.children && hoverKey === item.key" class="flyout">
          <div class="flyout-title">{{ item.label }}</div>
          <router-link
            v-for="(child, i) in item.children"
            :key="i"
            :to="child.route"
            class="flyout-item"
            :class="{ active: isChildActive(child) }"
            @click="onSelect(item)"
          >{{ child.label }}</router-link>
        </div>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ChevronRight } from 'lucide-vue-next'
import { menuConfigs, type MenuConfig, type MenuChild } from '@/config/menu'

const props = defineProps<{
  collapsed: boolean
  selectedKeys: string[]
}>()

const emit = defineEmits<{
  select: [key: string]
}>()

const route = useRoute()
/** 手风琴:当前展开的模块 key(一次一个) */
const expandedKey = ref<string | null>(null)
/** 折叠态下 hover 的模块 key(控制 flyout 显隐) */
const hoverKey = ref<string | null>(null)

/** 当前路由命中的模块 key(用于自动展开所在模块) */
const currentModuleKey = computed(() => {
  for (const c of menuConfigs) {
    if (route.path === c.route) return c.key
    if (c.matchPrefixes?.some(p => route.path.startsWith(p))) return c.key
    // 内联 isChildActive 逻辑(避免引用在后方声明的函数触发 TDZ)
    if (c.children?.some(ch => ch.exact ? route.path === ch.route : route.path === ch.route || route.path.startsWith(ch.route + '/'))) return c.key
  }
  return undefined
})

// 跟随路由自动展开当前模块(手风琴:进入某模块即展开它,其余收起)
watch(currentModuleKey, k => { if (k) expandedKey.value = k }, { immediate: true })

const isExpanded = (item: MenuConfig) => expandedKey.value === item.key

const isChildActive = (child: MenuChild) => {
  if (child.exact) return route.path === child.route
  return route.path === child.route || route.path.startsWith(child.route + '/')
}

/** 一级项跳转目标:有 children 的模块落到第一个子项,无则主路由 */
const firstChildRoute = (item: MenuConfig): string => {
  if (!item.children?.length) return item.route
  return item.children[0].route
}

const onSelect = (item: MenuConfig) => {
  emit('select', item.key)
  // 点击一级 = 展开该模块;导航到子项后 watch(currentModuleKey) 保持展开
  if (item.children?.length) {
    expandedKey.value = item.key
  }
}

const onHover = (item: MenuConfig) => {
  if (props.collapsed && item.children?.length) hoverKey.value = item.key
}
const onLeave = () => { hoverKey.value = null }
</script>

<style scoped>
.sider {
  width: 220px;
  background: hsl(var(--card));
  border-right: 1px solid hsl(var(--border));
  display: flex;
  flex-direction: column;
  transition: width 0.2s;
  flex-shrink: 0;
  position: relative;
  z-index: 20;
}

.sider.collapsed {
  width: 64px;
}

.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 18px;
  font-weight: bold;
  color: hsl(var(--primary));
  border-bottom: 1px solid hsl(var(--border));
}

.logo img {
  width: 32px;
  height: 32px;
}

.logo span {
  white-space: nowrap;
}

.sider.collapsed .logo span {
  display: none;
}

.menu {
  flex: 1;
  overflow-y: auto;
  overflow-x: visible;
  padding: 8px 0;
}

/* 折叠态允许 flyout 溢出 sider 显示 */
.sider.collapsed .menu {
  overflow: visible;
}

.menu-section {
  position: relative;
}

.menu-item {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  position: relative;
  gap: 4px;
}

.menu-item:hover {
  background: hsl(var(--border));
  color: hsl(var(--foreground));
}

.menu-item.selected {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.menu-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.menu-icon :deep(svg) {
  width: 16px;
  height: 16px;
}

.menu-label {
  font-size: 14px;
  white-space: nowrap;
}

.sider.collapsed .menu-label {
  display: none;
}

.sider.collapsed .menu-item {
  justify-content: center;
  padding: 10px 0;
}

.chevron {
  color: hsl(var(--muted-foreground));
  transition: transform 0.2s;
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(90deg);
}

/* 宽态:就地展开的二级菜单 */
.submenu {
  display: flex;
  flex-direction: column;
  padding: 2px 0 6px 0;
}

.submenu-item {
  display: block;
  padding: 7px 16px 7px 40px;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}

.submenu-item:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent));
}

.submenu-item.active {
  color: hsl(var(--primary));
  font-weight: 500;
}

/* 折叠态:hover flyout */
.flyout {
  position: absolute;
  left: 100%;
  top: 0;
  min-width: 180px;
  margin-left: 4px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: 8px;
  box-shadow: 0 8px 24px hsl(var(--foreground) / 0.12);
  padding: 6px;
  z-index: 50;
}

.flyout-title {
  padding: 6px 10px 8px 10px;
  font-size: 12px;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  border-bottom: 1px solid hsl(var(--border));
  margin-bottom: 4px;
}

.flyout-item {
  display: block;
  padding: 7px 10px;
  border-radius: 6px;
  color: hsl(var(--foreground));
  font-size: 13px;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}

.flyout-item:hover {
  background: hsl(var(--accent));
}

.flyout-item.active {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
  font-weight: 500;
}
</style>
