<template>
  <div class="flex items-center relative">
    <input
      type="text"
      class="px-2 py-2 w-80 rounded-lg flex-grow"
      placeholder="Search ..."
      v-model="searchQuery"
      @keyup.enter="querySubmit"
    />
    <MagnifyingGlassIcon class="h-5 w-5 absolute right-0 mr-4" aria-hidden="true" />
  </div>
</template>

<script setup>
import { MagnifyingGlassIcon } from '@heroicons/vue/20/solid'
import { ref, watch } from 'vue'
const emit = defineEmits(['parentMethod'])
let searchQuery = ref(null)

function querySubmit() {
  emit('parentMethod', searchQuery.value)
}
watch(searchQuery, (newValue, oldValue) => {
  console.log(newValue)
  emit('parentMethod', searchQuery.value)
})
</script>
