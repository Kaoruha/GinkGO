<script setup lang="ts">
// Label.vue（shadcn-vue UI 组件）
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface LabelProps {
  class?: HTMLAttributes['class']
  htmlFor?: string
}

const props = defineProps<LabelProps>()

const labelClass = computed(() =>
  cn(
    'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
    props.class
  )
)
</script>

<template>
  <label :class="labelClass" :for="htmlFor" v-bind="$attrs">
    <slot />
  </label>
</template>
