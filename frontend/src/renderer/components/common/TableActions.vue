<template>
  <div class="table-actions" @click.stop>
    <template v-for="action in visibleActions" :key="action.key">
      <!-- 详情按钮 -->
      <router-link v-if="action.key === 'detail' && action.to" :to="action.to" class="action-link">
        {{ action.label || '详情' }}
      </router-link>
      <a v-else-if="action.key === 'detail'" class="action-link" @click="emit('action', 'detail', record)">
        {{ action.label || '详情' }}
      </a>

      <!-- 编辑按钮 -->
      <router-link v-if="action.key === 'edit' && action.to" :to="action.to" class="action-link">
        {{ action.label || '编辑' }}
      </router-link>
      <a v-else-if="action.key === 'edit'" class="action-link" @click="emit('action', 'edit', record)">
        {{ action.label || '编辑' }}
      </a>

      <!-- 删除按钮（带确认） -->
      <a
        v-if="action.key === 'delete'"
        class="action-link action-danger"
        @click="handleConfirm(action)"
      >
        {{ action.label || '删除' }}
      </a>

      <!-- 停止按钮（带确认） -->
      <a
        v-if="action.key === 'stop'"
        class="action-link action-danger"
        @click="handleConfirm(action)"
      >
        {{ action.label || '停止' }}
      </a>

      <!-- 自定义按钮 -->
      <a
        v-if="!['detail', 'edit', 'delete', 'stop'].includes(action.key)"
        class="action-link"
        :class="{ 'action-danger': action.danger }"
        @click="emit('action', action.key, record)"
      >
        {{ action.label }}
      </a>
    </template>
  </div>
  <ConfirmDialog
    v-model:open="confirmOpen"
    :title="confirmTitle"
    :description="confirmDesc"
    danger
    :confirm-text="pendingAction?.label || '确定'"
    @confirm="onConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

export interface TableAction {
  key: string
  label?: string
  to?: RouteLocationRaw
  confirm?: string
  danger?: boolean
  show?: boolean
}

const props = withDefaults(defineProps<{
  record: Record<string, any>
  actions: (string | TableAction)[]
}>(), {
  actions: () => ['detail', 'edit', 'delete'],
})

const emit = defineEmits<{
  action: [key: string, record: any]
}>()

const defaultLabels: Record<string, string> = {
  detail: '详情',
  edit: '编辑',
  delete: '删除',
  stop: '停止',
}

const visibleActions = computed(() => {
  return props.actions
    .map(action => {
      if (typeof action === 'string') {
        return { key: action, label: defaultLabels[action] || action }
      }
      return action
    })
    .filter(action => action.show !== false)
})

const confirmOpen = ref(false)
const pendingAction = ref<TableAction | null>(null)
const confirmTitle = computed(() => pendingAction.value ? `确认${pendingAction.value.label || pendingAction.value.key}` : '')
const confirmDesc = computed(() => pendingAction.value?.confirm || `确定要${pendingAction.value?.label || pendingAction.value?.key}吗？`)
const handleConfirm = (action: TableAction) => {
  pendingAction.value = action
  confirmOpen.value = true
}
const onConfirm = () => {
  if (pendingAction.value) emit('action', pendingAction.value.key, props.record)
  confirmOpen.value = false
}
</script>

<style scoped>
.table-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.action-link {
  color: hsl(var(--primary));
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}

.action-link:hover {
  text-decoration: underline;
}

.action-danger {
  color: hsl(var(--error));
}

.action-danger:hover {
  text-decoration: underline;
}
</style>
