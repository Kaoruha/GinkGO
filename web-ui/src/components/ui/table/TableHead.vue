<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableHeadProps {
  class?: string
}

const props = withDefaults(defineProps<TableHeadProps>(), {
  class: ''
})

const tableHeadClass = computed(() =>
  cn('h-10 px-2 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0 [&:[role=checkbox]]:text-center', props.class)
)
</script>

<template>
  <th :class="tableHeadClass" v-bind="$attrs">
    <slot />
  </th>
</template>
