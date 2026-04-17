<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">系统</span>
        用户管理
      </div>
      <button class="btn btn-primary" @click="showCreateModal = true">添加用户</button>
    </div>

    <div class="card">
      <div class="filter-row">
        <div class="search-input-wrapper">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索用户名"
            class="search-input"
            @keyup.enter="handleSearch"
          />
          <button class="search-btn" @click="handleSearch">搜索</button>
        </div>
        <select v-model="statusFilter" class="form-select" @change="handleSearch">
          <option value="">全部状态</option>
          <option value="active">启用</option>
          <option value="disabled">禁用</option>
        </select>
      </div>

      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>用户名</th>
              <th>邮箱</th>
              <th>状态</th>
              <th>角色</th>
              <th>最后登录</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in users" :key="record.uuid">
              <td>{{ record.username }}</td>
              <td>{{ record.email }}</td>
              <td>
                <span class="tag" :class="record.status === 'active' ? 'tag-green' : 'tag-gray'">
                  {{ record.status === 'active' ? '启用' : '禁用' }}
                </span>
              </td>
              <td>
                <span v-for="role in record.roles" :key="role" class="tag tag-blue" style="margin-right: 4px">
                  {{ role }}
                </span>
              </td>
              <td>{{ record.last_login }}</td>
              <td>
                <div class="action-links">
                  <a @click="editUser(record)">编辑</a>
                  <a @click="resetPassword(record)">重置密码</a>
                  <a class="danger-link" @click="deleteUserWithConfirm(record)">删除</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="resetForm">
      <div class="modal-content">
        <div class="modal-header">
          <h3>{{ editingUser ? '编辑用户' : '添加用户' }}</h3>
          <button class="modal-close" @click="resetForm">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">用户名 <span class="required">*</span></label>
            <input v-model="userForm.username" type="text" class="form-input" placeholder="输入用户名" :disabled="!!editingUser" />
          </div>
          <div v-if="!editingUser" class="form-group">
            <label class="form-label">密码 <span class="required">*</span></label>
            <input v-model="userForm.password" type="password" class="form-input" placeholder="输入密码" />
          </div>
          <div class="form-group">
            <label class="form-label">邮箱 <span class="required">*</span></label>
            <input v-model="userForm.email" type="email" class="form-input" placeholder="输入邮箱" />
          </div>
          <div class="form-group">
            <label class="form-label">用户组</label>
            <div class="multi-select">
              <label v-for="group in userGroups" :key="group.uuid" class="checkbox-label">
                <input type="checkbox" :value="group.uuid" v-model="userForm.groups" />
                <span>{{ group.name }}</span>
              </label>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">状态</label>
            <label class="switch-label">
              <input type="checkbox" v-model="userForm.active" class="switch-input" />
              <span class="switch-slider"></span>
              <span class="switch-text">{{ userForm.active ? '启用' : '禁用' }}</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="resetForm">取消</button>
          <button class="btn btn-primary" @click="handleSubmit">确定</button>
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
const editingUser = ref<any>(null)
const searchText = ref('')
const statusFilter = ref<string | undefined>(undefined)

const users = ref([
  { uuid: '1', username: 'admin', email: 'admin@example.com', status: 'active', roles: ['管理员'], last_login: '2024-01-01 10:00:00' },
  { uuid: '2', username: 'researcher1', email: 'researcher1@example.com', status: 'active', roles: ['研究员'], last_login: '2024-01-02 09:00:00' },
  { uuid: '3', username: 'trader1', email: 'trader1@example.com', status: 'disabled', roles: ['交易员'], last_login: '2023-12-01 08:00:00' },
])

const userGroups = ref([
  { uuid: '1', name: '管理员' },
  { uuid: '2', name: '研究员' },
  { uuid: '3', name: '交易员' },
])

const userForm = reactive({
  username: '',
  password: '',
  email: '',
  groups: [] as string[],
  active: true,
})

const handleSearch = () => { showToast('搜索功能', 'info') }
const editUser = (record: any) => {
  editingUser.value = record
  Object.assign(userForm, { username: record.username, email: record.email, groups: [], active: record.status === 'active' })
  showCreateModal.value = true
}
const resetPassword = (record: any) => { showToast(`已发送重置密码邮件到 ${record.email}`) }

const deleteUserWithConfirm = (record: any) => {
  if (confirm(`确定删除用户 "${record.username}" 吗？`)) {
    deleteUser(record)
  }
}

const deleteUser = (record: any) => {
  users.value = users.value.filter(u => u.uuid !== record.uuid)
  showToast('用户已删除')
}

const handleSubmit = () => {
  if (!userForm.username || !userForm.email) {
    showToast('请填写必填项', 'warning')
    return
  }
  if (!editingUser.value && !userForm.password) {
    showToast('请输入密码', 'warning')
    return
  }
  if (editingUser.value) {
    editingUser.value.email = userForm.email
    editingUser.value.status = userForm.active ? 'active' : 'disabled'
    showToast('用户已更新')
  } else {
    users.value.push({ uuid: Date.now().toString(), username: userForm.username, email: userForm.email, status: userForm.active ? 'active' : 'disabled', roles: ['新用户'], last_login: '-' })
    showToast('用户已创建')
  }
  showCreateModal.value = false
  resetForm()
}

const resetForm = () => {
  editingUser.value = null
  Object.assign(userForm, { username: '', password: '', email: '', groups: [], active: true })
  showCreateModal.value = false
}

onMounted(() => {})
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
  font-size: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #ffffff;
}

/* Card */

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
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  padding: 6px 12px;
  flex: 1;
  max-width: 400px;
}

.search-input-wrapper svg {
  color: #8a8a9a;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 14px;
  padding: 0;
}

.search-input:focus {
  outline: none;
}

.search-btn {
  padding: 4px 12px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

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
  background: #3a3a4e;
  border-radius: 11px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-input:checked {
  background: #1890ff;
}

.switch-input::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  background: #ffffff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked::before {
  transform: translateX(22px);
}

.switch-text {
  font-size: 13px;
  color: #ffffff;
}

/* Button */

</style>
