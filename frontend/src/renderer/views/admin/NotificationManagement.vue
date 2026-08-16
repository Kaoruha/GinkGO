<template>
  <PageLayout>
    <template #title>
      通知管理
    </template>
    <template #actions>
      <button
        class="btn-primary"
        @click="openTemplateModal"
      >
        新建通知模板
      </button>
    </template>

    <div class="card">
      <TabsNav
        :model-value="activeTab"
        :items="tabs"
        @update:model-value="switchTab"
      />

      <!-- 通知模板标签页 -->
      <div
        v-if="activeTab === 'templates'"
        class="tab-content"
      >
        <div
          v-if="loading"
          class="loading-container"
        >
          <div class="spinner" />
        </div>
        <div
          v-else-if="templates.length > 0"
          class="table-wrapper"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th>模板名称</th>
                <th>类型</th>
                <th>主题</th>
                <th>状态</th>
                <th>更新时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in templates"
                :key="record.uuid"
                @contextmenu="openTemplateMenu($event, record)"
              >
                <td>{{ record.name }}</td>
                <td>
                  <span
                    class="tag"
                    :class="getTypeClass(record.type)"
                  >{{ getTypeLabel(record.type) }}</span>
                </td>
                <td>{{ record.subject || '-' }}</td>
                <td>
                  <div class="switch-container">
                    <input
                      :id="`switch-${record.uuid}`"
                      :checked="record.enabled"
                      type="checkbox"
                      class="switch-input"
                      @change="(e: any) => toggleTemplate(record, e.target.checked)"
                    >
                    <label
                      :for="`switch-${record.uuid}`"
                      class="switch-label"
                    />
                  </div>
                </td>
                <td>{{ formatDate(record.updated_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          description="暂无通知模板"
        />
      </div>

      <!-- 发送记录标签页 -->
      <div
        v-if="activeTab === 'history'"
        class="tab-content"
      >
        <div
          v-if="loading"
          class="loading-container"
        >
          <div class="spinner" />
        </div>
        <div
          v-else-if="history.length > 0"
          class="table-wrapper"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>主题</th>
                <th>接收者</th>
                <th>状态</th>
                <th>发送时间</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in history"
                :key="record.uuid"
              >
                <td>
                  <span
                    class="tag"
                    :class="getTypeClass(record.type)"
                  >{{ getTypeLabel(record.type) }}</span>
                </td>
                <td>{{ record.subject || '-' }}</td>
                <td>{{ record.recipient }}</td>
                <td>
                  <StatusTag
                    type="execution"
                    :status="record.status"
                  />
                </td>
                <td>{{ formatDate(record.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          description="暂无发送记录"
        />
      </div>

      <!-- 接收人标签页 -->
      <div
        v-if="activeTab === 'recipients'"
        class="tab-content"
      >
        <div class="tab-toolbar">
          <button
            class="btn-primary btn-sm"
            @click="openRecipientModal"
          >
            添加接收人
          </button>
        </div>
        <div
          v-if="loading"
          class="loading-container"
        >
          <div class="spinner" />
        </div>
        <div
          v-else-if="recipients.length > 0"
          class="table-wrapper"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>关联对象</th>
                <th>描述</th>
                <th>默认</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in recipients"
                :key="record.uuid"
                @contextmenu="openRecipientMenu($event, record)"
              >
                <td>{{ record.name }}</td>
                <td>
                  <span class="tag tag-blue">{{ record.recipient_type === 'USER' ? '用户' : '用户组' }}</span>
                </td>
                <td>{{ record.recipient_type === 'USER' ? (record.user_info?.display_name || record.user_info?.username) : record.user_group_info?.name }}</td>
                <td>{{ record.description || '-' }}</td>
                <td>
                  <span
                    v-if="record.is_default"
                    class="tag tag-green"
                  >默认</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState
          v-else
          description="暂无接收人"
        />
      </div>
    </div>

    <!-- 新建/编辑通知模板模态框 -->
    <div
      v-if="showTemplateModal"
      class="modal-overlay"
      @click.self="closeTemplateModal"
    >
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingTemplate ? '编辑通知模板' : '新建通知模板' }}</h3>
          <button
            class="modal-close"
            @click="closeTemplateModal"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleTemplateSubmit">
            <div class="form-group">
              <label class="form-label">模板名称 <span class="required">*</span></label>
              <input
                v-model="templateForm.name"
                type="text"
                placeholder="输入模板名称"
                class="form-input"
                required
              >
            </div>
            <div class="form-group">
              <label class="form-label">通知类型 <span class="required">*</span></label>
              <select
                v-model="templateForm.type"
                class="form-select"
              >
                <option value="email">
                  邮件
                </option>
                <option value="discord">
                  Discord
                </option>
                <option value="system">
                  系统通知
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">标题模板</label>
              <input
                v-model="templateForm.subject"
                type="text"
                placeholder="通知标题"
                class="form-input"
              >
            </div>
            <div class="modal-actions">
              <button
                type="button"
                class="btn-secondary"
                @click="closeTemplateModal"
              >
                取消
              </button>
              <button
                type="submit"
                class="btn-primary"
              >
                {{ editingTemplate ? '保存' : '创建' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- 添加/编辑接收人模态框 -->
    <div
      v-if="showRecipientModal"
      class="modal-overlay"
      @click.self="closeRecipientModal"
    >
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingRecipient ? '编辑接收人' : '添加接收人' }}</h3>
          <button
            class="modal-close"
            @click="closeRecipientModal"
          >
            ×
          </button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleRecipientSubmit">
            <div class="form-group">
              <label class="form-label">名称 <span class="required">*</span></label>
              <input
                v-model="recipientForm.name"
                type="text"
                placeholder="接收人名称"
                class="form-input"
                required
              >
            </div>
            <div class="form-group">
              <label class="form-label">类型</label>
              <select
                v-model="recipientForm.recipient_type"
                class="form-select"
              >
                <option value="USER">
                  用户
                </option>
                <option value="USER_GROUP">
                  用户组
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">描述</label>
              <input
                v-model="recipientForm.description"
                type="text"
                placeholder="描述（可选）"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label class="form-label">设为默认</label>
              <label class="switch-label">
                <input
                  v-model="recipientForm.is_default"
                  type="checkbox"
                  class="switch-input-inline"
                >
                <span>{{ recipientForm.is_default ? '是' : '否' }}</span>
              </label>
            </div>
            <div class="modal-actions">
              <button
                type="button"
                class="btn-secondary"
                @click="closeRecipientModal"
              >
                取消
              </button>
              <button
                type="submit"
                class="btn-primary"
              >
                {{ editingRecipient ? '保存' : '创建' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import TabsNav from '@/components/common/TabsNav.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { notificationsApi, type NotificationTemplate, type NotificationHistory, type NotificationRecipient } from '@/api/modules/settings'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'

/** 行右键菜单(替代操作列;删除走菜单内置确认) */
const { open: openCtxMenu } = useContextMenu()
const openTemplateMenu = (e: MouseEvent, record: NotificationTemplate) => {
  openCtxMenu(e, [
    { label: '编辑', action: () => editTemplate(record) },
    { label: '测试', action: () => testTemplate(record) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确定要删除模板「${record.name}」吗？`, action: () => deleteTemplate(record) },
  ])
}

const openRecipientMenu = (e: MouseEvent, record: NotificationRecipient) => {
  openCtxMenu(e, [
    { label: '编辑', action: () => editRecipient(record) },
    { label: '测试', action: () => testRecipient(record) },
    { divider: true },
    { label: '删除', danger: true, confirm: `确定要删除接收人「${record.name}」吗？`, action: () => deleteRecipient(record) },
  ])
}

const activeTab = ref('templates')
const loading = ref(false)
const showTemplateModal = ref(false)
const showRecipientModal = ref(false)
const editingTemplate = ref<NotificationTemplate | null>(null)
const editingRecipient = ref<NotificationRecipient | null>(null)

const templates = ref<NotificationTemplate[]>([])
const history = ref<NotificationHistory[]>([])
const recipients = ref<NotificationRecipient[]>([])

const templateForm = reactive({ name: '', type: 'email' as 'email' | 'discord' | 'system', subject: '' })
const recipientForm = reactive({
  name: '',
  recipient_type: 'USER' as 'USER' | 'USER_GROUP',
  description: '',
  is_default: false,
})

const tabs = [
  { key: 'templates', label: '通知模板' },
  { key: 'history', label: '发送记录' },
  { key: 'recipients', label: '接收人' },
]

const getTypeClass = (type: string) => {
  const classMap: Record<string, string> = { email: 'tag-blue', discord: 'tag-green', system: 'tag-orange' }
  return classMap[type] || 'tag-gray'
}

const getTypeLabel = (type: string) => {
  const labelMap: Record<string, string> = { email: '邮件', discord: 'Discord', system: '系统', webhook: 'Webhook' }
  return labelMap[type] || type
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// ===== 数据加载 =====

const loadTemplates = async () => {
  loading.value = true
  try {
    const res = await notificationsApi.listTemplates() as any
    templates.value = res.data || res || []
  } catch (e: any) {
    toast.error(e.message || '加载模板失败')
  } finally {
    loading.value = false
  }
}

const loadHistory = async () => {
  loading.value = true
  try {
    const res = await notificationsApi.listHistory() as any
    history.value = res.data || res || []
  } catch (e: any) {
    toast.error(e.message || '加载记录失败')
  } finally {
    loading.value = false
  }
}

const loadRecipients = async () => {
  loading.value = true
  try {
    const res = await notificationsApi.listRecipients() as any
    recipients.value = res.data || res || []
  } catch (e: any) {
    toast.error(e.message || '加载接收人失败')
  } finally {
    loading.value = false
  }
}

const switchTab = (key: string) => {
  activeTab.value = key
  if (key === 'templates') loadTemplates()
  else if (key === 'history') loadHistory()
  else if (key === 'recipients') loadRecipients()
}

// ===== 模板操作 =====

const openTemplateModal = () => {
  editingTemplate.value = null
  Object.assign(templateForm, { name: '', type: 'email', subject: '' })
  showTemplateModal.value = true
}

const editTemplate = (record: NotificationTemplate) => {
  editingTemplate.value = record
  Object.assign(templateForm, { name: record.name, type: record.type, subject: record.subject })
  showTemplateModal.value = true
}

const closeTemplateModal = () => {
  showTemplateModal.value = false
  editingTemplate.value = null
}

const toggleTemplate = async (record: NotificationTemplate, checked: boolean) => {
  try {
    await notificationsApi.toggleTemplate(record.uuid, checked)
    record.enabled = checked
    toast.success(`模板已${checked ? '启用' : '禁用'}`)
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  }
}

const testTemplate = async (record: NotificationTemplate) => {
  try {
    await notificationsApi.testTemplate(record.uuid)
    toast.success('测试通知已发送')
  } catch (e: any) {
    toast.error(e.message || '测试失败')
  }
}

const deleteTemplate = async (record: NotificationTemplate) => {
  try {
    await notificationsApi.deleteTemplate(record.uuid)
    toast.success('模板已删除')
    await loadTemplates()
  } catch (e: any) {
    toast.error(e.message || '删除失败')
  }
}

const handleTemplateSubmit = async () => {
  if (!templateForm.name) {
    toast.warning('请输入模板名称')
    return
  }

  try {
    if (editingTemplate.value) {
      await notificationsApi.updateTemplate(editingTemplate.value.uuid, templateForm)
      toast.success('模板已更新')
    } else {
      await notificationsApi.createTemplate(templateForm)
      toast.success('模板创建成功')
    }
    closeTemplateModal()
    await loadTemplates()
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  }
}

// ===== 接收人操作 =====

const openRecipientModal = () => {
  editingRecipient.value = null
  Object.assign(recipientForm, { name: '', recipient_type: 'USER', description: '', is_default: false })
  showRecipientModal.value = true
}

const editRecipient = (record: NotificationRecipient) => {
  editingRecipient.value = record
  Object.assign(recipientForm, {
    name: record.name,
    recipient_type: record.recipient_type,
    description: record.description || '',
    is_default: record.is_default,
  })
  showRecipientModal.value = true
}

const closeRecipientModal = () => {
  showRecipientModal.value = false
  editingRecipient.value = null
}

const testRecipient = async (record: NotificationRecipient) => {
  try {
    const res = await notificationsApi.testRecipient(record.uuid) as any
    const data = res.data || res
    toast.success(`测试通知已发送 (${data.success_count || 0} 成功, ${data.failed_count || 0} 失败)`)
  } catch (e: any) {
    toast.error(e.message || '测试失败')
  }
}

const deleteRecipient = async (record: NotificationRecipient) => {
  try {
    await notificationsApi.deleteRecipient(record.uuid)
    toast.success('接收人已删除')
    await loadRecipients()
  } catch (e: any) {
    toast.error(e.message || '删除失败')
  }
}

const handleRecipientSubmit = async () => {
  if (!recipientForm.name) {
    toast.warning('请输入接收人名称')
    return
  }

  try {
    if (editingRecipient.value) {
      await notificationsApi.updateRecipient(editingRecipient.value.uuid, recipientForm)
      toast.success('接收人已更新')
    } else {
      await notificationsApi.createRecipient(recipientForm)
      toast.success('接收人已创建')
    }
    closeRecipientModal()
    await loadRecipients()
  } catch (e: any) {
    toast.error(e.message || '操作失败')
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
/* 模态框样式走全局 modals.less */

.tab-content {
  padding: 20px;
}

.tab-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 16px;
}

.btn-sm {
  font-size: 12px;
  padding: 6px 12px;
}

/* 表格样式 */
.table-wrapper {
  overflow-x: clip;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid hsl(var(--border));
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--border));
  color: hsl(var(--foreground));
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: hsl(var(--foreground));
  font-size: 14px;
}

.data-table tr:hover {
  background: hsl(var(--border));
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
  background: hsl(var(--secondary));
  border-radius: 9999px;
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
  background: hsl(var(--card));
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked + .switch-label {
  background: hsl(var(--primary));
}

.switch-input:checked + .switch-label::after {
  transform: translateX(22px);
}

.switch-label-inline {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: hsl(var(--foreground));
  font-size: 13px;
}

.switch-input-inline {
  width: 16px;
  height: 16px;
  cursor: pointer;
}
</style>
