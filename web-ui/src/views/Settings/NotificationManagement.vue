<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">通知管理</h1>
      <button class="btn btn-primary" @click="showTemplateModal = true">新建通知模板</button>
    </div>

    <div class="card">
      <!-- Tabs -->
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

      <!-- Tab Content: Templates -->
      <div v-if="activeTab === 'templates'" class="tab-content">
        <div v-if="loading" class="loading-container">
          <div class="spinner"></div>
        </div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>模板名称</th>
                <th>类型</th>
                <th>状态</th>
                <th>更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in templates" :key="record.uuid">
                <td>{{ record.name }}</td>
                <td>
                  <span class="tag" :class="`tag-${getTypeColorClass(record.type)}`">
                    {{ getTypeLabel(record.type) }}
                  </span>
                </td>
                <td>
                  <label class="switch-label">
                    <input type="checkbox" :checked="record.enabled" @change="toggleTemplate(record, $event)" class="switch-input" />
                  </label>
                </td>
                <td>{{ formatDate(record.updated_at) }}</td>
                <td>
                  <div class="action-links">
                    <a @click="editTemplate(record)">编辑</a>
                    <a class="danger-link" @click="deleteTemplateWithConfirm(record)">删除</a>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab Content: History -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div v-if="loading" class="loading-container">
          <div class="spinner"></div>
        </div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>模板</th>
                <th>接收者</th>
                <th>状态</th>
                <th>发送时间</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in notificationHistory" :key="record.uuid">
                <td>{{ record.template }}</td>
                <td>{{ record.recipient }}</td>
                <td>
                  <span class="tag" :class="record.status === 'success' ? 'tag-green' : 'tag-red'">
                    {{ record.status === 'success' ? '成功' : '失败' }}
                  </span>
                </td>
                <td>{{ formatDate(record.sent_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Tab Content: Settings -->
      <div v-if="activeTab === 'settings'" class="tab-content">
        <div class="settings-form">
          <div class="form-group">
            <label class="form-label">邮件通知</label>
            <label class="switch-label">
              <input type="checkbox" v-model="settings.emailEnabled" class="switch-input" />
              <span class="switch-text">{{ settings.emailEnabled ? '启用' : '禁用' }}</span>
            </label>
          </div>
          <div v-if="settings.emailEnabled" class="form-group">
            <label class="form-label">SMTP服务器</label>
            <input v-model="settings.smtpServer" type="text" class="form-input" placeholder="smtp.example.com" />
          </div>
          <div class="form-group">
            <label class="form-label">Webhook通知</label>
            <label class="switch-label">
              <input type="checkbox" v-model="settings.webhookEnabled" class="switch-input" />
              <span class="switch-text">{{ settings.webhookEnabled ? '启用' : '禁用' }}</span>
            </label>
          </div>
          <div v-if="settings.webhookEnabled" class="form-group">
            <label class="form-label">Webhook URL</label>
            <input v-model="settings.webhookUrl" type="text" class="form-input" placeholder="https://example.com/webhook" />
          </div>
          <div class="form-group">
            <button class="btn btn-primary" @click="saveSettings">保存设置</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Template Modal -->
    <div v-if="showTemplateModal" class="modal-overlay" @click.self="closeTemplateModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>新建通知模板</h3>
          <button class="modal-close" @click="closeTemplateModal">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">模板名称 <span class="required">*</span></label>
            <input v-model="templateForm.name" type="text" class="form-input" placeholder="输入模板名称" />
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
            <input v-model="templateForm.subject" type="text" class="form-input" placeholder="通知标题" />
          </div>
          <div class="form-group">
            <label class="form-label">内容模板</label>
            <textarea v-model="templateForm.content" class="form-textarea" :rows="4" placeholder="通知内容，支持变量替换"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeTemplateModal">取消</button>
          <button class="btn btn-primary" @click="handleTemplateSubmit">确定</button>
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

const tabs = [
  { key: 'templates', label: '通知模板' },
  { key: 'history', label: '发送记录' },
  { key: 'settings', label: '通知设置' },
]

const templates = ref<any[]>([
  { uuid: '1', name: '交易通知', type: 'email', enabled: true, updated_at: '2024-01-01' },
  { uuid: '2', name: '风控告警', type: 'webhook', enabled: true, updated_at: '2024-01-02' },
])

const notificationHistory = ref<any[]>([
  { uuid: '1', template: '交易通知', recipient: 'user@example.com', status: 'success', sent_at: '2024-01-01 10:00:00' },
  { uuid: '2', template: '风控告警', recipient: 'webhook', status: 'success', sent_at: '2024-01-01 11:00:00' },
])

const settings = reactive({
  emailEnabled: true,
  smtpServer: '',
  webhookEnabled: false,
  webhookUrl: '',
})

const templateForm = reactive({
  name: '',
  type: 'email',
  subject: '',
  content: '',
})

const getTypeColorClass = (type: string) => {
  const colors: Record<string, string> = {
    email: 'blue',
    webhook: 'green',
    wechat: 'orange',
  }
  return colors[type] || 'gray'
}

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    email: '邮件',
    webhook: 'Webhook',
    wechat: '微信',
  }
  return labels[type] || type
}

const formatDate = (date: string) => {
  const d = new Date(date)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const toggleTemplate = (record: any, event: Event) => {
  const checked = (event.target as HTMLInputElement).checked
  record.enabled = checked
  showToast(`模板已${checked ? '启用' : '禁用'}`)
}

const editTemplate = (record: any) => {
  Object.assign(templateForm, record)
  showTemplateModal.value = true
}

const deleteTemplateWithConfirm = (record: any) => {
  if (confirm(`确定删除模板 "${record.name}" 吗？`)) {
    deleteTemplate(record)
  }
}

const deleteTemplate = (record: any) => {
  templates.value = templates.value.filter(t => t.uuid !== record.uuid)
  showToast('模板已删除')
}

const closeTemplateModal = () => {
  showTemplateModal.value = false
}

const handleTemplateSubmit = () => {
  if (!templateForm.name) {
    showToast('请输入模板名称', 'warning')
    return
  }
  templates.value.push({
    uuid: Date.now().toString(),
    ...templateForm,
    enabled: true,
    updated_at: new Date().toISOString(),
  })
  showTemplateModal.value = false
  showToast('模板创建成功')
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
.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

/* Tabs */
.tabs-header {
  display: flex;
  border-bottom: 1px solid #2a2a3e;
}

.tab-button {
  padding: 12px 20px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
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

/* Loading */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

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
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }

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

/* Settings Form */
.settings-form {
  max-width: 600px;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
  color: #ffffff;
}

.modal-close {
  background: none;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  color: #ffffff;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
}

/* Form */
.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 6px;
}

.required {
  color: #f5222d;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #1890ff;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* Button */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: #ffffff;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  background: transparent;
  border: 1px solid #3a3a4e;
  color: #ffffff;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}
</style>
