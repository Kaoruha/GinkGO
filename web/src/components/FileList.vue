<template>
  <div class="relative">
    <ConfirmDialog
      ref="file_rename_dialog"
      v-model="new_file_name"
      @confirmMethod="renameFile"
      :title="'Rename'"
      :show_input="true"
      :confirm_btn_text="'Submit'"
      :msg="rename_msg"
    >
    </ConfirmDialog>
    <div class="mb-2 px-1">
      <InputSearch @parentMethod="queryChange"></InputSearch>
    </div>
    <!-- FileDropdown show at right click -->
    <div class="z-10 absolute" ref="dropdown">
      <FileDropDown
        ref="file_dropdown"
        @copy="copyFileID"
        @rename="file_rename_dialog.openModal()"
        @delete="delFile"
      >
      </FileDropDown>
    </div>
    <div
      class="w-full z-0 overflow-y-auto h-[calc(100vh-102px)] px-1"
      ref="fileList"
      @scroll="checkScrollEnd"
    >
      <div class="mx-auto w-full max-w-md">
        <RadioGroup v-model="selected">
          <div class="space-y-2">
            <RadioGroupOption
              as="template"
              v-for="item in records"
              :key="item.uuid"
              :value="item"
              v-slot="{ active, checked }"
            >
              <div
                class="relative flex cursor-pointer rounded-lg px-5 py-4 shadow-md focus:outline-none select-none"
                :class="[
                  active ? 'ring-2 ring-white/60 ring-offset-2 ring-offset-sky-300' : '',
                  checked ? 'bg-sky-900/75 text-white' : 'bg-white  hover:bg-yellow-200'
                ]"
                @contextmenu.prevent="onRightClick($event, item)"
              >
                <div class="flex w-full items-center justify-between">
                  <div class="flex items-center">
                    <div class="text-sm">
                      <RadioGroupLabel
                        as="p"
                        :class="checked ? 'text-white' : 'text-gray-900'"
                        class="font-medium mb-2"
                      >
                        {{ item.file_name }}
                      </RadioGroupLabel>
                      <RadioGroupDescription
                        as="span"
                        :class="checked ? 'text-sky-100' : 'text-gray-500'"
                        class="inline cursor-pointer"
                      >
                        <span
                          class="px-1 py-1 text-xs rounded mr-2"
                          :class="getColorClass(item.type)"
                          >{{ item.type.toUpperCase() }}</span
                        >
                        <span class="mr-1">UpdateAt:</span>
                        <span>{{ item.update_at.split('T')[0] }} </span>
                      </RadioGroupDescription>
                    </div>
                  </div>
                  <div v-show="checked" class="shrink-0 text-white">
                    <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="12" fill="#fff" fill-opacity="0.2" />
                      <path
                        d="M7 13l3 3 7-7"
                        stroke="#fff"
                        stroke-width="1.5"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                      ></path>
                    </svg>
                  </div>
                </div>
              </div>
            </RadioGroupOption>
          </div>
        </RadioGroup>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import InputSearch from '../components/InputSearch.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import FileDropDown from '../components/dropdown/FileDropDown.vue'
import yaml from 'js-yaml'
import {
  RadioGroup,
  RadioGroupLabel,
  RadioGroupDescription,
  RadioGroupOption
} from '@headlessui/vue'

const records = ref([
  {
    uuid: 'uuid',
    file_name: 'test_file1',
    type: 'analyzer',
    update_at: '2002-01-01T11:22:11',
    create_at: '2002-01-01T11:22:11'
  },
  {
    uuid: 'uuid2',
    file_name: 'test_file2',
    type: 'strategy',
    update_at: '2002-01-01T11:22:11',
    create_at: '2002-01-01T11:22:11'
  }
])

// Responsible Pointer
const dropdown = ref(null)
const file_dropdown = ref(null)
const fileList = ref(null)
const file_rename_dialog = ref(null)

const selected = defineModel()
let query = ''
let page = 0
let size = 20

const rename_msg = ref('haha')

function renameFile() {
  console.log('fake rename')
  console.log(new_file_name)
  updateFileName(hover_file.uuid, new_file_name)
}

async function updateFileName(file_id, new_name) {
  try {
    console.log(file_id)
    console.log(new_name)
    const response = await axios.get(API_ENDPOINTS.renameFile + `?id=${file_id}&name=${new_name}`)
    const res = response.data
    new_file_name = ''
    queryChange('')
    console.log(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

let hover_file = null

var isUpdated = false

function queryChange(new_query) {
  query = new_query
  records.value.length = 0
  page = 0
  fetchRecords()
}

async function fetchRecords() {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchFileList + `?query=${query}&page=${page}&size=${size}`
    )
    const res = response.data
    if (res.length === 0) {
      console.log('No backtest records found.')
      return
    }
    for (let i = 0; i < res.length; i++) {
      var item = {
        uuid: res[i]['uuid'],
        file_name: res[i]['file_name'],
        type: res[i]['type'],
        update_at: res[i]['timestamp'],
        create_at: res[i]['update']
      }
      records.value.push(item)
      // console.log(i)
    }
    selected.value = records.value[0]
    if (isUpdated) {
      return
    }
    isUpdated = true
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

const color_dict = {
  other: 'bg-gray-400',
  analyzer: 'bg-red-400',
  strategy: 'bg-blue-400',
  selector: 'bg-yellow-400',
  riskmanager: 'bg-green-400',
  sizer: 'bg-purple-400',
  backtest: 'bg-orange-400',
  live: 'bg-pink-400'
}

const getColorClass = (type) => {
  return `${color_dict[type]} text-white`
}

const loadMore = async () => {
  page += 1
  fetchRecords()
}

const emit = defineEmits(['parentMethod'])

onMounted(() => {
  records.value.length = 0
  fetchRecords()
})

let file = '123file'
let new_file_name = ''

function onRightClick(event, file) {
  hover_file = file
  new_file_name = file.file_name
  const offset_x = -4
  const offset_y = -100
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  dropdown.value.style.top = y + 'px'
  dropdown.value.style.left = x + 'px'
  file_dropdown.value.simClick()
}

function delFile() {
  console.log('Try delete file', hover_file.file_name)
}

function copyFileID() {
  console.log('Try copy file id', hover_file.file_name, '  id:', hover_file.uuid)
}

const checkScrollEnd = () => {
  const div = fileList.value
  if (div) {
    const scrollTop = div.scrollTop // 已滚动的距离
    const clientHeight = div.clientHeight // 可视区域的高度
    const scrollHeight = div.scrollHeight // 整个滚动区域的高度

    if (scrollTop + clientHeight >= scrollHeight - 2) {
      console.log('滚动条到达底部')
      loadMore()
    }
    // 在这里执行到达底部后的操作
  }
}
</script>
