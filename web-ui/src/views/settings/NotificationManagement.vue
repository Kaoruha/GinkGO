<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">系统</span>
        通知管理
      </div>
      <button class="btn-primary" @click="showTemplateModal = true">新建通知模板</button>
    </div>

    <div class="card">
      <div class="tabs-header">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-button"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 通知模板标签页 -->
      <div v-if="activeTab === 'templates'" class="tab-content">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>模板名称</th>
                <th>类型</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody v-if="!loading">
              <tr v-for="record in templates" :key="record.uuid">
                <td>{{ record.name }}</td>
                <td>
                  <span class="tag" :class="getTypeClass(record.type)">{{ getTypeLabel(record.type) }}</span>
                </td>
                <td>
                  <div class="switch-container">
                    <input
                      :id="`switch-${record.uuid}`"
                      :checked="record.enabled"
                      type="checkbox"
                      class="switch-input"
                      @change="(e: any) => toggleTemplate(record, e.target.checked)"
                    />
                    <label :for="`switch-${record.uuid}`" class="switch-label"></label>
                  </div>
                </td>
                <td>
                  <div class="action-links">
                    <a class="link" @click="editTemplate(record)">编辑</a>
                    <a class="link text-red" @click="confirmDeleteTemplate(record)">删除</a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 发送记录标签页 -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>模板</th>
                <th>接收者</th>
                <th>状态</th>
                <th>发送时间</th>
              </tr>
            </thead>
            <tbody v-if="!loading">
              <tr v-for="record in notificationHistory" :key="record.uuid">
                <td>{{ record.template }}</td>
                <td>{{ record.recipient }}</td>
                <td>
                  <span class="tag" :class="record.status === 'success' ? 'tag-green' : 'tag-red'">
                    {{ record.status === 'success' ? '成功' : '失败' }}
                  </span>
                </td>
                <td>{{ record.sent_at }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 通知设置标签页 -->
      <div v-if="activeTab === 'settings'" class="tab-content">
        <div class="settings-form">
          <div class="form-group">
            <label class="form-label">邮件通知</label>
            <div class="switch-container">
              <input v-model="settings.emailEnabled" type="checkbox" id="email-enabled" class="switch-input" />
              <label for="email-enabled" class="switch-label"></label>
              <span>{{ settings.emailEnabled ? '启用' : '禁用' }}</span>
            </div>
          </div>
          <div v-if="settings.emailEnabled" class="form-group">
            <label class="form-label">SMTP服务器</label>
            <input v-model="settings.smtpServer" type="text" placeholder="smtp.example.com" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">Webhook通知</label>
            <div class="switch-container">
              <input v-model="settings.webhookEnabled" type="checkbox" id="webhook-enabled" class="switch-input" />
              <label for="webhook-enabled" class="switch-label"></label>
              <span>{{ settings.webhookEnabled ? '启用' : '禁用' }}</span>
            </div>
          </div>
          <div v-if="settings.webhookEnabled" class="form-group">
            <label class="form-label">Webhook URL</label>
            <input v-model="settings.webhookUrl" type="text" placeholder="https://example.com/webhook" class="form-input" />
          </div>
          <div class="form-group">
            <button class="btn-primary" @click="saveSettings">保存设置</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建通知模板模态框 -->
    <div v-if="showTemplateModal" class="modal-overlay" @click.self="closeTemplateModal">
      <div class="modal">
        <div class="modal-header">
          <h3>新建通知模板</h3>
          <button class="modal-close" @click="closeTemplateModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleTemplateSubmit">
            <div class="form-group">
              <label class="form-label">模板名称 <span class="required">*</span></label>
              <input v-model="templateForm.name" type="text" placeholder="输入模板名称" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">通知类型 <span class="required">*</span></label>
              <select v-model="templateForm.type" class="form-select">
                <option value="email">邮件</option>
                <option value="webhook">Webhook</option>
                <option value="wechat">微信</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">标题模板</label>
              <input v-model="templateForm.subject" type="text" placeholder="通知标题" class="form-input" />
            </div>
            <div class="form-group">
              <label class="form-label">内容模板</label>
              <textarea v-model="templateForm.content" :rows="4" placeholder="通知内容，支持变量替换" class="form-textarea"></textarea>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeTemplateModal">取消</button>
              <button type="submit" class="btn-primary">创建</button>
            </div>
          </form>
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

const tabs = [
  { key: 'templates', label: '通知模板' },
  { key: 'history', label: '发送记录' },
  { key: 'settings', label: '通知设置' },
]

const getTypeClass = (type: string) => {
  const classMap: Record<string, string> = {
    email: 'tag-blue',
    webhook: 'tag-green',
    wechat: 'tag-orange'
  }
  return classMap[type] || 'tag-gray'
}

const getTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = {
    email: '邮件',
    webhook: 'Webhook',
    wechat: '微信'
  }
  return labelMap[type] || type
}

const toggleTemplate = (record: any, checked: boolean) => {
  record.enabled = checked
  showToast(`模板已${checked ? '启用' : '禁用'}`)
}

const editTemplate = (record: any) => {
  Object.assign(templateForm, record)
  showTemplateModal.value = true
}

const confirmDeleteTemplate = (record: any) => {
  if (confirm(`确定要删除模板 "${record.name}" 吗？`)) {
    deleteTemplate(record)
  }
}

const deleteTemplate = (record: any) => {
  templates.value = templates.value.filter(t => t.uuid !== record.uuid)
  showToast('模板已删除')
}

const closeTemplateModal = () => {
  showTemplateModal.value = false
  resetTemplateForm()
}

const handleTemplateSubmit = () => {
  if (!templateForm.name) {
    showToast('请输入模板名称', 'warning')
    return
  }

  templates.value.push({
    uuid: Date.now().toString(),
    ...templateForm,
    enabled: true
  })

  showToast('模板创建成功')
  closeTemplateModal()
}

const resetTemplateForm = () => {
  Object.assign(templateForm, { name: '', type: 'email', subject: '', content: '' })
}

const saveSettings = () => {
  showToast('设置保存成功')
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

/* Tabs样式 */
.tabs-header {
  display: flex;
  border-bottom: 1px solid #2a2a3e;
}

.tab-button {
  padding: 16px 24px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: #8a8a9a;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #ffffff;
}

.tab-button.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
}

.tab-content {
  padding: 20px;
}

/* 表格样式 */
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

/* Switch组件 */
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

/* 设置表单 */
.settings-form {
  max-width: 600px;
}

.required {
  color: #f5222d;
}

/* 模态框样式 */

</style>
