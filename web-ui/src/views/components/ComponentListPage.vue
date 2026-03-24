<template>
  <div class="component-list-page">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="page-header-left">
        <h1 class="page-title">{{ title }}</h1>
        <button class="btn-primary" @click="handleCreate">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          创建第一个文件
        </button>
      </div>
      <div class="page-header-right">
        <div class="search-box">
          <input v-model="searchText" type="text" placeholder="搜索文件名" class="search-input" />
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
        </div>
      </div>
    </div>

    <!-- 表格区域 -->
    <div class="table-card">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="filteredFiles.length === 0" class="empty-state">
        <p>暂无文件</p>
        <button class="btn-primary" @click="handleCreate">创建第一个文件</button>
      </div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in filteredFiles" :key="record.uuid">
              <td>
                <router-link :to="getDetailUrl(record)" class="file-link">
                  {{ record.name }}
                </router-link>
              </td>
              <td>{{ formatDate(record.update_at || record.created_at) }}</td>
              <td>
                <div class="table-actions">
                  <router-link :to="getDetailUrl(record)" class="action-link">编辑</router-link>
                  <button class="action-link action-link-danger" @click="handleDelete(record)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- 分页 -->
        <div class="pagination">
          <div class="pagination-info">共 {{ filteredFiles.length }} 条</div>
          <div class="pagination-controls">
            <select class="pagination-size">
              <option :value="20">20条/页</option>
              <option :value="50">50条/页</option>
              <option :value="100">100条/页</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <!-- 新建文件对话框 -->
    <div v-if="createModalVisible" class="modal-overlay" @click.self="createModalVisible = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建文件</h3>
          <button class="modal-close" @click="createModalVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">文件名</label>
            <input v-model="newFileName" type="text" placeholder="例如: my_strategy.py" class="form-input" ref="fileNameInput" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-secondary" @click="createModalVisible = false">取消</button>
          <button class="btn-primary" @click="handleCreateConfirm">确定</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'

interface Props {
  title: string
  fileType: number
  basePath: string
}

const props = defineProps<Props>()
const router = useRouter()

const loading = ref(false)
const files = ref<any[]>([])
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')
const fileNameInput = ref<HTMLInputElement | null>(null)

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const search = searchText.value.toLowerCase()
  return files.value.filter(f => f.name.toLowerCase().includes(search))
})

function getDetailUrl(record: any): string {
  return `${props.basePath}/${record.uuid}`
}

function formatDate(timestamp: string): string {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

async function loadFiles() {
  loading.value = true
  try {
    // TODO: 调用 API 加载文件列表
    await new Promise(resolve => setTimeout(resolve, 500))
    files.value = []
  } catch (error: any) {
    console.error('加载失败:', error)
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  newFileName.value = ''
  createModalVisible.value = true
  nextTick(() => {
    fileNameInput.value?.focus()
  })
}

async function handleCreateConfirm() {
  if (!newFileName.value.trim()) {
    console.warn('请输入文件名')
    return
  }
  createModalVisible.value = false

  try {
    // TODO: 调用 API 创建文件
    await new Promise(resolve => setTimeout(resolve, 500))
    console.log('创建成功')
  } catch (error: any) {
    console.error('创建失败:', error)
  }
}

async function handleDelete(record: any) {
  if (!confirm(`确定删除 ${record.name}？`)) {
    return
  }

  try {
    // TODO: 调用 API 删除文件
    await new Promise(resolve => setTimeout(resolve, 500))
    console.log('删除成功')
    await loadFiles()
  } catch (error: any) {
    console.error('删除失败:', error)
  }
}

watch(() => props.fileType, () => {
  loadFiles()
}, { immediate: true })
</script>

<style scoped>
.component-list-page {
  padding: 0;
  background: transparent;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.page-header-right {
  display: flex;
  gap: 12px;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  padding: 6px 12px 6px 36px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  width: 240px;
}

.search-input:focus {
  outline: none;
  border-color: #1890ff;
}

.search-box svg {
  position: absolute;
  left: 12px;
  color: #8a8a9a;
  pointer-events: none;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
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

.table-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.loading-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0 0 16px 0;
}

.table-wrapper {
  overflow-x: auto;
  flex: 1;
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

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.file-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
}

.file-link:hover {
  text-decoration: underline;
}

.table-actions {
  display: flex;
  gap: 12px;
}

.action-link {
  background: none;
  border: none;
  color: #1890ff;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  text-decoration: none;
}

.action-link:hover {
  color: #40a9ff;
}

.action-link-danger {
  color: #f5222d;
}

.action-link-danger:hover {
  color: #ff4d4f;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
  flex-wrap: wrap;
  gap: 16px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  gap: 8px;
}

.pagination-size {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  animation: modalFadeIn 0.3s ease;
}

@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
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
  margin-bottom: 8px;
  font-size: 14px;
  color: #8a8a9a;
  font-weight: 500;
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

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .search-input {
    width: 100%;
  }
}
</style>
