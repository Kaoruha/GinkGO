<script setup lang="ts">
import { DialogPortal as RadixDialogPortal, type DialogPortalProps } from 'radix-vue'

const props = defineProps<DialogPortalProps>()
</script>

<template>
  <RadixDialogPortal v-bind="props">
    <slot />
  </RadixDialogPortal>
</template>
