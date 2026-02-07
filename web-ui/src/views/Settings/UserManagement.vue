<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-title">
        用户管理
      </h1>
      <a-button
        type="primary"
        @click="showCreateModal = true"
      >
        添加用户
      </a-button>
    </div>

    <!-- 搜索和筛选 -->
    <div class="card">
      <a-row :gutter="16">
        <a-col :span="8">
          <a-input-search
            v-model:value="searchText"
            placeholder="搜索用户名"
            @search="handleSearch"
          />
        </a-col>
        <a-col :span="8">
          <a-select
            v-model:value="statusFilter"
            placeholder="状态筛选"
            style="width: 100%"
            allow-clear
            @change="handleSearch"
          >
            <a-select-option value="active">
              启用
            </a-select-option>
            <a-select-option value="disabled">
              禁用
            </a-select-option>
          </a-select>
        </a-col>
      </a-row>
    </div>

    <!-- 用户列表 -->
    <div class="card">
      <a-table
        :columns="columns"
        :data-source="users"
        :loading="loading"
        :pagination="pagination"
        row-key="uuid"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'success' : 'default'">
              {{ record.status === 'active' ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'roles'">
            <a-tag
              v-for="role in record.roles"
              :key="role"
              color="blue"
            >
              {{ role }}
            </a-tag>
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="editUser(record)"
              >
                编辑
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="openContactsDrawer(record)"
              >
                联系方式
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="resetPassword(record)"
              >
                重置密码
              </a-button>
              <a-popconfirm
                title="确定要删除此用户吗？"
                @confirm="deleteUser(record)"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                >
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- 创建/编辑用户弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingUser ? '编辑用户' : '添加用户'"
      width="600px"
      @ok="handleSaveUser"
      @cancel="handleCancelEdit"
    >
      <a-form
        ref="formRef"
        :model="userForm"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item
          label="用户名"
          name="username"
        >
          <a-input
            v-model:value="userForm.username"
            placeholder="请输入用户名"
            :disabled="!!editingUser"
          />
        </a-form-item>

        <a-form-item
          v-if="!editingUser"
          label="密码"
          name="password"
        >
          <a-input-password
            v-model:value="userForm.password"
            placeholder="请输入密码"
          />
        </a-form-item>

        <a-form-item
          label="显示名称"
          name="display_name"
        >
          <a-input
            v-model:value="userForm.display_name"
            placeholder="请输入显示名称"
          />
        </a-form-item>

        <a-form-item
          label="邮箱"
          name="email"
        >
          <a-input
            v-model:value="userForm.email"
            placeholder="请输入邮箱"
          />
        </a-form-item>

        <a-form-item
          label="角色"
          name="roles"
        >
          <a-select
            v-model:value="userForm.roles"
            mode="multiple"
            placeholder="请选择角色"
            :options="roleOptions"
          />
        </a-form-item>

        <a-form-item
          label="状态"
          name="status"
        >
          <a-radio-group v-model:value="userForm.status">
            <a-radio value="active">
              启用
            </a-radio>
            <a-radio value="disabled">
              禁用
            </a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 联系方式管理抽屉 -->
    <a-drawer
      v-model:open="showContactsDrawer"
      :title="`${currentUser?.username || ''} 的联系方式`"
      width="800px"
      placement="right"
    >
      <template #extra>
        <a-button
          type="primary"
          @click="handleAddContact"
        >
          添加联系方式
        </a-button>
      </template>

      <!-- 联系方式列表 -->
      <a-table
        :columns="contactColumns"
        :data-source="contacts"
        :loading="contactsLoading"
        :pagination="false"
        row-key="uuid"
        size="small"
        class="mb-4"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'contact_type'">
            <a-tag :color="record.contact_type === 'email' ? 'blue' : 'green'">
              {{ getContactTypeName(record.contact_type) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'address'">
            <a-tooltip :title="record.address">
              <span
                class="address-cell"
                @click="copyAddress(record.address)"
              >
                {{ record.address }}
              </span>
            </a-tooltip>
          </template>
          <template v-if="column.key === 'is_primary'">
            <a-tag
              v-if="record.is_primary"
              color="orange"
            >
              主要
            </a-tag>
            <span
              v-else
              style="color: #999"
            >-</span>
          </template>
          <template v-if="column.key === 'is_active'">
            <a-switch
              :checked="record.is_active"
              size="small"
              @change="handleToggleContactStatus(record)"
            />
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="4">
              <a-button
                type="link"
                size="small"
                @click="editContact(record)"
              >
                编辑
              </a-button>
              <a-button
                type="link"
                size="small"
                :disabled="record.is_primary"
                @click="setPrimaryContact(record)"
              >
                主要
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="testContact(record)"
              >
                测试
              </a-button>
              <a-popconfirm
                title="确定要删除此联系方式吗？"
                @confirm="deleteContact(record)"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                >
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>

      <!-- 添加/编辑联系方式表单 -->
      <a-card
        :title="editingContact ? '编辑联系方式' : '添加联系方式'"
        size="small"
        style="margin-top: 16px"
      >
        <a-form
          ref="contactFormRef"
          :model="contactForm"
          :rules="contactRules"
          layout="vertical"
        >
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item
                label="类型"
                name="contact_type"
              >
                <a-select
                  v-model:value="contactForm.contact_type"
                  placeholder="请选择类型"
                  :disabled="!!editingContact"
                >
                  <a-select-option value="email">
                    邮箱
                  </a-select-option>
                  <a-select-option value="webhook">
                    Webhook
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="12">
              <a-form-item
                label="设为主要"
                name="is_primary"
              >
                <a-switch v-model:checked="contactForm.is_primary" />
              </a-form-item>
            </a-col>
          </a-row>

          <a-form-item
            label="地址"
            name="address"
          >
            <a-textarea
              v-model:value="contactForm.address"
              placeholder="邮箱地址或 Webhook URL"
              :rows="2"
            />
          </a-form-item>

          <a-form-item>
            <a-space>
              <a-button
                type="primary"
                @click="handleSaveContact"
              >
                {{ editingContact ? '保存' : '添加' }}
              </a-button>
              <a-button @click="handleCancelContact">
                取消
              </a-button>
            </a-space>
          </a-form-item>
        </a-form>
      </a-card>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { usersApi, type UserInfo, type UserCreate, type UserUpdate } from '@/api/modules/settings'

// 用户数据
const users = ref([])
const loading = ref(false)
const searchText = ref('')
const statusFilter = ref()

// 分页
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 表格列
const columns = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '显示名称', dataIndex: 'display_name', key: 'display_name' },
  { title: '邮箱', dataIndex: 'email', key: 'email' },
  { title: '角色', key: 'roles' },
  { title: '状态', key: 'status' },
  { title: '创建时间', key: 'created_at' },
  { title: '操作', key: 'action', width: 200 }
]

// 弹窗和表单
const showCreateModal = ref(false)
const editingUser = ref<any>(null)
const formRef = ref()
const userForm = reactive({
  username: '',
  password: '',
  display_name: '',
  email: '',
  roles: [],
  status: 'active'
})

// 表单验证规则
const rules = {
  username: [{ required: true, message: '请输入用户名' }],
  password: [{ required: true, message: '请输入密码', min: 6 }],
  display_name: [{ required: true, message: '请输入显示名称' }],
  email: [
    { required: true, message: '请输入邮箱' },
    { type: 'email', message: '邮箱格式不正确' }
  ],
  roles: [{ required: true, message: '请选择角色' }]
}

// 角色选项
const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '操作员', value: 'operator' },
  { label: '查看者', value: 'viewer' }
]

// 加载用户列表
const loadUsers = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (statusFilter.value) params.status = statusFilter.value
    if (searchText.value) params.search = searchText.value

    const data = await usersApi.list(params)
    users.value = data
    pagination.total = data.length
  } catch (error) {
    message.error('加载用户列表失败')
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.current = 1
  loadUsers()
}

// 表格变化
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadUsers()
}

// 编辑用户
const editUser = (user: any) => {
  editingUser.value = user
  Object.assign(userForm, {
    username: user.username,
    display_name: user.display_name,
    email: user.email,
    roles: user.roles,
    status: user.status
  })
  showCreateModal.value = true
}

// 保存用户
const handleSaveUser = async () => {
  try {
    await formRef.value.validate()

    if (editingUser.value) {
      // 更新用户
      const updateData: UserUpdate = {
        display_name: userForm.display_name,
        email: userForm.email,
        roles: userForm.roles,
        status: userForm.status as 'active' | 'disabled'
      }
      await usersApi.update(editingUser.value.uuid, updateData)
      message.success('用户更新成功')
    } else {
      // 创建用户
      const createData: UserCreate = {
        username: userForm.username,
        password: userForm.password,
        display_name: userForm.display_name,
        email: userForm.email,
        roles: userForm.roles,
        status: userForm.status as 'active' | 'disabled'
      }
      await usersApi.create(createData)
      message.success('用户创建成功')
    }

    handleCancelEdit()
    loadUsers()
  } catch (error: any) {
    if (error?.errorFields) {
      // 表单验证错误
      console.error('Validation failed:', error)
    } else {
      message.error('操作失败，请稍后重试')
    }
  }
}

// 取消编辑
const handleCancelEdit = () => {
  showCreateModal.value = false
  editingUser.value = null
  formRef.value?.resetFields()
}

// 重置密码
const resetPassword = async (user: UserInfo) => {
  try {
    await usersApi.resetPassword(user.uuid, user.username)
    message.success(`密码已重置为用户名: ${user.username}`)
  } catch (error) {
    message.error('重置密码失败')
  }
}

// 删除用户
const deleteUser = async (user: UserInfo) => {
  try {
    await usersApi.delete(user.uuid)
    message.success(`用户 ${user.username} 已删除`)
    loadUsers()
  } catch (error) {
    message.error('删除用户失败')
  }
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

// ==================== 联系方式管理 ====================

// 联系方式抽屉状态
const showContactsDrawer = ref(false)
const contactsLoading = ref(false)
const currentUser = ref<any>(null)
const contacts = ref<any[]>([])
const contactFormRef = ref()
const editingContact = ref<any>(null)

// 联系方式表单
const contactForm = reactive({
  uuid: '',
  contact_type: 'email',
  address: '',
  is_primary: false,
  is_active: true
})

// 联系方式表单验证规则
const contactRules = {
  contact_type: [{ required: true, message: '请选择联系方式类型' }],
  address: [
    { required: true, message: '请输入联系地址' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ]
}

// 联系方式表格列
const contactColumns = [
  { title: '类型', dataIndex: 'contact_type', key: 'contact_type', width: 70 },
  { title: '地址', dataIndex: 'address', key: 'address' },
  { title: '主要', dataIndex: 'is_primary', key: 'is_primary', width: 60, align: 'center' },
  { title: '状态', dataIndex: 'is_active', key: 'is_active', width: 60, align: 'center' },
  { title: '操作', key: 'action', width: 200 }
]

// 打开联系方式抽屉
const openContactsDrawer = async (user: any) => {
  currentUser.value = user
  showContactsDrawer.value = true
  await loadContacts()
}

// 加载联系方式列表
const loadContacts = async () => {
  if (!currentUser.value) return

  contactsLoading.value = true
  try {
    const data = await usersApi.listContacts(currentUser.value.uuid)
    contacts.value = data
  } catch (error) {
    message.error('加载联系方式失败')
  } finally {
    contactsLoading.value = false
  }
}

// 添加联系方式
const handleAddContact = () => {
  editingContact.value = null
  Object.assign(contactForm, {
    uuid: '',
    contact_type: 'email',
    address: '',
    is_primary: false,
    is_active: true
  })
}

// 编辑联系方式
const editContact = (contact: any) => {
  editingContact.value = contact
  Object.assign(contactForm, {
    uuid: contact.uuid,
    contact_type: contact.contact_type,
    address: contact.address,
    is_primary: contact.is_primary,
    is_active: contact.is_active
  })
}

// 保存联系方式
const handleSaveContact = async () => {
  if (!currentUser.value) return

  try {
    await contactFormRef.value.validate()

    if (contactForm.uuid) {
      // 更新
      await usersApi.updateContact(contactForm.uuid, {
        contact_type: contactForm.contact_type,
        address: contactForm.address,
        is_primary: contactForm.is_primary,
        is_active: contactForm.is_active
      })
      message.success('联系方式更新成功')
    } else {
      // 创建
      await usersApi.createContact(currentUser.value.uuid, {
        contact_type: contactForm.contact_type,
        address: contactForm.address,
        is_primary: contactForm.is_primary
      })
      message.success('联系方式添加成功')
    }

    await loadContacts()
    handleCancelContact()
  } catch (error: any) {
    if (error?.errorFields) {
      console.error('Validation failed:', error)
    } else {
      message.error('操作失败')
    }
  }
}

// 取消编辑联系方式
const handleCancelContact = () => {
  editingContact.value = null
  contactForm.uuid = ''
  contactForm.contact_type = 'email'
  contactForm.address = ''
  contactForm.is_primary = false
  contactForm.is_active = true
  contactFormRef.value?.resetFields()
}

// 删除联系方式
const deleteContact = async (contact: any) => {
  try {
    await usersApi.deleteContact(contact.uuid)
    message.success('联系方式删除成功')
    await loadContacts()
  } catch (error) {
    message.error('删除失败')
  }
}

// 测试联系方式
const testContact = async (contact: any) => {
  try {
    const result = await usersApi.testContact(contact.uuid, {
      address: contact.address,
      subject: 'Ginkgo 测试通知',
      content: '这是一条测试通知'
    })
    message.success(result.detail || result.message)
  } catch (error) {
    message.error('测试失败')
  }
}

// 设置主要联系方式
const setPrimaryContact = async (contact: any) => {
  try {
    await usersApi.setPrimaryContact(contact.uuid)
    message.success('已设置为主要联系方式')
    await loadContacts()
  } catch (error) {
    message.error('设置失败')
  }
}

// 切换联系方式状态
const handleToggleContactStatus = async (contact: any) => {
  try {
    await usersApi.updateContact(contact.uuid, {
      is_active: contact.is_active
    })
    message.success('状态更新成功')
  } catch (error) {
    message.error('状态更新失败')
    // 恢复状态
    contact.is_active = !contact.is_active
  }
}

// 获取联系方式类型显示名称
const getContactTypeName = (type: string) => {
  const typeMap: Record<string, string> = {
    'email': '邮箱',
    'webhook': 'Webhook'
  }
  return typeMap[type] || type
}

// 复制地址到剪贴板
const copyAddress = async (address: string) => {
  try {
    // 优先使用 Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(address)
      message.success('地址已复制到剪贴板')
      return
    }

    // 降级方案：创建临时 textarea
    const textarea = document.createElement('textarea')
    textarea.value = address
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const successful = document.execCommand('copy')
    document.body.removeChild(textarea)

    if (successful) {
      message.success('地址已复制到剪贴板')
    } else {
      message.error('复制失败')
    }
  } catch (error) {
    message.error('复制失败')
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped>
.address-cell {
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 350px;
}

.address-cell:hover {
  color: #1890ff;
}
</style>
