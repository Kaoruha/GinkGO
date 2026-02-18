<template>
  <div class="component-list-page">
    <div class="page-header">
      <div class="page-title">{{ title }}</div>
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索文件名"
          style="width: 240px"
          allow-clear
        />
        <a-button type="primary" @click="handleCreate">
          <template #icon><PlusOutlined /></template>
          新建
        </a-button>
      </a-space>
    </div>

    <a-table
      :columns="columns"
      :data-source="filteredFiles"
      :loading="loading"
      :pagination="{ pageSize: 20, showSizeChanger: true, showQuickJumper: true }"
      row-key="uuid"
      size="middle"
      class="file-table"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'name'">
          <router-link :to="getDetailUrl(record)" class="file-link">
            {{ record.name }}
          </router-link>
        </template>
        <template v-if="column.key === 'type'">
          <a-tag :color="getTypeColor(record.type)">{{ getTypeName(record.type) }}</a-tag>
        </template>
        <template v-if="column.key === 'update_at'">
          {{ formatDate(record.update_at || record.created_at) }}
        </template>
        <template v-if="column.key === 'actions'">
          <a-space>
            <router-link :to="getDetailUrl(record)">
              <a-button type="link" size="small">编辑</a-button>
            </router-link>
            <a-popconfirm
              title="确定删除此文件？"
              @confirm="handleDelete(record)"
            >
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 新建文件对话框 -->
    <a-modal
      v-model:open="createModalVisible"
      title="新建文件"
      @ok="handleCreateConfirm"
      @cancel="createModalVisible = false"
    >
      <a-form :label-col="{ span: 6 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="文件名" required>
          <a-input v-model:value="newFileName" placeholder="例如: my_strategy.py" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { fileApi, type FileItem } from '@/api/modules/file'

interface Props {
  title: string
  fileType: number
  basePath: string  // 如 '/components/strategies'
}

const props = defineProps<Props>()
const router = useRouter()

const loading = ref(false)
const files = ref<FileItem[]>([])
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')

const columns = [
  { title: '文件名', key: 'name', dataIndex: 'name', width: 250 },
  { title: '更新时间', key: 'update_at', dataIndex: 'update_at', width: 180 },
  { title: '操作', key: 'actions', width: 150 },
]

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const search = searchText.value.toLowerCase()
  return files.value.filter(f => f.name.toLowerCase().includes(search))
})

const typeNames: Record<number, string> = {
  1: '分析器', 3: '风控', 4: '选股器', 5: '仓位', 6: '策略', 8: '处理器'
}

const typeColors: Record<number, string> = {
  1: 'blue', 3: 'red', 4: 'green', 5: 'orange', 6: 'purple', 8: 'cyan'
}

function getTypeName(type: number): string {
  return typeNames[type] || '未知'
}

function getTypeColor(type: number): string {
  return typeColors[type] || 'default'
}

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

function getDetailUrl(record: FileItem): string {
  return `${props.basePath}/${record.uuid}`
}

async function loadFiles() {
  loading.value = true
  try {
    const data = await fileApi.list('', 0, 500, props.fileType)
    files.value = data
  } catch (error: any) {
    message.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function handleCreate() {
  newFileName.value = ''
  createModalVisible.value = true
}

async function handleCreateConfirm() {
  if (!newFileName.value.trim()) {
    message.error('请输入文件名')
    return
  }
  createModalVisible.value = false

  try {
    const result = await fileApi.create(newFileName.value.trim(), props.fileType, '')
    if (result.status === 'success') {
      message.success('创建成功')
      router.push(`${props.basePath}/${result.uuid}`)
    } else {
      message.error(result.name || '创建失败')
    }
  } catch (error: any) {
    message.error(error.message || '创建失败')
  }
}

async function handleDelete(file: FileItem) {
  try {
    const result = await fileApi.delete(file.uuid)
    if (result.status === 'success') {
      message.success('删除成功')
      await loadFiles()
    } else {
      message.error('删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

watch(() => props.fileType, () => {
  loadFiles()
}, { immediate: true })

onMounted(() => {
  loadFiles()
})
</script>

<style lang="less" scoped>
.component-list-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}

.file-table {
  background: #fff;
  border-radius: 8px;
}

.file-link {
  color: #1890ff;
  font-weight: 500;

  &:hover {
    text-decoration: underline;
  }
}
</style>
