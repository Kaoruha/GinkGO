<template>
  <div class="admin-page">
    <div class="admin-sidebar">
      <div class="admin-nav-group">
        <div class="admin-nav-title">系统管理</div>
        <router-link
          v-for="item in systemItems"
          :key="item.route"
          :to="item.route"
          class="admin-nav-item"
          :class="{ active: isActive(item.route) }"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
    <div class="admin-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const systemItems = [
  { label: '系统状态', route: '/admin' },
  { label: 'Worker 管理', route: '/admin/workers' },
  { label: 'API Key', route: '/admin/api-keys' },
  { label: '用户管理', route: '/admin/users' },
  { label: '用户组', route: '/admin/groups' },
  { label: '通知管理', route: '/admin/notifications' },
  { label: '告警中心', route: '/admin/alerts' },
]

const isActive = (itemRoute: string) => {
  if (itemRoute === '/admin') {
    return route.path === '/admin'
  }
  return route.path.startsWith(itemRoute)
}
</script>

<style scoped>
.admin-page {
  display: flex;
  height: 100%;
}
.admin-sidebar {
  width: 180px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  padding: 16px 0;
  overflow-y: auto;
}
.admin-nav-group {
  margin-bottom: 16px;
}
.admin-nav-title {
  padding: 6px 20px;
  font-size: 11px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.4);
  letter-spacing: 0.5px;
}
.admin-nav-item {
  display: block;
  padding: 8px 20px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.2s;
}
.admin-nav-item:hover {
  color: rgba(255,255,255,0.9);
  background: rgba(255,255,255,0.05);
}
.admin-nav-item.active {
  color: #3b82f6;
  background: rgba(59,130,246,0.1);
  border-right: 2px solid #3b82f6;
}
.admin-content {
  flex: 1;
  overflow: auto;
}
</style>
