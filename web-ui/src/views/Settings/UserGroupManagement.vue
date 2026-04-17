<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">用户组管理</h1>
      <button class="btn btn-primary" @click="showCreateModal = true">添加用户组</button>
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
                <span class="badge badge-green">{{ record.user_count }}</span>
              </td>
              <td>
                <template v-for="perm in record.permissions?.slice(0, 3)" :key="perm">
                  <span class="tag tag-blue" style="margin-right: 4px">{{ perm }}</span>
                </template>
                <span v-if="record.permissions?.length > 3" class="tag tag-gray">
                  +{{ record.permissions.length - 3 }}
                </span>
              </td>
              <td>
                <div class="action-links">
                  <a @click="editGroup(record)">编辑</a>
                  <a @click="managePermissions(record)">权限</a>
                  <a class="danger-link" @click="deleteGroupWithConfirm(record)">删除</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingGroup ? '编辑用户组' : '添加用户组' }}</h3>
          <button class="modal-close" @click="closeCreateModal">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">组名称 <span class="required">*</span></label>
            <input v-model="groupForm.name" type="text" class="form-input" placeholder="输入组名称" />
          </div>
          <div class="form-group">
            <label class="form-label">描述</label>
            <textarea v-model="groupForm.description" class="form-textarea" :rows="3" placeholder="输入描述"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">权限</label>
            <div class="multi-select">
              <label v-for="perm in allPermissions" :key="perm.key" class="checkbox-label">
                <input type="checkbox" :value="perm.key" v-model="groupForm.permissions" />
                <span>{{ perm.title }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeCreateModal">取消</button>
          <button class="btn btn-primary" @click="handleSubmit">确定</button>
        </div>
      </div>
    </div>

    <!-- Permission Modal -->
    <div v-if="showPermissionModal" class="modal-overlay" @click.self="closePermissionModal">
      <div class="modal-content modal-wide">
        <div class="modal-header">
          <h3>权限管理</h3>
          <button class="modal-close" @click="closePermissionModal">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="transfer-container">
            <div class="transfer-panel">
              <div class="transfer-header">可用权限</div>
              <div class="transfer-body">
                <label v-for="perm in availablePermissions" :key="perm.key" class="transfer-item">
                  <input type="checkbox" :value="perm.key" v-model="tempSelectedPermissions" />
                  <span>{{ perm.title }}</span>
                </label>
              </div>
            </div>
            <div class="transfer-panel">
              <div class="transfer-header">已有权限</div>
              <div class="transfer-body">
                <label v-for="perm in selectedPermissionsList" :key="perm.key" class="transfer-item">
                  <input type="checkbox" :value="perm.key" v-model="tempSelectedPermissions" />
                  <span>{{ perm.title }}</span>
                </label>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closePermissionModal">取消</button>
          <button class="btn btn-primary" @click="savePermissions">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const loading = ref(false)
const showCreateModal = ref(false)
const showPermissionModal = ref(false)
const editingGroup = ref<any>(null)

const userGroups = ref<any[]>([
  { uuid: '1', name: '管理员', description: '系统管理员组', user_count: 2, permissions: ['system:admin', 'data:manage'] },
  { uuid: '2', name: '研究员', description: '策略研究员组', user_count: 5, permissions: ['backtest:view', 'backtest:create', 'portfolio:view'] },
  { uuid: '3', name: '交易员', description: '交易执行组', user_count: 3, permissions: ['portfolio:create'] },
])

const groupForm = reactive({
  name: '',
  description: '',
  permissions: [] as string[],
})

const selectedPermissions = ref<string[]>([])
const tempSelectedPermissions = ref<string[]>([])

const allPermissions = [
  { key: 'backtest:view', title: '查看回测' },
  { key: 'backtest:create', title: '创建回测' },
  { key: 'portfolio:view', title: '查看组合' },
  { key: 'portfolio:create', title: '创建组合' },
  { key: 'data:manage', title: '数据管理' },
  { key: 'system:admin', title: '系统管理' },
]

const availablePermissions = computed(() => {
  return allPermissions.filter(p => !selectedPermissions.value.includes(p.key))
})

const selectedPermissionsList = computed(() => {
  return allPermissions.filter(p => selectedPermissions.value.includes(p.key))
})

const editGroup = (record: any) => {
  editingGroup.value = record
  Object.assign(groupForm, {
    name: record.name,
    description: record.description,
    permissions: record.permissions || [],
  })
  showCreateModal.value = true
}

const managePermissions = (record: any) => {
  editingGroup.value = record
  selectedPermissions.value = record.permissions || []
  tempSelectedPermissions.value = []
  showPermissionModal.value = true
}

const deleteGroupWithConfirm = (record: any) => {
  if (confirm(`确定删除用户组 "${record.name}" 吗？`)) {
    deleteGroup(record)
  }
}

const deleteGroup = (record: any) => {
  userGroups.value = userGroups.value.filter(g => g.uuid !== record.uuid)
  showToast('用户组已删除')
}

const closeCreateModal = () => {
  showCreateModal.value = false
  editingGroup.value = null
  Object.assign(groupForm, { name: '', description: '', permissions: [] })
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
      user_count: 0,
    })
    showToast('用户组已创建')
  }

  showCreateModal.value = false
  closeCreateModal()
}

const closePermissionModal = () => {
  showPermissionModal.value = false
  editingGroup.value = null
  selectedPermissions.value = []
  tempSelectedPermissions.value = []
}

const savePermissions = () => {
  if (editingGroup.value) {
    // For simplicity, just use the selected permissions
    // In a real transfer component, you'd move items between lists
    editingGroup.value.permissions = [...selectedPermissions.value]
    showToast('权限已更新')
  }
  showPermissionModal.value = false
  closePermissionModal()
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

/* Card */

/* Loading */

/* Table */
.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
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
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

/* Tag */

/* Badge */
.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}

.badge-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

/* Action Links */
.action-links {
  display: flex;
  gap: 12px;
}

.action-links a {
  color: #1890ff;
  cursor: pointer;
  font-size: 13px;
}

.action-links a:hover {
  text-decoration: underline;
}

.danger-link {
  color: #f5222d !important;
}

/* Modal */

/* Form */

.required {
  color: #f5222d;
}

/* Multi Select Checkbox */
.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-label span {
  color: #ffffff;
}

/* Transfer */
.transfer-container {
  display: flex;
  gap: 16px;
}

.transfer-panel {
  flex: 1;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  overflow: hidden;
}

.transfer-header {
  padding: 10px 12px;
  background: #2a2a3e;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  border-bottom: 1px solid #3a3a4e;
}

.transfer-body {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px;
}

.transfer-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  cursor: pointer;
  border-radius: 4px;
  font-size: 13px;
}

.transfer-item:hover {
  background: #2a2a3e;
}

.transfer-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.transfer-item span {
  color: #ffffff;
}

/* Button */

</style>
