<template>
  <a-space @click.stop>
    <template v-for="action in visibleActions" :key="action.key">
      <!-- 详情按钮 -->
      <router-link v-if="action.key === 'detail' && action.to" :to="action.to">
        <a-button type="link" size="small">{{ action.label || '详情' }}</a-button>
      </router-link>
      <a-button v-else-if="action.key === 'detail'" type="link" size="small" @click="emit('action', 'detail', record)">
        {{ action.label || '详情' }}
      </a-button>

      <!-- 编辑按钮 -->
      <router-link v-if="action.key === 'edit' && action.to" :to="action.to">
        <a-button type="link" size="small">{{ action.label || '编辑' }}</a-button>
      </router-link>
      <a-button v-else-if="action.key === 'edit'" type="link" size="small" @click="emit('action', 'edit', record)">
        {{ action.label || '编辑' }}
      </a-button>

      <!-- 删除按钮（带确认） -->
      <a-popconfirm
        v-if="action.key === 'delete'"
        :title="action.confirm || '确定删除？'"
        @confirm="emit('action', 'delete', record)"
      >
        <a-button type="link" size="small" danger>{{ action.label || '删除' }}</a-button>
      </a-popconfirm>

      <!-- 停止按钮（带确认） -->
      <a-popconfirm
        v-if="action.key === 'stop'"
        :title="action.confirm || '确定停止？'"
        @confirm="emit('action', 'stop', record)"
      >
        <a-button type="link" size="small" danger>{{ action.label || '停止' }}</a-button>
      </a-popconfirm>

      <!-- 自定义按钮 -->
      <a-button
        v-if="!['detail', 'edit', 'delete', 'stop'].includes(action.key)"
        type="link"
        size="small"
        :danger="action.danger"
        @click="emit('action', action.key, record)"
      >
        {{ action.label }}
      </a-button>
    </template>
  </a-space>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { RouteLocationRaw } from 'vue-router'

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
  action: [key: string, record: Record<string, any>]
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
</script>
