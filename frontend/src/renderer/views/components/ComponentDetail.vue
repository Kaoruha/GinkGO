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
          <span v-if="fileTypeLabel" class="tag" :class="`tag-${fileTypeColorClass}`" style="margin-left: 8px">
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

    <!-- 描述栏:列表页展示的 desc 在此编辑 -->
    <div class="desc-bar" v-if="!loading && !loadError">
      <input
        v-model="currentDesc"
        type="text"
        class="desc-input"
        placeholder="添加组件描述（列表页展示）"
        maxlength="255"
      />
    </div>

    <!-- 加载失败占位:避免空白编辑器让用户误判为空文件 -->
    <div v-if="loadError" class="editor-loading">
      <p class="load-error">{{ loadError }}</p>
      <button class="btn-back" @click="loadFile">重试</button>
      <button class="btn-back" @click="goBack">返回列表</button>
    </div>

    <!-- 编辑器区域 -->
    <div class="editor-container" v-else-if="!loading">
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
import { componentsApi } from '@/api/modules/components'
import message from '@/utils/toast'

const router = useRouter()
const route = useRoute()

const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const originalContent = ref('')
const currentContent = ref('')
const cursorLine = ref(1)
const cursorColumn = ref(1)
const editor = shallowRef<any>(null)

const fileId = computed(() => route.params.id as string)

const typeNames: Record<number, string> = {
  1: '分析器', 3: '风控', 4: '选股器', 5: '仓位', 6: '策略', 8: '处理器'
}

// 组件类型 → 全局 tag-* 色板后缀(tags.less,token 化 + .dark 自动反相)。
// 取代旧 Ant Design hex 全色板(ADR-045 去 Ant 蓝):走中心化 tag 体系,
// 主题切换由 CSS 接管,无需 JS 重染。语义就近:风控=红/策略=蓝(primary)。
const typeColorClass: Record<number, string> = {
  1: 'purple',  // 分析器
  3: 'red',     // 风控
  4: 'green',   // 选股器
  5: 'orange',  // 仓位
  6: 'blue',    // 策略
  8: 'gray',    // 处理器
}

const fileName = ref('')
const fileType = ref<number>(0)
const originalDesc = ref('')
const currentDesc = ref('')

const fileTypeLabel = computed(() => typeNames[fileType.value] || '')
const fileTypeColorClass = computed(() => typeColorClass[fileType.value] || 'gray')

const hasUnsavedChanges = computed(() => {
  return currentContent.value !== originalContent.value || currentDesc.value !== originalDesc.value
})

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
  editorInstance.onDidChangeCursorPosition((e: any) => {
    cursorLine.value = e.position.lineNumber
    cursorColumn.value = e.position.column
  })
  // Ctrl+S 统一走全局 keydown(下方 handleKeyDown),不再在 Monaco 内重复注册:
  // 双通道会同步触发两次 handleSave,无防重入时重复 PUT
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
  loadError.value = ''
  try {
    const res: any = await componentsApi.get(fileId.value)
    const data = res?.data || res
    fileName.value = data.name || ''
    fileType.value = data.file_type || 0

    const code = data.code || ''
    originalContent.value = code
    currentContent.value = code
    originalDesc.value = data.description || ''
    currentDesc.value = data.description || ''
  } catch (error: any) {
    console.error('加载文件失败:', error)
    loadError.value = error?.message || '加载文件失败，请重试'
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (!hasUnsavedChanges.value || !fileId.value || saving.value) return

  saving.value = true
  try {
    await componentsApi.update(fileId.value, {
      name: fileName.value,
      code: currentContent.value,
      description: currentDesc.value,
    })
    originalContent.value = currentContent.value
    originalDesc.value = currentDesc.value
    message.success('保存成功')
  } catch (error: any) {
    // 静默失败会让用户以为已保存(未保存 badge 亮着却无解释),必须明确报错
    console.error('保存失败:', error)
    message.error(error?.message || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  if (!hasUnsavedChanges.value) return
  currentContent.value = originalContent.value
  currentDesc.value = originalDesc.value
}

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
  background: hsl(var(--card));
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: hsl(var(--card));
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
}

.desc-bar {
  display: flex;
  padding: 8px 16px;
  background: hsl(var(--card));
  border-bottom: 1px solid hsl(var(--border));
  flex-shrink: 0;
}

.desc-input {
  width: 100%;
  padding: 6px 10px;
  font-size: 13px;
  color: hsl(var(--foreground));
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  outline: none;
  transition: border-color 0.15s;
}
.desc-input:focus {
  border-color: hsl(var(--primary));
}
.desc-input::placeholder {
  color: hsl(var(--muted-foreground));
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
  background: hsl(var(--muted-foreground));
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid hsl(var(--muted-foreground));
  border-radius: var(--radius-sm);
  color: hsl(var(--muted-foreground));
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover {
  border-color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.btn-secondary:hover:not(:disabled) {
  border-color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.file-info {
  color: hsl(var(--muted-foreground));
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.unsaved-badge {
  margin-left: 8px;
  padding: 2px 8px;
  background: hsl(var(--warning));
  color: hsl(var(--foreground));
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}

.editor-container {
  flex: 1;
  overflow: hidden;
  background: hsl(var(--card));
}

.editor-loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: hsl(var(--card));
  color: hsl(var(--muted-foreground));
}

.editor-loading p {
  margin-top: 16px;
}

.load-error {
  color: hsl(var(--error));
  font-size: 14px;
  margin: 0 0 8px;
}

.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
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
