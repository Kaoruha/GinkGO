<script setup lang="ts">
import { DialogRoot as RadixDialogRoot, useForwardPropsEmits } from 'radix-vue'
import type { DialogRootEmits, DialogRootProps } from 'radix-vue'

const props = defineProps<DialogRootProps>()
const emits = defineEmits<DialogRootEmits>()

const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <RadixDialogRoot v-bind="forwarded">
    <slot />
  </RadixDialogRoot>
</template>
