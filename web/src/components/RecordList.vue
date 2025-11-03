<template>
  <div class="w-full relative">
    <ConfirmDialog
      ref="transfer_backtest_dialog"
      v-model="live_name"
      @confirmMethod="transfer2Live"
      :title="'Transfer Backtest to LIVE'"
      :confirm_btn_text="'TRANSFER'"
      :show_input="true"
      :msg="transfer_msg"
    >
    </ConfirmDialog>
    <ConfirmDialog
      ref="del_backtest_dialog"
      @confirmMethod="delBacktest"
      :title="'Remove Backtest'"
      :confirm_btn_text="'DELETE'"
      :msg="del_msg"
    >
    </ConfirmDialog>
    <div class="mb-2">
      <InputSearch @parentMethod="queryChange"></InputSearch>
    </div>
    <!-- FileDropdown show at right click -->
    <div class="z-10 absolute select-none" ref="dropdown">
      <BacktestDropDown
        ref="backtest_dropdown"
        @copy="copyBacktestID"
        @analyze="analyzeBacktest"
        @tolive="transfer_backtest_dialog.openModal()"
        @delete="del_backtest_dialog.openModal()"
      >
      </BacktestDropDown>
    </div>
    <div
      class="w-full z-0 h-[calc(100vh-102px)] select-none overflow-y-auto"
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
                        Worth: ${{ item.worth }}
                      </RadioGroupLabel>
                      <RadioGroupDescription
                        as="span"
                        :class="checked ? 'text-sky-100' : 'text-gray-500'"
                        class="inline"
                      >
                        <span>
                          {{ item.start_at.split('T')[0] }}
                        </span>
                        <span aria-hidden="true"> &middot;&middot;&middot;&middot; </span>
                        <span>
                          {{ item.finish_at.split('T')[0] }}
                        </span>
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

<script setup>
import axios from 'axios'
import { ref, onMounted, watch } from 'vue'
import { API_ENDPOINTS } from '../request.js'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronUpIcon } from '@heroicons/vue/20/solid'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import InputSearch from '../components/InputSearch.vue'
import BacktestDropDown from '../components/dropdown/BacktestDropDown.vue'
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
    status: 'Running',
    worth: 100000,
    finish_at: '2002-01-01T11:22:11',
    start_at: '2002-01-01T11:22:11'
  },
  {
    uuid: 'uuid2',
    status: 'Running',
    worth: 100002,
    finish_at: '2002-01-01T11:22:11',
    start_at: '2002-01-01T11:22:11'
  }
])

const selected = defineModel()
let page = 0
let size = 30
const del_msg = ref('haha')
const transfer_msg = ref('haha')

let live_name = ''

let isUpdated = false
// Responsible Pointer
const dropdown = ref(null)
const backtest_dropdown = ref(null)
const recordList = ref(null)
const del_backtest_dialog = ref(null)
const transfer_backtest_dialog = ref(null)

async function getRecords() {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchRecord + `?page=${page}&size=${size}`)
    const res = response.data
    if (res.length === 0) {
      console.log('No backtest records found.')
      return
    }
    for (let i = 0; i < res.length; i++) {
      const bytes = res[i].content
      const obj = yaml.load(bytes)
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
  getRecords()
}

const emit = defineEmits(['parentMethod'])

onMounted(() => {
  records.value.length = 0
  getRecords()
})

watch(selected, (newValue, oldValue) => {
  emit('parentMethod', selected.value)
})

function queryChange() {
  page = 0
  console.log('backtest query changed.')
}

function copyBacktestID() {
  console.log('copy backtest id', selected.value.uuid)
}

function transfer2Live() {
  console.log('transfer to live', selected.value.uuid)
  if (live_name.length == 0) {
    return
  }
  addLivePortfolio(selected.value.uuid, live_name)
}

function delBacktest() {
  console.log('del backtest', selected.value.uuid)
  delRecords(selected.value.uuid)
}

async function addLivePortfolio(id, portfolio_name) {
  try {
    const response = await axios.get(
      API_ENDPOINTS.addLivePortfolio + `?id=${id}&name=${portfolio_name}`
    )
    const res = response.data
    console.log(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function delRecords(id) {
  try {
    const response = await axios.get(API_ENDPOINTS.delBacktest + `?id=${id}`)
    const res = response.data
    console.log(res)
    if (res) {
      records.value = []
      page = 0
      getRecords()
    } else {
      console.error('Delte Failed.')
    }
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

function onRightClick(event, file) {
  del_msg.value = `Sure to remove ${file.uuid}?`
  transfer_msg.value = `Sure to transfer ${file.uuid} to live?`
  const offset_x = -4
  const offset_y = -100
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  dropdown.value.style.top = y + 'px'
  dropdown.value.style.left = x + 'px'
  backtest_dropdown.value.simClick()
}

function analyzeBacktest() {
  console.log('fake analyze.')
}
</script>
