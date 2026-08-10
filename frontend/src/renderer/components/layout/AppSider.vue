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
      >
        <router-link
          :to="item.route"
          class="menu-item"
          :class="{ selected: selectedKeys.includes(item.key) }"
          :data-testid="`nav-${item.key}`"
          @click="$emit('select', item.key)"
        >
          <div class="menu-item-content">
            <component :is="item.icon" class="menu-icon" :size="16" v-if="item.icon" />
            <span class="menu-label">{{ item.label }}</span>
          </div>
        </router-link>
      </div>
    </nav>
  </div>
</template>

<script setup lang="ts">
import { menuConfigs } from '@/config/menu'

defineProps<{
  collapsed: boolean
  selectedKeys: string[]
}>()

defineEmits<{
  select: [key: string]
}>()
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
  padding: 8px 0;
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
</style>
