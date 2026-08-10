<script setup lang="ts">
import { DialogClose as RadixDialogClose, type DialogCloseProps } from 'radix-vue'

const props = defineProps<DialogCloseProps>()
</script>

<template>
  <RadixDialogClose v-bind="props">
    <slot />
  </RadixDialogClose>
</template>
