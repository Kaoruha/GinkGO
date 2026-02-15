<template>
  <div class="component-list-container">
    <div class="page-header">
      <h1 class="page-title">组件管理</h1>
      <p class="page-subtitle">管理策略、分析器、风控等组件</p>
    </div>

    <a-row :gutter="16" class="stats-row">
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="策略组件" :value="componentStats.strategies" :value-style="{ color: '#1890ff' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="分析器" :value="componentStats.analyzers" :value-style="{ color: '#52c41a' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="风控组件" :value="componentStats.risk" :value-style="{ color: '#faad14' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="其他组件" :value="componentStats.others" :value-style="{ color: '#722ed1' }" />
        </a-card>
      </a-col>
    </a-row>

    <a-card class="filter-card">
      <a-row :gutter="16" align="middle">
        <a-col :span="6">
          <a-select
            v-model:value="filterType"
            placeholder="组件类型"
            style="width: 100%"
            allow-clear
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
        <a-col :span="10" style="text-align: right">
          <a-button type="primary" @click="goToCreate">
            <PlusOutlined /> 创建组件
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <a-card class="table-card">
      <a-table
        :columns="columns"
        :data-source="components"
        :loading="loading"
        :pagination="pagination"
        :scroll="{ x: 900 }"
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
            {{ formatDate(record.created_at, 'YYYY-MM-DD') }}
          </template>
          <template v-if="column.key === 'updated_at'">
            {{ record.updated_at ? formatDate(record.updated_at, 'YYYY-MM-DD HH:mm') : '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="viewDetail(record)">查看</a>
              <a @click="editComponent(record)">编辑</a>
              <a-popconfirm title="确定删除此组件？" @confirm="deleteComponent(record)">
                <a class="danger-link">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { componentsApi } from '@/api/modules/components'
import type { ComponentSummary as Component } from '@/types/component'
import { formatDate } from '@/utils/format'

const router = useRouter()

const loading = ref(false)
const components = ref<Component[]>([])
const filterType = ref('')
const searchText = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const componentStats = reactive({
  strategies: 0,
  analyzers: 0,
  risk: 0,
  others: 0
})

const columns = [
  { title: '组件名称', dataIndex: 'name', key: 'name', width: 200 },
  { title: '类型', dataIndex: 'component_type', key: 'component_type', width: 120 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 120 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 150 },
  { title: '操作', key: 'action', width: 150, fixed: 'right' }
]

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

const loadComponents = async () => {
  loading.value = true
  try {
    const response = await componentsApi.list({
      type: filterType.value || undefined,
      search: searchText.value || undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })

    components.value = response.data?.items || []
    pagination.total = response.data?.total || 0

    // 更新统计
    updateStats()
  } catch (error: any) {
    message.error(`加载组件失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  componentStats.strategies = components.value.filter(c => c.component_type === 'strategy').length
  componentStats.analyzers = components.value.filter(c => c.component_type === 'analyzer').length
  componentStats.risk = components.value.filter(c => c.component_type === 'risk').length
  componentStats.others = components.value.filter(c =>
    !['strategy', 'analyzer', 'risk'].includes(c.component_type)
  ).length
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadComponents()
}

const goToCreate = () => {
  router.push('/components/create')
}

const viewDetail = (record: Component) => {
  router.push(`/components/${record.uuid}`)
}

const editComponent = (record: Component) => {
  router.push(`/components/${record.uuid}/edit`)
}

const deleteComponent = async (record: Component) => {
  try {
    await componentsApi.delete(record.uuid)
    message.success('删除成功')
    loadComponents()
  } catch (error: any) {
    message.error(`删除失败: ${error.message}`)
  }
}

onMounted(() => {
  loadComponents()
})
</script>

<style scoped>
.component-list-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.stats-row {
  margin-bottom: 24px;
}

.stat-card {
  border-radius: 8px;
}

.filter-card,
.table-card {
  margin-bottom: 24px;
  border-radius: 8px;
}

.danger-link {
  color: #ff4d4f;
}
</style>
