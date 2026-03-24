<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardFooterProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardFooterProps>()

const cardFooterClass = computed(() =>
  cn('flex items-center p-6 pt-0', props.class)
)
</script>

<template>
  <div :class="cardFooterClass" v-bind="$attrs">
    <slot />
  </div>
</template>
