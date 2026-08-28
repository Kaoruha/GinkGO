<template>
  <PageLayout>
    <template #title>
      实盘账号配置
    </template>
    <template #description>
      管理交易所API凭证，配置实盘交易账号
    </template>
    <template #actions>
      <button
        class="btn-primary"
        @click="showAddModal"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <line
            x1="12"
            y1="5"
            x2="12"
            y2="19"
          />
          <line
            x1="5"
            y1="12"
            x2="19"
            y2="12"
          />
        </svg>
        添加账号
      </button>
    </template>

    <!-- 账号列表 -->
    <div class="card account-list-card">
      <div class="card-header">
        <div class="card-title">
          <span>账号列表</span>
          <span class="tag tag-blue">{{ accounts.length }} 个账号</span>
        </div>
      </div>

      <div class="card-body">
        <div
          v-if="loading"
          class="loading-state"
        >
          加载中...
        </div>
        <div
          v-else
          class="table-wrapper"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th>账号名称</th>
                <th>交易所</th>
                <th>状态</th>
                <th>最后验证</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in accounts"
                :key="record.uuid"
                @contextmenu="openAccountMenu($event, record)"
              >
                <td>
                  <div class="account-name">
                    <span>{{ record.name }}</span>
                    <span
                      v-if="record.environment === 'production'"
                      class="tag tag-red"
                      style="margin-left: 8px"
                    >
                      生产环境
                    </span>
                    <span
                      v-else
                      class="tag tag-green"
                      style="margin-left: 8px"
                    >
                      测试网
                    </span>
                  </div>
                </td>
                <td>
                  <span
                    class="tag"
                    :class="record.exchange === 'okx' ? 'tag-cyan' : 'tag-yellow'"
                  >
                    {{ record.exchange.toUpperCase() }}
                  </span>
                </td>
                <td>
                  <span
                    class="tag"
                    :class="getStatusTagClass(record.status)"
                  >
                    {{ getStatusText(record.status) }}
                  </span>
                </td>
                <td>
                  <span v-if="record.last_validated_at">
                    {{ formatDate(record.last_validated_at) }}
                  </span>
                  <span
                    v-else
                    class="text-muted"
                  >未验证</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 添加/编辑账号模态框 -->
    <FormModal
      v-model:open="modalVisible"
      :title="isEditMode ? '编辑账号' : '添加账号'"
      :loading="saving"
      loading-text="保存中..."
      @submit="handleModalOk"
      @cancel="handleModalCancel"
    >
      <div class="form-group">
        <label class="form-label">账号名称</label>
        <input
          v-model="formData.name"
          type="text"
          placeholder="输入账号名称"
          class="form-input"
        >
      </div>

      <div class="form-group">
        <label class="form-label">交易所</label>
        <select
          v-model="formData.exchange"
          class="form-select"
        >
          <option value="okx">
            OKX
          </option>
          <option value="binance">
            Binance
          </option>
        </select>
      </div>

      <div class="form-group">
        <label class="form-label">环境</label>
        <div class="radio-group">
          <label class="radio-label">
            <input
              v-model="formData.environment"
              type="radio"
              value="testnet"
            >
            测试网
          </label>
          <label class="radio-label">
            <input
              v-model="formData.environment"
              type="radio"
              value="production"
            >
            生产环境
          </label>
        </div>
        <div class="form-tip">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <circle
              cx="12"
              cy="12"
              r="10"
            />
            <line
              x1="12"
              y1="8"
              x2="12"
              y2="12"
            />
            <line
              x1="12"
              y1="16"
              x2="12.01"
              y2="16"
            />
          </svg>
          生产环境使用真实资金进行交易，请谨慎操作
        </div>
      </div>

      <div class="form-divider">
        API凭证
      </div>

      <div class="form-group">
        <label class="form-label">API Key</label>
        <input
          v-model="formData.api_key"
          type="password"
          placeholder="输入API Key"
          class="form-input"
        >
      </div>

      <div class="form-group">
        <label class="form-label">API Secret</label>
        <input
          v-model="formData.api_secret"
          type="password"
          placeholder="输入API Secret"
          class="form-input"
        >
      </div>

      <div
        v-if="formData.exchange === 'okx'"
        class="form-group"
      >
        <label class="form-label">Passphrase</label>
        <input
          v-model="formData.passphrase"
          type="password"
          placeholder="输入Passphrase (OKX需要)"
          class="form-input"
        >
      </div>

      <div class="form-group">
        <label class="form-label">描述</label>
        <textarea
          v-model="formData.description"
          class="form-textarea"
          rows="3"
          placeholder="账号描述（可选）"
        />
      </div>

      <!-- 验证结果 -->
      <div
        v-if="validationResult"
        class="alert"
        :class="validationResult.success ? 'alert-success' : 'alert-error'"
      >
        <div class="alert-icon">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line
              x1="12"
              y1="9"
              x2="12"
              y2="13"
            />
            <line
              x1="12"
              y1="17"
              x2="12.01"
              y2="17"
            />
          </svg>
        </div>
        <div class="alert-content">
          <div class="alert-message">
            {{ validationResult.message }}
          </div>
          <div
            v-if="validationResult.account_info"
            class="alert-description"
          >
            <div>余额: {{ validationResult.account_info.balance }}</div>
            <div>环境: {{ validationResult.account_info.environment }}</div>
          </div>
        </div>
      </div>
    </FormModal>
  </PageLayout>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { liveAccountApi } from '@/api'
import { useContextMenu, useAsyncAction } from '@/composables'
import FormModal from '@/components/common/FormModal.vue'
import { message as toast } from '@/utils/toast'
import { formatDate } from '@/utils/format'
import { ACCOUNT_STATUS_CONFIG } from '@/constants/statusConfig'

/** 行右键菜单(替代操作列;删除走菜单内置确认) */
const { open: openCtxMenu } = useContextMenu()
const openAccountMenu = (e, record) => {
  openCtxMenu(e, [
    { label: '测试连接', action: () => testConnection(record.uuid) },
    { label: '编辑', action: () => editAccount(record) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确认删除账号「${record.name}」？`, action: () => deleteAccountDirect(record) },
  ])
}

// 状态
const loading = ref(false)
const accounts = ref([])
const testing = ref({})
const modalVisible = ref(false)
const isEditMode = ref(false)
const validationResult = ref(null)

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
    // 拦截器已拆信封:code!==0 会 reject,resolve 即成功 payload
    const result = await liveAccountApi.getAccounts()
    accounts.value = result?.accounts || []
  } catch (error) {
    console.error('获取账号列表失败：', error)
  } finally {
    loading.value = false
  }
}

// 测试连接
const testConnection = async (uuid) => {
  testing.value[uuid] = true
  try {
    // 拦截器已拆信封:resolve 即 {valid,message,account_info} payload
    const result = await liveAccountApi.validateAccount(uuid)
    validationResult.value = {
      success: result?.valid,
      message: result?.message || '连接测试成功',
      account_info: result?.account_info
    }
    await fetchAccounts()
  } catch (error) {
    console.error('连接测试失败：', error)
    validationResult.value = { success: false, message: '连接测试失败' }
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

// 删除账号(确认由菜单内置 ConfirmDialog 承担)
const deleteAccountDirect = async (record) => {
  try {
    await liveAccountApi.deleteAccount(record.uuid)
    await fetchAccounts()
  } catch (error) {
    console.error('删除失败：', error)
  }
}

// 处理模态框确认
const handleModalOk = () => {
  if (!formData.name || !formData.exchange || !formData.environment || !formData.api_key || !formData.api_secret) {
    toast.warning('请填写必填字段')
    return
  }

  if (formData.exchange === 'okx' && !formData.passphrase) {
    toast.warning('OKX 需要填写 Passphrase')
    return
  }
  runSaveAccount()
}

const { running: saving, run: runSaveAccount } = useAsyncAction(async () => {
  if (isEditMode.value) {
    await liveAccountApi.updateAccount(formData.uuid, {
      name: formData.name,
      api_key: formData.api_key,
      api_secret: formData.api_secret,
      passphrase: formData.passphrase || undefined,
      description: formData.description || undefined,
    })
  } else {
    await liveAccountApi.createAccount({
      exchange: formData.exchange,
      name: formData.name,
      api_key: formData.api_key,
      api_secret: formData.api_secret,
      passphrase: formData.passphrase || undefined,
      environment: formData.environment,
      description: formData.description || undefined,
    })
  }
}, {
  onSuccess: async () => {
    modalVisible.value = false
    await fetchAccounts()
  },
})

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

// 获取状态标签类/文本(枚举收敛在 constants/statusConfig)
const getStatusTagClass = (status) => ACCOUNT_STATUS_CONFIG[status]?.tagClass ?? 'tag-gray'

const getStatusText = (status) => ACCOUNT_STATUS_CONFIG[status]?.label ?? status

// 生命周期
onMounted(() => {
  fetchAccounts()
})
</script>

<style scoped>

/* 字号覆盖:小屏 12px 见文末 @media;公共基线见 styles/tables.less;弹窗走全局 modals.less */
.data-table td {
  font-size: 13px;
}

/* 标题排版走全局 cards.less .card-title,此处仅标题行的 flex 布局 */
.card-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-small:hover:not(:disabled) {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
}

.btn-small:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.tag-yellow { background: hsl(var(--warning) / 0.2); color: hsl(var(--warning)); }

.account-name {
  display: flex;
  align-items: center;
}

.text-muted {
  color: hsl(var(--muted-foreground));
}

.table-wrapper {
  overflow-x: clip;
}

/* 模态框样式 */

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: hsl(var(--foreground));
  cursor: pointer;
}

.form-divider {
  margin: 20px 0;
  padding-top: 20px;
  border-top: 1px solid hsl(var(--border));
  font-size: 14px;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.form-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  color: hsl(var(--warning));
  font-size: 12px;
  margin-top: 8px;
}

.alert {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius);
  margin-top: 16px;
}

.alert-success {
  background: hsl(var(--success) / 0.1);
  border: 1px solid hsl(var(--success) / 0.3);
}

.alert-error {
  background: hsl(var(--error) / 0.1);
  border: 1px solid hsl(var(--error) / 0.3);
}

.alert-icon {
  flex-shrink: 0;
}

.alert-error .alert-icon {
  color: hsl(var(--error));
}

.alert-success .alert-icon {
  color: hsl(var(--success));
}

.alert-content {
  flex: 1;
}

.alert-message {
  font-size: 14px;
  color: hsl(var(--foreground));
  margin-bottom: 4px;
}

.alert-description {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .data-table {
    font-size: 12px;
  }
}
</style>
