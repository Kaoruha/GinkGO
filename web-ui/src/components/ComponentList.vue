<template>
  <div class="component-list">
    <div class="page-header">
      <div class="page-title">{{ title }}</div>
      <a-space>
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索文件名"
          style="width: 200px"
          @search="handleSearch"
          allow-clear
        />
        <a-button type="primary" @click="handleCreate">
          <template #icon><PlusOutlined /></template>
          新建
        </a-button>
      </a-space>
    </div>

    <div class="content-layout">
      <div class="file-list-panel">
        <a-table
          :columns="columns"
          :data-source="filteredFiles"
          :loading="loading"
          :pagination="{ pageSize: 20 }"
          row-key="uuid"
          size="small"
          :custom-row="(record: FileItem) => ({
            onClick: () => handleSelectFile(record),
            style: { cursor: 'pointer' }
          })"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <div class="file-name" :class="{ active: selectedFile?.uuid === record.uuid }">
                {{ record.name }}
              </div>
            </template>
            <template v-if="column.key === 'created_at'">
              {{ formatDate(record.created_at) }}
            </template>
            <template v-if="column.key === 'actions'">
              <a-popconfirm
                title="确定删除此文件？"
                @confirm="handleDelete(record)"
              >
                <a-button type="link" danger size="small" @click.stop>
                  删除
                </a-button>
              </a-popconfirm>
            </template>
          </template>
        </a-table>
      </div>

      <div class="editor-panel">
        <div v-if="selectedFile || isCreating" class="editor-wrapper">
          <CodeEditor
            :file-id="selectedFile?.uuid || ''"
            :file-name="selectedFile?.name || newFileName"
            :file-type="fileType"
            :content="fileContent"
            @saved="handleSaved"
          />
        </div>
        <div v-else class="empty-state">
          <FileOutlined style="font-size: 48px; color: #d9d9d9" />
          <p>选择文件进行编辑，或点击"新建"创建新文件</p>
        </div>
      </div>
    </div>

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
import { message } from 'ant-design-vue'
import { PlusOutlined, FileOutlined } from '@ant-design/icons-vue'
import CodeEditor from './CodeEditor.vue'
import { fileApi, type FileItem } from '@/api/modules/file'

interface Props {
  title: string
  fileType: number
}

const props = defineProps<Props>()

const loading = ref(false)
const files = ref<FileItem[]>([])
const selectedFile = ref<FileItem | null>(null)
const fileContent = ref('')
const searchText = ref('')
const createModalVisible = ref(false)
const newFileName = ref('')
const isCreating = ref(false)

const columns = [
  { title: '文件名', key: 'name', dataIndex: 'name' },
  { title: '创建时间', key: 'created_at', dataIndex: 'created_at', width: 180 },
  { title: '操作', key: 'actions', width: 80 }
]

const filteredFiles = computed(() => {
  if (!searchText.value) return files.value
  const search = searchText.value.toLowerCase()
  return files.value.filter(f => f.name.toLowerCase().includes(search))
})

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

async function loadFiles() {
  loading.value = true
  try {
    // 传递 fileType 到 API 进行服务端过滤
    const data = await fileApi.list('', 0, 500, props.fileType)
    files.value = data
  } catch (error: any) {
    message.error(error.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function handleSelectFile(file: FileItem) {
  if (selectedFile.value?.uuid === file.uuid) return

  selectedFile.value = file
  isCreating.value = false
  newFileName.value = ''

  try {
    const fullFile = await fileApi.get(file.uuid)
    // 解码 data 字段（base64 或直接 bytes）
    let content = ''
    if (fullFile.data) {
      if (typeof fullFile.data === 'string') {
        content = fullFile.data
      } else if (fullFile.data instanceof Uint8Array) {
        content = new TextDecoder().decode(fullFile.data)
      }
    }
    fileContent.value = content
  } catch (error: any) {
    message.error('加载文件内容失败')
    fileContent.value = ''
  }
}

function handleCreate() {
  isCreating.value = true
  selectedFile.value = null
  fileContent.value = getTemplateContent()
  createModalVisible.value = true
  newFileName.value = ''
}

function handleCreateConfirm() {
  if (!newFileName.value.trim()) {
    message.error('请输入文件名')
    return
  }
  createModalVisible.value = false
  fileContent.value = getTemplateContent(newFileName.value)
}

function getTemplateContent(name: string = 'NewComponent'): string {
  const className = name.replace('.py', '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).replace(/ /g, '')
  switch (props.fileType) {
    case 6: // STRATEGY
      return `# -*- coding: utf-8 -*-
from ginkgo.core.strategies.base_strategy import BaseStrategy
from ginkgo.core.signals.signal import Signal
from ginkgo.enums import DIRECTION_TYPES
from typing import Dict, List
from ginkgo.core.events.event_base import EventBase


class ${className}(BaseStrategy):
    """
    自定义策略模板
    """

    def __init__(self, name: str = "${className}"):
        super().__init__(name)

    def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        策略核心计算逻辑

        Args:
            portfolio_info: 投资组合信息
            event: 事件对象（通常是 EventPriceUpdate）

        Returns:
            信号列表
        """
        signals = []

        # TODO: 实现你的策略逻辑
        # 示例：获取当前价格
        # code = event.code
        # price = event.price
        # if self.should_buy(price):
        #     signals.append(Signal(code=code, direction=DIRECTION_TYPES.LONG))

        return signals
`
    case 3: // RISKMANAGER
      return `# -*- coding: utf-8 -*-
from ginkgo.core.risk.base_risk import BaseRiskManagement
from ginkgo.core.signals.signal import Signal
from ginkgo.core.orders.order import Order
from ginkgo.enums import DIRECTION_TYPES
from typing import Dict, List
from ginkgo.core.events.event_base import EventBase


class ${className}(BaseRiskManagement):
    """
    自定义风控模板
    """

    def __init__(self, name: str = "${className}"):
        super().__init__(name)

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查（被动拦截）

        Args:
            portfolio_info: 投资组合信息
            order: 待执行订单

        Returns:
            修改后的订单
        """
        # TODO: 实现风控逻辑
        return order

    def generate_signals(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:
        """
        主动风控信号生成

        Args:
            portfolio_info: 投资组合信息
            event: 事件对象

        Returns:
            风控信号列表（如止损信号）
        """
        signals = []

        # TODO: 实现主动风控逻辑
        # if self.should_stop_loss(portfolio_info, event):
        #     signals.append(Signal(direction=DIRECTION_TYPES.SHORT, reason="Stop Loss"))

        return signals
`
    default:
      return `# -*- coding: utf-8 -*-
# ${name}

# TODO: 实现你的代码
`
  }
}

async function handleDelete(file: FileItem) {
  try {
    const result = await fileApi.delete(file.uuid)
    if (result.status === 'success') {
      message.success('删除成功')
      if (selectedFile.value?.uuid === file.uuid) {
        selectedFile.value = null
        fileContent.value = ''
      }
      await loadFiles()
    } else {
      message.error('删除失败')
    }
  } catch (error: any) {
    message.error(error.message || '删除失败')
  }
}

function handleSaved(file: { uuid: string; name: string }) {
  if (isCreating.value) {
    isCreating.value = false
    loadFiles().then(() => {
      // 选中新创建的文件
      const newFile = files.value.find(f => f.uuid === file.uuid)
      if (newFile) {
        selectedFile.value = newFile
      }
    })
  }
}

function handleSearch() {
  // 搜索由 computed 属性处理
}

// 监听 fileType 变化重新加载
watch(() => props.fileType, () => {
  selectedFile.value = null
  fileContent.value = ''
  loadFiles()
}, { immediate: true })

onMounted(() => {
  loadFiles()
})
</script>

<style lang="less" scoped>
.component-list {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
}

.content-layout {
  flex: 1;
  display: flex;
  gap: 16px;
  overflow: hidden;
}

.file-list-panel {
  width: 400px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 8px;
  overflow: auto;

  :deep(.ant-table) {
    font-size: 13px;
  }

  .file-name {
    &.active {
      color: #1890ff;
      font-weight: 500;
    }
  }
}

.editor-panel {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.editor-wrapper {
  flex: 1;
  padding: 16px;
  overflow: hidden;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;

  p {
    margin-top: 16px;
  }
}
</style>
