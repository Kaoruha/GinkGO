<template>
  <form
    ref="formRef"
    :class="['pro-form', sizeClass]"
    @submit.prevent="handleSubmit"
  >
    <slot />

    <div v-if="showActions" class="form-actions">
      <button type="button" class="btn-secondary" @click="handleReset">重置</button>
      <button type="submit" class="btn-primary" :disabled="submitting">
        {{ submitting ? '提交中...' : submitText }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref, computed, provide, reactive } from 'vue'

interface Props {
  modelValue?: Record<string, any>
  layout?: 'horizontal' | 'vertical' | 'inline'
  labelCol?: Record<string, number>
  wrapperCol?: Record<string, number>
  size?: 'small' | 'middle' | 'large'
  showActions?: boolean
  submitText?: string
  rules?: Record<string, any>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => ({}),
  layout: 'horizontal',
  labelCol: () => ({ span: 6 }),
  wrapperCol: () => ({ span: 18 }),
  size: 'middle',
  showActions: true,
  submitText: '提交',
  rules: () => ({}),
})

const emit = defineEmits<{
  (e: 'submit', values: Record<string, any>): void
  (e: 'reset'): void
  (e: 'update:modelValue', value: Record<string, any>): void
}>()

const formRef = ref<HTMLFormElement>()
const submitting = ref(false)

const formState = reactive<Record<string, any>>({ ...props.modelValue })

const sizeClass = computed(() => `pro-form--${props.size}`)

const handleSubmit = async () => {
  submitting.value = true
  emit('submit', { ...formState })
  emit('update:modelValue', { ...formState })
  submitting.value = false
}

const handleReset = () => {
  Object.keys(formState).forEach(key => {
    formState[key] = props.modelValue[key] ?? undefined
  })
  if (formRef.value) {
    formRef.value.reset()
  }
  emit('reset')
}

const validate = () => Promise.resolve(true)
const resetFields = () => handleReset()
const clearValidate = () => {}

provide('proForm', {
  formState,
  size: props.size,
})

defineExpose({
  validate,
  resetFields,
  clearValidate,
  formRef,
})
</script>

<style scoped>
.pro-form {
  width: 100%;
}

.pro-form--small {
  font-size: 12px;
}

.pro-form--middle {
  font-size: 14px;
}

.pro-form--large {
  font-size: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #2a2a3e;
  margin-top: 16px;
}

.btn-primary {
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}
</style>
