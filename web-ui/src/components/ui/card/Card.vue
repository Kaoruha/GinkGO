<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardProps>()

const cardClass = computed(() =>
  cn('rounded-lg border bg-card text-card-foreground shadow-sm', props.class)
)
</script>

<template>
  <div :class="cardClass" v-bind="$attrs">
    <slot />
  </div>
</template>
