<template>
  <div>
    <span v-if="raw.length == 0" class="text-red-400 font-bold">No Signals on {{ date }}</span>
    <div v-for="item in raw" :key="item.uuid" :value="item">
      <div
        class="mx-2 my-2 px-2 py-2 rounded-xl hover:bg-yellow-200 select-none cursor-pointer"
        :class="item.direction == 1 ? 'bg-green-200' : 'bg-red-200'"
        @click="updateCandle(item.code)"
      >
        <div class="font-bold">
          {{ item.code }}
        </div>
        <div class="text-gray-500">
          {{ item.reason }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, provide, watch } from 'vue'
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'

const emit = defineEmits(['parentMethod'])
const backtest_id = ref('test_id')
const date = ref('2020-01-10')
const raw = ref([{}])

const fetchSignal = async (back_id, new_date) => {
  backtest_id.value = back_id
  date.value = new_date
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchSignal + `?backtest_id=${backtest_id.value}&date=${date.value}`
    )
    const res = response.data
    raw.value = []
    if (res.length === 0) {
      return
    }
    for (let i = 0; i < res.length; i++) {
      raw.value.push(res[i])
    }
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

defineExpose({
  fetchSignal
})

const updateCandle = (code) => {
  emit('parentMethod', code)
}
</script>
