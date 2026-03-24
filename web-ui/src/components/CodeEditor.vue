<template>
  <div class="code-editor">
    <div class="editor-toolbar">
      <input
        v-model="localFileName"
        type="text"
        placeholder="文件名"
        class="filename-input"
        :disabled="!isNewFile"
      />
      <div class="toolbar-actions">
        <button class="btn-primary" :disabled="saving" @click="handleSave">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          {{ saving ? '保存中...' : '保存' }}
        </button>
        <button class="btn-secondary" :disabled="!hasChanges" @click="handleReset">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          重置
        </button>
      </div>
    </div>
    <div class="editor-container">
      <textarea
        v-model="localContent"
        class="code-textarea"
        spellcheck="false"
        @input="markChanged"
      ></textarea>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 简化的API（实际项目中需要导入真实的API）
const fileApi: any = {
  create: async () => ({ status: 'success', uuid: 'new-uuid', name: 'new_file.py' }),
  update: async () => ({ status: 'success' })
}

interface Props {
  fileId?: string
  fileName?: string
  fileType: number
  content?: string
}

const props = withDefaults(defineProps<Props>(), {
  fileId: '',
  fileName: '',
  fileType: 6, // 默认 STRATEGY
  content: ''
})

const emit = defineEmits<{
  (e: 'saved', file: { uuid: string; name: string }): void
  (e: 'deleted', fileId: string): void
}>()

const localContent = ref(props.content || '')
const localFileName = ref(props.fileName || '')
const originalContent = ref(props.content || '')
const saving = ref(false)
const hasChanges = ref(false)

const isNewFile = computed(() => !props.fileId)

watch(() => props.content, (newContent) => {
  localContent.value = newContent || ''
  originalContent.value = newContent || ''
  hasChanges.value = false
})

watch(() => props.fileName, (newName) => {
  localFileName.value = newName || ''
})

function markChanged() {
  hasChanges.value = localContent.value !== originalContent.value
}

async function handleSave() {
  if (!localFileName.value.trim()) {
    showToast('请输入文件名', 'error')
    return
  }

  saving.value = true
  try {
    if (isNewFile.value) {
      // 创建新文件
      const result = await fileApi.create(
        localFileName.value.trim(),
        props.fileType,
        localContent.value
      )
      if (result.status === 'success') {
        showToast('文件创建成功')
        emit('saved', { uuid: result.uuid, name: result.name })
        originalContent.value = localContent.value
        hasChanges.value = false
      } else {
        showToast('创建失败', 'error')
      }
    } else {
      // 更新现有文件
      const result = await fileApi.update(props.fileId, localContent.value)
      if (result.status === 'success') {
        showToast('保存成功')
        emit('saved', { uuid: props.fileId, name: localFileName.value })
        originalContent.value = localContent.value
        hasChanges.value = false
      } else {
        showToast('保存失败', 'error')
      }
    }
  } catch (error: any) {
    showToast('操作失败', 'error')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  localContent.value = originalContent.value
  hasChanges.value = false
}
</script>

<style scoped>
.code-editor {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.editor-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #2a2a3e;
}

.filename-input {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  width: 200px;
}

.filename-input:focus {
  outline: none;
  border-color: #1890ff;
}

.filename-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toolbar-actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.editor-container {
  flex: 1;
  margin-top: 12px;
  overflow: hidden;
}

.code-textarea {
  width: 100%;
  height: 100%;
  font-family: 'Fira Code', 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
  line-height: 1.5;
  padding: 12px;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  resize: none;
  outline: none;
  background: #1a1a2e;
  color: #ffffff;
  box-sizing: border-box;
}

.code-textarea:focus {
  border-color: #1890ff;
}

.code-textarea::placeholder {
  color: #8a8a9a;
}
</style>
