<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-title">用户组管理</h1>
      <a-button type="primary" @click="showCreateModal = true">添加用户组</a-button>
    </div>

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
            <a-badge :count="record.user_count" :number-style="{ backgroundColor: '#52c41a' }" />
          </template>
          <template v-if="column.key === 'permissions'">
            <a-space wrap>
              <a-tag v-for="perm in record.permissions?.slice(0, 3)" :key="perm" color="blue">
                {{ perm }}
              </a-tag>
              <a-tag v-if="record.permissions?.length > 3" color="default">
                +{{ record.permissions.length - 3 }}
              </a-tag>
            </a-space>
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="editGroup(record)">编辑</a>
              <a @click="managePermissions(record)">权限</a>
              <a-popconfirm title="确定删除?" @confirm="deleteGroup(record)">
                <a class="text-red-500">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <a-modal v-model:open="showCreateModal" :title="editingGroup ? '编辑用户组' : '添加用户组'" @ok="handleSubmit">
      <a-form layout="vertical">
        <a-form-item label="组名称" required>
          <a-input v-model:value="groupForm.name" placeholder="输入组名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="groupForm.description" :rows="3" placeholder="输入描述" />
        </a-form-item>
        <a-form-item label="权限">
          <a-select v-model:value="groupForm.permissions" mode="multiple" placeholder="选择权限">
            <a-select-option value="backtest:view">查看回测</a-select-option>
            <a-select-option value="backtest:create">创建回测</a-select-option>
            <a-select-option value="portfolio:view">查看组合</a-select-option>
            <a-select-option value="portfolio:create">创建组合</a-select-option>
            <a-select-option value="data:manage">数据管理</a-select-option>
            <a-select-option value="system:admin">系统管理</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="showPermissionModal" title="权限管理" width="600px" @ok="savePermissions">
      <a-transfer
        v-model:target-keys="selectedPermissions"
        :data-source="allPermissions"
        :titles="['可用权限', '已有权限']"
        :render="(item: any) => item.title"
        show-search
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'

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

const columns = [
  { title: '组名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '用户数', dataIndex: 'user_count', key: 'user_count', width: 100 },
  { title: '权限', dataIndex: 'permissions', key: 'permissions' },
  { title: '操作', key: 'action', width: 180 },
]

const allPermissions = [
  { key: 'backtest:view', title: '查看回测' },
  { key: 'backtest:create', title: '创建回测' },
  { key: 'portfolio:view', title: '查看组合' },
  { key: 'portfolio:create', title: '创建组合' },
  { key: 'data:manage', title: '数据管理' },
  { key: 'system:admin', title: '系统管理' },
]

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
  showPermissionModal.value = true
}

const deleteGroup = (record: any) => {
  userGroups.value = userGroups.value.filter(g => g.uuid !== record.uuid)
  message.success('用户组已删除')
}

const handleSubmit = () => {
  if (!groupForm.name) {
    message.warning('请输入组名称')
    return
  }

  if (editingGroup.value) {
    Object.assign(editingGroup.value, groupForm)
    message.success('用户组已更新')
  } else {
    userGroups.value.push({
      uuid: Date.now().toString(),
      ...groupForm,
      user_count: 0,
    })
    message.success('用户组已创建')
  }

  showCreateModal.value = false
  editingGroup.value = null
  Object.assign(groupForm, { name: '', description: '', permissions: [] })
}

const savePermissions = () => {
  if (editingGroup.value) {
    editingGroup.value.permissions = [...selectedPermissions.value]
    message.success('权限已更新')
  }
  showPermissionModal.value = false
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.space-y-6 > * + * {
  margin-top: 24px;
}
.card {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
}
.text-title {
  font-size: 24px;
  font-weight: 600;
}
.text-red-500 {
  color: #f5222d;
}
</style>
