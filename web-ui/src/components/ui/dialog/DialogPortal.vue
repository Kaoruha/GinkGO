<script setup lang="ts">
// DialogPortal.vue（shadcn-vue UI 组件）
import { DialogPortal as RadixDialogPortal, type DialogPortalProps } from 'radix-vue'

const props = defineProps<DialogPortalProps>()
</script>

<template>
  <RadixDialogPortal v-bind="props">
    <slot />
  </RadixDialogPortal>
</template>
