<template>
  <div class="code-editor">
    <div class="editor-toolbar">
      <a-input
        v-model:value="localFileName"
        placeholder="文件名"
        style="width: 200px"
        :disabled="!isNewFile"
      />
      <a-space>
        <a-button type="primary" @click="handleSave" :loading="saving">
          <template #icon><SaveOutlined /></template>
          保存
        </a-button>
        <a-button @click="handleReset" :disabled="!hasChanges">
          <template #icon><ReloadOutlined /></template>
          重置
        </a-button>
      </a-space>
    </div>
    <div class="editor-container">
      <textarea
        v-model="localContent"
        class="code-textarea"
        spellcheck="false"
        @input="markChanged"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import { SaveOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { fileApi } from '@/api/modules/file'

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
    message.error('请输入文件名')
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
        message.success('文件创建成功')
        emit('saved', { uuid: result.uuid, name: result.name })
        originalContent.value = localContent.value
        hasChanges.value = false
      } else {
        message.error('创建失败')
      }
    } else {
      // 更新现有文件
      const result = await fileApi.update(props.fileId, localContent.value)
      if (result.status === 'success') {
        message.success('保存成功')
        emit('saved', { uuid: props.fileId, name: localFileName.value })
        originalContent.value = localContent.value
        hasChanges.value = false
      } else {
        message.error('保存失败')
      }
    }
  } catch (error: any) {
    message.error(error.message || '操作失败')
  } finally {
    saving.value = false
  }
}

function handleReset() {
  localContent.value = originalContent.value
  hasChanges.value = false
}
</script>

<style lang="less" scoped>
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
  border-bottom: 1px solid #f0f0f0;
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
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  resize: none;
  outline: none;
  background: #fafafa;
  color: #333;

  &:focus {
    border-color: #1890ff;
    box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.2);
  }
}
</style>
