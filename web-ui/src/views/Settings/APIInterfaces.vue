<template>
  <div class="space-y-6">
    <h1 class="text-title">API接口设置</h1>

    <div class="card">
      <h2 class="text-subtitle mb-4">API文档</h2>
      <a-space size="large">
        <a-button type="primary" @click="openDocs">
          <template #icon><BookOutlined /></template>
          Swagger UI
        </a-button>
        <a-button @click="openRedoc">
          <template #icon><FileTextOutlined /></template>
          ReDoc
        </a-button>
        <a-button @click="downloadOpenApi">
          <template #icon><DownloadOutlined /></template>
          OpenAPI Spec
        </a-button>
      </a-space>
    </div>

    <div class="card">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-subtitle">API密钥</h2>
        <a-button type="primary" @click="showCreateKeyModal = true">创建新密钥</a-button>
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
            <a-typography-text copyable>
              {{ record.key }}
            </a-typography-text>
          </template>
          <template v-if="column.key === 'status'">
            <a-tag :color="record.status === 'active' ? 'success' : 'default'">
              {{ record.status === 'active' ? '启用' : '禁用' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'created_at'">
            {{ record.created_at }}
          </template>
          <template v-if="column.key === 'last_used'">
            {{ record.last_used || '-' }}
          </template>
          <template v-if="column.key === 'action'">
            <a-space>
              <a @click="toggleKeyStatus(record)">
                {{ record.status === 'active' ? '禁用' : '启用' }}
              </a>
              <a-popconfirm title="确定删除?" @confirm="deleteKey(record)">
                <a class="text-red-500">删除</a>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </div>

    <div class="card">
      <h2 class="text-subtitle mb-4">API配置</h2>
      <a-form layout="vertical" style="max-width: 600px">
        <a-form-item label="API基础URL">
          <a-input v-model:value="apiConfig.baseUrl" placeholder="http://localhost:8000/api" />
        </a-form-item>
        <a-form-item label="请求超时(秒)">
          <a-input-number v-model:value="apiConfig.timeout" :min="1" :max="300" style="width: 100%" />
        </a-form-item>
        <a-form-item label="启用速率限制">
          <a-switch v-model:checked="apiConfig.rateLimitEnabled" />
        </a-form-item>
        <a-form-item v-if="apiConfig.rateLimitEnabled" label="每分钟请求数限制">
          <a-input-number v-model:value="apiConfig.rateLimit" :min="1" :max="1000" style="width: 100%" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="saveApiConfig">保存配置</a-button>
        </a-form-item>
      </a-form>
    </div>

    <a-modal v-model:open="showCreateKeyModal" title="创建API密钥" @ok="handleCreateKey">
      <a-form layout="vertical">
        <a-form-item label="密钥名称" required>
          <a-input v-model:value="newKeyName" placeholder="输入密钥名称" />
        </a-form-item>
        <a-form-item label="过期时间">
          <a-radio-group v-model:value="keyExpiry">
            <a-radio value="never">永不过期</a-radio>
            <a-radio value="30d">30天</a-radio>
            <a-radio value="90d">90天</a-radio>
            <a-radio value="1y">1年</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="权限">
          <a-checkbox-group v-model:value="keyPermissions">
            <a-checkbox value="read">读取</a-checkbox>
            <a-checkbox value="write">写入</a-checkbox>
            <a-checkbox value="admin">管理</a-checkbox>
          </a-checkbox-group>
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal v-model:open="showKeyResult" title="密钥已创建" :footer="null">
      <a-alert type="success" message="请保存您的API密钥" description="密钥只会显示一次，请妥善保管" show-icon class="mb-4" />
      <a-typography-text copyable :code="true" class="key-display">
        {{ createdKey }}
      </a-typography-text>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { BookOutlined, FileTextOutlined, DownloadOutlined } from '@ant-design/icons-vue'

const loading = ref(false)
const showCreateKeyModal = ref(false)
const showKeyResult = ref(false)
const newKeyName = ref('')
const keyExpiry = ref('never')
const keyPermissions = ref<string[]>(['read'])
const createdKey = ref('')

const apiKeys = ref<any[]>([
  { keyId: '1', name: '默认密钥', key: 'gk_live_xxxxxxxxxxxxxxxx', status: 'active', created_at: '2024-01-01', last_used: '2024-01-15' },
  { keyId: '2', name: '测试密钥', key: 'gk_test_yyyyyyyyyyyyyyyy', status: 'disabled', created_at: '2024-01-10', last_used: '-' },
])

const apiConfig = reactive({
  baseUrl: 'http://localhost:8000/api',
  timeout: 30,
  rateLimitEnabled: true,
  rateLimit: 100,
})

const keyColumns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '密钥', dataIndex: 'key', key: 'key' },
  { title: '状态', dataIndex: 'status', key: 'status', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '最后使用', dataIndex: 'last_used', key: 'last_used' },
  { title: '操作', key: 'action', width: 150 },
]

const openDocs = () => {
  window.open('/docs', '_blank')
}

const openRedoc = () => {
  window.open('/redoc', '_blank')
}

const downloadOpenApi = () => {
  message.info('正在下载 OpenAPI 规范文件...')
}

const toggleKeyStatus = (record: any) => {
  record.status = record.status === 'active' ? 'disabled' : 'active'
  message.success(`密钥已${record.status === 'active' ? '启用' : '禁用'}`)
}

const deleteKey = (record: any) => {
  apiKeys.value = apiKeys.value.filter(k => k.keyId !== record.keyId)
  message.success('密钥已删除')
}

const handleCreateKey = () => {
  if (!newKeyName.value) {
    message.warning('请输入密钥名称')
    return
  }

  const newKey = `gk_live_${Math.random().toString(36).substring(2, 18)}`
  apiKeys.value.push({
    keyId: Date.now().toString(),
    name: newKeyName.value,
    key: newKey,
    status: 'active',
    created_at: new Date().toISOString().split('T')[0],
    last_used: '-',
  })

  createdKey.value = newKey
  showCreateKeyModal.value = false
  showKeyResult.value = true
  newKeyName.value = ''
  message.success('API密钥创建成功')
}

const saveApiConfig = () => {
  message.success('API配置已保存')
}

onMounted(() => {
  // 加载数据
})
</script>

<style scoped>
.space-y-6 > * + * {
  margin-top: 24px;
}
.card {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
}
.text-title {
  font-size: 24px;
  font-weight: 600;
}
.text-subtitle {
  font-size: 18px;
  font-weight: 500;
}
.mb-4 {
  margin-bottom: 16px;
}
.text-red-500 {
  color: #f5222d;
}
.key-display {
  display: block;
  padding: 16px;
  background: #f5f5f5;
  border-radius: 8px;
  font-size: 14px;
  word-break: break-all;
}
</style>
