<template>
  <ListPage
    :title="title"
    :columns="columns"
    :data-source="filteredFiles"
    :loading="loading"
    row-key="uuid"
    :searchable="true"
    :search-value="searchText"
    search-placeholder="搜索文件名"
    :creatable="true"
    create-label="新建文件"
    empty-text="暂无文件"
    empty-action-text="创建第一个文件"
    show-actions
    @update:search-value="searchText = $event"
    @create="handleCreate"
    @row-click="record => $router.push(getDetailUrl(record))"
  >
    <template #name="{ record }">
      <router-link :to="getDetailUrl(record)" class="file-link">{{ record.name }}</router-link>
    </template>
    <template #actions="{ record }">
      <router-link :to="getDetailUrl(record)" class="act-link">编辑</router-link>
      <button class="act-link danger" @click.stop="handleDelete(record)">删除</button>
    </template>
  </ListPage>

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
          <input v-model="newFileName" type="text" placeholder="例如: my_strategy.py" class="form-input" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" @click="createModalVisible = false">取消</button>
        <button class="btn-primary" @click="handleCreateConfirm">确定</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import ListPage from '@/components/common/ListPage.vue'
import { componentsApi } from '@/api/modules/components'

const route = useRoute()

const routeTypeMap: Record<string, { api: string; label: string }> = {
  strategies: { api: 'strategy', label: '策略组件' },
  analyzers: { api: 'analyzer', label: '分析器' },
  risks: { api: 'risk', label: '风控组件' },
  sizers: { api: 'sizer', label: '仓位组件' },
  selectors: { api: 'selector', label: '选股器' },
}

const currentType = computed(() => {
  const t = route.params.type as string
  return routeTypeMap[t]?.api || ''
})

const title = computed(() => {
  const t = route.params.type as string
  return routeTypeMap[t]?.label || '组件列表'
})

const basePath = computed(() => `/components/${route.params.type}`)

const columns = [
  { title: '文件名', dataIndex: 'name' },
  { title: '更新时间', dataIndex: 'update_at' },
]

const loading = ref(false)
const files = ref<any[]>([])
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const s = searchText.value.toLowerCase()
  return files.value.filter(f => f.name?.toLowerCase().includes(s))
})

function getDetailUrl(record: any) {
  return `${basePath.value}/${record.uuid}`
}

function handleCreate() {
  newFileName.value = ''
  createModalVisible.value = true
}

async function loadFiles() {
  if (!currentType.value) return
  loading.value = true
  try {
    const res: any = await componentsApi.list(currentType.value)
    files.value = Array.isArray(res) ? res : (res?.data || [])
  } catch (e) {
    files.value = []
  } finally {
    loading.value = false
  }
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
  } catch (e) {
    console.error('创建失败:', e)
  }
}

async function handleDelete(record: any) {
  if (!confirm(`确定删除 ${record.name}？`)) return
  try {
    await componentsApi.delete(record.uuid)
    await loadFiles()
  } catch (e) {
    console.error('删除失败:', e)
  }
}

watch(() => route.params.type, () => loadFiles(), { immediate: true })
</script>

<style scoped>
.file-link {
  color: #1890ff;
  font-weight: 500;
  text-decoration: none;
}
.file-link:hover { text-decoration: underline; }

.act-link {
  background: none;
  border: none;
  color: #1890ff;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  text-decoration: none;
}
.act-link:hover { color: #40a9ff; }
.act-link.danger { color: #f5222d; }
.act-link.danger:hover { color: #ff4d4f; }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  min-width: 400px;
  max-height: 90vh;
}
</style>
