<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableCellProps {
  class?: string
}

const props = withDefaults(defineProps<TableCellProps>(), {
  class: ''
})

const cellClass = computed(() =>
  cn('p-4 align-middle [&:has([role=checkbox])]:pr-0', props.class)
)
</script>

<template>
  <td :class="cellClass" v-bind="$attrs">
    <slot />
  </td>
</template>
