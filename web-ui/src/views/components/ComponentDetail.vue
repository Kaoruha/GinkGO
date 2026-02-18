<template>
  <div class="component-detail">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <a-button @click="goBack" class="back-btn">
          <template #icon><ArrowLeftOutlined /></template>
          返回列表
        </a-button>
        <a-divider type="vertical" />
        <span class="file-info">
          <FileOutlined style="margin-right: 6px" />
          <span class="file-name">{{ fileName }}</span>
          <a-tag v-if="fileTypeLabel" :color="fileTypeColor" style="margin-left: 8px">{{ fileTypeLabel }}</a-tag>
        </span>
        <span v-if="hasUnsavedChanges" class="unsaved-badge">未保存</span>
      </div>
      <div class="toolbar-right">
        <a-button @click="handleReset" :disabled="!hasUnsavedChanges">
          <template #icon><ReloadOutlined /></template>
          重置
        </a-button>
        <a-button type="primary" @click="handleSave" :loading="saving" :disabled="!hasUnsavedChanges">
          <template #icon><SaveOutlined /></template>
          保存
        </a-button>
      </div>
    </div>

    <!-- 编辑器区域 -->
    <div class="editor-container" v-loading="loading">
      <vue-monaco-editor
        v-model:value="currentContent"
        language="python"
        :theme="editorTheme"
        :options="editorOptions"
        @change="handleContentChange"
        @mount="handleEditorMount"
      />
    </div>

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <span class="status-item">
        <span class="label">行:</span>
        <span>{{ cursorLine }}</span>
      </span>
      <span class="status-item">
        <span class="label">列:</span>
        <span>{{ cursorColumn }}</span>
      </span>
      <span class="status-item">
        <span class="label">编码:</span>
        <span>UTF-8</span>
      </span>
      <span class="status-item">
        <span class="label">语言:</span>
        <span>Python</span>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  SaveOutlined,
  ReloadOutlined,
  FileOutlined,
} from '@ant-design/icons-vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { fileApi } from '@/api/modules/file'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const saving = ref(false)
const originalContent = ref('')
const currentContent = ref('')
const cursorLine = ref(1)
const cursorColumn = ref(1)
const editor = shallowRef<any>(null)

const fileId = computed(() => route.params.id as string)

const typeNames: Record<number, string> = {
  1: '分析器', 3: '风控', 4: '选股器', 5: '仓位', 6: '策略', 8: '处理器'
}

const typeColors: Record<number, string> = {
  1: '#1890ff', 3: '#ff4d4f', 4: '#52c41a', 5: '#fa8c16', 6: '#eb2f96', 8: '#13c2c2'
}

const fileName = ref('')
const fileType = ref<number>(0)

const fileTypeLabel = computed(() => typeNames[fileType.value] || '')
const fileTypeColor = computed(() => typeColors[fileType.value] || 'default')

const hasUnsavedChanges = computed(() => {
  return currentContent.value !== originalContent.value
})

// 编辑器配置
const editorTheme = ref('vs-dark')
const editorOptions = {
  fontSize: 14,
  lineHeight: 22,
  minimap: { enabled: true },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  tabSize: 4,
  insertSpaces: true,
  wordWrap: 'on' as const,
  lineNumbers: 'on' as const,
  renderLineHighlight: 'all' as const,
  cursorBlinking: 'smooth' as const,
  smoothScrolling: true,
  folding: true,
  foldingStrategy: 'indentation' as const,
  showFoldingControls: 'always' as const,
  bracketPairColorization: { enabled: true },
  suggest: {
    showKeywords: true,
    showSnippets: true,
  },
  quickSuggestions: {
    other: true,
    comments: false,
    strings: true,
  },
}

function handleEditorMount(editorInstance: any) {
  editor.value = editorInstance

  // 监听光标位置变化
  editorInstance.onDidChangeCursorPosition((e: any) => {
    cursorLine.value = e.position.lineNumber
    cursorColumn.value = e.position.column
  })

  // 快捷键保存
  editorInstance.addCommand(
    // Ctrl+S
    editorInstance._standaloneEditor?.constructor?.KeyMod?.CtrlCmd | editorInstance._standaloneEditor?.constructor?.KeyCode?.KeyS,
    () => {
      handleSave()
    }
  )
}

function handleContentChange(value: string) {
  // 确保响应式更新
  if (value !== currentContent.value) {
    currentContent.value = value
  }
}

function getBasePath(): string {
  const path = route.path
  const parts = path.split('/')
  parts.pop()
  return parts.join('/')
}

function goBack() {
  router.push(getBasePath())
}

async function loadFile() {
  if (!fileId.value) return

  loading.value = true
  try {
    const data = await fileApi.get(fileId.value)
    fileName.value = data.name
    fileType.value = data.type

    let content = ''
    if (data.data) {
      if (typeof data.data === 'string') {
        content = data.data
      }
    }

    originalContent.value = content
    currentContent.value = content
  } catch (error: any) {
    message.error('加载文件失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!hasUnsavedChanges.value || !fileId.value) return

  saving.value = true
  try {
    const result = await fileApi.update(fileId.value, currentContent.value)
    if (result.status === 'success') {
      originalContent.value = currentContent.value
      message.success('保存成功')
    } else {
      message.error('保存失败')
    }
  } catch (error: any) {
    message.error(error.message || '保存失败')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  if (!hasUnsavedChanges.value) return
  currentContent.value = originalContent.value
}

// 键盘快捷键
function handleKeyDown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    handleSave()
  }
}

watch(fileId, () => {
  loadFile()
}, { immediate: true })

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style lang="less" scoped>
.component-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1e1e1e;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #2d2d2d;
  border-bottom: 1px solid #404040;
  flex-shrink: 0;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;

  :deep(.ant-btn) {
    color: #e0e0e0;
    border-color: #555;

    &:hover {
      color: #fff;
      border-color: #1890ff;
      background: rgba(24, 144, 255, 0.1);
    }

    &:disabled {
      color: #666;
      border-color: #444;
    }
  }

  :deep(.ant-btn-primary) {
    color: #fff;
    background: #1890ff;
    border-color: #1890ff;

    &:hover {
      background: #40a9ff;
      border-color: #40a9ff;
    }

    &:disabled {
      background: #444;
      border-color: #444;
      color: #666;
    }
  }
}

.back-btn {
  color: #e0e0e0 !important;
  border-color: #555 !important;
  background: transparent !important;

  :deep(.anticon) {
    color: #e0e0e0;
  }

  &:hover {
    color: #fff !important;
    border-color: #1890ff !important;
    background: rgba(24, 144, 255, 0.1) !important;
  }
}

.file-info {
  color: #e0e0e0;
  display: flex;
  align-items: center;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.unsaved-badge {
  margin-left: 8px;
  padding: 2px 8px;
  background: #faad14;
  color: #000;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

:deep(.ant-divider-vertical) {
  background: #555;
}

:deep(.ant-tag) {
  color: #fff;
  font-weight: 500;
  border: none;
  padding: 2px 10px;
}

.editor-container {
  flex: 1;
  overflow: hidden;
  background: #1e1e1e;

  :deep(.monaco-editor) {
    padding-top: 8px;
  }

  :deep(.overflow-guard) {
    background: #1e1e1e;
  }
}

.status-bar {
  display: flex;
  align-items: center;
  padding: 4px 16px;
  background: #007acc;
  color: #fff;
  font-size: 12px;
  flex-shrink: 0;
}

.status-item {
  margin-right: 24px;

  .label {
    opacity: 0.8;
    margin-right: 4px;
  }
}
</style>
