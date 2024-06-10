<template>
  <div class="w-full max-w-md">
    <TabGroup v-model="selectedIndex">
      <TabList class="flex rounded-xl">
        <Tab v-for="(category, index) in categories" :key="category.name" class="px-2">
          <button class="px-10" :class="tabClass(index)" @click="go_router(categories[index].path)">
            {{ category.name }}
          </button>
        </Tab>
      </TabList>
    </TabGroup>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { TabGroup, TabList, Tab } from '@headlessui/vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const categories = ref([
  { name: 'Summary', path: '/summary' },
  { name: 'Live', path: '/live' },
  { name: 'Backtest', path: '/backtest' },
  { name: 'Data', path: '/data' },
  { name: 'File', path: '/file' },
  { name: 'PlayGround', path: '/playground' }
])

const selectedIndex = computed(() => {
  return categories.value.findIndex((category) => category.path === route.path)
})

const tabClass = (index) => {
  return [
    'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
    'ring-white/60 ring-offset-2 ring-offset-blue-400 focus:outline-none focus:ring-2',
    selectedIndex.value === index
      ? 'bg-white text-blue-700 shadow'
      : 'text-blue-100 hover:bg-white/[0.12] hover:text-white'
  ]
}

function go_router(path) {
  router.push(path)
}
</script>
