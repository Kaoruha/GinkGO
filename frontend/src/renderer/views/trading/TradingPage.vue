<template>
  <!-- 交易(2 项,≤4 → 顶部 tab):模拟盘/实盘。实盘进子页时保持高亮(前缀匹配) -->
  <SubNavLayout :items="items">
    <router-view />
  </SubNavLayout>
</template>

<script setup lang="ts">
import SubNavLayout from '@/components/common/SubNavLayout.vue'
import type { SubNavItem } from '@/components/common/SubNavLayout.vue'

const items: SubNavItem[] = [
  { label: '模拟盘', route: '/trading/paper' },
  { label: '实盘', route: '/trading/live' },
]
</script>
