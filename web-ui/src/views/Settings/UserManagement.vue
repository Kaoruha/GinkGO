<template>
  <div class="user-management">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <button class="btn-primary" @click="showCreateModal = true">添加用户</button>
    </div>

    <div class="card">
      <div class="card-body">
        <div class="filter-row">
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索用户名"
            class="form-input"
            @keyup.enter="handleSearch"
          />
          <select
            v-model="statusFilter"
            class="form-select"
            @change="handleSearch"
          >
            <option value="">状态筛选</option>
            <option value="active">启用</option>
            <option value="disabled">禁用</option>
          </select>
          <button class="btn-secondary" @click="handleSearch">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            搜索
          </button>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="table-wrapper">
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
          <tbody v-if="!loading">
            <tr v-for="record in users" :key="record.uuid">
              <td>{{ record.username }}</td>
              <td>{{ record.email }}</td>
              <td>
                <span class="tag" :class="record.status === 'active' ? 'tag-green' : 'tag-gray'">
                  {{ record.status === 'active' ? '启用' : '禁用' }}
                </span>
              </td>
              <td>
                <span v-for="role in record.roles" :key="role" class="tag tag-blue">{{ role }}</span>
              </td>
              <td>{{ record.last_login || '-' }}</td>
              <td>
                <div class="action-links">
                  <a class="link" @click="editUser(record)">编辑</a>
                  <a class="link" @click="resetPassword(record)">重置密码</a>
                  <a class="link text-red" @click="confirmDelete(record)">删除</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <div class="pagination-info">共 {{ pagination.total }} 条</div>
        <div class="pagination-controls">
          <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(1)">首页</button>
          <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(pagination.current - 1)">上一页</button>
          <span class="pagination-current">{{ pagination.current }}</span>
          <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(pagination.current + 1)">下一页</button>
        </div>
      </div>
    </div>

    <!-- 用户编辑/创建模态框 -->
    <div v-if="showCreateModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingUser ? '编辑用户' : '添加用户' }}</h3>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <div class="form-group">
              <label class="form-label">用户名 <span class="required">*</span></label>
              <input v-model="userForm.username" type="text" placeholder="输入用户名" class="form-input" :disabled="!!editingUser" required />
            </div>
            <div v-if="!editingUser" class="form-group">
              <label class="form-label">密码 <span class="required">*</span></label>
              <input v-model="userForm.password" type="password" placeholder="输入密码" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">邮箱 <span class="required">*</span></label>
              <input v-model="userForm.email" type="email" placeholder="输入邮箱" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">用户组</label>
              <select v-model="selectedGroups" multiple class="form-select">
                <option v-for="group in userGroups" :key="group.uuid" :value="group.uuid">
                  {{ group.name }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">状态</label>
              <div class="switch-container">
                <input v-model="userForm.active" type="checkbox" id="user-status" class="switch-input" />
                <label for="user-status" class="switch-label"></label>
                <span>{{ userForm.active ? '启用' : '禁用' }}</span>
              </div>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeModal">取消</button>
              <button type="submit" class="btn-primary">{{ editingUser ? '更新' : '创建' }}</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const loading = ref(false)
const showCreateModal = ref(false)
const editingUser = ref<any>(null)
const searchText = ref('')
const statusFilter = ref<string>('')
const selectedGroups = ref<string[]>([])

const users = ref<any[]>([
  { uuid: '1', username: 'admin', email: 'admin@example.com', status: 'active', roles: ['管理员'], last_login: '2024-01-01 10:00:00' },
  { uuid: '2', username: 'researcher1', email: 'researcher1@example.com', status: 'active', roles: ['研究员'], last_login: '2024-01-02 09:00:00' },
  { uuid: '3', username: 'trader1', email: 'trader1@example.com', status: 'disabled', roles: ['交易员'], last_login: '2023-12-01 08:00:00' },
])

const userGroups = ref<any[]>([
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

const pagination = reactive({
  current: 1,
  pageSize: 10,
  total: 3,
})

const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize))

const handleSearch = () => {
  showToast('搜索功能', 'info')
}

const goToPage = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  pagination.current = page
}

const editUser = (record: any) => {
  editingUser.value = record
  Object.assign(userForm, {
    username: record.username,
    email: record.email,
    groups: [],
    active: record.status === 'active',
  })
  selectedGroups.value = []
  showCreateModal.value = true
}

const resetPassword = (record: any) => {
  showToast(`已发送重置密码邮件到 ${record.email}`)
}

const confirmDelete = (record: any) => {
  if (confirm(`确定要删除用户 "${record.username}" 吗？`)) {
    deleteUser(record)
  }
}

const deleteUser = (record: any) => {
  users.value = users.value.filter(u => u.uuid !== record.uuid)
  showToast('用户已删除')
}

const closeModal = () => {
  showCreateModal.value = false
  editingUser.value = null
  Object.assign(userForm, { username: '', password: '', email: '', groups: [], active: true })
  selectedGroups.value = []
}

const handleSubmit = () => {
  if (!userForm.username || !userForm.email) {
    showToast('请填写必填项', 'error')
    return
  }

  if (!editingUser.value && !userForm.password) {
    showToast('请输入密码', 'error')
    return
  }

  if (editingUser.value) {
    editingUser.value.email = userForm.email
    editingUser.value.status = userForm.active ? 'active' : 'disabled'
    showToast('用户已更新')
  } else {
    users.value.push({
      uuid: Date.now().toString(),
      username: userForm.username,
      email: userForm.email,
      status: userForm.active ? 'active' : 'disabled',
      roles: ['新用户'],
      last_login: '-',
    })
    showToast('用户已创建')
  }

  closeModal()
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.user-management {
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
  margin: 0;
}

.filter-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
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

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-btn {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  color: #ffffff;
  font-size: 14px;
  padding: 0 8px;
}

/* 模态框样式 */

.required {
  color: #f5222d;
}

.switch-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.switch-input {
  display: none;
}

.switch-label {
  position: relative;
  width: 44px;
  height: 22px;
  background: #3a3a4e;
  border-radius: 11px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-label::after {
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

.switch-input:checked + .switch-label {
  background: #1890ff;
}

.switch-input:checked + .switch-label::after {
  transform: translateX(22px);
}

@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .form-input,
  .form-select {
    width: 100%;
  }

  .pagination {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
