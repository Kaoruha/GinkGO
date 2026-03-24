<script setup lang="ts">
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { type HTMLAttributes } from 'vue'

export interface InputProps {
  class?: HTMLAttributes['class']
  type?: string
  modelValue?: string
  placeholder?: string
  disabled?: boolean
  readonly?: boolean
  id?: string
  name?: string
}

const props = withDefaults(defineProps<InputProps>(), {
  type: 'text',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const inputClass = computed(() =>
  cn(
    'flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
    props.class
  )
)

const onInput = (e: Event) => {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <input
    :id="id"
    :name="name"
    :type="type"
    :class="inputClass"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    @input="onInput"
    v-bind="$attrs"
  />
</template>
