<template>
  <header class="header">
    <div class="header-left">
      <button
        class="trigger"
        @click="$emit('toggle')"
      >
        <svg
          v-if="collapsed"
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
            ry="2"
          />
          <line
            x1="9"
            y1="3"
            x2="9"
            y2="21"
          />
        </svg>
        <svg
          v-else
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <rect
            x="3"
            y="3"
            width="18"
            height="18"
            rx="2"
            ry="2"
          />
          <line
            x1="15"
            y1="3"
            x2="15"
            y2="21"
          />
        </svg>
      </button>
      <nav class="breadcrumb">
        <span
          v-for="item in breadcrumbs"
          :key="item.path"
          class="breadcrumb-item"
        >
          {{ item.title }}
        </span>
      </nav>
    </div>
    <div class="header-right">
      <button
        class="notification-btn"
        @click="showNotifications"
      >
        <span
          class="notification-badge"
          :class="{ 'has-count': notificationCount > 0 }"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span
            v-if="notificationCount > 0"
            class="count"
          >{{ notificationCount }}</span>
        </span>
      </button>
      <ThemeToggle />
      <div class="user-dropdown">
        <button
          class="avatar-btn"
          data-testid="user-menu-btn"
          @click="toggleUserMenu"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle
              cx="12"
              cy="7"
              r="4"
            />
          </svg>
        </button>
        <div
          class="dropdown-menu"
          :class="{ show: showUserMenu }"
        >
          <div class="dropdown-item user-info">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle
                cx="12"
                cy="7"
                r="4"
              />
            </svg>
            {{ authStore.displayName || '用户' }}
          </div>
          <div class="dropdown-divider" />
          <button
            class="dropdown-item"
            @click="goSettings"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <circle
                cx="12"
                cy="12"
                r="3"
              />
              <path d="M12 1v6m0 6v6" />
              <path d="m19 21-7-5 7-5" />
            </svg>
            系统设置
          </button>
          <button
            class="dropdown-item text-danger"
            data-testid="logout-btn"
            @click="handleLogout"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line
                x1="21"
                y1="12"
                x2="9"
                y2="12"
              />
            </svg>
            退出登录
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ThemeToggle } from '@/components/common'

defineProps<{
  collapsed: boolean
}>()

defineEmits<{
  toggle: []
}>()

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const showUserMenu = ref(false)
const notificationCount = ref(0)

const breadcrumbs = computed(() =>
  route.matched
    .filter(r => r.meta?.title)
    .map(r => ({ path: r.path, title: r.meta!.title as string }))
)

const toggleUserMenu = () => {
  showUserMenu.value = !showUserMenu.value
}

const handleClickOutside = (event: MouseEvent) => {
  const dropdown = document.querySelector('.user-dropdown')
  if (dropdown && !dropdown.contains(event.target as Node)) {
    showUserMenu.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

const showNotifications = () => {
  // TODO: 通知面板待实现
}

const goSettings = () => {
  showUserMenu.value = false
  router.push('/admin')
}

const handleLogout = async () => {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.header {
  height: 64px;
  background: hsl(var(--card));
  border-bottom: 1px solid hsl(var(--border));
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.trigger {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
  border-radius: var(--radius-sm);
  transition: all 0.2s;
}

.trigger:hover {
  background: hsl(var(--border));
  color: hsl(var(--primary));
}

.breadcrumb {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

.breadcrumb-item:not(:last-child)::after {
  content: '/';
  margin-left: 8px;
  color: hsl(var(--secondary));
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.notification-btn {
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  color: hsl(var(--muted-foreground));
}

.notification-badge {
  position: relative;
  display: block;
}

.notification-badge .count {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  background: hsl(var(--error));
  color: hsl(var(--foreground));
  font-size: 10px;
  line-height: 16px;
  text-align: center;
  border-radius: var(--radius-lg);
}

.avatar-btn {
  width: 32px;
  height: 32px;
  background: hsl(var(--primary));
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: hsl(var(--primary-foreground));
}

.user-dropdown {
  position: relative;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  min-width: 160px;
  box-shadow: var(--shadow-md);
  display: none;
  z-index: 100;
}

.dropdown-menu.show {
  display: block;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  color: hsl(var(--foreground));
  font-size: 13px;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s;
}

.dropdown-item:hover {
  background: hsl(var(--border));
}

.dropdown-item.user-info {
  cursor: default;
}

.dropdown-item.text-danger {
  color: hsl(var(--error));
}

.dropdown-divider {
  height: 1px;
  background: hsl(var(--border));
  margin: 4px 0;
}
</style>
