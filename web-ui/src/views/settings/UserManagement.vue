<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="blue">系统</a-tag>
        用户管理
      </div>
      <a-button type="primary" @click="showCreateModal = true">添加用户</a-button>
    </div>

    <a-card>
      <a-row :gutter="16" style="margin-bottom: 16px">
        <a-col :span="8">
          <a-input-search v-model:value="searchText" placeholder="搜索用户名" @search="handleSearch" />
        </a-col>
        <a-col :span="6">
          <a-select v-model:value="statusFilter" placeholder="状态筛选" style="width: 100%" allow-clear @change="handleSearch">
            <a-select-option value="active">启用</a-select-option>
            <a-select-option value="disabled">禁用</a-select-option>
          </a-select>
        </a-col>
      </a-row>

      <a-table :columns="columns" :data-source="users" :loading="loading" row-key="uuid">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'success' : 'default'">
              {{ record.status === 'active' ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'roles'">
            <a-space wrap>
              <a-tag v-for="role in record.roles" :key="role" color="blue">{{ role }}</a-tag>
            </a-space>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editUser(record)">编辑</a>
              <a @click="resetPassword(record)">重置密码</a>
              <a-popconfirm title="确定删除?" @confirm="deleteUser(record)">
                <a style="color: #f5222d">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-modal v-model:open="showCreateModal" :title="editingUser ? '编辑用户' : '添加用户'" @ok="handleSubmit" @cancel="resetForm">
      <a-form :model="userForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="用户名" required>
          <a-input v-model:value="userForm.username" placeholder="输入用户名" :disabled="!!editingUser" />
        </a-form-item>
        <a-form-item v-if="!editingUser" label="密码" required>
          <a-input-password v-model:value="userForm.password" placeholder="输入密码" />
        </a-form-item>
        <a-form-item label="邮箱" required>
          <a-input v-model:value="userForm.email" placeholder="输入邮箱" />
        </a-form-item>
        <a-form-item label="用户组">
          <a-select v-model:value="userForm.groups" mode="multiple" placeholder="选择用户组">
            <a-select-option v-for="group in userGroups" :key="group.uuid" :value="group.uuid">{{ group.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="状态">
          <a-switch v-model:checked="userForm.active" checked-children="启用" un-checked-children="禁用" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'

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

const columns = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '角色', dataIndex: 'roles', key: 'roles' },
  { title: '最后登录', dataIndex: 'last_login', key: 'last_login' },
  { title: '操作', key: 'action', width: 200 },
]

const handleSearch = () => { message.info('搜索功能') }
const editUser = (record: any) => {
  editingUser.value = record
  Object.assign(userForm, { username: record.username, email: record.email, groups: [], active: record.status === 'active' })
  showCreateModal.value = true
}
const resetPassword = (record: any) => { message.success(`已发送重置密码邮件到 ${record.email}`) }
const deleteUser = (record: any) => { users.value = users.value.filter(u => u.uuid !== record.uuid); message.success('用户已删除') }

const handleSubmit = () => {
  if (!userForm.username || !userForm.email) { message.warning('请填写必填项'); return }
  if (!editingUser.value && !userForm.password) { message.warning('请输入密码'); return }
  if (editingUser.value) {
    editingUser.value.email = userForm.email
    editingUser.value.status = userForm.active ? 'active' : 'disabled'
    message.success('用户已更新')
  } else {
    users.value.push({ uuid: Date.now().toString(), username: userForm.username, email: userForm.email, status: userForm.active ? 'active' : 'disabled', roles: ['新用户'], last_login: '-' })
    message.success('用户已创建')
  }
  showCreateModal.value = false
  resetForm()
}

const resetForm = () => {
  editingUser.value = null
  Object.assign(userForm, { username: '', password: '', email: '', groups: [], active: true })
}

onMounted(() => {})
</script>
