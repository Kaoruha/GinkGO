<template>
  <div class="api-interfaces">
    <h1 class="page-title">API接口设置</h1>

    <div class="card">
      <h2 class="card-subtitle">API文档</h2>
      <div class="button-group">
        <button class="btn-primary" @click="openDocs">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          </svg>
          Swagger UI
        </button>
        <button class="btn-secondary" @click="openRedoc">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
            <polyline points="10 9 9 9 8 9"></polyline>
          </svg>
          ReDoc
        </button>
        <button class="btn-secondary" @click="downloadOpenApi">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          OpenAPI Spec
        </button>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h2 class="card-subtitle">API密钥</h2>
        <button class="btn-primary" @click="showCreateKeyModal = true">创建新密钥</button>
      </div>

      <div class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>密钥</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>最后使用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody v-if="!loading">
            <tr v-for="record in apiKeys" :key="record.keyId">
              <td>{{ record.name }}</td>
              <td>
                <span class="code-text" @click="copyToClipboard(record.key)">{{ record.key }}</span>
              </td>
              <td>
                <span class="tag" :class="record.status === 'active' ? 'tag-green' : 'tag-gray'">
                  {{ record.status === 'active' ? '启用' : '禁用' }}
                </span>
              </td>
              <td>{{ record.created_at }}</td>
              <td>{{ record.last_used || '-' }}</td>
              <td>
                <div class="action-links">
                  <a class="link" @click="toggleKeyStatus(record)">
                    {{ record.status === 'active' ? '禁用' : '启用' }}
                  </a>
                  <a class="link text-red" @click="confirmDeleteKey(record)">删除</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h2 class="card-subtitle">API配置</h2>
      <form class="config-form" @submit.prevent="saveApiConfig">
        <div class="form-group">
          <label class="form-label">API基础URL</label>
          <input v-model="apiConfig.baseUrl" type="text" placeholder="http://localhost:8000/api" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">请求超时(秒)</label>
          <input v-model.number="apiConfig.timeout" type="number" :min="1" :max="300" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">启用速率限制</label>
          <div class="switch-container">
            <input v-model="apiConfig.rateLimitEnabled" type="checkbox" id="rate-limit" class="switch-input" />
            <label for="rate-limit" class="switch-label"></label>
            <span>{{ apiConfig.rateLimitEnabled ? '启用' : '禁用' }}</span>
          </div>
        </div>
        <div v-if="apiConfig.rateLimitEnabled" class="form-group">
          <label class="form-label">每分钟请求数限制</label>
          <input v-model.number="apiConfig.rateLimit" type="number" :min="1" :max="1000" class="form-input" />
        </div>
        <div class="form-group">
          <button type="submit" class="btn-primary">保存配置</button>
        </div>
      </form>
    </div>

    <!-- 创建密钥模态框 -->
    <div v-if="showCreateKeyModal" class="modal-overlay" @click.self="closeCreateModal">
      <div class="modal">
        <div class="modal-header">
          <h3>创建API密钥</h3>
          <button class="modal-close" @click="closeCreateModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleCreateKey">
            <div class="form-group">
              <label class="form-label">密钥名称 <span class="required">*</span></label>
              <input v-model="newKeyName" type="text" placeholder="输入密钥名称" class="form-input" required />
            </div>
            <div class="form-group">
              <label class="form-label">过期时间</label>
              <div class="radio-group">
                <label v-for="option in expiryOptions" :key="option.value" class="radio-label">
                  <input v-model="keyExpiry" type="radio" :value="option.value" />
                  {{ option.label }}
                </label>
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">权限</label>
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input v-model="keyPermissions" type="checkbox" value="read" />
                  读取
                </label>
                <label class="checkbox-label">
                  <input v-model="keyPermissions" type="checkbox" value="write" />
                  写入
                </label>
                <label class="checkbox-label">
                  <input v-model="keyPermissions" type="checkbox" value="admin" />
                  管理
                </label>
              </div>
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="closeCreateModal">取消</button>
              <button type="submit" class="btn-primary">创建</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 密钥结果模态框 -->
    <div v-if="showKeyResult" class="modal-overlay" @click.self="closeKeyResult">
      <div class="modal">
        <div class="modal-header">
          <h3>密钥已创建</h3>
          <button class="modal-close" @click="closeKeyResult">×</button>
        </div>
        <div class="modal-body">
          <div class="alert alert-success">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
            <div class="alert-content">
              <div class="alert-title">请保存您的API密钥</div>
              <div class="alert-description">密钥只会显示一次，请妥善保管</div>
            </div>
          </div>
          <div class="key-display" @click="copyToClipboard(createdKey)">
            {{ createdKey }}
          </div>
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
const showCreateKeyModal = ref(false)
const showKeyResult = ref(false)
const newKeyName = ref('')
const keyExpiry = ref('never')
const keyPermissions = ref<string[]>(['read'])
const createdKey = ref('')

const apiKeys = ref<any[]>([
  { keyId: '1', name: '默认密钥', key: 'gk_live_xxxxxxxxxxxxxxxx', status: 'active', created_at: '2024-01-01', last_used: '2024-01-15' },
  { keyId: '2', name: '测试密钥', key: 'gk_test_yyyyyyyyyyyyyyyy', status: 'disabled', created_at: '2024-01-10', last_used: '-' },
])

const apiConfig = reactive({
  baseUrl: 'http://localhost:8000/api',
  timeout: 30,
  rateLimitEnabled: true,
  rateLimit: 100,
})

const expiryOptions = [
  { value: 'never', label: '永不过期' },
  { value: '30d', label: '30天' },
  { value: '90d', label: '90天' },
  { value: '1y', label: '1年' },
]

const openDocs = () => {
  window.open('/docs', '_blank')
}

const openRedoc = () => {
  window.open('/redoc', '_blank')
}

const downloadOpenApi = () => {
  showToast('正在下载 OpenAPI 规范文件...', 'info')
}

const toggleKeyStatus = (record: any) => {
  record.status = record.status === 'active' ? 'disabled' : 'active'
  showToast(`密钥已${record.status === 'active' ? '启用' : '禁用'}`)
}

const confirmDeleteKey = (record: any) => {
  if (confirm(`确定要删除密钥 "${record.name}" 吗？`)) {
    deleteKey(record)
  }
}

const deleteKey = (record: any) => {
  apiKeys.value = apiKeys.value.filter(k => k.keyId !== record.keyId)
  showToast('密钥已删除')
}

const closeCreateModal = () => {
  showCreateKeyModal.value = false
  newKeyName.value = ''
  keyExpiry.value = 'never'
  keyPermissions.value = ['read']
}

const closeKeyResult = () => {
  showKeyResult.value = false
}

const handleCreateKey = () => {
  if (!newKeyName.value) {
    showToast('请输入密钥名称', 'warning')
    return
  }

  const newKey = `gk_live_${Math.random().toString(36).substring(2, 18)}`
  apiKeys.value.push({
    keyId: Date.now().toString(),
    name: newKeyName.value,
    key: newKey,
    status: 'active',
    created_at: new Date().toISOString().split('T')[0],
    last_used: '-',
  })

  createdKey.value = newKey
  showCreateKeyModal.value = false
  showKeyResult.value = true
  newKeyName.value = ''
  showToast('API密钥创建成功')
}

const saveApiConfig = () => {
  showToast('API配置已保存')
}

const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text).then(() => {
    showToast('已复制到剪贴板')
  }).catch(() => {
    showToast('复制失败', 'error')
  })
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.api-interfaces {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 24px 0;
}

.card-subtitle {
  font-size: 18px;
  font-weight: 500;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.card-header h2 {
  margin: 0;
}

.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
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

.code-text {
  font-family: monospace;
  color: #1890ff;
  cursor: pointer;
  user-select: all;
}

.code-text:hover {
  text-decoration: underline;
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

/* 表单样式 */
.config-form {
  max-width: 600px;
}

.required {
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

/* Radio组 */
.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.radio-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

/* Checkbox组 */
.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #1890ff;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

/* 模态框样式 */

/* Alert样式 */
.alert {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.alert-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid #52c41a;
}

.alert svg {
  flex-shrink: 0;
  color: #52c41a;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 4px;
}

.alert-description {
  font-size: 13px;
  color: #8a8a9a;
}

.key-display {
  display: block;
  padding: 16px;
  background: #2a2a3e;
  border-radius: 8px;
  font-size: 14px;
  font-family: monospace;
  word-break: break-all;
  color: #1890ff;
  cursor: pointer;
  user-select: all;
}

.key-display:hover {
  background: #3a3a4e;
}
</style>
