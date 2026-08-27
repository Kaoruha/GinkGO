<template>
  <PageLayout>
    <template #title>
      用户管理
    </template>
    <template #actions>
      <button
        class="btn btn-primary"
        @click="openCreateModal"
      >
        添加用户
      </button>
    </template>

    <div class="card">
      <div class="filter-row">
        <div class="search-input-wrapper">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle
              cx="11"
              cy="11"
              r="8"
            />
            <path d="m21 21-4.35-4.35" />
          </svg>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索用户名"
            class="search-input"
            @keyup.enter="loadUsers"
          >
          <button
            class="search-btn"
            @click="loadUsers"
          >
            搜索
          </button>
        </div>
        <select
          v-model="statusFilter"
          class="form-select"
          @change="loadUsers"
        >
          <option value="">
            全部状态
          </option>
          <option value="active">
            启用
          </option>
          <option value="disabled">
            禁用
          </option>
        </select>
      </div>

      <div
        v-if="loading"
        class="loading-container"
      >
        <div class="spinner" />
      </div>
      <div
        v-else-if="users.length > 0"
        class="table-wrapper"
      >
        <p class="table-hint">
          提示：右键点击用户行可编辑 / 重置密码 / 删除
        </p>
        <table class="data-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>显示名</th>
              <th>邮箱</th>
              <th>状态</th>
              <th>角色</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="record in users"
              :key="record.uuid"
              @contextmenu="openRowMenu($event, record)"
            >
              <td>{{ record.username }}</td>
              <td>{{ record.display_name || '-' }}</td>
              <td>{{ record.email }}</td>
              <td>
                <StatusTag
                  type="enable"
                  :status="record.status"
                />
              </td>
              <td>
                <span
                  v-for="role in record.roles"
                  :key="role"
                  class="tag tag-blue role-tag"
                >
                  {{ role }}
                </span>
              </td>
              <td>{{ formatDate(record.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState
        v-else
        description="暂无用户数据"
      />
    </div>

    <!-- 创建/编辑用户 Modal -->
    <FormModal
      v-model:open="showCreateModal"
      :title="editingUser ? '编辑用户' : '添加用户'"
      :loading="submitting"
      loading-text="提交中..."
      @submit="handleSubmit"
      @cancel="closeModal"
    >
      <div class="form-group">
        <label class="form-label">用户名 <span class="required">*</span></label>
        <input
          v-model="userForm.username"
          type="text"
          class="form-input"
          placeholder="输入用户名"
          :disabled="!!editingUser"
        >
      </div>
      <div
        v-if="!editingUser"
        class="form-group"
      >
        <label class="form-label">密码 <span class="required">*</span></label>
        <input
          v-model="userForm.password"
          type="password"
          class="form-input"
          placeholder="输入密码"
        >
      </div>
      <div class="form-group">
        <label class="form-label">显示名 <span class="required">*</span></label>
        <input
          v-model="userForm.display_name"
          type="text"
          class="form-input"
          placeholder="输入显示名"
        >
      </div>
      <div class="form-group">
        <label class="form-label">邮箱 <span class="required">*</span></label>
        <input
          v-model="userForm.email"
          type="email"
          class="form-input"
          placeholder="输入邮箱"
        >
      </div>
      <div class="form-group">
        <label class="form-label">状态</label>
        <label class="switch-label">
          <input
            v-model="userForm.active"
            type="checkbox"
            class="switch-input"
          >
          <span class="switch-slider" />
          <span class="switch-text">{{ userForm.active ? '启用' : '禁用' }}</span>
        </label>
      </div>
    </FormModal>

    <!-- 重置密码 Modal -->
    <FormModal
      v-model:open="showResetModal"
      :title="`重置密码 - ${resetTarget?.username ?? ''}`"
      size="sm"
      :loading="resetting"
      loading-text="重置中..."
      @submit="handleResetPassword"
    >
      <div class="form-group">
        <label class="form-label">新密码 <span class="required">*</span></label>
        <input
          v-model="newPassword"
          type="password"
          class="form-input"
          placeholder="输入新密码"
        >
      </div>
    </FormModal>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import FormModal from '@/components/common/FormModal.vue'
import { usersApi, type UserInfo } from '@/api/modules/users'
import { message as toast } from '@/utils/toast'
import { useContextMenu, useAsyncAction } from '@/composables'
import { formatDate } from '@/utils/format'

/** 行右键菜单(替代操作列;删除走菜单内置确认) */
const { open: openRowMenu0 } = useContextMenu()
const openRowMenu = (e: MouseEvent, record: UserInfo) => {
  openRowMenu0(e, [
    { label: '编辑', action: () => editUser(record) },
    { label: '重置密码', action: () => openResetPassword(record) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确定删除用户「${record.username}」吗？`, action: () => deleteUser(record) },
  ])
}

const loading = ref(false)
const showCreateModal = ref(false)
const showResetModal = ref(false)
const editingUser = ref<UserInfo | null>(null)
const resetTarget = ref<UserInfo | null>(null)
const searchText = ref('')
const statusFilter = ref<string>('')
const newPassword = ref('')

const users = ref<UserInfo[]>([])

const userForm = reactive({
  username: '',
  password: '',
  display_name: '',
  email: '',
  roles: [] as string[],
  active: true,
})

const loadUsers = async () => {
  loading.value = true
  try {
    const params: { status?: string; search?: string } = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (searchText.value) params.search = searchText.value
    const res = await usersApi.list(params)
    users.value = res ?? []
  } catch (e: any) {
    toast.error(e.message || '加载用户失败')
  } finally {
    loading.value = false
  }
}

const openCreateModal = () => {
  editingUser.value = null
  Object.assign(userForm, { username: '', password: '', display_name: '', email: '', roles: [], active: true })
  showCreateModal.value = true
}

const editUser = (record: UserInfo) => {
  editingUser.value = record
  Object.assign(userForm, {
    username: record.username,
    display_name: record.display_name,
    email: record.email,
    roles: [...record.roles],
    active: record.status === 'active',
  })
  showCreateModal.value = true
}

const closeModal = () => {
  showCreateModal.value = false
  editingUser.value = null
}

const handleSubmit = () => {
  if (!userForm.username || !userForm.email) {
    toast.warning('请填写必填项')
    return
  }
  if (!editingUser.value && !userForm.password) {
    toast.warning('请输入密码')
    return
  }
  runSubmitUser()
}

const { running: submitting, run: runSubmitUser } = useAsyncAction(async () => {
  if (editingUser.value) {
    await usersApi.update(editingUser.value.uuid, {
      display_name: userForm.display_name,
      email: userForm.email,
      status: userForm.active ? 'active' : 'disabled',
    })
    toast.success('用户已更新')
  } else {
    await usersApi.create({
      username: userForm.username,
      password: userForm.password,
      display_name: userForm.display_name,
      email: userForm.email,
      roles: userForm.roles,
      status: userForm.active ? 'active' : 'disabled',
    })
    toast.success('用户已创建')
  }
}, {
  onSuccess: async () => {
    closeModal()
    await loadUsers()
  },
})

const openResetPassword = (record: UserInfo) => {
  resetTarget.value = record
  newPassword.value = ''
  showResetModal.value = true
}

const handleResetPassword = () => {
  if (!resetTarget.value || !newPassword.value) {
    toast.warning('请输入新密码')
    return
  }
  runResetPassword()
}

const { running: resetting, run: runResetPassword } = useAsyncAction(async () => {
  const target = resetTarget.value
  if (!target) return
  await usersApi.resetPassword(target.uuid, newPassword.value)
}, {
  success: '密码已重置',
  onSuccess: () => {
    showResetModal.value = false
  },
})

const { run: deleteUser } = useAsyncAction(async (record: UserInfo) => {
  await usersApi.delete(record.uuid)
}, { success: '用户已删除', onSuccess: loadUsers })

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>

/* 字号覆盖:正文 13px(公共基线 14px,见 styles/tables.less) */
.data-table td {
  font-size: 13px;
}

/* 模态框样式走全局 modals.less */

/* Filter Row */
.filter-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  /* 固定份额:flex:1 会被 width:100% 的 select 挤到只剩 min-content(input 塌成 0 宽) */
  flex: 0 1 360px;
  min-width: 220px;
}

.search-input-wrapper svg {
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: hsl(var(--foreground));
  font-size: 14px;
  padding: 0;
}

.search-input:focus {
  outline: none;
}

.search-btn {
  padding: 4px 12px;
  background: hsl(var(--primary));
  border: none;
  border-radius: var(--radius-sm);
  color: hsl(var(--primary-foreground));
  font-size: 13px;
  cursor: pointer;
  /* 容器挤压时按钮内文字逐字竖排("搜/索"),禁换行 + 禁收缩 */
  white-space: nowrap;
  flex-shrink: 0;
}

/* 行操作走右键菜单(与回测中心同约定),菜单无视觉示证,补一行提示 */
.table-hint {
  margin: 0 0 8px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* width:100%(forms.less 全局)在 flex 行内会抢占整行,改为占满剩余空间 */
.filter-row .form-select {
  flex: 1;
  width: auto;
  min-width: 180px;
}

/* Table */
.table-wrapper {
  overflow-x: clip;
}

.role-tag {
  margin-right: 4px;
}

/* Switch */
.switch-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.switch-input {
  position: relative;
  width: 44px;
  height: 22px;
  appearance: none;
  background: hsl(var(--secondary));
  border-radius: 9999px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-input:checked {
  background: hsl(var(--primary));
}

.switch-input::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: hsl(var(--card));
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked::before {
  transform: translateX(22px);
}

.switch-text {
  font-size: 13px;
  color: hsl(var(--foreground));
}
</style>
