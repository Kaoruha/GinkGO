<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardHeaderProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardHeaderProps>()

const cardHeaderClass = computed(() =>
  cn('flex flex-col space-y-1.5 p-6', props.class)
)
</script>

<template>
  <div :class="cardHeaderClass" v-bind="$attrs">
    <slot />
  </div>
</template>
