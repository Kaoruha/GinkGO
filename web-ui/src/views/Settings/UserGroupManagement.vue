<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-title">
        用户组管理
      </h1>
      <a-button
        type="primary"
        @click="showCreateModal = true"
      >
        添加用户组
      </a-button>
    </div>

    <!-- 用户组列表 -->
    <div class="card">
      <a-table
        :columns="columns"
        :data-source="userGroups"
        :loading="loading"
        :pagination="false"
        row-key="uuid"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'description'">
            {{ record.description || '-' }}
          </template>
          <template v-if="column.key === 'user_count'">
            <a-badge
              :count="record.user_count"
              :number-style="{ backgroundColor: '#52c41a' }"
            />
          </template>
          <template v-if="column.key === 'permissions'">
            <a-tag
              v-for="perm in record.permissions?.slice(0, 3)"
              :key="perm"
              color="blue"
            >
              {{ perm }}
            </a-tag>
            <a-tag
              v-if="record.permissions?.length > 3"
              color="default"
            >
              +{{ record.permissions.length - 3 }}
            </a-tag>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="editGroup(record)"
              >
                编辑
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="openMembersDrawer(record)"
              >
                成员管理
              </a-button>
              <a-button
                type="link"
                size="small"
                @click="configPermissions(record)"
              >
                权限配置
              </a-button>
              <a-popconfirm
                title="确定要删除此用户组吗？"
                @confirm="deleteGroup(record)"
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

    <!-- 创建/编辑用户组弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      :title="editingGroup ? '编辑用户组' : '添加用户组'"
      width="600px"
      @ok="handleSaveGroup"
      @cancel="handleCancelEdit"
    >
      <a-form
        ref="formRef"
        :model="groupForm"
        :rules="rules"
        layout="vertical"
      >
        <a-form-item
          label="组名称"
          name="name"
        >
          <a-input
            v-model:value="groupForm.name"
            placeholder="请输入组名称"
          />
        </a-form-item>

        <a-form-item
          label="描述"
          name="description"
        >
          <a-textarea
            v-model:value="groupForm.description"
            placeholder="请输入描述"
            :rows="3"
          />
        </a-form-item>

        <a-form-item
          label="权限"
          name="permissions"
        >
          <a-select
            v-model:value="groupForm.permissions"
            mode="multiple"
            placeholder="请选择权限"
            :options="permissionOptions"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 权限配置弹窗 -->
    <a-modal
      v-model:open="showPermissionModal"
      title="权限配置"
      width="700px"
      @ok="handleSavePermissions"
      @cancel="showPermissionModal = false"
    >
      <a-form layout="vertical">
        <a-form-item label="用户组">
          <a-input
            :value="currentGroup?.name"
            disabled
          />
        </a-form-item>

        <a-form-item label="权限列表">
          <a-checkbox-group v-model:value="selectedPermissions">
            <a-row>
              <a-col
                v-for="perm in allPermissions"
                :key="perm.value"
                :span="12"
              >
                <a-checkbox :value="perm.value">
                  {{ perm.label }}
                  <span class="text-gray-500 text-sm">- {{ perm.description }}</span>
                </a-checkbox>
              </a-col>
            </a-row>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 成员管理抽屉 -->
    <a-drawer
      v-model:open="showMembersDrawer"
      :title="`${currentGroup?.name || ''} 的成员`"
      width="700px"
      placement="right"
    >
      <template #extra>
        <a-button
          type="primary"
          @click="openAddMemberModal"
        >
          添加成员
        </a-button>
      </template>

      <!-- 成员列表 -->
      <a-table
        :columns="memberColumns"
        :data-source="members"
        :loading="membersLoading"
        :pagination="false"
        row-key="uuid"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'email'">
            {{ record.email || '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-popconfirm
              title="确定要将此用户移出该组吗？"
              @confirm="removeMember(record)"
            >
              <a-button
                type="link"
                size="small"
                danger
              >
                移除
              </a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-drawer>

    <!-- 添加成员弹窗 -->
    <a-modal
      v-model:open="showAddMemberModal"
      title="添加成员"
      @ok="handleAddMember"
      @cancel="showAddMemberModal = false"
    >
      <a-form layout="vertical">
        <a-form-item label="选择用户">
          <a-select
            v-model:value="selectedUserUuid"
            placeholder="请选择用户"
            :options="availableUsers"
            :loading="usersLoading"
            show-search
            :filter-option="filterUserOption"
          >
            <template #label="{ value, label }">
              <span>{{ label }}</span>
              <span class="text-gray-500 ml-2">{{ value }}</span>
            </template>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { userGroupsApi, usersApi, type UserGroupInfo, type UserGroupCreate } from '@/api/modules/settings'

// 用户组数据
const userGroups = ref<UserGroupInfo[]>([])
const loading = ref(false)

// 所有用户列表
const allUsers = ref<any[]>([])

// 加载所有用户
const loadAllUsers = async () => {
  try {
    const data = await usersApi.list()
    allUsers.value = data
  } catch (error) {
    console.error('Failed to load users:', error)
  }
}

// 表格列
const columns = [
  { title: '组名称', dataIndex: 'name', key: 'name' },
  { title: '描述', key: 'description' },
  { title: '用户数', dataIndex: 'user_count', key: 'user_count' },
  { title: '权限', key: 'permissions' },
  { title: '操作', key: 'action', width: 250 }
]

// 创建/编辑弹窗
const showCreateModal = ref(false)
const editingGroup = ref<any>(null)
const formRef = ref()
const groupForm = reactive({
  name: '',
  description: '',
  permissions: []
})

const rules = {
  name: [{ required: true, message: '请输入组名称' }],
  permissions: [{ required: true, message: '请选择权限' }]
}

// 权限配置弹窗
const showPermissionModal = ref(false)
const currentGroup = ref<any>(null)
const selectedPermissions = ref<string[]>([])

// 权限选项
const permissionOptions = [
  { label: '查看仪表盘', value: 'dashboard:view' },
  { label: '管理Portfolio', value: 'portfolio:manage' },
  { label: '查看Portfolio', value: 'portfolio:view' },
  { label: '管理回测', value: 'backtest:manage' },
  { label: '查看回测', value: 'backtest:view' },
  { label: '管理组件', value: 'component:manage' },
  { label: '系统设置', value: 'system:config' }
]

// 所有权限（带描述）
const allPermissions = [
  { label: '查看仪表盘', value: 'dashboard:view', description: '查看仪表盘和统计信息' },
  { label: '管理Portfolio', value: 'portfolio:manage', description: '创建、编辑、删除Portfolio' },
  { label: '查看Portfolio', value: 'portfolio:view', description: '查看Portfolio详情和状态' },
  { label: '管理回测', value: 'backtest:manage', description: '创建和管理回测任务' },
  { label: '查看回测', value: 'backtest:view', description: '查看回测结果' },
  { label: '管理组件', value: 'component:manage', description: '创建和编辑自定义组件' },
  { label: '系统设置', value: 'system:config', description: '修改系统配置和用户管理' }
]

// 加载用户组列表
const loadUserGroups = async () => {
  loading.value = true
  try {
    const data = await userGroupsApi.list()
    userGroups.value = data
  } catch (error) {
    message.error('加载用户组列表失败')
  } finally {
    loading.value = false
  }
}

// 编辑用户组
const editGroup = (group: UserGroupInfo) => {
  editingGroup.value = group
  Object.assign(groupForm, {
    name: group.name,
    description: group.description,
    permissions: group.permissions
  })
  showCreateModal.value = true
}

// 保存用户组
const handleSaveGroup = async () => {
  try {
    await formRef.value.validate()

    if (editingGroup.value) {
      // 更新用户组
      await userGroupsApi.update(editingGroup.value.uuid, {
        name: groupForm.name,
        description: groupForm.description,
        permissions: groupForm.permissions
      })
      message.success('用户组更新成功')
    } else {
      // 创建用户组
      const createData: UserGroupCreate = {
        name: groupForm.name,
        description: groupForm.description,
        permissions: groupForm.permissions
      }
      await userGroupsApi.create(createData)
      message.success('用户组创建成功')
    }

    handleCancelEdit()
    loadUserGroups()
  } catch (error: any) {
    if (error?.errorFields) {
      console.error('Validation failed:', error)
    } else {
      message.error('操作失败')
    }
  }
}

// 取消编辑
const handleCancelEdit = () => {
  showCreateModal.value = false
  editingGroup.value = null
  formRef.value?.resetFields()
}

// 配置权限
const configPermissions = (group: UserGroupInfo) => {
  currentGroup.value = group
  selectedPermissions.value = [...group.permissions]
  showPermissionModal.value = true
}

// 保存权限
const handleSavePermissions = async () => {
  try {
    if (currentGroup.value) {
      await userGroupsApi.update(currentGroup.value.uuid, {
        permissions: selectedPermissions.value
      })
      message.success(`用户组 ${currentGroup.value.name} 的权限已更新`)
      showPermissionModal.value = false
      loadUserGroups()
    }
  } catch (error) {
    message.error('权限更新失败')
  }
}

// ==================== 成员管理 ====================

// 成员管理抽屉
const showMembersDrawer = ref(false)
const members = ref<any[]>([])
const membersLoading = ref(false)

// 添加成员弹窗
const showAddMemberModal = ref(false)
const selectedUserUuid = ref('')
const availableUsers = ref<any[]>([])
const usersLoading = ref(false)

// 打开添加成员弹窗
const openAddMemberModal = () => {
  // 过滤掉已经在组中的用户
  const memberUuids = new Set(members.value.map(m => m.user_uuid))
  availableUsers.value = allUsers.value
    .filter(u => !memberUuids.has(u.uuid))
    .map(u => ({
      value: u.uuid,
      label: `${u.display_name || u.username} (${u.username})`
    }))
  showAddMemberModal.value = true
}

// 成员表格列
const memberColumns = [
  { title: '用户名', dataIndex: 'username', key: 'username' },
  { title: '显示名称', dataIndex: 'display_name', key: 'display_name' },
  { title: '邮箱', key: 'email' },
  { title: '操作', key: 'action', width: 100 }
]

// 打开成员管理抽屉
const openMembersDrawer = async (group: UserGroupInfo) => {
  currentGroup.value = group
  showMembersDrawer.value = true
  await loadMembers()
}

// 加载成员列表
const loadMembers = async () => {
  if (!currentGroup.value) return

  membersLoading.value = true
  try {
    const data = await userGroupsApi.listMembers(currentGroup.value.uuid)
    members.value = data
  } catch (error) {
    message.error('加载成员列表失败')
  } finally {
    membersLoading.value = false
  }
}

// 用户搜索过滤
const filterUserOption = (input: string, option: any) => {
  const label = option.label.toLowerCase()
  const value = option.value.toLowerCase()
  return label.includes(input.toLowerCase()) || value.includes(input.toLowerCase())
}

// 添加成员
const handleAddMember = async () => {
  if (!currentGroup.value || !selectedUserUuid.value) {
    message.warning('请选择用户')
    return
  }

  try {
    await userGroupsApi.addMember(currentGroup.value.uuid, selectedUserUuid.value)
    message.success('成员添加成功')
    showAddMemberModal.value = false
    selectedUserUuid.value = ''
    await loadMembers()
    await loadUserGroups() // 更新用户数量
  } catch (error: any) {
    if (error?.response?.status === 409) {
      message.error('该用户已在组中')
    } else {
      message.error('添加失败')
    }
  }
}

// 移除成员
const removeMember = async (member: any) => {
  if (!currentGroup.value) return

  try {
    await userGroupsApi.removeMember(currentGroup.value.uuid, member.user_uuid)
    message.success('成员移除成功')
    await loadMembers()
    await loadUserGroups() // 更新用户数量
  } catch (error) {
    message.error('移除失败')
  }
}

// 删除用户组
const deleteGroup = async (group: UserGroupInfo) => {
  try {
    await userGroupsApi.delete(group.uuid)
    message.success(`用户组 ${group.name} 已删除`)
    loadUserGroups()
  } catch (error) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadUserGroups()
  loadAllUsers()
})
</script>
