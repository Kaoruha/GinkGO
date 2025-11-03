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
          {{ selected_backtest?.uuid }}
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'selector'"
        >
          <span class="text-white bg-blue-400 px-2 text-sm rounded-lg">
            {{ selected_backtest?.content.selector.id }}
          </span>
          <div>
            <span class="text-gray-400 bg-gray-200 px-2 text-sm rounded-lg">
              {{ selected_backtest?.content.selector.parameters[0] }}
            </span>
          </div>
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'sizer'"
        >
          <span class="text-white bg-blue-400 px-2 text-sm rounded-lg">
            {{ selected_backtest?.content.sizer.id }}
          </span>
          <div>
            <span
              v-for="item in selected_backtest?.content.sizer.parameters"
              class="text-gray-400 bg-gray-200 px-2 text-sm rounded-xl mr-3"
              >{{ item }}</span
            >
          </div>
        </DisclosurePanel>
        <DisclosurePanel
          class="px-4 pb-2 pt-4 text-sm text-gray-500"
          v-if="props.rtype === 'strategy'"
        >
          <div
            v-for="(strategy, index) in selected_backtest?.content.strategies"
            :key="index"
            class="mb-2"
          >
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
          <div>
            {{ selected_backtest?.content.risk_manager.id }}
          </div>
          <span
            v-for="param in selected_backtest?.content.risk_manager.parameters"
            class="text-gray-400 bg-gray-200 px-2 text-sm rounded-xl mr-3"
            >{{ param }}</span
          >
        </DisclosurePanel>
      </Disclosure>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Disclosure, DisclosureButton, DisclosurePanel } from '@headlessui/vue'
import { ChevronUpIcon } from '@heroicons/vue/20/solid'

const selected_backtest = defineModel()

watch(selected_backtest, (newValue, oldValue) => {
  // console.log("ConstructionItem got new backtest, ", newValue.uuid)
})

const props = defineProps({
  title: {
    type: String,
    default: '默认标题'
  },
  rtype: {
    type: String,
    default: 'summary' // summary, strategy, risk
  }
})

const colors = [
  'bg-red-400',
  'bg-green-400',
  'bg-blue-400',
  'bg-yellow-400',
  'bg-indigo-400',
  'bg-purple-400'
]

function getColorClass(index) {
  return `${colors[index % colors.length]} text-white`
}
</script>
