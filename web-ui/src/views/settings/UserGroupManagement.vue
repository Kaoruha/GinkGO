<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">系统</span>
        用户组管理
      </div>
      <button class="btn-primary" @click="showCreateModal = true">添加用户组</button>
    </div>

    <div class="card">
      <div class="table-wrapper">
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
          <tbody v-if="!loading">
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
          <h3>权限管理</h3>
          <button class="modal-close" @click="closePermissionModal">×</button>
        </div>
        <div class="modal-body">
          <div class="transfer-container">
            <div class="transfer-panel">
              <h4>可用权限</h4>
              <div class="transfer-list">
                <label v-for="perm in availablePermissions" :key="perm.value" class="transfer-item" :class="{ disabled: selectedPermissions.includes(perm.value) }">
                  <input
                    v-model="selectedPermissions"
                    type="checkbox"
                    :value="perm.value"
                    :disabled="selectedPermissions.includes(perm.value)"
                  />
                  {{ perm.label }}
                </label>
              </div>
            </div>
            <div class="transfer-panel">
              <h4>已有权限</h4>
              <div class="transfer-list">
                <label v-for="permValue in selectedPermissions" :key="permValue" class="transfer-item">
                  <input v-model="selectedPermissions" type="checkbox" :value="permValue" />
                  {{ getPermissionLabel(permValue) }}
                </label>
              </div>
            </div>
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

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const loading = ref(false)
const showCreateModal = ref(false)
const showPermissionModal = ref(false)
const editingGroup = ref<any>(null)

const userGroups = ref([
  { uuid: '1', name: '管理员', description: '系统管理员组', user_count: 2, permissions: ['system:admin', 'data:manage'] },
  { uuid: '2', name: '研究员', description: '策略研究员组', user_count: 5, permissions: ['backtest:view', 'backtest:create', 'portfolio:view'] },
  { uuid: '3', name: '交易员', description: '交易执行组', user_count: 3, permissions: ['portfolio:create'] },
])

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

const getPermissionLabel = (value: string) => {
  return availablePermissions.find(p => p.value === value)?.label || value
}

const editGroup = (record: any) => {
  editingGroup.value = record
  Object.assign(groupForm, { name: record.name, description: record.description, permissions: record.permissions || [] })
  showCreateModal.value = true
}

const managePermissions = (record: any) => {
  editingGroup.value = record
  selectedPermissions.value = record.permissions || []
  showPermissionModal.value = true
}

const confirmDelete = (record: any) => {
  if (confirm(`确定要删除用户组 "${record.name}" 吗？`)) {
    deleteGroup(record)
  }
}

const deleteGroup = (record: any) => {
  userGroups.value = userGroups.value.filter(g => g.uuid !== record.uuid)
  showToast('用户组已删除')
}

const closeModal = () => {
  showCreateModal.value = false
  editingGroup.value = null
  Object.assign(groupForm, { name: '', description: '', permissions: [] })
}

const closePermissionModal = () => {
  showPermissionModal.value = false
  selectedPermissions.value = []
}

const handleSubmit = () => {
  if (!groupForm.name) {
    showToast('请输入组名称', 'warning')
    return
  }

  if (editingGroup.value) {
    Object.assign(editingGroup.value, groupForm)
    showToast('用户组已更新')
  } else {
    userGroups.value.push({
      uuid: Date.now().toString(),
      ...groupForm,
      user_count: 0
    })
    showToast('用户组已创建')
  }

  closeModal()
}

const savePermissions = () => {
  if (editingGroup.value) {
    editingGroup.value.permissions = [...selectedPermissions.value]
    showToast('权限已更新')
  }
  closePermissionModal()
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.page-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-primary {
  padding: 10px 20px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
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

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-gray {
  background: #2a2a3e;
  color: #8a8a9a;
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

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-large {
  max-width: 700px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
  padding: 4px 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 8px;
}

.required {
  color: #f5222d;
}

.form-input,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #1890ff;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
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

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
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

/* Transfer 组件样式 */
.transfer-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.transfer-panel h4 {
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 12px 0;
}

.transfer-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 250px;
  overflow-y: auto;
  padding: 12px;
  background: #2a2a3e;
  border-radius: 4px;
}

.transfer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background: #1a1a2e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.transfer-item:hover {
  border-color: #1890ff;
}

.transfer-item.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.transfer-item input[type="checkbox"] {
  cursor: pointer;
}

@media (max-width: 768px) {
  .transfer-container {
    grid-template-columns: 1fr;
  }
}
</style>
