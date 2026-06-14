<script setup lang="ts">
// TableHeader.vue（shadcn-vue UI 组件）
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableHeaderProps {
  class?: string
}

const props = withDefaults(defineProps<TableHeaderProps>(), {
  class: ''
})

const tableHeaderClass = computed(() =>
  cn('border-b bg-muted/50', props.class)
)
</script>

<template>
  <tr :class="tableHeaderClass" v-bind="$attrs">
    <slot />
  </tr>
</template>
