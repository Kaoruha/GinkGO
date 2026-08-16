<template>
  <div
    class="sider"
    :class="{ collapsed }"
  >
    <div class="logo">
      <!-- 内联银杏叶品牌标:极简剪影,与 public/favicon.svg 同源 -->
      <svg
        class="logo-mark"
        viewBox="8 6 84 96"
        aria-hidden="true"
      >
        <path
          class="leaf-body"
          d="M50 64
          C38 58 12 50 12 30
          C12 14 26 8 36 14
          C42 17 46 22 50 30
          C54 22 58 17 64 14
          C74 8 88 14 88 30
          C88 50 62 58 50 64 Z"
        />
        <path
          class="leaf-stem"
          d="M50 64 C50 75 50 86 50 98"
          fill="none"
          stroke-linecap="round"
        />
      </svg>
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
        <!-- 一级:有 children 仅展开二级(不导航),无 children 直达主路由 -->
        <router-link
          v-if="!item.children?.length"
          :to="item.route"
          class="menu-item no-flyout"
          :class="{ selected: selectedKeys.includes(item.key) }"
          :data-label="item.label"
          :data-testid="`nav-${item.key}`"
          @click="onSelect(item)"
        >
          <div class="menu-item-content">
            <component
              :is="item.icon"
              v-if="item.icon"
              class="menu-icon"
              :size="16"
            />
            <span class="menu-label">{{ item.label }}</span>
          </div>
        </router-link>
        <button
          v-else
          type="button"
          class="menu-item"
          :class="{ selected: selectedKeys.includes(item.key) }"
          :data-label="item.label"
          :data-testid="`nav-${item.key}`"
          :aria-expanded="isExpanded(item)"
          @click="toggleExpand(item)"
        >
          <div class="menu-item-content">
            <component
              :is="item.icon"
              v-if="item.icon"
              class="menu-icon"
              :size="16"
            />
            <span class="menu-label">{{ item.label }}</span>
          </div>
          <ChevronRight
            v-if="!collapsed"
            class="chevron"
            :class="{ open: isExpanded(item) }"
            :size="14"
          />
        </button>

        <!-- 宽态:就地展开二级(手风琴,一次只展开一个模块)。
             持久 wrapper + grid-rows 高度过渡,避免收起时下方项瞬移 -->
        <div
          v-if="item.children && !collapsed"
          class="submenu-wrap"
          :class="{ open: isExpanded(item) }"
        >
          <div class="submenu">
            <router-link
              v-for="(child, i) in item.children"
              :key="i"
              :to="child.route"
              class="submenu-item"
              :class="{ active: isChildActive(child) }"
              :tabindex="isExpanded(item) ? undefined : -1"
            >
              {{ child.label }}
            </router-link>
          </div>
        </div>

        <!-- 折叠态:hover 弹出二级 flyout -->
        <Transition name="flyout">
          <div
            v-if="collapsed && item.children && hoverKey === item.key"
            class="flyout"
          >
            <div class="flyout-title">
              {{ item.label }}
            </div>
            <router-link
              v-for="(child, i) in item.children"
              :key="i"
              :to="child.route"
              class="flyout-item"
              :class="{ active: isChildActive(child) }"
              @click="onSelect(item)"
            >
              {{ child.label }}
            </router-link>
          </div>
        </Transition>
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

/** 一级(有 children)点击 = 仅手风琴展开/收起,导航交给二级菜单 */
const toggleExpand = (item: MenuConfig) => {
  expandedKey.value = isExpanded(item) ? null : item.key
}

const onSelect = (item: MenuConfig) => {
  emit('select', item.key)
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
  transition: width var(--dur-normal, 0.2s) var(--ease-out, ease-out);
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

.logo-mark {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
}

/* 银杏叶品牌标:纯剪影单色(双主题均可读;与 favicon 同源) */
.leaf-body {
  fill: #4c8a5c;
}

.leaf-stem {
  stroke: #4c8a5c;
  stroke-width: 5;
}

.logo span {
  white-space: nowrap;
  overflow: hidden;
  transition: opacity var(--dur-fast, 0.15s) ease, width var(--dur-normal, 0.2s) var(--ease-out, ease-out);
}

.sider.collapsed .logo span {
  opacity: 0;
  width: 0;
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

/* button 渲染的一级项(有 children)需重置默认样式,与 router-link 版对齐 */
button.menu-item {
  width: 100%;
  border: none;
  background: none;
  font: inherit;
  text-align: left;
}

.menu-item:focus-visible {
  outline: 2px solid hsl(var(--primary) / 0.5);
  outline-offset: -2px;
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
  gap: 12px;
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
  overflow: hidden;
  transition: opacity var(--dur-fast, 0.15s) ease, width var(--dur-normal, 0.2s) var(--ease-out, ease-out);
}

.sider.collapsed .menu-label {
  opacity: 0;
  width: 0;
}

.sider.collapsed .menu-item {
  justify-content: center;
  padding: 10px 0;
}

/* 折叠态:content 占满整行(flex:1),必须自身居中且去掉 icon 与 0 宽 label 之间的 gap,否则图标贴左缘 */
.sider.collapsed .menu-item-content {
  justify-content: center;
  gap: 0;
}

/* 折叠态 tooltip:无 children 的一级项 hover 显示文字(有 children 的走 flyout,标题即模块名) */
.sider.collapsed .menu-item.no-flyout::after {
  content: attr(data-label);
  position: absolute;
  left: calc(100% + 8px);
  top: 50%;
  transform: translateY(-50%) translateX(-4px);
  padding: 5px 10px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  box-shadow: var(--shadow-lg);
  color: hsl(var(--foreground));
  font-size: 13px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  z-index: 50;
  transition: opacity var(--dur-fast, 0.15s) var(--ease-out, ease-out), transform var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}

.sider.collapsed .menu-item.no-flyout:hover::after {
  opacity: 1;
  transform: translateY(-50%) translateX(0);
}

.chevron {
  color: hsl(var(--muted-foreground));
  transition: transform 0.2s;
  flex-shrink: 0;
}

.chevron.open {
  transform: rotate(90deg);
}

/* 宽态:就地展开的二级菜单。
   grid-template-rows 0fr→1fr 让高度随内容平滑过渡(收起时下方项不再跳位) */
.submenu-wrap {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows var(--dur-normal, 0.2s) var(--ease-out, ease-out);
}

.submenu-wrap.open {
  grid-template-rows: 1fr;
}

.submenu {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
  padding: 2px 0 6px 0;
  opacity: 0;
  transition: opacity var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}

.submenu-wrap.open .submenu {
  opacity: 1;
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
  background: hsl(var(--primary) / 0.1);
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
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
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
  border-radius: var(--radius);
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

/* 折叠态 flyout 弹出/收起 */
.flyout-enter-active,
.flyout-leave-active {
  transition: opacity var(--dur-fast, 0.15s) var(--ease-out, ease-out), transform var(--dur-fast, 0.15s) var(--ease-out, ease-out);
}
.flyout-enter-from,
.flyout-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .sider,
  .logo span,
  .menu-label,
  .submenu-wrap,
  .submenu,
  .flyout-enter-active,
  .flyout-leave-active,
  .sider.collapsed .menu-item.no-flyout::after {
    transition: none;
  }
}
</style>
