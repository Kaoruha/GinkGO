<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardDescriptionProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardDescriptionProps>()

const cardDescriptionClass = computed(() =>
  cn('text-sm text-muted-foreground', props.class)
)
</script>

<template>
  <p :class="cardDescriptionClass" v-bind="$attrs">
    <slot />
  </p>
</template>
