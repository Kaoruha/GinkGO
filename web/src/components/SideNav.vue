<template>
  <div class="w-full">
    <div class="mx-auto w-full max-w-md">
      <RadioGroup v-model="selected">
        <RadioGroupLabel class="sr-only">Backtest</RadioGroupLabel>
        <div class="space-y-2">
          <RadioGroupOption
            as="template"
            v-for="(file, index) in backtest_files"
            :key="file.uuid"
            :value="file"
            v-slot="{ active, checked }"
          >
            <div
              :class="[
                active ? 'ring-2 ring-white/60 ring-offset-2 ring-offset-sky-300' : '',
                checked ? 'bg-sky-900/75 text-white ' : 'bg-white '
              ]"
              class="relative flex cursor-pointer rounded-lg px-5 py-4 shadow-md focus:outline-none"
            >
              <div class="flex w-full items-center justify-between">
                <div class="flex items-center">
                  <div class="text-sm">
                    <RadioGroupLabel
                      as="p"
                      :class="checked ? 'text-white' : 'text-gray-900'"
                      class="font-medium"
                    >
                      {{ file.file_name }}
                    </RadioGroupLabel>
                    <RadioGroupDescription
                      as="span"
                      :class="checked ? 'text-sky-100' : 'text-gray-500'"
                      class="inline"
                    >
                      <h4>From {{ file.date_start.split('T')[0] }}</h4>
                      <h4>To {{ file.date_end.split('T')[0] }}</h4>
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
import { ref, onMounted } from 'vue'
import {
  RadioGroup,
  RadioGroupLabel,
  RadioGroupDescription,
  RadioGroupOption
} from '@headlessui/vue'
import { API_ENDPOINTS } from '../request.js'

var backtest_files = [
  /* { */
  /*   file_name: 'Startup', */
  /*   uuid:"uuid", */
  /*   date_start:"2020-01-01", */
  /*   date_end:"2022-01-01", */
  /*   update:"2022-01-01", */
  /* }, */
]

const selected = ref(backtest_files[0])

const fetchBacktest = async () => {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchBacktest)
    const res = response.data
    if (res.length === 0) {
      console.log('No backtest files found.')
      return
    }
    backtest_files = []
    for (let i = 0; i < res.length; i++) {
      backtest_files.push(res[i])
    }
    selected.value = backtest_files[0]
    console.log('Shoud update backtest file list.')
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

onMounted(() => {
  fetchBacktest()
})
</script>
