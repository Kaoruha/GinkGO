<template>
  <PageLayout>
    <template #title>
      用户组管理
    </template>
    <template #actions>
      <button
        class="btn-primary"
        @click="openCreateModal"
      >
        添加用户组
      </button>
    </template>

    <div class="card">
      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="spinner" />
      </div>
      <div
        v-else-if="userGroups.length > 0"
        class="table-wrapper"
      >
        <table class="data-table">
          <thead>
            <tr>
              <th>组名称</th>
              <th>描述</th>
              <th>用户数</th>
              <th>权限</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="record in userGroups"
              :key="record.uuid"
              @contextmenu="openGroupMenu($event, record)"
            >
              <td>{{ record.name }}</td>
              <td>{{ record.description || '-' }}</td>
              <td>{{ record.user_count }}</td>
              <td>
                <div class="tags-wrapper">
                  <span
                    v-for="perm in record.permissions?.slice(0, 3)"
                    :key="perm"
                    class="tag tag-blue"
                  >{{ perm }}</span>
                  <span
                    v-if="record.permissions?.length > 3"
                    class="tag tag-gray"
                  >+{{ record.permissions.length - 3 }}</span>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        description="暂无用户组数据"
      />
    </div>

    <!-- 用户组编辑/创建模态框 -->
    <FormModal
      v-model:open="showCreateModal"
      :title="editingGroup ? '编辑用户组' : '添加用户组'"
      :confirm-text="editingGroup ? '更新' : '创建'"
      :loading="submitting"
      loading-text="提交中..."
      @submit="handleSubmit"
      @cancel="closeModal"
    >
      <div class="form-group">
        <label class="form-label">组名称 <span class="required">*</span></label>
        <input
          v-model="groupForm.name"
          type="text"
          placeholder="输入组名称"
          class="form-input"
          required
        >
      </div>
      <div class="form-group">
        <label class="form-label">描述</label>
        <textarea
          v-model="groupForm.description"
          :rows="3"
          placeholder="输入描述"
          class="form-textarea"
        />
      </div>
      <div class="form-group">
        <label class="form-label">权限</label>
        <div class="multi-select">
          <label
            v-for="perm in availablePermissions"
            :key="perm.value"
            class="checkbox-label"
          >
            <input
              v-model="groupForm.permissions"
              type="checkbox"
              :value="perm.value"
            >
            {{ perm.label }}
          </label>
        </div>
      </div>
    </FormModal>

    <!-- 权限管理模态框 -->
    <FormModal
      v-model:open="showPermissionModal"
      :title="`权限管理 - ${permissionTarget?.name ?? ''}`"
      size="xl"
      confirm-text="保存"
      :loading="savingPerms"
      loading-text="保存中..."
      @submit="savePermissions"
      @cancel="closePermissionModal"
    >
      <div class="multi-select">
        <label
          v-for="perm in availablePermissions"
          :key="perm.value"
          class="checkbox-label"
          :class="{ selected: selectedPermissions.includes(perm.value) }"
        >
          <input
            v-model="selectedPermissions"
            type="checkbox"
            :value="perm.value"
          >
          {{ perm.label }}
        </label>
      </div>
    </FormModal>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import FormModal from '@/components/common/FormModal.vue'
import { userGroupsApi, type UserGroupInfo } from '@/api/modules/settings'
import { message as toast } from '@/utils/toast'
import { useContextMenu, useAsyncAction } from '@/composables'

/** 行右键菜单(替代操作列;删除走菜单内置确认) */
const { open: openCtxMenu } = useContextMenu()
const openGroupMenu = (e: MouseEvent, record: UserGroupInfo) => {
  openCtxMenu(e, [
    { label: '编辑', action: () => editGroup(record) },
    { label: '权限', action: () => managePermissions(record) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确定要删除用户组「${record.name}」吗？`, action: () => deleteGroup(record) },
  ])
}

const loading = ref(false)
const showCreateModal = ref(false)
const showPermissionModal = ref(false)
const editingGroup = ref<UserGroupInfo | null>(null)
const permissionTarget = ref<UserGroupInfo | null>(null)

const userGroups = ref<UserGroupInfo[]>([])

const groupForm = reactive({ name: '', description: '', permissions: [] as string[] })
const selectedPermissions = ref<string[]>([])

const availablePermissions = [
  { value: 'backtest:view', label: '查看回测' },
  { value: 'backtest:create', label: '创建回测' },
  { value: 'portfolio:view', label: '查看组合' },
  { value: 'portfolio:create', label: '创建组合' },
  { value: 'data:manage', label: '数据管理' },
  { value: 'system:admin', label: '系统管理' },
]

const loadGroups = async () => {
  loading.value = true
  try {
    const res = await userGroupsApi.list()
    userGroups.value = res ?? []
  } catch (e: any) {
    toast.error(e.message || '加载用户组失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingGroup.value = null
  Object.assign(groupForm, { name: '', description: '', permissions: [] })
  showCreateModal.value = true
}

const editGroup = (record: UserGroupInfo) => {
  editingGroup.value = record
  Object.assign(groupForm, { name: record.name, description: record.description || '', permissions: record.permissions || [] })
  showCreateModal.value = true
}

const managePermissions = (record: UserGroupInfo) => {
  permissionTarget.value = record
  selectedPermissions.value = [...(record.permissions || [])]
  showPermissionModal.value = true
}

const deleteGroup = async (record: UserGroupInfo) => {
  try {
    await userGroupsApi.delete(record.uuid)
    toast.success('用户组已删除')
    await loadGroups()
  } catch (e: any) {
    toast.error(e.message || '删除失败')
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingGroup.value = null
  Object.assign(groupForm, { name: '', description: '', permissions: [] })
}

const closePermissionModal = () => {
  showPermissionModal.value = false
  selectedPermissions.value = []
  permissionTarget.value = null
}

const handleSubmit = () => {
  if (!groupForm.name) {
    toast.warning('请输入组名称')
    return
  }
  runSubmitGroup()
}

const { running: submitting, run: runSubmitGroup } = useAsyncAction(async () => {
  if (editingGroup.value) {
    await userGroupsApi.update(editingGroup.value.uuid, {
      name: groupForm.name,
      description: groupForm.description,
      permissions: groupForm.permissions,
    })
    toast.success('用户组已更新')
  } else {
    await userGroupsApi.create({
      name: groupForm.name,
      description: groupForm.description,
      permissions: groupForm.permissions,
    })
    toast.success('用户组已创建')
  }
}, {
  onSuccess: async () => {
    closeModal()
    await loadGroups()
  },
})

const savePermissions = () => {
  if (!permissionTarget.value) return
  runSavePermissions()
}

const { running: savingPerms, run: runSavePermissions } = useAsyncAction(async () => {
  const target = permissionTarget.value
  if (!target) return
  await userGroupsApi.update(target.uuid, {
    permissions: selectedPermissions.value,
  })
}, {
  success: '权限已更新',
  onSuccess: async () => {
    closePermissionModal()
    await loadGroups()
  },
})

onMounted(() => {
  loadGroups()
})
</script>

<style scoped>
/* 模态框样式走全局 modals.less */

.table-wrapper {
  overflow-x: clip;
}

.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: hsl(var(--primary));
}

.checkbox-label.selected {
  border-color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}
</style>
