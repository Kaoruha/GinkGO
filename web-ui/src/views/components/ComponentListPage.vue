<template>
  <ListPageLayout
    :title="title"
    :loading="loading"
    :empty="filteredFiles.length === 0 && !loading"
    empty-text="暂无文件"
    empty-action-text="创建第一个文件"
    :show-search="true"
    search-placeholder="搜索文件名"
    :search-value="searchText"
    @update:search="searchText = $event"
    @create="handleCreate"
  >
    <!-- 内容区 -->
    <div class="table-card">
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

    <!-- 新建文件对话框 -->
    <div v-if="createModalVisible" class="modal-overlay" @click.self="createModalVisible = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新建文件</h3>
          <button class="modal-close" @click="createModalVisible = false">&times;</button>
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
  </ListPageLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListPageLayout from '@/components/common/ListPageLayout.vue'
import { componentsApi } from '@/api/modules/components'

const route = useRoute()

const routeTypeToApiType: Record<string, string> = {
  strategies: 'strategy',
  analyzers: 'analyzer',
  risks: 'risk',
  sizers: 'sizer',
  selectors: 'selector',
}

const routeTypeToLabel: Record<string, string> = {
  strategies: '策略组件',
  analyzers: '分析器',
  risks: '风控组件',
  sizers: '仓位组件',
  selectors: '选股器',
}

const currentType = computed(() => {
  const t = route.params.type as string
  return routeTypeToApiType[t] || ''
})

const title = computed(() => {
  const t = route.params.type as string
  return routeTypeToLabel[t] || '组件列表'
})

const basePath = computed(() => {
  const t = route.params.type as string
  return `/components/${t}`
})

const loading = ref(false)
const files = ref<any[]>([])
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const search = searchText.value.toLowerCase()
  return files.value.filter(f => f.name.toLowerCase().includes(search))
})

function getDetailUrl(record: any): string {
  return `${basePath.value}/${record.uuid}`
}

function formatDate(timestamp: string): string {
  if (!timestamp) return '-'
  return new Date(timestamp).toLocaleString('zh-CN')
}

async function loadFiles() {
  if (!currentType.value) return
  loading.value = true
  try {
    const res: any = await componentsApi.list(currentType.value)
    files.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (error: any) {
    console.error('加载失败:', error)
    files.value = []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  newFileName.value = ''
  createModalVisible.value = true
}

async function handleCreateConfirm() {
  if (!newFileName.value.trim()) return
  createModalVisible.value = false

  try {
    await componentsApi.create({
      name: newFileName.value.trim(),
      component_type: currentType.value,
      code: `# ${newFileName.value.trim()}\n# TODO: implement\n`,
    })
    await loadFiles()
  } catch (error: any) {
    console.error('创建失败:', error)
  }
}

async function handleDelete(record: any) {
  if (!confirm(`确定删除 ${record.name}？`)) return

  try {
    await componentsApi.delete(record.uuid)
    await loadFiles()
  } catch (error: any) {
    console.error('删除失败:', error)
  }
}

watch(() => route.params.type, () => {
  loadFiles()
}, { immediate: true })
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content, .modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: 90vh;
}


.table-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  overflow: hidden;
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
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
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
</style>
