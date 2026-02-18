<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">系统状态</div>
      <div class="page-actions">
        <a-switch v-model:checked="autoRefresh" @change="toggleAutoRefresh" />
        <span style="margin-left: 8px">自动刷新</span>
        <a-button style="margin-left: 16px" @click="fetchStatus">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </div>
    </div>

    <!-- 系统概览 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card>
          <a-statistic title="服务状态" :value="systemStatus.status === 'running' ? '运行中' : '异常'">
            <template #prefix>
              <CheckCircleOutlined v-if="systemStatus.status === 'running'" style="color: #52c41a" />
              <CloseCircleOutlined v-else style="color: #ff4d4f" />
            </template>
          </a-statistic>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="版本" :value="systemStatus.version" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="运行时间" :value="systemStatus.uptime" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card>
          <a-statistic title="调试模式" :value="systemStatus.debug_mode ? '开启' : '关闭'">
            <template #suffix>
              <a-tag :color="systemStatus.debug_mode ? 'orange' : 'green'">
                {{ systemStatus.debug_mode ? 'DEBUG' : 'PROD' }}
              </a-tag>
            </template>
          </a-statistic>
        </a-card>
      </a-col>
    </a-row>

    <!-- 模块状态 -->
    <a-card title="模块状态" style="margin-bottom: 16px">
      <a-table
        :columns="moduleColumns"
        :dataSource="moduleList"
        :rowKey="(record: ModuleInfo) => record.name"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status ? 'green' : 'red'">
              {{ record.status ? '正常' : '异常' }}
            </a-tag>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Worker 状态 -->
    <a-card title="Worker 状态" :loading="workerLoading">
      <a-table
        :columns="workerColumns"
        :dataSource="workers"
        :rowKey="(record: WorkerInfo) => record.id"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'running' ? 'green' : 'default'">
              {{ record.status === 'running' ? '运行中' : '已停止' }}
            </a-tag>
          </template>
        </template>
      </a-table>
      <a-empty v-if="workers.length === 0" description="暂无 Worker" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons-vue'
import request from '@/api/request'

interface ModuleInfo {
  name: string
  status: boolean
}

interface WorkerInfo {
  id: string
  status: string
  task_count?: number
  last_heartbeat?: string
}

interface SystemStatusResponse {
  status: string
  version: string
  uptime: string
  debug_mode: boolean
  modules: Record<string, boolean>
}

const autoRefresh = ref(false)
const workerLoading = ref(false)

const systemStatus = reactive({
  status: 'unknown',
  version: '-',
  uptime: '-',
  debug_mode: false,
})

const moduleList = ref<ModuleInfo[]>([])
const workers = ref<WorkerInfo[]>([])

let refreshInterval: ReturnType<typeof setInterval> | null = null

const moduleColumns = [
  { title: '模块名称', dataIndex: 'name', width: 200 },
  { title: '状态', key: 'status', width: 100 },
]

const workerColumns = [
  { title: 'Worker ID', dataIndex: 'id', width: 200 },
  { title: '状态', key: 'status', width: 100 },
  { title: '任务数', dataIndex: 'task_count', width: 100 },
  { title: '最后心跳', dataIndex: 'last_heartbeat', width: 180 },
]

const fetchStatus = async () => {
  try {
    const response = await request.get('/api/v1/system/status')
    const data: SystemStatusResponse = response.data

    systemStatus.status = data.status
    systemStatus.version = data.version
    systemStatus.uptime = data.uptime
    systemStatus.debug_mode = data.debug_mode

    // 转换模块状态
    if (data.modules) {
      moduleList.value = Object.entries(data.modules).map(([name, status]) => ({
        name,
        status,
      }))
    }
  } catch (e: any) {
    message.error('获取系统状态失败')
    console.error(e)
  }
}

const fetchWorkers = async () => {
  workerLoading.value = true
  try {
    const response = await request.get('/api/v1/system/workers')
    workers.value = response.data?.data || []
  } catch (e: any) {
    console.error('获取 Worker 状态失败:', e)
    workers.value = []
  } finally {
    workerLoading.value = false
  }
}

const toggleAutoRefresh = (checked: boolean) => {
  if (checked) {
    refreshInterval = setInterval(() => {
      fetchStatus()
      fetchWorkers()
    }, 5000)
  } else {
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }
}

onMounted(() => {
  fetchStatus()
  fetchWorkers()
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.page-container {
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
</style>
