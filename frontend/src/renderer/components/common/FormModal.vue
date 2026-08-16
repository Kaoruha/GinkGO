<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="modal-overlay"
      @click.self="onOverlay"
    >
      <!-- form 即 .modal 本体:Enter 提交与 footer 的 type=submit 天然关联 -->
      <form
        class="modal"
        :class="sizeClass"
        @submit.prevent="emit('submit')"
      >
        <div class="modal-header">
          <h3>{{ title }}</h3>
          <button
            type="button"
            class="modal-close"
            @click="onCancel"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <slot />
        </div>
        <div
          v-if="!hideFooter"
          class="modal-footer"
        >
          <slot name="footer">
            <button
              type="button"
              class="btn-secondary"
              :disabled="loading"
              @click="onCancel"
            >
              {{ cancelText }}
            </button>
            <button
              type="submit"
              class="btn-primary"
              :disabled="loading || disabled"
            >
              {{ loading ? loadingText : confirmText }}
            </button>
          </slot>
        </div>
      </form>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
/**
 * 通用表单弹窗:封装 modals.less 全局类名(.modal-overlay/.modal/.modal-{small,wide,large})
 * 提交不自动关闭 —— submit 只派发事件,父级成功后自行置 open=false
 */
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  /** v-model:open */
  open: boolean
  title: string
  /** sm=400 md=500(默认) lg=800 xl=1200 */
  size?: 'sm' | 'md' | 'lg' | 'xl'
  confirmText?: string
  cancelText?: string
  /** 提交中:按钮禁用 + 文案切换 */
  loading?: boolean
  /** 提交按钮额外禁用(校验不过时) */
  disabled?: boolean
  loadingText?: string
  /** 点击遮罩关闭(默认开;loading 中强制不可关) */
  closeOnOverlay?: boolean
  /** 隐藏底部按钮区(纯展示弹窗/自定义 footer) */
  hideFooter?: boolean
}>(), {
  size: 'md',
  confirmText: '确定',
  cancelText: '取消',
  loading: false,
  disabled: false,
  loadingText: '处理中...',
  closeOnOverlay: true,
  hideFooter: false,
})

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
  (e: 'submit'): void
  (e: 'cancel'): void
}>()

const SIZE_CLASS: Record<string, string> = {
  sm: 'modal-small',
  md: '',
  lg: 'modal-wide',
  xl: 'modal-large',
}

const sizeClass = computed(() => SIZE_CLASS[props.size] ?? '')

const onOverlay = () => {
  if (props.closeOnOverlay && !props.loading) onCancel()
}

const onCancel = () => {
  emit('update:open', false)
  emit('cancel')
}
</script>
