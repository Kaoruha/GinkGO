<template>
  <div class="w-full relative">
    <ConfirmDialog
      ref="del_dialog"
      @confirmMethod="delLivePortfolio"
      :title="'Remove Live Portfolio'"
      :confirm_btn_text="'DELETE'"
      :msg="confirm_msg"
    >
    </ConfirmDialog>
    <div class="mb-2">
      <InputSearch @parentMethod="queryChange"></InputSearch>
    </div>
    <!-- FileDropdown show at right click -->
    <div class="z-10 absolute select-none" ref="dropdown">
      <LiveDropDown
        ref="live_dropdown"
        @detail="ShowDetail"
        @start="LiveControl(current_record.uuid, 'start')"
        @pause="LiveControl(current_record.uuid, 'pause')"
        @stop="LiveControl(current_record.uuid, 'stop')"
        @restart="LiveControl(current_record.uuid, 'restart')"
        @delete="CallDelLiveModal"
      >
      </LiveDropDown>
    </div>
    <div
      class="w-full z-0 h-[calc(100vh-102px)] select-none"
      ref="recordList"
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
                class="relative flex cursor-pointer rounded-lg px-5 py-4 shadow-md focus:outline-none"
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
                        class="font-medium"
                      >
                        <div
                          class="w-[10px] h-[10px] rounded-lg inline-block mr-1"
                          :class="get_live_status_class(item.status)"
                        ></div>
                        {{ item.name }}
                      </RadioGroupLabel>
                      <RadioGroupDescription
                        as="span"
                        :class="checked ? 'text-sky-100' : 'text-gray-500'"
                        class="inline"
                      >
                      </RadioGroupDescription>
                      <span> Worth: ${{ item.worth }} </span>
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
                      />
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

<script setup lang="ts">
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronUpIcon } from '@heroicons/vue/20/solid'
import { ref, onMounted, watch } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import InputSearch from '../components/InputSearch.vue'
import LiveDropDown from '../components/dropdown/LiveDropDown.vue'
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
    status: 'running',
    worth: 100000,
    finish_at: '2002-01-01T11:22:11',
    start_at: '2002-01-01T11:22:11'
  },
  {
    uuid: 'uuid2',
    status: 'running',
    worth: 100004,
    finish_at: '2002-01-01T11:22:11',
    start_at: '2002-01-01T11:22:11'
  }
])

const selected = ref(records.value[0])
let page = 0
let size = 20
const confirm_msg = ref('haha')

let isUpdated = false
// Responsible Pointer
const dropdown = ref(null)
const live_dropdown = ref(null)
const recordList = ref(null)
const del_dialog = ref(null)

function get_live_status_class(status) {
  switch (status) {
    case 'running':
      return 'bg-green-400 animate-pulse-fast'
    case 'pause':
      return 'bg-yellow-400'
    case 'stop':
      return 'bg-red-400'
    case 'restart':
      return 'bg-orange-400 animate-pulse-fast'
    default:
      return 'bg-blue-400 animate-pulse-fast'
  }
  return 'bg-green-400'
}

async function fetchRecords() {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchLivePortfolio + `?page=${page}&size=${size}`
    )
    const res = response.data
    if (res.length === 0) {
      console.log('No backtest records found.')
      return
    }
    for (let i = 0; i < res.length; i++) {
      const bytes = res[i].content
      const obj = yaml.load(bytes)
      console.log(res[i])
      res[i].content = obj
      records.value.push(res[i])
    }
    if (isUpdated) {
      return
    }
    selected.value = records.value[0]
    isUpdated = true
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

const loadMore = async () => {
  page += 1
  fetchRecords()
}

const emit = defineEmits(['parentMethod'])

onMounted(() => {
  records.value.length = 0
  fetchRecords()
  conLiveStatusSSE()
})

watch(selected, (newValue, oldValue) => {
  emit('parentMethod', selected.value)
})

function queryChange() {
  page = 0
  console.log('live portfolio query changed.')
}

function copyLivePortfolioID() {
  console.log('copy LivePortfolio id', current_record.value.uuid)
}

function CallDelLiveModal() {
  del_dialog.value.openModal()
}

function delLivePortfolio() {
  console.log('del live portfolio', current_record.value.uuid)
  delRecords(current_record.value.uuid)
}

async function delRecords(id: string) {
  try {
    const response = await axios.post(API_ENDPOINTS.delLivePortfolio + `?id=${id}`)
    const res = response.data
    console.log(res)
    records.value.length = 0
    fetchRecords()
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

const checkScrollEnd = () => {
  const div = recordList.value
  if (div) {
    const scrollTop = div.scrollTop // 已滚动的距离
    const clientHeight = div.clientHeight // 可视区域的高度
    const scrollHeight = div.scrollHeight // 整个滚动区域的高度

    if (scrollTop + clientHeight >= scrollHeight) {
      console.log('滚动条到达底部')
      loadMore()
      // 在这里执行到达底部后的操作
    }
  }
}

const current_record = ref(null)

function onRightClick(event, file) {
  current_record.value = file
  confirm_msg.value = `Sure to remove live: ${file.uuid}?`
  const offset_x = -4
  const offset_y = -100
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  dropdown.value.style.top = y + 'px'
  dropdown.value.style.left = x + 'px'
  live_dropdown.value.simClick()
}

function conLiveStatusSSE() {
  const eventSource = new EventSource(API_ENDPOINTS.sseLiveStatus)
  console.log(eventSource)
  eventSource.onmessage = (msg) => {
    const res = JSON.parse(msg.data)
    console.info("live_status", res)
    records.value.forEach((value) => {
      const id = value.uuid
      if (id in res) {
        value.status = res[id]
      } else {
        value.status = 'stop'
      }
    })
  }
  eventSource.onerror = (error) => {
    console.error('EventSource Failed: ', error)
    eventSource.close()
  }
}

function ShowDetail() {
  console.log('Show detail', current_record.value.uuid)
}

async function LiveControl(id: string, cmd: string) {
  try {
    const response = await axios.post(API_ENDPOINTS.LiveControl + `?id=${id}&command=${cmd}`)
    const res = response.data
    console.log(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}
</script>
