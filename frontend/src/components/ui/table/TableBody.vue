<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableBodyProps {
  class?: string
}

const props = withDefaults(defineProps<TableBodyProps>(), {
  class: ''
})

const tableBodyClass = computed(() =>
  cn('[&_tr:last-child]:border-0', props.class)
)
</script>

<template>
  <tbody :class="tableBodyClass" v-bind="$attrs">
    <slot />
  </tbody>
</template>
