<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">系统</span>
        用户组管理
      </div>
      <button class="btn-primary" @click="openCreateModal">添加用户组</button>
    </div>

    <div class="card">
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>组名称</th>
              <th>描述</th>
              <th>用户数</th>
              <th>权限</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in userGroups" :key="record.uuid">
              <td>{{ record.name }}</td>
              <td>{{ record.description || '-' }}</td>
              <td>
                <span class="badge badge-success">{{ record.user_count }}</span>
              </td>
              <td>
                <div class="tags-wrapper">
                  <span v-for="perm in record.permissions?.slice(0, 3)" :key="perm" class="tag tag-blue">{{ perm }}</span>
                  <span v-if="record.permissions?.length > 3" class="tag tag-gray">+{{ record.permissions.length - 3 }}</span>
                </div>
              </td>
              <td>
                <div class="action-links">
                  <a class="link" @click="editGroup(record)">编辑</a>
                  <a class="link" @click="managePermissions(record)">权限</a>
                  <a class="link text-red" @click="confirmDelete(record)">删除</a>
                </div>
              </td>
            </tr>
            <tr v-if="userGroups.length === 0">
              <td colspan="5" class="empty-state">暂无用户组数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 用户组编辑/创建模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingGroup ? '编辑用户组' : '添加用户组' }}</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label class="form-label">组名称 <span class="required">*</span></label>
              <input v-model="groupForm.name" type="text" placeholder="输入组名称" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">描述</label>
              <textarea v-model="groupForm.description" :rows="3" placeholder="输入描述" class="form-textarea"></textarea>
            </div>
            <div class="form-group">
              <label class="form-label">权限</label>
              <div class="multi-select">
                <label v-for="perm in availablePermissions" :key="perm.value" class="checkbox-label">
                  <input v-model="groupForm.permissions" type="checkbox" :value="perm.value" />
                  {{ perm.label }}
                </label>
              </div>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeModal">取消</button>
              <button type="submit" class="btn-primary">{{ editingGroup ? '更新' : '创建' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 权限管理模态框 -->
    <div v-if="showPermissionModal" class="modal-overlay" @click.self="closePermissionModal">
      <div class="modal modal-large">
        <div class="modal-header">
          <h3>权限管理 - {{ permissionTarget?.name }}</h3>
          <button class="modal-close" @click="closePermissionModal">×</button>
        </div>
        <div class="modal-body">
          <div class="multi-select" style="margin-bottom: 16px">
            <label v-for="perm in availablePermissions" :key="perm.value" class="checkbox-label" :class="{ selected: selectedPermissions.includes(perm.value) }">
              <input v-model="selectedPermissions" type="checkbox" :value="perm.value" />
              {{ perm.label }}
            </label>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="closePermissionModal">取消</button>
            <button type="button" class="btn-primary" @click="savePermissions">保存</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { userGroupsApi, type UserGroupInfo } from '@/api/modules/settings'
import { message as toast } from '@/utils/toast'

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
    const res = await userGroupsApi.list() as any
    userGroups.value = res.data || res || []
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

const confirmDelete = (record: UserGroupInfo) => {
  if (confirm(`确定要删除用户组 "${record.name}" 吗？`)) {
    deleteGroup(record)
  }
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

const handleSubmit = async () => {
  if (!groupForm.name) {
    toast.warning('请输入组名称')
    return
  }

  try {
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
    closeModal()
    await loadGroups()
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  }
}

const savePermissions = async () => {
  if (!permissionTarget.value) return
  try {
    await userGroupsApi.update(permissionTarget.value.uuid, {
      permissions: selectedPermissions.value,
    })
    toast.success('权限已更新')
    closePermissionModal()
    await loadGroups()
  } catch (e: any) {
    toast.error(e.message || '保存失败')
  }
}

onMounted(() => {
  loadGroups()
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content, .modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}

.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tr:hover {
  background: #2a2a3e;
}

.tags-wrapper {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  min-width: 24px;
  text-align: center;
}

.badge-success {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.action-links {
  display: flex;
  gap: 12px;
}

.link {
  color: #1890ff;
  cursor: pointer;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

.text-red {
  color: #f5222d;
}

.required {
  color: #f5222d;
}

.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #1890ff;
}

.checkbox-label.selected {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.empty-state {
  text-align: center;
  color: #8a8a9a;
  padding: 32px !important;
}
</style>
