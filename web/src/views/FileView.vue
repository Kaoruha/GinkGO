<template>
  <div class="flex h-screen" @contextmenu="preventDefault">
    <!-- 左边部分，固定宽度 -->
    <div class="w-[320px] bg-gray-200 px-2 py-2 select-none">
      <FileList v-model="file_selected"></FileList>
    </div>
    <!-- 右边部分，撑满剩余空间 -->
    <div class="flex-grow pl-2 pt-2 overflow-y-auto">
      <EditorView v-model="file_selected"></EditorView>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import FileList from '../components/FileList.vue'
import EditorView from '../views/EditorView.vue'

const file_selected = ref('')

function preventDefault(event) {
  event.preventDefault()
}
</script>
