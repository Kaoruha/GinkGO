<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <div class="flex items-center justify-between">
      <h1 class="text-title">通知管理</h1>
      <a-button type="primary" @click="showTemplateModal = true">
        新建通知模板
      </a-button>
    </div>

    <!-- 标签页 -->
    <a-card>
      <a-tabs v-model:activeKey="activeTab">
        <!-- 通知模板 -->
        <a-tab-pane key="templates" tab="通知模板">
          <div class="mb-4">
            <a-table
              :columns="templateColumns"
              :data-source="templates"
              :loading="loading"
              :pagination="pagination"
              row-key="uuid"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'type'">
                  <a-tag :color="getTypeColor(record.type)">
                    {{ getTypeLabel(record.type) }}
                  </a-tag>
                </template>
                <template v-if="column.key === 'enabled'">
                  <a-switch
                    :checked="record.enabled"
                    @change="(checked) => toggleTemplate(record, checked)"
                  />
                </template>
                <template v-if="column.key === 'updated_at'">
                  {{ formatDate(record.updated_at) }}
                </template>
                <template v-if="column.key === 'action'">
                  <a-space>
                    <a-button type="link" size="small" @click="editTemplate(record)">
                      编辑
                    </a-button>
                    <a-button type="link" size="small" @click="testNotification(record)">
                      测试
                    </a-button>
                    <a-popconfirm
                      title="确定要删除此模板吗？"
                      @confirm="deleteTemplate(record)"
                    >
                      <a-button type="link" size="small" danger>删除</a-button>
                    </a-popconfirm>
                  </a-space>
                </template>
              </template>
            </a-table>
          </div>
        </a-tab-pane>

        <!-- 通知历史 -->
        <a-tab-pane key="history" tab="通知历史">
          <div class="mb-4 flex gap-4">
            <a-input-search
              v-model:value="searchText"
              placeholder="搜索通知"
              style="width: 300px"
              @search="loadHistory"
            />
            <a-select
              v-model:value="typeFilter"
              placeholder="类型筛选"
              style="width: 150px"
              allowClear
              @change="loadHistory"
            >
              <a-select-option value="email">邮件</a-select-option>
              <a-select-option value="discord">Discord</a-select-option>
              <a-select-option value="system">系统</a-select-option>
            </a-select>
          </div>

          <a-table
            :columns="historyColumns"
            :data-source="history"
            :loading="historyLoading"
            :pagination="historyPagination"
            row-key="uuid"
            @change="handleHistoryTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'type'">
                <a-tag :color="getTypeColor(record.type)">
                  {{ getTypeLabel(record.type) }}
                </a-tag>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'success' ? 'success' : 'error'">
                  {{ record.status === 'success' ? '成功' : '失败' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'created_at'">
                {{ formatDateTime(record.created_at) }}
              </template>
              <template v-if="column.key === 'action'">
                <a-button type="link" size="small" @click="viewDetail(record)">
                  查看详情
                </a-button>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <!-- 接收人管理 -->
        <a-tab-pane key="recipients" tab="接收人管理">
          <div class="mb-4 flex justify-between">
            <a-button type="primary" @click="showRecipientModal = true">
              添加接收人
            </a-button>
          </div>
          <a-table
            :columns="recipientColumns"
            :data-source="recipients"
            :loading="recipientsLoading"
            row-key="uuid"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'recipient_type'">
                <a-tag :color="record.recipient_type === 'USER' ? 'blue' : 'green'">
                  {{ record.recipient_type === 'USER' ? '用户' : '用户组' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'target'">
                <div v-if="record.recipient_type === 'USER' && record.user_info" class="text-sm">
                  <div class="font-medium">{{ record.user_info.display_name || record.user_info.username }}</div>
                  <div class="text-xs text-gray-500">@{{ record.user_info.username }}</div>
                </div>
                <div v-else-if="record.recipient_type === 'USER_GROUP' && record.user_group_info" class="text-sm">
                  <div class="font-medium">{{ record.user_group_info.name }}</div>
                  <div class="text-xs text-gray-500">用户组</div>
                </div>
                <span v-else class="text-gray-400">-</span>
              </template>
              <template v-if="column.key === 'description'">
                <span class="text-gray-500">{{ record.description || '-' }}</span>
              </template>
              <template v-if="column.key === 'is_default'">
                <a-tag v-if="record.is_default" color="orange">默认</a-tag>
                <span v-else class="text-gray-400">-</span>
              </template>
              <template v-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="editRecipient(record)">
                    编辑
                  </a-button>
                  <a-button type="link" size="small" @click="testRecipient(record)">
                    测试
                  </a-button>
                  <a-popconfirm
                    title="确定要删除此接收人吗？"
                    @confirm="deleteRecipient(record)"
                  >
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <!-- 创建/编辑模板弹窗 -->
    <a-modal
      v-model:open="showTemplateModal"
      :title="editingTemplate ? '编辑通知模板' : '新建通知模板'"
      width="800px"
      @ok="handleSaveTemplate"
      @cancel="handleCancelTemplate"
    >
      <a-form
        ref="templateFormRef"
        :model="templateForm"
        :rules="templateRules"
        layout="vertical"
      >
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="模板名称" name="name">
              <a-input v-model:value="templateForm.name" placeholder="请输入模板名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="通知类型" name="type">
              <a-select v-model:value="templateForm.type" placeholder="选择类型">
                <a-select-option value="email">邮件</a-select-option>
                <a-select-option value="discord">Discord</a-select-option>
                <a-select-option value="system">系统</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="主题" name="subject">
          <a-input v-model:value="templateForm.subject" placeholder="请输入主题" />
        </a-form-item>

        <a-form-item label="内容模板" name="content">
          <a-textarea
            v-model:value="templateForm.content"
            placeholder="支持变量: {portfolio_name}, {signal}, {time} 等"
            :rows="6"
          />
        </a-form-item>

        <a-form-item label="触发条件" name="trigger">
          <a-select v-model:value="templateForm.trigger" mode="multiple" placeholder="选择触发条件">
            <a-select-option value="signal_created">信号生成</a-select-option>
            <a-select-option value="order_filled">订单成交</a-select-option>
            <a-select-option value="risk_alert">风控警报</a-select-option>
            <a-select-option value="backtest_completed">回测完成</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 创建/编辑接收人弹窗 -->
    <a-modal
      v-model:open="showRecipientModal"
      :title="editingRecipient ? '编辑接收人' : '新建接收人'"
      width="600px"
      @ok="handleSaveRecipient"
      @cancel="handleCancelRecipient"
    >
      <a-form
        ref="recipientFormRef"
        :model="recipientForm"
        :rules="recipientRules"
        layout="vertical"
      >
        <a-form-item label="名称" name="name">
          <a-input v-model:value="recipientForm.name" placeholder="请输入接收人名称" />
        </a-form-item>

        <a-form-item label="接收人类型" name="recipient_type">
          <a-select v-model:value="recipientForm.recipient_type" placeholder="选择类型">
            <a-select-option value="USER">单个用户</a-select-option>
            <a-select-option value="USER_GROUP">用户组</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="用户" name="user_id" v-if="recipientForm.recipient_type === 'USER'">
          <a-select
            v-model:value="recipientForm.user_id"
            placeholder="选择用户"
            :filter-option="filterUser"
            show-search
          >
            <a-select-option v-for="user in users" :key="user.uuid" :value="user.uuid">
              {{ user.display_name || user.username }} ({{ user.email }})
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="用户组" name="user_group_id" v-if="recipientForm.recipient_type === 'USER_GROUP'">
          <a-select
            v-model:value="recipientForm.user_group_id"
            placeholder="选择用户组"
            :filter-option="filterGroup"
            show-search
          >
            <a-select-option v-for="group in userGroups" :key="group.uuid" :value="group.uuid">
              {{ group.name }}
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item label="描述" name="description">
          <a-textarea
            v-model:value="recipientForm.description"
            placeholder="请输入描述（可选）"
            :rows="3"
          />
        </a-form-item>

        <a-form-item>
          <a-checkbox v-model:checked="recipientForm.is_default">
            设为默认接收人
          </a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 通知详情弹窗 -->
    <a-modal
      v-model:open="showDetailModal"
      title="通知详情"
      width="700px"
      :footer="null"
    >
      <a-descriptions :column="1" bordered v-if="currentDetail">
        <a-descriptions-item label="类型">
          <a-tag :color="getTypeColor(currentDetail.type)">
            {{ getTypeLabel(currentDetail.type) }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="主题">
          {{ currentDetail.subject }}
        </a-descriptions-item>
        <a-descriptions-item label="接收人">
          {{ currentDetail.recipient }}
        </a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-tag :color="currentDetail.status === 'success' ? 'success' : 'error'">
            {{ currentDetail.status === 'success' ? '成功' : '失败' }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="发送时间">
          {{ formatDateTime(currentDetail.created_at) }}
        </a-descriptions-item>
        <a-descriptions-item label="内容">
          <pre class="whitespace-pre-wrap">{{ currentDetail.content }}</pre>
        </a-descriptions-item>
        <a-descriptions-item label="错误信息" v-if="currentDetail.error">
          <span class="text-red-500">{{ currentDetail.error }}</span>
        </a-descriptions-item>
      </a-descriptions>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { notificationsApi, usersApi, userGroupsApi, type NotificationTemplate, type NotificationHistory, type NotificationRecipient } from '@/api/modules/settings'

const activeTab = ref('templates')
const loading = ref(false)
const historyLoading = ref(false)
const recipientsLoading = ref(false)

// 通知模板
const templates = ref<NotificationTemplate[]>([])
const pagination = reactive({ current: 1, pageSize: 10, total: 0 })
const templateColumns = [
  { title: '模板名称', dataIndex: 'name', key: 'name' },
  { title: '类型', key: 'type' },
  { title: '主题', dataIndex: 'subject', key: 'subject' },
  { title: '状态', key: 'enabled' },
  { title: '更新时间', key: 'updated_at' },
  { title: '操作', key: 'action', width: 200 }
]

// 通知历史
const history = ref<NotificationHistory[]>([])
const historyPagination = reactive({ current: 1, pageSize: 20, total: 0 })
const historyColumns = [
  { title: '类型', key: 'type' },
  { title: '主题', dataIndex: 'subject', key: 'subject' },
  { title: '接收人', dataIndex: 'recipient', key: 'recipient' },
  { title: '状态', key: 'status' },
  { title: '发送时间', key: 'created_at' },
  { title: '操作', key: 'action', width: 100 }
]

// 接收人
const recipients = ref<NotificationRecipient[]>([])
const recipientColumns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '类型', key: 'recipient_type', width: 100 },
  { title: '目标', key: 'target', width: 250 },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '默认', key: 'is_default', width: 80 },
  { title: '操作', key: 'action', width: 150 }
]

// 用户和用户组列表（用于选择）
const users = ref<any[]>([])
const userGroups = ref<any[]>([])

// 加载用户和用户组
const loadUsers = async () => {
  try {
    const data = await usersApi.list()
    users.value = data
  } catch (error) {
    console.error('Failed to load users:', error)
  }
}

const loadUserGroups = async () => {
  try {
    const data = await userGroupsApi.list()
    userGroups.value = data
  } catch (error) {
    console.error('Failed to load user groups:', error)
  }
}

// 过滤函数
const filterUser = (input: string, option: any) => {
  const user = option.props.children[0] || ''
  return user.toLowerCase().includes(input.toLowerCase())
}

const filterGroup = (input: string, option: any) => {
  const group = option.props.children
  return group.toLowerCase().includes(input.toLowerCase())
}

const searchText = ref('')
const typeFilter = ref<string>()

// 弹窗
const showTemplateModal = ref(false)
const showDetailModal = ref(false)
const editingTemplate = ref<NotificationTemplate | null>(null)
const currentDetail = ref<NotificationHistory | null>(null)

// 表单
const templateFormRef = ref()
const templateForm = reactive({
  name: '',
  type: 'email',
  subject: '',
  content: '',
  trigger: []
})

const templateRules = {
  name: [{ required: true, message: '请输入模板名称' }],
  type: [{ required: true, message: '请选择类型' }],
  subject: [{ required: true, message: '请输入主题' }],
  content: [{ required: true, message: '请输入内容模板' }],
  trigger: [{ required: true, message: '请选择触发条件' }]
}

// 接收人表单
const showRecipientModal = ref(false)
const editingRecipient = ref<NotificationRecipient | null>(null)
const recipientFormRef = ref()
const recipientForm = reactive({
  name: '',
  recipient_type: 'USER' as 'USER' | 'USER_GROUP',
  user_id: undefined as string | undefined,
  user_group_id: undefined as string | undefined,
  is_default: false,
  description: ''
})

const recipientRules = {
  name: [{ required: true, message: '请输入接收人名称' }],
  recipient_type: [{ required: true, message: '请选择接收人类型' }],
  user_id: [
    {
      validator: (_rule: any, value: string) => {
        return new Promise((resolve, reject) => {
          if (recipientForm.recipient_type === 'USER') {
            if (!value) {
              reject(new Error('请选择用户'))
            } else {
              resolve()
            }
          } else {
            resolve()
          }
        })
      }
    }
  ],
  user_group_id: [
    {
      validator: (_rule: any, value: string) => {
        return new Promise((resolve, reject) => {
          if (recipientForm.recipient_type === 'USER_GROUP') {
            if (!value) {
              reject(new Error('请选择用户组'))
            } else {
              resolve()
            }
          } else {
            resolve()
          }
        })
      }
    }
  ]
}

// 获取类型颜色
const getTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    email: 'blue',
    discord: 'purple',
    system: 'green'
  }
  return colors[type] || 'default'
}

// 获取类型标签
const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    email: '邮件',
    discord: 'Discord',
    system: '系统'
  }
  return labels[type] || type
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 加载模板列表
const loadTemplates = async () => {
  loading.value = true
  try {
    const data = await notificationsApi.listTemplates()
    templates.value = data
  } catch (error) {
    message.error('加载模板列表失败')
  } finally {
    loading.value = false
  }
}

// 加载通知历史
const loadHistory = async () => {
  historyLoading.value = true
  try {
    const data = await notificationsApi.listHistory({
      type: typeFilter.value,
      page: historyPagination.current,
      page_size: historyPagination.pageSize
    })
    history.value = data
  } catch (error) {
    message.error('加载通知历史失败')
  } finally {
    historyLoading.value = false
  }
}

// 加载接收人
const loadRecipients = async () => {
  recipientsLoading.value = true
  try {
    const data = await notificationsApi.listRecipients()
    recipients.value = data
  } catch (error) {
    message.error('加载接收人列表失败')
  } finally {
    recipientsLoading.value = false
  }
}

// 切换模板状态
const toggleTemplate = async (template: NotificationTemplate, enabled: boolean) => {
  try {
    await notificationsApi.toggleTemplate(template.uuid, enabled)
    message.success(`模板 ${template.name} 已${enabled ? '启用' : '禁用'}`)
    loadTemplates()
  } catch (error) {
    message.error('操作失败')
  }
}

// 编辑模板
const editTemplate = (template: NotificationTemplate) => {
  editingTemplate.value = template
  Object.assign(templateForm, {
    name: template.name,
    type: template.type,
    subject: template.subject,
    content: '', // 需要从后端获取完整内容
    trigger: []
  })
  showTemplateModal.value = true
}

// 保存模板
const handleSaveTemplate = async () => {
  try {
    await templateFormRef.value.validate()

    if (editingTemplate.value) {
      await notificationsApi.updateTemplate(editingTemplate.value.uuid, templateForm)
      message.success('模板更新成功')
    } else {
      await notificationsApi.createTemplate(templateForm)
      message.success('模板创建成功')
    }

    handleCancelTemplate()
    loadTemplates()
  } catch (error: any) {
    if (error?.errorFields) {
      console.error('Validation failed:', error)
    } else {
      message.error('操作失败')
    }
  }
}

// 取消编辑
const handleCancelTemplate = () => {
  showTemplateModal.value = false
  editingTemplate.value = null
  templateFormRef.value?.resetFields()
}

// 测试通知
const testNotification = async (template: NotificationTemplate) => {
  try {
    await notificationsApi.testTemplate(template.uuid)
    message.success(`已发送测试通知: ${template.name}`)
  } catch (error) {
    message.error('测试失败')
  }
}

// 删除模板
const deleteTemplate = async (template: NotificationTemplate) => {
  try {
    await notificationsApi.deleteTemplate(template.uuid)
    message.success(`模板 ${template.name} 已删除`)
    loadTemplates()
  } catch (error) {
    message.error('删除失败')
  }
}

// 历史表格变化
const handleHistoryTableChange = (pag: any) => {
  historyPagination.current = pag.current
  loadHistory()
}

// 查看详情
const viewDetail = (record: NotificationHistory) => {
  currentDetail.value = record
  showDetailModal.value = true
}

// 接收人管理函数
const editRecipient = (recipient: NotificationRecipient) => {
  editingRecipient.value = recipient
  Object.assign(recipientForm, {
    name: recipient.name,
    recipient_type: recipient.recipient_type,
    user_id: recipient.user_id || undefined,
    user_group_id: recipient.user_group_id || undefined,
    is_default: recipient.is_default,
    description: recipient.description || ''
  })
  showRecipientModal.value = true
}

const handleSaveRecipient = async () => {
  try {
    console.log('开始保存接收人...', recipientForm)
    await recipientFormRef.value.validate()
    console.log('表单验证通过')

    if (editingRecipient.value) {
      console.log('更新接收人...', editingRecipient.value.uuid)
      await notificationsApi.updateRecipient(editingRecipient.value.uuid, recipientForm)
      message.success('接收人更新成功')
    } else {
      console.log('创建接收人...', recipientForm)
      await notificationsApi.createRecipient(recipientForm)
      message.success('接收人创建成功')
    }

    handleCancelRecipient()
    loadRecipients()
  } catch (error: any) {
    console.error('保存接收人失败:', error)
    if (error?.errorFields) {
      console.error('表单验证失败:', error)
    } else {
      message.error(`操作失败: ${error?.message || error?.response?.data?.message || '未知错误'}`)
    }
  }
}

const handleCancelRecipient = () => {
  showRecipientModal.value = false
  editingRecipient.value = null
  recipientFormRef.value?.resetFields()
}

const toggleRecipient = async (recipient: NotificationRecipient) => {
  try {
    await notificationsApi.toggleRecipient(recipient.uuid)
    message.success(`接收人 ${recipient.name} 已切换默认状态`)
    loadRecipients()
  } catch (error) {
    message.error('操作失败')
  }
}

const deleteRecipient = async (recipient: NotificationRecipient) => {
  try {
    await notificationsApi.deleteRecipient(recipient.uuid)
    message.success(`接收人 ${recipient.name} 已删除`)
    loadRecipients()
  } catch (error) {
    message.error('删除失败')
  }
}

// 测试接收人
const testRecipient = async (recipient: NotificationRecipient) => {
  const loadingKey = `test_${recipient.uuid}`
  try {
    // 添加加载状态
    message.loading({ content: '正在发送测试通知...', key: loadingKey, duration: 0 })

    const result = await notificationsApi.testRecipient(recipient.uuid)

    // 根据结果显示消息
    if (result.failed_count === 0) {
      message.success({
        content: `测试通知发送成功！已发送到 ${result.success_count} 个联系方式`,
        key: loadingKey,
        duration: 5
      })
    } else if (result.success_count > 0) {
      message.warning({
        content: `测试通知部分成功：${result.success_count} 成功, ${result.failed_count} 失败`,
        key: loadingKey,
        duration: 5
      })
    } else {
      message.error({
        content: `测试通知发送失败：${result.details?.join(', ') || '未知错误'}`,
        key: loadingKey,
        duration: 5
      })
    }

    // 显示详情
    if (result.details && result.details.length > 0) {
      console.log('测试通知详情:', result.details)
    }
  } catch (error: any) {
    message.error({
      content: `测试失败: ${error?.response?.data?.detail || error?.message || '未知错误'}`,
      key: loadingKey,
      duration: 5
    })
  }
}

onMounted(() => {
  loadTemplates()
  loadHistory()
  loadRecipients()
  loadUsers()
  loadUserGroups()
})
</script>
