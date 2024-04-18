<template>
  <div class="w-full max-w-md">
    <TabGroup>
      <TabList class="flex space-x-1 rounded-xl p-1">
        <Tab
          v-for="category in Object.keys(categories)"
          as="template"
          :key="category"
          v-slot="{ selected }"
        >
          <button
            :class="[
              'w-full rounded-lg py-2.5 text-sm font-medium leading-5 mx-2.5',
              'ring-white/60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
              selected
                ? 'bg-white text-blue-700 shadow'
                : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
            ]"
            @click="go_router(categories[category].path)"
          >
            {{ category }}
          </button>
        </Tab>
      </TabList>
    </TabGroup>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@headlessui/vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const categories = ref({
  Summary: {
    path: '/summary'
  },
  Live: {
    path: '/live'
  },
  Backtest: {
    path: '/backtest'
  },
  Data: {
    path: '/Data'
  },
  File: {
    path: '/Data'
  }
})

function go_router(path) {
  router.push(path)
}
</script>
