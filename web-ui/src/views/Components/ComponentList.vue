<template>
  <div class="space-y-6 p-6">
    <!-- 数据统计卡片 -->
    <a-row :gutter="16">
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="策略组件"
            :value="componentStats.strategies"
            :value-style="{ color: '#1890ff' }"
          >
            <template #prefix>
              <RocketOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="分析器"
            :value="componentStats.analyzers"
            :value-style="{ color: '#52c41a' }"
          >
            <template #prefix>
            <BarChartOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="风控组件"
            :value="componentStats.risk"
            :value-style="{ color: '#faad14' }"
          >
            <template #prefix>
              <SafetyOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic
            title="其他组件"
            :value="componentStats.others"
            :value-style="{ color: '#722ed1' }"
          >
            <template #prefix>
              <AppstoreOutlined />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 过滤器 -->
    <a-card class="mb-4">
      <a-row :gutter="16" align="middle">
        <a-col :span="8">
          <a-select
            v-model:value="filterType"
            placeholder="组件类型"
            style="width: 150px"
            allowClear
            @change="loadComponents"
          >
            <a-select-option value="">全部类型</a-select-option>
            <a-select-option value="strategy">策略</a-select-option>
            <a-select-option value="analyzer">分析器</a-select-option>
            <a-select-option value="risk">风控</a-select-option>
            <a-select-option value="sizer">仓位管理</a-select-option>
            <a-select-option value="selector">选择器</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="8">
          <a-input-search
            v-model:value="searchText"
            placeholder="搜索组件名称"
            @search="loadComponents"
          />
        </a-col>
      </a-row>
    </a-card>

    <!-- 组件列表 -->
    <a-card>
      <a-table
        :columns="columns"
        :data-source="components"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: 890 }"
        row-key="uuid"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'component_type'">
            <a-tag :color="getComponentTypeColor(record.component_type)">
              {{ getComponentTypeLabel(record.component_type) }}
            </a-tag>
          </template>
          <template v-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-if="column.key === 'updated_at'">
            {{ record.updated_at ? formatRelativeTime(record.updated_at) : '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space :size="8">
              <a-button type="link" size="small" @click="viewComponent(record)">详情</a-button>
              <a-button type="link" size="small" @click="openEditor(record)">
                <template #icon><EditOutlined /></template>
                编辑
              </a-button>
              <a-popconfirm
                title="确定要删除此组件吗？"
                @confirm="deleteComponent(record)"
              >
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 组件详情弹窗 -->
    <a-modal
      v-model:open="showDetailModal"
      title="组件详情"
      width="900px"
      :footer="null"
    >
      <a-descriptions v-if="currentComponent" :column="2" bordered>
        <a-descriptions-item label="组件名称">
          {{ currentComponent.name }}
        </a-descriptions-item>
        <a-descriptions-item label="组件类型">
          <a-tag :color="getComponentTypeColor(currentComponent.component_type)">
            {{ getComponentTypeLabel(currentComponent.component_type) }}
          </a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="创建时间" :span="2">
          {{ formatDateTime(currentComponent.created_at) }}
        </a-descriptions-item>
        <a-descriptions-item label="更新时间" :span="2">
          {{ currentComponent.updated_at ? formatDateTime(currentComponent.updated_at) : '-' }}
        </a-descriptions-item>
        <a-descriptions-item label="代码" :span="2">
          <div v-if="currentComponent.code" class="bg-gray-900 text-gray-100 p-4 rounded">
            <pre class="text-sm whitespace-pre-wrap">{{ currentComponent.code }}</pre>
          </div>
          <a-empty v-else description="无代码" />
        </a-descriptions-item>
      </a-descriptions>
    </a-modal>

    <!-- 创建组件弹窗 -->
    <a-modal
      v-model:open="showCreateModal"
      title="新建组件"
      width="800px"
      @ok="handleCreateComponent"
      @cancel="resetCreateForm"
    >
      <a-form layout="vertical" :model="createForm">
        <a-form-item label="组件名称" required>
          <a-input v-model:value="createForm.name" placeholder="请输入组件名称" />
        </a-form-item>
        <a-form-item label="组件类型" required>
          <a-select v-model:value="createForm.component_type" placeholder="请选择组件类型">
            <a-select-option value="strategy">策略</a-select-option>
            <a-select-option value="analyzer">分析器</a-select-option>
            <a-select-option value="risk">风控</a-select-option>
            <a-select-option value="sizer">仓位管理</a-select-option>
            <a-select-option value="selector">选择器</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="createForm.description" :rows="3" placeholder="请输入组件描述" />
        </a-form-item>
        <a-form-item label="代码" required>
          <a-textarea
            v-model:value="createForm.code"
            :rows="15"
            placeholder="请输入组件代码"
            style="font-family: monospace"
          />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑组件弹窗 -->
    <a-modal
      v-model:open="showEditModal"
      title="编辑组件"
      width="800px"
      @ok="handleEditComponent"
      @cancel="resetEditForm"
    >
      <a-form layout="vertical" :model="editForm">
        <a-form-item label="组件名称" required>
          <a-input v-model:value="editForm.name" placeholder="请输入组件名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="editForm.description" :rows="3" placeholder="请输入组件描述" />
        </a-form-item>
        <a-form-item label="代码" required>
          <a-textarea
            v-model:value="editForm.code"
            :rows="15"
            placeholder="请输入组件代码"
            style="font-family: monospace"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  PlusOutlined,
  RocketOutlined,
  BarChartOutlined,
  SafetyOutlined,
  AppstoreOutlined,
  EditOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { componentsApi, type ComponentSummary, type ComponentDetail } from '@/api/modules/components'
import { useComponentList } from '@/composables/useComponentList'

// 扩展 dayjs 支持相对时间
dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const router = useRouter()

// 使用 composable 管理创建弹窗状态
const { showCreateModal, closeCreateModal } = useComponentList()

const loading = ref(false)
const searchText = ref('')
const filterType = ref('')

// 组件统计
const componentStats = reactive({
  strategies: 0,
  analyzers: 0,
  risk: 0,
  others: 0
})

// 组件列表
const components = ref<ComponentSummary[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0
})

// 表格列
const columns = [
  { title: '组件名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '类型', key: 'component_type', width: 90 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '创建时间', key: 'created_at', width: 150 },
  { title: '更新时间', key: 'updated_at', width: 150 },
  { title: '操作', key: 'action', width: 220, fixed: 'right' }
]

// 弹窗
const showEditModal = ref(false)
const showDetailModal = ref(false)
const currentComponent = ref<ComponentDetail | null>(null)
const editingComponentUuid = ref<string>('')

// 创建组件表单
const createForm = reactive({
  name: '',
  component_type: '',
  description: '',
  code: ''
})

// 编辑组件表单
const editForm = reactive({
  name: '',
  description: '',
  code: ''
})

// 获取组件类型颜色
const getComponentTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    analyzer: 'green',
    risk: 'orange',
    sizer: 'purple',
    selector: 'cyan'
  }
  return colors[type] || 'default'
}

// 获取组件类型标签
const getComponentTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    strategy: '策略',
    analyzer: '分析器',
    risk: '风控',
    sizer: '仓位管理',
    selector: '选择器'
  }
  return labels[type] || type
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm:ss')
}

// 格式化相对时间（如：5分钟前、3小时前、2天前）
const formatRelativeTime = (date: string) => {
  return dayjs(date).fromNow()
}

// 加载组件列表
const loadComponents = async () => {
  loading.value = true
  try {
    const params: any = {}
    if (filterType.value) {
      params.component_type = filterType.value
    }

    const data = await componentsApi.list(params)
    components.value = data

    // 更新统计
    updateStats(data)

  } catch (error: any) {
    message.error(`加载组件列表失败: ${error?.response?.data?.detail || error?.message}`)
  } finally {
    loading.value = false
  }
}

// 更新统计信息
const updateStats = (data: ComponentSummary[]) => {
  componentStats.strategies = 0
  componentStats.analyzers = 0
  componentStats.risk = 0
  componentStats.others = 0

  for (const item of data) {
    switch (item.component_type) {
      case 'strategy':
        componentStats.strategies++
        break
      case 'analyzer':
        componentStats.analyzers++
        break
      case 'risk':
        componentStats.risk++
        break
      default:
        componentStats.others++
    }
  }
}

// 表格变化
const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadComponents()
}

// 查看组件详情
const viewComponent = async (record: ComponentSummary) => {
  try {
    const detail = await componentsApi.get(record.uuid)
    currentComponent.value = detail
    showDetailModal.value = true
  } catch (error: any) {
    message.error('获取组件详情失败')
  }
}

// 编辑组件
const editComponent = async (record: ComponentSummary) => {
  try {
    const detail = await componentsApi.get(record.uuid)
    editingComponentUuid.value = record.uuid
    editForm.name = detail.name
    editForm.description = detail.description || ''
    editForm.code = detail.code || ''
    showEditModal.value = true
  } catch (error: any) {
    message.error('获取组件详情失败')
  }
}

// 打开编辑器
const openEditor = (record: ComponentSummary) => {
  router.push(`/components/${record.uuid}/edit`)
}

// 保存编辑
const handleEditComponent = async () => {
  if (!editForm.name) {
    message.warning('请输入组件名称')
    return
  }

  try {
    await componentsApi.update(editingComponentUuid.value, {
      name: editForm.name,
      code: editForm.code,
      description: editForm.description
    })
    message.success('组件更新成功')
    showEditModal.value = false
    loadComponents()
  } catch (error: any) {
    message.error(`更新失败: ${error?.response?.data?.detail || error?.message}`)
  }
}

// 重置编辑表单
const resetEditForm = () => {
  editForm.name = ''
  editForm.description = ''
  editForm.code = ''
  editingComponentUuid.value = ''
}

// 删除组件
const deleteComponent = async (record: ComponentSummary) => {
  try {
    await componentsApi.delete(record.uuid)
    message.success('组件已删除')
    loadComponents()
  } catch (error: any) {
    message.error(`删除失败: ${error?.response?.data?.detail || error?.message}`)
  }
}

// 创建组件
const handleCreateComponent = async () => {
  if (!createForm.name || !createForm.component_type || !createForm.code) {
    message.warning('请填写必填项')
    return
  }

  try {
    await componentsApi.create({
      name: createForm.name,
      component_type: createForm.component_type,
      code: createForm.code,
      description: createForm.description
    })
    message.success('组件创建成功')
    closeCreateModal()
    resetCreateForm()
    loadComponents()
  } catch (error: any) {
    message.error(`创建失败: ${error?.response?.data?.detail || error?.message}`)
  }
}

// 重置创建表单
const resetCreateForm = () => {
  createForm.name = ''
  createForm.component_type = ''
  createForm.description = ''
  createForm.code = ''
}

onMounted(() => {
  loadComponents()
})
</script>
