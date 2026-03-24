<template>
  <div class="component-list">
    <div class="page-header">
      <div class="page-title">{{ title }}</div>
      <div class="header-actions">
        <div class="search-box">
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索文件名"
            class="form-input"
            @keyup.enter="handleSearch"
          />
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
        </div>
        <button class="btn-primary" @click="handleCreate">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          新建
        </button>
      </div>
    </div>

    <div class="content-layout">
      <div class="file-list-panel">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>文件名</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody v-if="!loading">
              <tr
                v-for="record in filteredFiles"
                :key="record.uuid"
                :class="{ active: selectedFile?.uuid === record.uuid }"
                @click="handleSelectFile(record)"
              >
                <td>
                  <div class="file-name" :class="{ active: selectedFile?.uuid === record.uuid }">
                    {{ record.name }}
                  </div>
                </td>
                <td>{{ formatDate(record.created_at) }}</td>
                <td>
                  <button class="btn-link text-red" @click.stop="confirmDelete(record)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="editor-panel">
        <div v-if="selectedFile || isCreating" class="editor-wrapper">
          <CodeEditor
            :file-id="selectedFile?.uuid || ''"
            :file-name="selectedFile?.name || newFileName"
            :file-type="fileType"
            :content="fileContent"
            @saved="handleSaved"
          />
        </div>
        <div v-else class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
          <p>选择文件进行编辑，或点击"新建"创建新文件</p>
        </div>
      </div>
    </div>

    <!-- 新建文件模态框 -->
    <div v-if="createModalVisible" class="modal-overlay" @click.self="createModalVisible = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建文件</h3>
          <button class="modal-close" @click="createModalVisible = false">×</button>
        </div>
        <div class="modal-body">
          <form @submit.prevent="handleCreateConfirm">
            <div class="form-group">
              <label class="form-label">文件名 <span class="required">*</span></label>
              <input v-model="newFileName" type="text" placeholder="例如: my_strategy.py" class="form-input" required />
            </div>
            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="createModalVisible = false">取消</button>
              <button type="submit" class="btn-primary">创建</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 简化的API（实际项目中需要导入真实的API）
const fileApi: any = {
  list: async () => [],
  get: async () => ({ data: '' }),
  delete: async () => ({ status: 'success' })
}

interface FileItem {
  uuid: string
  name: string
  created_at: string
}

interface Props {
  title: string
  fileType: number
}

const props = defineProps<Props>()

const loading = ref(false)
const files = ref<FileItem[]>([])
const selectedFile = ref<FileItem | null>(null)
const fileContent = ref('')
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')
const isCreating = ref(false)

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const search = searchText.value.toLowerCase()
  return files.value.filter(f => f.name.toLowerCase().includes(search))
})

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

async function loadFiles() {
  loading.value = true
  try {
    // 模拟数据加载
    files.value = []
  } catch (error: any) {
    showToast('加载失败', 'error')
  } finally {
    loading.value = false
  }
}

async function handleSelectFile(file: FileItem) {
  if (selectedFile.value?.uuid === file.uuid) return

  selectedFile.value = file
  isCreating.value = false
  newFileName.value = ''

  try {
    const fullFile = await fileApi.get(file.uuid)
    let content = ''
    if (fullFile.data) {
      if (typeof fullFile.data === 'string') {
        content = fullFile.data
      } else if (fullFile.data instanceof Uint8Array) {
        content = new TextDecoder().decode(fullFile.data)
      }
    }
    fileContent.value = content
  } catch (error: any) {
    showToast('加载文件内容失败', 'error')
    fileContent.value = ''
  }
}

function handleCreate() {
  isCreating.value = true
  selectedFile.value = null
  fileContent.value = getTemplateContent()
  createModalVisible.value = true
  newFileName.value = ''
}

function handleCreateConfirm() {
  if (!newFileName.value.trim()) {
    showToast('请输入文件名', 'error')
    return
  }
  createModalVisible.value = false
  fileContent.value = getTemplateContent(newFileName.value)
}

function getTemplateContent(name: string = 'NewComponent'): string {
  const className = name.replace('.py', '').replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()).replace(/ /g, '')
  switch (props.fileType) {
    case 6: // STRATEGY
      return `# -*- coding: utf-8 -*-
from ginkgo.core.strategies.base_strategy import BaseStrategy
from ginkgo.core.signals.signal import Signal
from ginkgo.enums import DIRECTION_TYPES
from typing import Dict, List
from ginkgo.core.events.event_base import EventBase


class ${className}(BaseStrategy):
    """
    自定义策略模板
    """

    def __init__(self, name: str = "${className}"):
        super().__init__(name)

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        策略核心计算逻辑

        Args:
            portfolio_info: 投资组合信息
            event: 事件对象（通常是 EventPriceUpdate）

        Returns:
            信号列表
        """
        signals = []

        # TODO: 实现你的策略逻辑
        # 示例：获取当前价格
        # code = event.code
        # price = event.price
        # if self.should_buy(price):
        #     signals.append(Signal(code=code, direction=DIRECTION_TYPES.LONG))

        return signals
`
    case 3: // RISKMANAGER
      return `# -*- coding: utf-8 -*-
from ginkgo.core.risk.base_risk import BaseRiskManagement
from ginkgo.core.signals.signal import Signal
from ginkgo.core.orders.order import Order
from ginkgo.enums import DIRECTION_TYPES
from typing import Dict, List
from ginkgo.core.events.event_base import EventBase


class ${className}(BaseRiskManagement):
    """
    自定义风控模板
    """

    def __init__(self, name: str = "${className}"):
        super().__init__(name)

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查（被动拦截）

        Args:
            portfolio_info: 投资组合信息
            order: 待执行订单

        Returns:
            修改后的订单
        """
        # TODO: 实现风控逻辑
        return order

    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        主动风控信号生成

        Args:
            portfolio_info: 投资组合信息
            event: 事件对象

        Returns:
            风控信号列表（如止损信号）
        """
        signals = []

        # TODO: 实现主动风控逻辑
        # if self.should_stop_loss(portfolio_info, event):
        #     signals.append(Signal(direction=DIRECTION_TYPES.SHORT, reason="Stop Loss"))

        return signals
`
    default:
      return `# -*- coding: utf-8 -*-
# ${name}

# TODO: 实现你的代码
`
  }
}

function confirmDelete(file: FileItem) {
  if (confirm(`确定要删除文件 "${file.name}" 吗？`)) {
    handleDelete(file)
  }
}

async function handleDelete(file: FileItem) {
  try {
    const result = await fileApi.delete(file.uuid)
    if (result.status === 'success') {
      showToast('删除成功')
      if (selectedFile.value?.uuid === file.uuid) {
        selectedFile.value = null
        fileContent.value = ''
      }
      await loadFiles()
    } else {
      showToast('删除失败', 'error')
    }
  } catch (error: any) {
    showToast('删除失败', 'error')
  }
}

function handleSaved(file: { uuid: string; name: string }) {
  if (isCreating.value) {
    isCreating.value = false
    loadFiles().then(() => {
      const newFile = files.value.find(f => f.uuid === file.uuid)
      if (newFile) {
        selectedFile.value = newFile
      }
    })
  }
}

function handleSearch() {
  // 搜索由 computed 属性处理
}

// 监听 fileType 变化重新加载
watch(() => props.fileType, () => {
  selectedFile.value = null
  fileContent.value = ''
  loadFiles()
}, { immediate: true })

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.component-list {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #0f0f1a;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.search-box {
  display: flex;
  align-items: center;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  padding: 8px 12px;
}

.search-box .form-input {
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
  width: 180px;
}

.search-box .form-input:focus {
  outline: none;
  box-shadow: none;
}

.search-box svg {
  color: #8a8a9a;
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

.btn-primary:hover {
  background: #40a9ff;
}

.content-layout {
  flex: 1;
  display: flex;
  gap: 16px;
  overflow: hidden;
}

.file-list-panel {
  width: 400px;
  flex-shrink: 0;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  overflow: auto;
}

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
  position: sticky;
  top: 0;
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr {
  cursor: pointer;
  transition: background 0.2s;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.data-table tbody tr.active {
  background: rgba(24, 144, 255, 0.1);
}

.file-name {
  color: #ffffff;
}

.file-name.active {
  color: #1890ff;
  font-weight: 500;
}

.btn-link {
  padding: 0;
  background: transparent;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: 13px;
}

.btn-link:hover {
  text-decoration: underline;
}

.btn-link.text-red {
  color: #f5222d;
}

.editor-panel {
  flex: 1;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-wrapper {
  flex: 1;
  padding: 16px;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #8a8a9a;
}

.empty-state svg {
  opacity: 0.3;
}

.empty-state p {
  margin-top: 16px;
  font-size: 14px;
}

/* 模态框样式 */
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

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 90%;
  max-width: 400px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
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
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
  padding: 4px 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #2a2a3e;
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
  margin-bottom: 8px;
}

.required {
  color: #f5222d;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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
</style>
