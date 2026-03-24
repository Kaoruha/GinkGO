<script setup lang="ts">
import { computed } from 'vue'
import { DialogTitle as RadixDialogTitle, type DialogTitleProps as RadixDialogTitleProps } from 'radix-vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface DialogTitleProps extends RadixDialogTitleProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<DialogTitleProps>()

const titleClass = computed(() =>
  cn('text-lg font-semibold leading-none tracking-tight', props.class)
)
</script>

<template>
  <RadixDialogTitle v-bind="props" :class="titleClass">
    <slot />
  </RadixDialogTitle>
</template>
