<template>
  <div class="w-full px-1">
    <div class="mx-auto w-full max-w-md rounded-lg bg-white p-1 mb-2">
      <Disclosure v-slot="{ open }" :defaultOpen="true">
        <DisclosureButton
          class="flex w-full justify-between rounded-lg bg-blue-200 hover:bg-yellow-200 px-4 py-2 text-left text-sm font-medium text-purple-900 focus:outline-none focus-visible:ring focus-visible:ring-purple-500/75"
        >
          <span>{{ props.title }}</span>
          <ChevronUpIcon
            :class="open ? 'rotate-180 transform' : ''"
            class="h-5 w-5 text-purple-500"
          />
        </DisclosureButton>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'summary'"
        >
          {{ props.raw.uuid }}
          Summary
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'selector'"
        >
          <span class="text-white bg-blue-400 px-2 text-sm rounded-lg">
            {{ getSelectorID() }}
          </span>
          <div>
            <span class="text-gray-400 bg-gray-200 px-2 text-sm rounded-lg">
              {{ getSelectorName() }}
            </span>
          </div>
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'sizer'"
        >
          <span class="text-white bg-blue-400 px-2 text-sm rounded-lg">
            {{ getSizerID() }}
          </span>
          <div>
            <span
              v-for="item in getSizerParam()"
              class="text-gray-400 bg-gray-200 px-2 text-sm rounded-xl mr-3"
              >{{ item }}</span
            >
          </div>
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'strategy'"
        >
          <div v-for="(strategy, index) in getStrategies()" :key="index" class="mb-2">
            <span class="px-2 text-sm rounded-lg" :class="getColorClass(index)">
              {{ strategy.id }}
            </span>
            <div>
              <span
                v-for="param in strategy.parameters"
                class="text-gray-400 bg-gray-200 px-2 text-sm rounded-xl mr-3"
                >{{ param }}</span
              >
            </div>
          </div>
        </DisclosurePanel>
        <DisclosurePanel class="px-4 pb-2 pt-4 text-sm text-gray-500" v-if="props.rtype === 'risk'">
          {{ props.raw.uuid }}
          Risk
        </DisclosurePanel>
      </Disclosure>
    </div>
  </div>
</template>

<script setup>
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronUpIcon } from '@heroicons/vue/20/solid'
import { ref } from 'vue'
const props = defineProps({
  title: {
    type: String,
    default: '默认标题'
  },
  rtype: {
    type: String,
    default: 'summary' // summary, strategy, risk
  },
  raw: {
    rtype: Object,
    default: {}
  }
})

const getSelectorID = () => {
  try {
    return props.raw.content.selector.id
  } catch (error) {
    console.warn('获取Selector ID出错:', error)
    console.warn(props.raw)
    return 'Unknown ID'
  }
}
const getSelectorName = () => {
  try {
    return props.raw.content.selector.parameters[0]
  } catch (error) {
    console.warn('获取Selector Name出错:', error)
    console.warn(props.raw)
    return 'Unknown Name'
  }
}
const getSizerID = () => {
  try {
    return props.raw.content.sizer.id
  } catch (error) {
    console.warn('获取Sizer ID出错:', error)
    console.warn(props.raw)
    return 'Unknown ID'
  }
}

const getSizerParam = () => {
  try {
    return props.raw.content.sizer.parameters
  } catch (error) {
    console.warn('获取Sizer Param出错:', error)
    console.warn(props.raw)
    return []
  }
}

const getStrategies = () => {
  try {
    return props.raw.content.strategies
  } catch (error) {
    console.warn('获取Sizer Param出错:', error)
    console.warn(props.raw)
    return []
  }
}

const colors = [
  'bg-red-400',
  'bg-green-400',
  'bg-blue-400',
  'bg-yellow-400',
  'bg-indigo-400',
  'bg-purple-400'
]
const getColorClass = (index) => {
  return `${colors[index % colors.length]} text-white`
}
</script>
