<template>
  <div class="component-detail">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button class="btn-back" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          返回列表
        </button>
        <div class="toolbar-divider"></div>
        <span class="file-info">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
            <polyline points="13 2 13 9 20 9"></polyline>
          </svg>
          <span class="file-name">{{ fileName }}</span>
          <span v-if="fileTypeLabel" class="tag" :style="{ background: `${fileTypeColor}20`, color: fileTypeColor, marginLeft: '8px' }">
            {{ fileTypeLabel }}
          </span>
        </span>
        <span v-if="hasUnsavedChanges" class="unsaved-badge">未保存</span>
      </div>
      <div class="toolbar-right">
        <button class="btn-secondary" :disabled="!hasUnsavedChanges" @click="handleReset">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
            <path d="M3 3v5h5"></path>
            <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
            <path d="M16 21h5v-5"></path>
          </svg>
          重置
        </button>
        <button class="btn-primary" :disabled="!hasUnsavedChanges || saving" @click="handleSave">
          <svg v-if="!saving" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          <span v-else class="loading-spinner"></span>
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

    <!-- 编辑器区域 -->
    <div class="editor-container" v-if="!loading">
      <vue-monaco-editor
        v-model:value="currentContent"
        language="python"
        :theme="editorTheme"
        :options="editorOptions"
        @change="handleContentChange"
        @mount="handleEditorMount"
      />
    </div>
    <div v-else class="editor-loading">
      <div class="spinner"></div>
      <p>加载中...</p>
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
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'

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
const fileTypeColor = computed(() => typeColors[fileType.value] || '#8c8c8c')

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
    // TODO: 调用 API 加载文件
    await new Promise(resolve => setTimeout(resolve, 500))
    fileName.value = 'example.py'
    fileType.value = 6

    const content = '# 示例文件\n# TODO: 实现策略逻辑\n'
    originalContent.value = content
    currentContent.value = content
  } catch (error: any) {
    console.error('加载文件失败:', error)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!hasUnsavedChanges.value || !fileId.value) return

  saving.value = true
  try {
    // TODO: 调用 API 保存文件
    await new Promise(resolve => setTimeout(resolve, 500))
    originalContent.value = currentContent.value
    console.log('保存成功')
  } catch (error: any) {
    console.error('保存失败:', error)
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

<style scoped>
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
}

.toolbar-divider {
  width: 1px;
  height: 20px;
  background: #555;
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #555;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #555;
  border-radius: 4px;
  color: #e0e0e0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
}

.btn-secondary:disabled {
  color: #666;
  border-color: #444;
  cursor: not-allowed;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1890ff;
  border: 1px solid #1890ff;
  border-radius: 4px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
  border-color: #40a9ff;
}

.btn-primary:disabled {
  background: #444;
  border-color: #444;
  color: #666;
  cursor: not-allowed;
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

.tag {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  border: none;
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

.editor-container {
  flex: 1;
  overflow: hidden;
  background: #1e1e1e;
}

.editor-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #1e1e1e;
  color: #8a8a9a;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.editor-loading p {
  margin-top: 16px;
}

.loading-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
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
}

.status-item .label {
  opacity: 0.8;
  margin-right: 4px;
}
</style>
