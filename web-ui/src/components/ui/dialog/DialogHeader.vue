<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface DialogHeaderProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<DialogHeaderProps>()

const headerClass = computed(() =>
  cn('flex flex-col space-y-1.5 text-center sm:text-left', props.class)
)
</script>

<template>
  <div :class="headerClass" v-bind="$attrs">
    <slot />
  </div>
</template>
