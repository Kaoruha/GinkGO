<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface TableProps {
  class?: string
}

const props = withDefaults(defineProps<TableProps>(), {
  class: ''
})

const tableClass = computed(() =>
  cn('w-full caption-bottom text-sm', props.class)
)
</script>

<template>
  <div class="relative w-full overflow-auto">
    <table :class="tableClass" v-bind="$attrs">
      <slot />
    </table>
  </div>
</template>
