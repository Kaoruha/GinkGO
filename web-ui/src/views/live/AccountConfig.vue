<template>
  <div class="account-config-page">
    <div class="page-header">
      <div class="header-left">
        <div class="title-section">
          <h1 class="page-title">实盘账号配置</h1>
          <p class="page-subtitle">管理交易所API凭证，配置实盘交易账号</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn-primary" @click="showAddModal">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          添加账号
        </button>
      </div>
    </div>

    <!-- 账号列表 -->
    <div class="card account-list-card">
      <div class="card-header">
        <div class="card-title">
          <span>账号列表</span>
          <span class="tag tag-blue">{{ accounts.length }} 个账号</span>
        </div>
      </div>

      <div class="card-body">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>账号名称</th>
                <th>交易所</th>
                <th>状态</th>
                <th>最后验证</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in accounts" :key="record.uuid">
                <td>
                  <div class="account-name">
                    <span>{{ record.name }}</span>
                    <span v-if="record.environment === 'production'" class="tag tag-red" style="margin-left: 8px">
                      生产环境
                    </span>
                    <span v-else class="tag tag-green" style="margin-left: 8px">
                      测试网
                    </span>
                  </div>
                </td>
                <td>
                  <span class="tag" :class="record.exchange === 'okx' ? 'tag-cyan' : 'tag-yellow'">
                    {{ record.exchange.toUpperCase() }}
                  </span>
                </td>
                <td>
                  <span class="tag" :class="getStatusTagClass(record.status)">
                    {{ getStatusText(record.status) }}
                  </span>
                </td>
                <td>
                  <span v-if="record.last_validated_at">
                    {{ formatDateTime(record.last_validated_at) }}
                  </span>
                  <span v-else class="text-muted">未验证</span>
                </td>
                <td>
                  <div class="action-buttons">
                    <button class="btn-small" :disabled="testing[record.uuid]" @click="testConnection(record.uuid)">
                      <svg v-if="!testing[record.uuid]" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="16" x2="12" y2="12"></line>
                        <line x1="12" y1="8" x2="12.01" y2="8"></line>
                      </svg>
                      <span v-else class="loading-spinner"></span>
                      测试连接
                    </button>
                    <button class="btn-small" @click="editAccount(record)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                      </svg>
                      编辑
                    </button>
                    <button class="btn-small btn-danger" @click="confirmDelete(record)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"></polyline>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                      </svg>
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 添加/编辑账号模态框 -->
    <div v-if="modalVisible" class="modal-overlay" @click.self="handleModalCancel">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ isEditMode ? '编辑账号' : '添加账号' }}</h3>
          <button class="modal-close" @click="handleModalCancel">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleModalOk">
            <div class="form-group">
              <label class="form-label">账号名称</label>
              <input v-model="formData.name" type="text" placeholder="输入账号名称" class="form-input" />
            </div>

            <div class="form-group">
              <label class="form-label">交易所</label>
              <select v-model="formData.exchange" class="form-select">
                <option value="okx">OKX</option>
                <option value="binance">Binance</option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">环境</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input v-model="formData.environment" type="radio" value="testnet" />
                  测试网
                </label>
                <label class="radio-label">
                  <input v-model="formData.environment" type="radio" value="production" />
                  生产环境
                </label>
              </div>
              <div class="form-tip">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                生产环境使用真实资金进行交易，请谨慎操作
              </div>
            </div>

            <div class="form-divider">API凭证</div>

            <div class="form-group">
              <label class="form-label">API Key</label>
              <input v-model="formData.api_key" type="password" placeholder="输入API Key" class="form-input" />
            </div>

            <div class="form-group">
              <label class="form-label">API Secret</label>
              <input v-model="formData.api_secret" type="password" placeholder="输入API Secret" class="form-input" />
            </div>

            <div v-if="formData.exchange === 'okx'" class="form-group">
              <label class="form-label">Passphrase</label>
              <input v-model="formData.passphrase" type="password" placeholder="输入Passphrase (OKX需要)" class="form-input" />
            </div>

            <div class="form-group">
              <label class="form-label">描述</label>
              <textarea v-model="formData.description" class="form-textarea" rows="3" placeholder="账号描述（可选）"></textarea>
            </div>

            <!-- 验证结果 -->
            <div v-if="validationResult" class="alert" :class="validationResult.success ? 'alert-success' : 'alert-error'">
              <div class="alert-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                  <line x1="12" y1="9" x2="12" y2="13"></line>
                  <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
              </div>
              <div class="alert-content">
                <div class="alert-message">{{ validationResult.message }}</div>
                <div v-if="validationResult.account_info" class="alert-description">
                  <div>余额: {{ validationResult.account_info.balance }}</div>
                  <div>环境: {{ validationResult.account_info.environment }}</div>
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button type="submit" class="btn-primary" :disabled="saving">
                {{ saving ? '保存中...' : '确定' }}
              </button>
              <button type="button" class="btn-secondary" @click="handleModalCancel">取消</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 删除确认对话框 -->
    <div v-if="deleteConfirmVisible" class="modal-overlay" @click.self="deleteConfirmVisible = false">
      <div class="modal modal-small">
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="modal-close" @click="deleteConfirmVisible = false">×</button>
        </div>
        <div class="modal-body">
          <p>确认删除此账号？</p>
          <div class="form-actions">
            <button class="btn-danger" @click="confirmDeleteAccount">确定</button>
            <button class="btn-secondary" @click="deleteConfirmVisible = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import request from '@/api/request'

// 状态
const loading = ref(false)
const accounts = ref([])
const testing = ref({})
const modalVisible = ref(false)
const isEditMode = ref(false)
const saving = ref(false)
const validationResult = ref(null)
const deleteConfirmVisible = ref(false)
const recordToDelete = ref(null)

// 表单数据
const formData = reactive({
  name: '',
  exchange: 'okx',
  environment: 'testnet',
  api_key: '',
  api_secret: '',
  passphrase: '',
  description: ''
})

// 表格列
const columns = [
  { title: '账号名称', key: 'name', dataIndex: 'name' },
  { title: '交易所', key: 'exchange', dataIndex: 'exchange', width: 120 },
  { title: '状态', key: 'status', dataIndex: 'status', width: 120 },
  { title: '最后验证', key: 'last_validated_at', dataIndex: 'last_validated_at', width: 180 },
  { title: '操作', key: 'actions', width: 220, align: 'center' }
]

// 获取账号列表
const fetchAccounts = async () => {
  loading.value = true
  try {
    const response = await request.get('/api/v1/accounts')
    if (response.code === 0) {
      accounts.value = response.data || []
    } else {
      console.error('获取账号列表失败')
    }
  } catch (error) {
    console.error('网络错误：' + error.message)
  } finally {
    loading.value = false
  }
}

// 测试连接
const testConnection = async (uuid) => {
  testing.value[uuid] = true
  try {
    const response = await request.post(`/api/v1/accounts/${uuid}/validate`)
    if (response.code === 0) {
      console.log('连接测试成功')
      await fetchAccounts()
    } else {
      console.error('连接测试失败：' + response.message)
    }
  } catch (error) {
    console.error('网络错误：' + error.message)
  } finally {
    testing.value[uuid] = false
  }
}

// 显示添加模态框
const showAddModal = () => {
  isEditMode.value = false
  resetForm()
  modalVisible.value = true
  validationResult.value = null
}

// 编辑账号
const editAccount = (record) => {
  isEditMode.value = true
  Object.assign(formData, {
    uuid: record.uuid,
    name: record.name,
    exchange: record.exchange,
    environment: record.environment,
    description: record.description,
    api_key: '',
    api_secret: '',
    passphrase: ''
  })
  modalVisible.value = true
  validationResult.value = null
}

// 删除账号
const confirmDelete = (record) => {
  recordToDelete.value = record
  deleteConfirmVisible.value = true
}

const confirmDeleteAccount = async () => {
  if (!recordToDelete.value) return
  try {
    const response = await request.delete(`/api/v1/accounts/${recordToDelete.value.uuid}`)
    if (response.code === 0) {
      console.log('账号删除成功')
      await fetchAccounts()
    } else {
      console.error('删除失败：' + response.message)
    }
  } catch (error) {
    console.error('网络错误：' + error.message)
  } finally {
    deleteConfirmVisible.value = false
    recordToDelete.value = null
  }
}

// 处理模态框确认
const handleModalOk = async () => {
  if (!formData.name || !formData.exchange || !formData.environment || !formData.api_key || !formData.api_secret) {
    console.warn('请填写必填字段')
    return
  }

  if (formData.exchange === 'okx' && !formData.passphrase) {
    console.warn('OKX需要Passphrase')
    return
  }

  saving.value = true

  const data = { ...formData }

  try {
    if (isEditMode.value) {
      const response = await request.put(`/api/v1/accounts/${data.uuid}`, data)
      if (response.code === 0) {
        console.log('账号更新成功')
        modalVisible.value = false
        await fetchAccounts()
      } else {
        console.error('更新失败：' + response.message)
      }
    } else {
      const response = await request.post('/api/v1/accounts', data)
      if (response.code === 0) {
        console.log('账号创建成功')
        modalVisible.value = false
        await fetchAccounts()
      } else {
        console.error('创建失败：' + response.message)
      }
    }
  } catch (error) {
    console.error('操作失败：' + error.message)
  } finally {
    saving.value = false
  }
}

// 处理模态框取消
const handleModalCancel = () => {
  modalVisible.value = false
  resetForm()
}

// 重置表单
const resetForm = () => {
  Object.assign(formData, {
    uuid: null,
    name: '',
    exchange: 'okx',
    environment: 'testnet',
    api_key: '',
    api_secret: '',
    passphrase: '',
    description: ''
  })
  validationResult.value = null
}

// 获取状态标签类
const getStatusTagClass = (status) => {
  const classMap = {
    enabled: 'tag-green',
    disabled: 'tag-gray',
    connecting: 'tag-blue',
    disconnected: 'tag-orange',
    error: 'tag-red'
  }
  return classMap[status] || 'tag-gray'
}

// 获取状态文本
const getStatusText = (status) => {
  const textMap = {
    enabled: '已启用',
    disabled: '已禁用',
    connecting: '连接中',
    disconnected: '已断开',
    error: '错误'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  return new Date(dateTime).toLocaleString('zh-CN')
}

// 生命周期
onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped>
.account-config-page {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.page-subtitle {
  margin: 4px 0 0 0;
  color: #8a8a9a;
  font-size: 14px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-danger {
  padding: 8px 16px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #ff4d4f;
}

.btn-small {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }
.tag-orange { background: rgba(250, 140, 22, 0.2); color: #fa8c16; }
.tag-cyan { background: rgba(19, 194, 194, 0.2); color: #13c2c2; }
.tag-yellow { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-gray { background: rgba(140, 140, 140, 0.2); color: #8c8c8c; }

.account-name {
  display: flex;
  align-items: center;
}

.text-muted {
  color: #8a8a9a;
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

.action-buttons {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-small {
  max-width: 400px;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
  background: none;
  border: none;
  color: #8a8a9a;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
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
  font-family: inherit;
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

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
}

.form-divider {
  margin: 20px 0;
  padding-top: 20px;
  border-top: 1px solid #2a2a3e;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #faad14;
  font-size: 12px;
  margin-top: 8px;
}

.alert {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 6px;
  margin-top: 16px;
}

.alert-success {
  background: rgba(82, 196, 26, 0.1);
  border: 1px solid rgba(82, 196, 26, 0.3);
}

.alert-error {
  background: rgba(245, 34, 45, 0.1);
  border: 1px solid rgba(245, 34, 45, 0.3);
}

.alert-icon {
  flex-shrink: 0;
}

.alert-error .alert-icon {
  color: #f5222d;
}

.alert-success .alert-icon {
  color: #52c41a;
}

.alert-content {
  flex: 1;
}

.alert-message {
  font-size: 14px;
  color: #ffffff;
  margin-bottom: 4px;
}

.alert-description {
  font-size: 12px;
  color: #8a8a9a;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

.loading-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #ffffff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .data-table {
    font-size: 12px;
  }

  .action-buttons {
    flex-direction: column;
  }
}
</style>
