<script setup lang="ts">
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

withDefaults(
  defineProps<{
    open: boolean
    title: string
    description?: string
    danger?: boolean
    confirmText?: string
    cancelText?: string
    loading?: boolean
  }>(),
  {
    confirmText: '确定',
    cancelText: '取消',
    loading: false,
  },
)

const emit = defineEmits<{
  'update:open': [boolean]
  confirm: []
  cancel: []
}>()

// 取消按钮:关窗 + 通知父(父可选监听做清理)
const onCancel = () => {
  emit('cancel')
  emit('update:open', false)
}
// 确认交父执行(父在异步操作完成后关闭,loading 期间保持开)
const onConfirm = () => emit('confirm')
// ESC 关闭(radix 触发)视为取消;遮罩点击已被 interact-outside.prevent 拦截
const onOpenChange = (v: boolean) => {
  if (!v) emit('cancel')
  emit('update:open', v)
}
</script>

<template>
  <DialogRoot :open="open" @update:open="onOpenChange">
    <DialogPortal>
      <DialogOverlay />
      <DialogContent class="confirm-dialog-content" @interact-outside.prevent>
        <DialogTitle class="confirm-dialog-title">
          {{ title }}
        </DialogTitle>
        <DialogDescription v-if="description" class="confirm-dialog-desc">
          {{ description }}
        </DialogDescription>
        <div class="confirm-dialog-actions">
          <Button
            variant="outline"
            :disabled="loading"
            @click="onCancel"
          >
            {{ cancelText }}
          </Button>
          <Button
            :variant="danger ? 'destructive' : 'default'"
            :disabled="loading"
            @click="onConfirm"
          >
            {{ confirmText }}
          </Button>
        </div>
      </DialogContent>
    </DialogPortal>
  </DialogRoot>
</template>

<style scoped>
.confirm-dialog-content {
  max-width: 420px;
}

.confirm-dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.confirm-dialog-desc {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
  line-height: 1.6;
  margin: 0;
}

.confirm-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
