<template>
  <div class="w-full">
    <div class="mx-auto w-full max-w-md">
      <RadioGroup v-model="selected">
        <RadioGroupLabel class="sr-only">Server size</RadioGroupLabel>
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
</template>

<script setup>
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronUpIcon } from '@heroicons/vue/20/solid'
import { ref, onMounted, watch } from 'vue'
import yaml from 'js-yaml'
import {
  RadioGroup,
  RadioGroupLabel,
  RadioGroupDescription,
  RadioGroupOption
} from '@headlessui/vue'

var records = ref([
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

const selected = ref(records.value[0])
var page = 0
var size = 20

var isUpdated = false

const fetchRecords = async () => {
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
  fetchRecords()
}

const emit = defineEmits(['parentMethod'])

onMounted(() => {
  records = ref([])
  fetchRecords()
})

watch(selected, (newValue, oldValue) => {
  emit('parentMethod', selected.value)
})

defineExpose({ loadMore })
</script>
