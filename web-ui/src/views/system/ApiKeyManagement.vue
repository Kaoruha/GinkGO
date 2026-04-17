<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-blue">API</span>
        API Key 管理
      </h1>
      <div class="page-actions">
        <button class="btn-primary" @click="showCreateModal = true">
          <i class="icon-plus"></i>
          创建 API Key
        </button>
        <button class="btn-secondary" @click="loadApiKeys">
          <i class="icon-refresh"></i>
          刷新
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">总 API Key</div>
        <div class="stat-value">{{ apiKeys.length }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">激活</div>
        <div class="stat-value stat-success">{{ activeCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">已过期</div>
        <div class="stat-value stat-danger">{{ expiredCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">禁用</div>
        <div class="stat-value">{{ inactiveCount }}</div>
      </div>
    </div>

    <!-- API Keys 表格 -->
    <div class="card">
      <div class="card-header">
        <h3>API Keys</h3>
      </div>
      <div class="card-body">
        <table class="data-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>Key 前缀</th>
              <th>权限</th>
              <th>状态</th>
              <th>过期时间</th>
              <th>最后使用</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="key in apiKeys" :key="key.uuid">
              <td>
                <div class="key-name">
                  {{ key.name }}
                  <span v-if="key.description" class="key-desc">{{ key.description }}</span>
                </div>
              </td>
              <td><code class="key-prefix">{{ key.key_prefix }}***</code></td>
              <td>
                <span class="permission-tags">
                  <span v-for="perm in key.permissions_list" :key="perm" :class="`perm-tag perm-${perm}`">
                    {{ perm }}
                  </span>
                </span>
              </td>
              <td>
                <span v-if="key.is_expired" class="status-badge status-expired">已过期</span>
                <span v-else-if="!key.is_active" class="status-badge status-inactive">禁用</span>
                <span v-else class="status-badge status-active">激活</span>
              </td>
              <td>{{ key.expires_at ? formatDate(key.expires_at) : '永不过期' }}</td>
              <td>{{ key.last_used_at ? formatDateTime(key.last_used_at) : '从未使用' }}</td>
              <td class="actions-cell">
                <button class="btn-icon" @click="copyApiKey(key)" title="复制 API Key">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                  </svg>
                </button>
                <button class="btn-icon" @click="editKey(key)" title="编辑">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                  </svg>
                </button>
                <button class="btn-icon btn-danger" @click="deleteKey(key)" title="删除">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              </td>
            </tr>
            <tr v-if="apiKeys.length === 0">
              <td colspan="7" class="empty-state">
                暂无 API Key
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 创建/编辑 API Key 模态框 -->
    <div v-if="showCreateModal || editingKey" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingKey ? '编辑 API Key' : '创建 API Key' }}</h2>
          <button class="modal-close" @click="closeModal">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveApiKey">
            <div class="form-group">
              <label>名称 *</label>
              <input v-model="formData.name" type="text" required placeholder="如：Claw MCP Key" />
            </div>

            <div class="form-group">
              <label>权限 *</label>
              <div class="checkbox-group">
                <label v-for="perm in availablePermissions" :key="perm" class="checkbox-label">
                  <input
                    type="checkbox"
                    :value="perm"
                    v-model="formData.permissions"
                  />
                  <span>{{ permLabels[perm] }}</span>
                </label>
              </div>
            </div>

            <div class="form-group" v-if="!editingKey">
              <label>有效期（天）</label>
              <input
                v-model.number="formData.expires_days"
                type="number"
                min="1"
                placeholder="留空表示永不过期"
              />
            </div>

            <div class="form-group">
              <label>备注</label>
              <textarea v-model="formData.description" rows="2" placeholder="用途说明（可选）"></textarea>
            </div>

            <div v-if="newKeyValue" class="form-group success-message">
              <label>⚠️ 重要：请保存此 API Key</label>
              <div class="key-display">
                <code>{{ newKeyValue }}</code>
                <button type="button" class="btn-copy" @click="copyKey">复制</button>
              </div>
              <p class="help-text">此 Key 仅显示一次，请立即保存</p>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-secondary" @click="closeModal">
                {{ newKeyValue ? '关闭' : '取消' }}
              </button>
              <button v-if="!newKeyValue" type="submit" class="btn-primary">
                {{ editingKey ? '保存' : '创建' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiKeyApi, type ApiKey, type CreateApiKeyRequest, type UpdateApiKeyRequest, PermissionType } from '@/api/modules/apiKey'

const apiKeys = ref<ApiKey[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

const showCreateModal = ref(false)
const editingKey = ref<ApiKey | null>(null)
const newKeyValue = ref<string | null>(null)

const formData = ref<CreateApiKeyRequest & { expires_days?: number }>({
  name: '',
  permissions: ['read', 'trade'],
  description: '',
  expires_days: undefined,
  auto_generate: true
})

const availablePermissions: PermissionType[] = ['read', 'trade', 'admin']

const permLabels: Record<PermissionType, string> = {
  read: '只读',
  trade: '交易',
  admin: '管理'
}

const activeCount = computed(() => apiKeys.value.filter(k => k.is_active && !k.is_expired).length)
const expiredCount = computed(() => apiKeys.value.filter(k => k.is_expired).length)
const inactiveCount = computed(() => apiKeys.value.filter(k => !k.is_active).length)

const loadApiKeys = async () => {
  loading.value = true
  error.value = null
  try {
    const res = await apiKeyApi.listApiKeys()
    apiKeys.value = (res as any).data || []
  } catch (err: any) {
    error.value = err.message || '加载失败'
    console.error('Failed to load API keys:', err)
  } finally {
    loading.value = false
  }
}

const saveApiKey = async () => {
  loading.value = true
  error.value = null
  try {
    if (editingKey.value) {
      // 更新
      const updateData: UpdateApiKeyRequest = {
        name: formData.value.name,
        permissions: formData.value.permissions,
        description: formData.value.description,
        expires_days: formData.value.expires_days
      }
      await apiKeyApi.updateApiKey(editingKey.value.uuid, updateData)
    } else {
      // 创建
      const res = await apiKeyApi.createApiKey(formData.value)
      newKeyValue.value = (res as any).data.key_value
    }
    await loadApiKeys()
    if (!newKeyValue.value) closeModal()
  } catch (err: any) {
    error.value = err.message || '保存失败'
    console.error('Failed to save API key:', err)
  } finally {
    loading.value = false
  }
}

const editKey = (key: ApiKey) => {
  editingKey.value = key
  formData.value = {
    name: key.name,
    permissions: [...key.permissions_list],
    description: key.description || '',
    auto_generate: true
  }
}

const deleteKey = async (key: ApiKey) => {
  if (!confirm(`确定要删除 API Key "${key.name}" 吗？此操作不可恢复。`)) return
  loading.value = true
  try {
    await apiKeyApi.deleteApiKey(key.uuid)
    await loadApiKeys()
  } catch (err: any) {
    error.value = err.message || '删除失败'
    console.error('Failed to delete API key:', err)
  } finally {
    loading.value = false
  }
}

const closeModal = () => {
  showCreateModal.value = false
  editingKey.value = null
  newKeyValue.value = null
  formData.value = {
    name: '',
    permissions: ['read', 'trade'],
    description: '',
    auto_generate: true
  }
}

const copyKey = () => {
  if (newKeyValue.value) {
    copyToClipboard(newKeyValue.value)
  }
}

const copyApiKey = async (key: ApiKey) => {
  try {
    const res = await apiKeyApi.revealApiKey(key.uuid)
    if ((res as any).success || (res as any).code === 0) {
      const fullKey = (res as any).data.key_value
      copyToClipboard(fullKey)
      alert('✅ API Key 已复制到剪贴板')
    } else {
      alert('❌ ' + ((res as any).message || '获取失败'))
    }
  } catch (err: any) {
    // 如果是没有加密的旧 Key，提示用户
    const errorMsg = err.response?.data?.detail || err.message || '获取失败'
    if (errorMsg.includes('解密') || errorMsg.includes('encrypted')) {
      alert('❌ 此 API Key 是旧版本创建的，无法获取完整值。\n\n请删除并重新生成新的 API Key。')
    } else {
      alert('❌ ' + errorMsg)
    }
  }
}

// 复制到剪贴板的兼容方法
const copyToClipboard = (text: string) => {
  // 优先使用现代 Clipboard API
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text)
    return
  }

  // Fallback: 使用传统方法
  const textArea = document.createElement('textarea')
  textArea.value = text
  textArea.style.position = 'fixed'
  textArea.style.left = '-999999px'
  document.body.appendChild(textArea)
  textArea.focus()
  textArea.select()
  try {
    document.execCommand('copy')
  } catch (err) {
    console.error('复制失败:', err)
    throw new Error('复制失败，请手动复制')
  }
  document.body.removeChild(textArea)
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatDateTime = (dateStr: string) => {
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  loadApiKeys()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-actions {
  display: flex;
  gap: 12px;
}

/* 统计卡片 */

.stat-danger {
  color: #f87171;
}

/* 卡片 */

.filter-controls {
  display: flex;
  gap: 12px;
}

.filter-select {
  background: #12121a;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  padding: 6px 12px;
  color: #ffffff;
  font-size: 14px;
}

/* 表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table thead {
  background: #12121a;
}

.data-table th {
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #8a8a9a;
  text-transform: uppercase;
}

.data-table td {
  padding: 12px 16px;
  border-top: 1px solid #3a3a4e;
  font-size: 14px;
  color: #ffffff;
}

.data-table tr:hover {
  background: #12121a;
}

.key-name {
  font-weight: 500;
}

.key-desc {
  font-size: 12px;
  color: #8a8a9a;
  margin-left: 8px;
}

.key-prefix {
  background: #12121a;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: #4ade80;
}

.permission-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.perm-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
}

.perm-read {
  background: #3b82f6;
  color: #ffffff;
}

.perm-trade {
  background: #f59e0b;
  color: #ffffff;
}

.perm-admin {
  background: #ef4444;
  color: #ffffff;
}

.status-badge {
  display: inline-block;
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

.status-active {
  background: rgba(74, 222, 128, 0.2);
  color: #4ade80;
}

.status-inactive {
  background: rgba(138, 138, 154, 0.2);
  color: #8a8a9a;
}

.status-expired {
  background: rgba(248, 113, 113, 0.2);
  color: #f87171;
}

.actions-cell {
  white-space: nowrap;
}

.btn-icon svg {
  width: 16px;
  height: 16px;
  stroke-width: 2;
}

.btn-icon.btn-danger:hover {
  color: #f87171;
}

.empty-state {
  text-align: center;
  color: #8a8a9a;
  padding: 32px !important;
}

/* 模态框 */

.checkbox-group {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 24px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
  padding: 4px 0;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-label span {
  line-height: 1;
}

.success-message {
  background: rgba(74, 222, 128, 0.1);
  border: 1px solid rgba(74, 222, 128, 0.3);
  border-radius: 4px;
  padding: 12px;
}

.key-display {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.key-display code {
  flex: 1;
  background: #12121a;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #4ade80;
  word-break: break-all;
}

.btn-copy {
  background: #6366f1;
  border: none;
  border-radius: 4px;
  padding: 8px 16px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

.btn-copy:hover {
  background: #4f46e5;
}

.help-text {
  font-size: 12px;
  color: #fbbf24;
  margin: 8px 0 0 0;
}

/* 按钮 */

</style>
