<script setup lang="ts">
// CardTitle.vue（shadcn-vue UI 组件）
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface CardTitleProps {
  class?: HTMLAttributes['class']
}

const props = defineProps<CardTitleProps>()

const cardTitleClass = computed(() =>
  cn('text-2xl font-semibold leading-none tracking-tight', props.class)
)
</script>

<template>
  <h3 :class="cardTitleClass" v-bind="$attrs">
    <slot />
  </h3>
</template>
