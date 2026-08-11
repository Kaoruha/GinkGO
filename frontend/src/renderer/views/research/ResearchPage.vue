<template>
  <!-- 研究(2 项,≤4 → 顶部 tab):因子分析/参数优化 -->
  <SubNavLayout :items="items" padded>
    <router-view />
  </SubNavLayout>
</template>

<script setup lang="ts">
import SubNavLayout from '@/components/common/SubNavLayout.vue'
import type { SubNavItem } from '@/components/common/SubNavLayout.vue'

const items: SubNavItem[] = [
  { label: '因子分析', route: '/research/factor' },
  { label: '参数优化', route: '/research/optimization' },
]
</script>
