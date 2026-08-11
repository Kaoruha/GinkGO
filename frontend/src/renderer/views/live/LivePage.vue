<template>
  <!-- 实盘(6 项,≥5 → 侧栏):概览/账号配置/账户监控/Broker/行情/交易历史。
       '/trading/live' exact,避免在所有 live 子页都高亮概览。
       原 tab(6 项横排) 按自适应规则改为侧栏 -->
  <SubNavLayout :items="items">
    <router-view />
  </SubNavLayout>
</template>

<script setup lang="ts">
import SubNavLayout from '@/components/common/SubNavLayout.vue'
import type { SubNavItem } from '@/components/common/SubNavLayout.vue'

const items: SubNavItem[] = [
  { label: '概览', route: '/trading/live', exact: true },
  { label: '账号配置', route: '/trading/live/accounts' },
  { label: '账户监控', route: '/trading/live/monitor' },
  { label: 'Broker', route: '/trading/live/brokers' },
  { label: '行情', route: '/trading/live/market' },
  { label: '交易历史', route: '/trading/live/history' },
]
</script>
