<script setup lang="ts">
import { computed } from 'vue'
import { DialogOverlay as RadixDialogOverlay } from 'radix-vue'
import { type DialogOverlayProps } from 'radix-vue'
import { cn } from '@/lib/utils'

const props = defineProps<DialogOverlayProps>()

const overlayClass = computed(() =>
  cn(
    'fixed inset-0 z-50 bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0'
  )
)
</script>

<template>
  <RadixDialogOverlay v-bind="props" :class="overlayClass" />
</template>
