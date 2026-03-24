<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardContentProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardContentProps>()

const cardContentClass = computed(() =>
  cn('p-6 pt-0', props.class)
)
</script>

<template>
  <div :class="cardContentClass" v-bind="$attrs">
    <slot />
  </div>
</template>
