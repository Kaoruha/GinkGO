<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="blue">系统</a-tag>
        通知管理
      </div>
      <a-button type="primary" @click="showTemplateModal = true">新建通知模板</a-button>
    </div>

    <a-card>
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="templates" tab="通知模板">
          <a-table :columns="templateColumns" :data-source="templates" :loading="loading" row-key="uuid">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'type'">
                <a-tag :color="getTypeColor(record.type)">{{ getTypeLabel(record.type) }}</a-tag>
              </template>
              <template v-if="column.key === 'enabled'">
                <a-switch :checked="record.enabled" @change="(checked: boolean) => toggleTemplate(record, checked)" />
              </template>
              <template v-if="column.key === 'action'">
                <a-space>
                  <a @click="editTemplate(record)">编辑</a>
                  <a-popconfirm title="确定删除?" @confirm="deleteTemplate(record)">
                    <a style="color: #f5222d">删除</a>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="history" tab="发送记录">
          <a-table :columns="historyColumns" :data-source="notificationHistory" :loading="loading" row-key="uuid">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag :color="record.status === 'success' ? 'success' : 'error'">
                  {{ record.status === 'success' ? '成功' : '失败' }}
                </a-tag>
              </template>
            </template>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="settings" tab="通知设置">
          <a-form layout="vertical" style="max-width: 600px">
            <a-form-item label="邮件通知">
              <a-switch v-model:checked="settings.emailEnabled" />
            </a-form-item>
            <a-form-item v-if="settings.emailEnabled" label="SMTP服务器">
              <a-input v-model:value="settings.smtpServer" placeholder="smtp.example.com" />
            </a-form-item>
            <a-form-item label="Webhook通知">
              <a-switch v-model:checked="settings.webhookEnabled" />
            </a-form-item>
            <a-form-item v-if="settings.webhookEnabled" label="Webhook URL">
              <a-input v-model:value="settings.webhookUrl" placeholder="https://example.com/webhook" />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </a-card>

    <a-modal v-model:open="showTemplateModal" title="新建通知模板" @ok="handleTemplateSubmit" @cancel="resetTemplateForm">
      <a-form :model="templateForm" :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="模板名称" required>
          <a-input v-model:value="templateForm.name" placeholder="输入模板名称" />
        </a-form-item>
        <a-form-item label="通知类型" required>
          <a-select v-model:value="templateForm.type">
            <a-select-option value="email">邮件</a-select-option>
            <a-select-option value="webhook">Webhook</a-select-option>
            <a-select-option value="wechat">微信</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="标题模板">
          <a-input v-model:value="templateForm.subject" placeholder="通知标题" />
        </a-form-item>
        <a-form-item label="内容模板">
          <a-textarea v-model:value="templateForm.content" :rows="4" placeholder="通知内容，支持变量替换" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'

const activeTab = ref('templates')
const loading = ref(false)
const showTemplateModal = ref(false)

const templates = ref([
  { uuid: '1', name: '交易通知', type: 'email', enabled: true },
  { uuid: '2', name: '风控告警', type: 'webhook', enabled: true },
])

const notificationHistory = ref([
  { uuid: '1', template: '交易通知', recipient: 'user@example.com', status: 'success', sent_at: '2024-01-01 10:00:00' },
  { uuid: '2', template: '风控告警', recipient: 'webhook', status: 'success', sent_at: '2024-01-01 11:00:00' },
])

const settings = reactive({ emailEnabled: true, smtpServer: '', webhookEnabled: false, webhookUrl: '' })
const templateForm = reactive({ name: '', type: 'email', subject: '', content: '' })

const templateColumns = [
  { title: '模板名称', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '状态', dataIndex: 'enabled', key: 'enabled' },
  { title: '操作', key: 'action', width: 150 },
]

const historyColumns = [
  { title: '模板', dataIndex: 'template', key: 'template' },
  { title: '接收者', dataIndex: 'recipient', key: 'recipient' },
  { title: '状态', dataIndex: 'status', key: 'status' },
  { title: '发送时间', dataIndex: 'sent_at', key: 'sent_at' },
]

const getTypeColor = (type: string) => ({ email: 'blue', webhook: 'green', wechat: 'orange' }[type] || 'default')
const getTypeLabel = (type: string) => ({ email: '邮件', webhook: 'Webhook', wechat: '微信' }[type] || type)
const toggleTemplate = (record: any, checked: boolean) => { record.enabled = checked; message.success(`模板已${checked ? '启用' : '禁用'}`) }
const editTemplate = (record: any) => { Object.assign(templateForm, record); showTemplateModal.value = true }
const deleteTemplate = (record: any) => { templates.value = templates.value.filter(t => t.uuid !== record.uuid); message.success('模板已删除') }

const handleTemplateSubmit = () => {
  if (!templateForm.name) { message.warning('请输入模板名称'); return }
  templates.value.push({ uuid: Date.now().toString(), ...templateForm, enabled: true })
  showTemplateModal.value = false
  message.success('模板创建成功')
  resetTemplateForm()
}

const resetTemplateForm = () => { Object.assign(templateForm, { name: '', type: 'email', subject: '', content: '' }) }
const saveSettings = () => { message.success('设置保存成功') }

onMounted(() => {})
</script>
