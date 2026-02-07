<template>
  <div class="space-y-6">
    <!-- 页面标题 -->
    <h1 class="text-title">
      API接口设置
    </h1>

    <!-- API文档链接 -->
    <div class="card">
      <h2 class="text-subtitle mb-4">
        API文档
      </h2>
      <a-space size="large">
        <a-button
          type="primary"
          @click="openDocs"
        >
          <template #icon>
            <BookOutlined />
          </template>
          Swagger UI
        </a-button>
        <a-button @click="openRedoc">
          <template #icon>
            <FileTextOutlined />
          </template>
          ReDoc
        </a-button>
        <a-button @click="downloadOpenApi">
          <template #icon>
            <DownloadOutlined />
          </template>
          OpenAPI Spec
        </a-button>
      </a-space>
    </div>

    <!-- API密钥管理 -->
    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-subtitle">
          API密钥
        </h2>
        <a-button
          type="primary"
          @click="showCreateKeyModal = true"
        >
          创建新密钥
        </a-button>
      </div>

      <a-table
        :columns="keyColumns"
        :data-source="apiKeys"
        :loading="loading"
        :pagination="false"
        row-key="keyId"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'key'">
            <a-space>
              <code class="bg-gray-100 px-2 py-1 rounded">
                {{ record.maskedKey }}
              </code>
              <a-button
                type="link"
                size="small"
                @click="copyKey(record)"
              >
                复制
              </a-button>
            </a-space>
          </template>
          <template v-if="column.key === 'status'">
            <a-switch
              :checked="record.status === 'active'"
              @change="(checked) => toggleKey(record, checked)"
            />
          </template>
          <template v-if="column.key === 'expiresAt'">
            {{ record.expiresAt ? formatDate(record.expiresAt) : '永不过期' }}
          </template>
          <template v-if="column.key === 'lastUsed'">
            {{ record.lastUsed ? formatDateTime(record.lastUsed) : '未使用' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a-button
                type="link"
                size="small"
                @click="editKey(record)"
              >
                编辑
              </a-button>
              <a-popconfirm
                title="确定要删除此密钥吗？"
                @confirm="deleteKey(record)"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                >
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <!-- API调用统计 -->
    <div class="card">
      <h2 class="text-subtitle mb-4">
        API调用统计
      </h2>
      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic
            title="今日调用次数"
            :value="stats.todayCalls"
            :value-style="{ color: '#3f8600' }"
          />
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="本月调用次数"
            :value="stats.monthCalls"
            :value-style="{ color: '#1890ff' }"
          />
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="成功率"
            :value="stats.successRate"
            suffix="%"
            :value-style="{ color: '#cf1322' }"
          />
        </a-col>
        <a-col :span="6">
          <a-statistic
            title="平均响应时间"
            :value="stats.avgResponseTime"
            suffix="ms"
          />
        </a-col>
      </a-row>
    </div>

    <!-- 速率限制配置 -->
    <div class="card">
      <h2 class="text-subtitle mb-4">
        速率限制配置
      </h2>
      <a-form
        :model="rateLimitConfig"
        layout="vertical"
        @finish="saveRateLimit"
      >
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="每分钟请求数限制">
              <a-input-number
                v-model:value="rateLimitConfig.requestsPerMinute"
                :min="10"
                :max="10000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="并发连接数限制">
              <a-input-number
                v-model:value="rateLimitConfig.maxConnections"
                :min="1"
                :max="1000"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
          >
            保存配置
          </a-button>
        </a-form-item>
      </a-form>
    </div>

    <!-- 创建密钥弹窗 -->
    <a-modal
      v-model:open="showCreateKeyModal"
      title="创建API密钥"
      width="600px"
      @ok="handleCreateKey"
      @cancel="showCreateKeyModal = false"
    >
      <a-form
        ref="keyFormRef"
        :model="keyForm"
        :rules="keyRules"
        layout="vertical"
      >
        <a-form-item
          label="名称"
          name="name"
        >
          <a-input
            v-model:value="keyForm.name"
            placeholder="请输入密钥名称"
          />
        </a-form-item>

        <a-form-item
          label="过期时间"
          name="expiresIn"
        >
          <a-select
            v-model:value="keyForm.expiresIn"
            placeholder="选择过期时间"
          >
            <a-select-option value="30d">
              30天
            </a-select-option>
            <a-select-option value="90d">
              90天
            </a-select-option>
            <a-select-option value="1y">
              1年
            </a-select-option>
            <a-select-option value="never">
              永不过期
            </a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item
          label="权限范围"
          name="scopes"
        >
          <a-checkbox-group v-model:value="keyForm.scopes">
            <a-checkbox value="portfolio">
              Portfolio管理
            </a-checkbox>
            <a-checkbox value="backtest">
              回测管理
            </a-checkbox>
            <a-checkbox value="data">
              数据查询
            </a-checkbox>
            <a-checkbox value="system">
              系统设置
            </a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-form>

      <a-alert
        v-if="newKey"
        type="success"
        message="密钥创建成功"
        class="mb-4"
      >
        <template #description>
          <p>请妥善保管您的密钥，此密钥只会显示一次：</p>
          <div class="bg-gray-100 p-2 rounded mt-2">
            <code>{{ newKey }}</code>
            <a-button
              type="link"
              size="small"
              @click="copyNewKey"
            >
              复制
            </a-button>
          </div>
        </template>
      </a-alert>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  BookOutlined,
  FileTextOutlined,
  DownloadOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'

const API_BASE = '/api'
const loading = ref(false)

// API密钥数据
const apiKeys = ref([
  {
    keyId: 'key-1',
    name: '生产环境密钥',
    maskedKey: 'ginkgo_sk_****************************',
    fullKey: 'ginkgo_sk_prod_1234567890abcdef',
    status: 'active',
    expiresAt: '2025-01-31T00:00:00Z',
    lastUsed: '2024-01-30T15:30:00Z'
  },
  {
    keyId: 'key-2',
    name: '测试环境密钥',
    maskedKey: 'ginkgo_sk_****************************',
    fullKey: 'ginkgo_sk_test_abcdef1234567890',
    status: 'active',
    expiresAt: null,
    lastUsed: null
  }
])

const keyColumns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '密钥', key: 'key' },
  { title: '状态', key: 'status' },
  { title: '过期时间', key: 'expiresAt' },
  { title: '最后使用', key: 'lastUsed' },
  { title: '操作', key: 'action', width: 150 }
]

// 统计数据
const stats = ref({
  todayCalls: 15234,
  monthCalls: 456789,
  successRate: 99.8,
  avgResponseTime: 85
})

// 速率限制配置
const rateLimitConfig = reactive({
  requestsPerMinute: 100,
  maxConnections: 50
})

// 创建密钥弹窗
const showCreateKeyModal = ref(false)
const newKey = ref('')
const keyFormRef = ref()
const keyForm = reactive({
  name: '',
  expiresIn: '90d',
  scopes: ['portfolio', 'backtest', 'data']
})

const keyRules = {
  name: [{ required: true, message: '请输入密钥名称' }],
  scopes: [{ required: true, message: '请选择权限范围' }]
}

// 打开文档
const openDocs = () => {
  window.open(`${API_BASE.replace('/api', 'http://localhost:8000')}/docs`, '_blank')
}

const openRedoc = () => {
  window.open(`${API_BASE.replace('/api', 'http://localhost:8000')}/redoc`, '_blank')
}

const downloadOpenApi = () => {
  // TODO: 下载OpenAPI规范文件
  message.info('OpenAPI规范下载功能开发中')
}

// 复制密钥
const copyKey = (record: any) => {
  navigator.clipboard.writeText(record.fullKey)
  message.success('密钥已复制到剪贴板')
}

const copyNewKey = () => {
  navigator.clipboard.writeText(newKey.value)
  message.success('密钥已复制到剪贴板')
}

// 切换密钥状态
const toggleKey = (record: any, checked: boolean) => {
  record.status = checked ? 'active' : 'disabled'
  // TODO: 调用API
  message.success(`密钥 ${record.name} 已${checked ? '启用' : '禁用'}`)
}

// 编辑密钥
const editKey = (record: any) => {
  // TODO: 实现编辑功能
  message.info(`编辑密钥 ${record.name}`)
}

// 删除密钥
const deleteKey = (record: any) => {
  // TODO: 调用API
  message.success(`密钥 ${record.name} 已删除`)
}

// 创建密钥
const handleCreateKey = async () => {
  try {
    await keyFormRef.value.validate()
    // TODO: 调用API创建密钥
    newKey.value = `ginkgo_sk_${Date.now()}_${Math.random().toString(36).substr(2, 16)}`
    message.success('密钥创建成功')
  } catch (error) {
    console.error('Validation failed:', error)
  }
}

// 保存速率限制配置
const saveRateLimit = () => {
  // TODO: 调用API
  message.success('速率限制配置已保存')
}

// 格式化日期
const formatDate = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD')
}

const formatDateTime = (date: string) => {
  return dayjs(date).format('YYYY-MM-DD HH:mm')
}

onMounted(() => {
  // 加载API密钥和统计数据
})
</script>
