<script setup lang="ts">
import { computed } from 'vue'
import { DialogRoot, DialogPortal, DialogOverlay, DialogContent, DialogHeader, DialogTitle } from './index'
import { X } from 'lucide-vue-next'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface SimpleDialogProps {
  open?: boolean
  class?: HTMLAttributes['class']
  title?: string
}

const props = withDefaults(defineProps<SimpleDialogProps>(), {
  open: false,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
}>()

const handleOpenChange = (open: boolean) => {
  emit('update:open', open)
}

const contentClass = computed(() =>
  cn(
    'fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 border bg-background p-6 shadow-lg duration-200 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%] sm:rounded-lg',
    props.class
  )
)
</script>

<template>
  <DialogRoot :open="open" @update:open="handleOpenChange">
    <DialogPortal>
      <DialogOverlay />
      <DialogContent :class="contentClass">
        <button
          class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none"
          @click="handleOpenChange(false)"
        >
          <X class="h-4 w-4" />
          <span class="sr-only">关闭</span>
        </button>

        <DialogHeader v-if="title">
          <DialogTitle>{{ title }}</DialogTitle>
        </DialogHeader>

        <slot />
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>
