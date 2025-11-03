<template>
  <div class="fixed w-42">
    <Combobox v-model="selected_code">
      <div class="relative">
        <div
          class="relative w-full cursor-default overflow-hidden rounded-lg bg-white text-left shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-white/75 focus-visible:ring-offset-2 focus-visible:ring-offset-teal-300 sm:text-sm"
        >
          <ComboboxInput
            class="w-full border-none py-2 pl-3 pr-10 text-sm leading-5 text-gray-900 focus:ring-0"
            :displayValue="(item) => item"
            @change="query = $event.target.value"
          />
          <ComboboxButton class="absolute inset-y-0 right-0 flex items-center pr-2">
            <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
          </ComboboxButton>
        </div>
        <TransitionRoot
          leave="transition ease-in duration-100"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
          @after-leave="query = ''"
        >
          <ComboboxOptions
            class="absolute mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black/5 focus:outline-none sm:text-sm"
          >
            <div
              v-if="codes.length === 0 && query !== ''"
              class="relative cursor-default select-none px-4 py-2 text-gray-700"
            >
              Nothing found.
            </div>
            <ComboboxOption
              v-for="item in codes"
              as="template"
              :key="item.code"
              :value="item.code"
              v-slot="{ selected, active }"
            >
              <li
                class="relative cursor-default select-none py-2 pl-10 pr-4"
                :class="{ 'bg-teal-600 text-white': active, 'text-gray-900': !active }"
              >
                <span
                  class="block truncate"
                  :class="{ 'font-medium': selected, 'font-normal': !selected }"
                >
                  <div>{{ item.name }}</div>
                  <div class="text-gray-400">{{ item.code }}</div>
                </span>
                <span
                  v-if="selected"
                  class="absolute inset-y-0 left-0 flex items-center pl-3"
                  :class="{ 'text-white': active, 'text-teal-600': !active }"
                >
                  <CheckIcon class="h-5 w-5" aria-hidden="true" />
                </span>
              </li>
            </ComboboxOption>
          </ComboboxOptions>
        </TransitionRoot>
      </div>
    </Combobox>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { API_ENDPOINTS } from '../request.js'
import axios from 'axios'
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
  TransitionRoot
} from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid'

const codes = ref([
  {
    code: '000001.SZ',
    name: '平安银行'
  },
  {
    code: '000783.SZ',
    name: '长江证券'
  }
])

const selected_code = defineModel()

const query = ref('')
watch(query, (newValue, oldValue) => {
  codes.value.length = 0
  getCodes()
})
const size = ref(20)

async function getCodes() {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchCodeList + `?query=${query.value}&page=0&size=${size.value}`
    )
    const res = response.data
    if (res.length === 0) {
      console.log('No code found.')
      return
    }
    for (let i = 0; i < res.length; i++) {
      var item = { code: res[i].code, name: res[i].code_name }
      codes.value.push(item)
    }
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}
</script>
