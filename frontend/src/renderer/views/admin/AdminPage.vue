<template>
  <!-- 组件库(6 项,≥5 → 侧栏):策略/风控/仓位/选股器/分析器/事件处理器 -->
  <SubNavLayout :items="items" title="组件库" padded>
    <router-view />
  </SubNavLayout>
</template>

<script setup lang="ts">
import SubNavLayout from '@/components/common/SubNavLayout.vue'
import type { SubNavItem } from '@/components/common/SubNavLayout.vue'

const items: SubNavItem[] = [
  { label: '策略组件', route: '/components/strategies' },
  { label: '风控组件', route: '/components/risks' },
  { label: '仓位组件', route: '/components/sizers' },
  { label: '选股器', route: '/components/selectors' },
  { label: '分析器', route: '/components/analyzers' },
  { label: '事件处理器', route: '/components/handlers' },
]
</script>
