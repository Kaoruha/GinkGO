<template>
  <PageLayout>
    <template #title>
      告警中心
    </template>

    <div class="card">
      <EmptyState
        title="功能开发中"
        description="告警中心尚未开放，敬请期待"
      />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
// 告警中心页面 - 占位实现
</script>
