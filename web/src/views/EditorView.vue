<template>
  <div class="w-full max-w-md px-2">
    <ConfirmDialog
      ref="save_ok_dialog"
      :title="'Save Success.'"
      :confirm_btn_text="'GOT IT'"
      :msg="'Content updated.'"
    >
    </ConfirmDialog>
    <ConfirmDialog
      ref="save_failed_dialog"
      :title="'Save not complete.'"
      :confirm_btn_text="'GOT IT'"
      :msg="'Ops something wrong with saving.'"
    >
    </ConfirmDialog>
    <button
      :disabled="!is_content_update"
      @click="save"
      class="w-[208px] h-[44px] rounded-xl absolute right-4 shadow"
      :class="{
        'bg-gray-300 text-gray-700 cursor-not-allowed opacity-50': !is_content_update,
        'bg-blue-500 hover:bg-blue-700 text-white': is_content_update
      }"
    >
      SAVE
    </button>
    <TabGroup>
      <TabList class="flex space-x-1 rounded-xl bg-blue-900/20 p-1">
        <Tab v-for="category in categories" as="template" :key="category" v-slot="{ selected }">
          <button
            @click="tab_switch"
            :class="[
              'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
              'ring-white/60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
              selected
                ? 'bg-white text-blue-700 shadow'
                : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
            ]"
          >
            {{ category }}
          </button>
        </Tab>
      </TabList>

      <TabPanels class="mt-2">
        <TabPanel>
          <CodeEditor ref="code_editor" v-model="code"></CodeEditor>
        </TabPanel>
        <TabPanel>
          <NodeEditor ref="node_editor" class="bg-blue-400"></NodeEditor>
        </TabPanel>
      </TabPanels>
    </TabGroup>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@headlessui/vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import CodeEditor from '../components/CodeEditor.vue'
import NodeEditor from '../components/NodeEditor.vue'

const save_ok_dialog = ref(null)
const save_failed_dialog = ref(null)
const code_editor = ref(null)
const node_editor = ref(null)

const file_selected = defineModel()

const is_content_update = ref(false)

const categories = ref(['Code', 'Node'])
const code = ref(null)

let raw_code = ''
let old_code = ''

function tab_switch() {
  console.log('Tab Switch.')
}

function getCode() {
  const file_id = file_selected.value.uuid
  // Fetch content from remote.
  if (file_id == null) {
    console.warn('Try get code, but file id is null.')
    return
  }
  getFileContent(file_id)
}

async function getFileContent(file_id) {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchFile + `?file_id=${file_id}`)
    const res = response.data
    raw_code = res.content
    code.value = res.content
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

function save() {
  const f_id = file_selected.value.uuid
  saveContentToRemote(f_id, code.value)
}

async function saveContentToRemote(file_id, content) {
  try {
    let postData = {
      content: content
    }
    const response = await axios.post(API_ENDPOINTS.updateFile + `?file_id=${file_id}`, postData)
    const res = response
    raw_code = code.value
    is_content_update.value = false
    save_ok_dialog.value.openModal()
  } catch (error) {
    console.error('请求API时出错:', error)
    save_failed_dialog.value.openModal()
  }
}

watch(code, (newValue, oldValue) => {
  if (newValue != raw_code) {
    is_content_update.value = true
  } else {
    is_content_update.value = false
  }
})

watch(file_selected, (newValue, oldValue) => {
  getCode()
})

onMounted(() => {
  getCode()
})
</script>
