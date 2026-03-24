<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'

export interface DialogFooterProps {
  class?: string
}

const props = withDefaults(defineProps<DialogFooterProps>(), {
  class: ''
})

const footerClass = computed(() =>
  cn('flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2', props.class)
)
</script>

<template>
  <div :class="footerClass" v-bind="$attrs">
    <slot />
  </div>
</template>
