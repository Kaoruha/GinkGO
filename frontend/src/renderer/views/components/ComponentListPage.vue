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
    :context-menu="rowMenu"
    @update:search-value="searchText = $event"
    @create="handleCreate"
  >
    <template #name="{ record }">
      <router-link
        :to="getDetailUrl(record)"
        class="file-link"
      >
        {{ record.name }}
      </router-link>
    </template>
  </ListPage>

  <!-- 新建文件对话框 -->
  <FormModal
    v-model:open="createModalVisible"
    title="新建文件"
    :loading="saving"
    :disabled="!newFileName.trim()"
    loading-text="创建中..."
    @submit="handleCreateConfirm"
  >
    <div class="form-group">
      <label class="form-label">文件名</label>
      <input
        v-model="newFileName"
        type="text"
        placeholder="例如: my_strategy.py"
        class="form-input"
      >
    </div>
  </FormModal>
  <ConfirmDialog
    v-model:open="confirmOpen"
    title="确认删除"
    :description="confirmDesc"
    danger
    confirm-text="删除"
    @confirm="onConfirm"
  />
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ListPage from '@/components/common/ListPage.vue'
import { componentsApi } from '@/api/modules/components'
import { message } from '@/utils/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import FormModal from '@/components/common/FormModal.vue'
import type { MenuItem } from '@/composables/useContextMenu'
import { useAsyncAction } from '@/composables'

const route = useRoute()
const router = useRouter()

/** 行右键菜单:编辑/删除(替代操作列) */
const rowMenu = (record: any): MenuItem[] => [
  { label: '编辑', action: () => router.push(getDetailUrl(record)) },
  { divider: true },
  { label: '删除', danger: true, action: () => handleDelete(record) },
]

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
  // 不设描述列:后端对 src 组件回填恒定样板文案("Strategy component"),全列零信息量;
  // 描述在详情页仍可查
  { title: '文件名', dataIndex: 'name' },
  { title: '持有组合', dataIndex: 'portfolio_count', sortable: true, num: true },
  { title: '更新时间', dataIndex: 'updated_at' },
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
    files.value = Array.isArray(res) ? res : (res?.items ?? [])
  } catch (e: any) {
    files.value = []
    message.error('加载失败: ' + (e?.message || e))
  } finally {
    loading.value = false
  }
}

function handleCreateConfirm() {
  if (!newFileName.value.trim()) return
  runCreate()
}

const { running: saving, run: runCreate } = useAsyncAction(async () => {
  await componentsApi.create({
    name: newFileName.value.trim(),
    component_type: currentType.value,
    code: `# ${newFileName.value.trim()}\n# TODO: implement\n`,
  })
  createModalVisible.value = false
  await loadFiles()
}, {
  success: '创建成功',
})

const confirmOpen = ref(false)
const confirmDesc = ref('')
const confirmAction = ref<(() => Promise<void> | void) | null>(null)
const onConfirm = async () => {
  confirmOpen.value = false
  const fn = confirmAction.value
  confirmAction.value = null
  await fn?.()
}

function handleDelete(record: any) {
  confirmDesc.value = `确定删除 ${record.name}？`
  confirmAction.value = async () => {
    try {
      await componentsApi.delete(record.uuid)
      message.success('已删除')
      await loadFiles()
    } catch (e: any) {
      message.error('删除失败: ' + (e?.message || e))
    }
  }
  confirmOpen.value = true
}

watch(() => route.params.type, () => loadFiles(), { immediate: true })
</script>

<style scoped>
.file-link {
  color: hsl(var(--primary));
  font-weight: 500;
  text-decoration: none;
}
.file-link:hover { text-decoration: underline; }
</style>
