<template>
  <a-form
    ref="formRef"
    :model="formState"
    :rules="rules"
    :layout="layout"
    :label-col="labelCol"
    :wrapper-col="wrapperCol"
    :class="['pro-form', sizeClass]"
  >
    <template v-if="showActions" #footer>
      <div class="form-actions">
        <a-space>
          <a-button @click="handleReset">重置</a-button>
          <a-button type="primary" :loading="submitting" @click="handleSubmit">
            {{ submitText }}
          </a-button>
        </a-space>
      </div>
    </template>

    <slot />
  </a-form>
</template>

<script setup lang="ts">
import { ref, computed, provide, reactive } from 'vue'
import type { FormInstance, FormProps } from 'ant-design-vue'

interface Props {
  modelValue?: Record<string, any>
  layout?: FormProps['layout']
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

const formRef = ref<FormInstance>()
const submitting = ref(false)

const formState = reactive<Record<string, any>>({ ...props.modelValue })

const sizeClass = computed(() => `pro-form--${props.size}`)

const handleSubmit = async () => {
  try {
    await formRef.value?.validate()
    submitting.value = true
    emit('submit', { ...formState })
    emit('update:modelValue', { ...formState })
  } catch (error) {
    console.error('Form validation failed:', error)
  } finally {
    submitting.value = false
  }
}

const handleReset = () => {
  formRef.value?.resetFields()
  Object.keys(formState).forEach(key => {
    formState[key] = props.modelValue[key] ?? undefined
  })
  emit('reset')
}

const validate = () => formRef.value?.validate()
const resetFields = () => formRef.value?.resetFields()
const clearValidate = () => formRef.value?.clearValidate()

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
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
  margin-top: 16px;
}
</style>
