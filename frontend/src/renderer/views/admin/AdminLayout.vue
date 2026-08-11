<template>
  <!-- 管理(8 项,≥5 → 侧栏):系统状态/Worker/APIKey/用户/组/通知/告警/定时。
       '/admin' exact 避免在所有子页都高亮 -->
  <SubNavLayout :items="items" title="系统管理" padded>
    <router-view />
  </SubNavLayout>
</template>

<script setup lang="ts">
import SubNavLayout from '@/components/common/SubNavLayout.vue'
import type { SubNavItem } from '@/components/common/SubNavLayout.vue'

const items: SubNavItem[] = [
  { label: '系统状态', route: '/admin', exact: true },
  { label: 'Worker 管理', route: '/admin/workers' },
  { label: 'API Key', route: '/admin/api-keys' },
  { label: '用户管理', route: '/admin/users' },
  { label: '用户组', route: '/admin/groups' },
  { label: '通知管理', route: '/admin/notifications' },
  { label: '告警中心', route: '/admin/alerts' },
  { label: '定时任务', route: '/admin/task-timer' },
]
</script>
