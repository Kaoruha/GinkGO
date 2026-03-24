<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableRowProps {
  class?: string
}

const props = withDefaults(defineProps<TableRowProps>(), {
  class: ''
})

const tableRowClass = computed(() =>
  cn('border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted', props.class)
)
</script>

<template>
  <tr :class="tableRowClass" v-bind="$attrs">
    <slot />
  </tr>
</template>
