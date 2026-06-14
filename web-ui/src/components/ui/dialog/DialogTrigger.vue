<script setup lang="ts">
// DialogTrigger.vue（shadcn-vue UI 组件）
import { DialogTrigger as RadixDialogTrigger, type DialogTriggerProps } from 'radix-vue'

const props = defineProps<DialogTriggerProps>()
</script>

<template>
  <RadixDialogTrigger v-bind="props">
    <slot />
  </RadixDialogTrigger>
</template>
