<template>
  <PageLayout>
    <template #title>
      API Key 管理
    </template>
    <template #actions>
      <button
        class="btn-primary"
        @click="showCreateModal = true"
      >
        <i class="icon-plus" />
        创建 API Key
      </button>
      <button
        class="btn-secondary"
        @click="loadApiKeys"
      >
        <i class="icon-refresh" />
        刷新
      </button>
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <StatCard
        title="总 API Key"
        :value="apiKeys.length"
      />
      <StatCard
        title="激活"
        :value="activeCount"
        :color="activeCount > 0 ? 'positive' : 'neutral'"
      />
      <StatCard
        title="已过期"
        :value="expiredCount"
        :color="expiredCount > 0 ? 'negative' : 'positive'"
      />
      <StatCard
        title="禁用"
        :value="inactiveCount"
        color="neutral"
      />
    </div>

    <!-- API Keys 表格 -->
    <div class="card">
      <div class="card-header">
        <h3>API Keys</h3>
      </div>
      <div class="card-body">
        <div
          v-if="loading"
          class="loading-container"
        >
          <div class="spinner" />
        </div>
        <EmptyState
          v-else-if="error"
          title="加载失败"
          :description="error"
          action-text="重试"
          :on-action="loadApiKeys"
        />
        <table
          v-else-if="apiKeys.length > 0"
          class="data-table"
        >
          <thead>
            <tr>
              <th>名称</th>
              <th>Key 前缀</th>
              <th>权限</th>
              <th>状态</th>
              <th>过期时间</th>
              <th>最后使用</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="key in apiKeys"
              :key="key.uuid"
              @contextmenu="openKeyMenu($event, key)"
            >
              <td>
                <div class="key-name">
                  {{ key.name }}
                  <span
                    v-if="key.description"
                    class="key-desc"
                  >{{ key.description }}</span>
                </div>
              </td>
              <td><code class="key-prefix">{{ key.key_prefix }}***</code></td>
              <td>
                <span class="permission-tags">
                  <span
                    v-for="perm in key.permissions_list"
                    :key="perm"
                    :class="`perm-tag perm-${perm}`"
                  >
                    {{ perm }}
                  </span>
                </span>
              </td>
              <td>
                <StatusTag
                  type="enable"
                  :status="keyStatus(key)"
                >
                  {{ key.is_expired ? '已过期' : key.is_active ? '激活' : '禁用' }}
                </StatusTag>
              </td>
              <td>{{ key.expires_at ? formatDate(key.expires_at) : '永不过期' }}</td>
              <td>{{ key.last_used_at ? formatDateTime(key.last_used_at) : '从未使用' }}</td>
            </tr>
          </tbody>
        </table>
        <EmptyState
          v-else
          description="暂无 API Key"
        />
      </div>
    </div>

    <!-- 创建/编辑 API Key 模态框 -->
    <div
      v-if="showCreateModal || editingKey"
      class="modal-overlay"
      @click.self="closeModal"
    >
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingKey ? '编辑 API Key' : '创建 API Key' }}</h2>
          <button
            class="modal-close"
            @click="closeModal"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="saveApiKey">
            <div class="form-group">
              <label class="form-label">名称 <span class="required">*</span></label>
              <input
                v-model="formData.name"
                type="text"
                class="form-input"
                required
                placeholder="如：Claw MCP Key"
              >
            </div>

            <div class="form-group">
              <label class="form-label">权限 <span class="required">*</span></label>
              <div class="checkbox-group">
                <label
                  v-for="perm in availablePermissions"
                  :key="perm"
                  class="checkbox-label"
                >
                  <input
                    v-model="formData.permissions"
                    type="checkbox"
                    :value="perm"
                  >
                  <span>{{ permLabels[perm] }}</span>
                </label>
              </div>
            </div>

            <div
              v-if="!editingKey"
              class="form-group"
            >
              <label class="form-label">有效期（天）</label>
              <input
                v-model.number="formData.expires_days"
                type="number"
                class="form-input"
                min="1"
                placeholder="留空表示永不过期"
              >
            </div>

            <div class="form-group">
              <label class="form-label">备注</label>
              <textarea
                v-model="formData.description"
                rows="2"
                class="form-textarea"
                placeholder="用途说明（可选）"
              />
            </div>

            <div
              v-if="newKeyValue"
              class="form-group success-message"
            >
              <label class="form-label">⚠️ 重要：请保存此 API Key</label>
              <div class="key-display">
                <code>{{ newKeyValue }}</code>
                <button
                  type="button"
                  class="btn-copy"
                  @click="copyKey"
                >
                  复制
                </button>
              </div>
              <p class="help-text">
                此 Key 仅显示一次，请立即保存
              </p>
            </div>

            <div class="modal-footer">
              <button
                type="button"
                class="btn-secondary"
                @click="closeModal"
              >
                {{ newKeyValue ? '关闭' : '取消' }}
              </button>
              <button
                v-if="!newKeyValue"
                type="submit"
                class="btn-primary"
              >
                {{ editingKey ? '保存' : '创建' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { apiKeyApi, type ApiKey, type CreateApiKeyRequest, type UpdateApiKeyRequest, PermissionType } from '@/api/modules/apiKey'
import { message } from '@/utils/toast'
import { copyText } from '@/utils/clipboard'
import { useContextMenu } from '@/composables/useContextMenu'

/** 行右键菜单(替代操作列;删除走菜单内置确认) */
const { open: openCtxMenu } = useContextMenu()
const openKeyMenu = (e: MouseEvent, key: ApiKey) => {
  openCtxMenu(e, [
    { label: '复制完整 Key', action: () => copyApiKey(key) },
    { label: '编辑', action: () => editKey(key) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确定要删除 API Key「${key.name}」吗？此操作不可恢复。`, action: () => deleteKey(key) },
  ])
}

/** API Key 状态映射(StatusTag enable 配置,label 由 slot 覆盖为 激活/禁用) */
const keyStatus = (key: ApiKey): string => {
  if (key.is_expired) return 'expired'
  return key.is_active ? 'active' : 'inactive'
}

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
    // request.ts 拦截器已拆包: payload 即 ApiKey[] 裸数组
    apiKeys.value = (res as any) || []
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
      // request.ts 拦截器已拆包: res 即 CreateApiKeyResponse { key_value, ... }
      newKeyValue.value = (res as any).key_value
    }
    await loadApiKeys()
    if (!newKeyValue.value) closeModal()
  } catch (err: any) {
    error.value = err.message || '保存失败'
    console.error('Failed to save API key:', err)
    // 保存失败必须让用户感知(模态框内表单无错误提示,静默=假成功)
    message.error(error.value || '保存失败')
  } finally {
    loading.value = false
  }
}

/** 裸删(确认由菜单内置 ConfirmDialog 承担) */
const deleteKey = async (key: ApiKey) => {
  loading.value = true
  try {
    await apiKeyApi.deleteApiKey(key.uuid)
    await loadApiKeys()
  } catch (err: any) {
    error.value = err.message || '删除失败'
    console.error('Failed to delete API key:', err)
    message.error(error.value || '删除失败')
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
    // request.ts 拦截器已拆包: fulfilled 即 code===0, res 即 key 对象
    const fullKey = (res as any)?.key_value
    if (fullKey) {
      copyToClipboard(fullKey)
      message.success('API Key 已复制到剪贴板')
    } else {
      message.error('获取失败')
    }
  } catch (err: any) {
    // 如果是没有加密的旧 Key，提示用户
    const errorMsg = err.response?.data?.detail || err.message || '获取失败'
    if (errorMsg.includes('解密') || errorMsg.includes('encrypted')) {
      message.warning('此 API Key 是旧版本创建的,无法获取完整值,请删除后重新生成')
    } else {
      message.error(errorMsg)
    }
  }
}

// 复制到剪贴板(降级兼容见 utils/clipboard)
const copyToClipboard = async (text: string) => {
  const ok = await copyText(text)
  if (!ok) message.error('复制失败，请手动复制')
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
/* 模态框样式走全局 modals.less;表单走全局 forms.less;统计卡片走 StatCard + 全局 .stats-grid */

/* 统计卡片间距需页内补 */
.stats-grid { margin-bottom: 16px; }

/* 表格 */
.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--card));
  text-align: left;
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  text-transform: uppercase;
}

.data-table td {
  padding: 12px 16px;
  border-top: 1px solid hsl(var(--secondary));
  font-size: 14px;
  color: hsl(var(--foreground));
}

.data-table tr:hover {
  background: hsl(var(--card));
}

.key-name {
  font-weight: 500;
}

.key-desc {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-left: 8px;
}

.key-prefix {
  background: hsl(var(--card));
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: hsl(var(--success));
}

.permission-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.perm-tag {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.perm-read {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.perm-trade {
  background: hsl(var(--warning));
  color: hsl(var(--foreground));
}

.perm-admin {
  background: hsl(var(--error));
  color: hsl(var(--foreground));
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
  color: hsl(var(--foreground));
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
  background: hsl(var(--success) / 0.1);
  border: 1px solid hsl(var(--success) / 0.3);
  border-radius: var(--radius-sm);
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
  background: hsl(var(--card));
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: hsl(var(--success));
  word-break: break-all;
}

.btn-copy {
  background: hsl(var(--primary));
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 16px;
  color: hsl(var(--primary-foreground));
  font-size: 13px;
  cursor: pointer;
}

.btn-copy:hover {
  background: hsl(var(--primary));
}

.help-text {
  font-size: 12px;
  color: hsl(var(--warning));
  margin: 8px 0 0 0;
}

/* 按钮 */

</style>
