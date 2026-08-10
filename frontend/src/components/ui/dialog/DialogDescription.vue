<script setup lang="ts">
import { computed } from 'vue'
import { DialogDescription as RadixDialogDescription, type DialogDescriptionProps as RadixDialogDescriptionProps } from 'radix-vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface DialogDescriptionProps extends RadixDialogDescriptionProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<DialogDescriptionProps>()

const descriptionClass = computed(() =>
  cn('text-sm text-muted-foreground', props.class)
)
</script>

<template>
  <RadixDialogDescription v-bind="props" :class="descriptionClass">
    <slot />
  </RadixDialogDescription>
</template>
