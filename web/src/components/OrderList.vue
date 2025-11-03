<template>
  <div>
    <span v-if="raw.length == 0" class="text-red-400 font-bold">No Orders on {{ date }}</span>
    <div v-for="item in raw" :key="item.uuid" :value="item">
      <div
        class="mx-2 my-2 px-2 py-2 rounded-xl hover:bg-yellow-200 select-none cursor-pointer"
        :class="bgColorClass(item)"
        @click="updateCandle(item.code)"
      >
        <div class="font-bold">
          {{ item.code }}
          <span class="text-red-400">
            {{ item.status }}
          </span>
        </div>
        <div class="text-gray-500">Price: {{ item.transaction_price }}</div>
        <div class="text-gray-500">Volume: {{ item.volume }}</div>
        <div class="text-gray-500">Fee: {{ item.fee }}</div>
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

function bgColorClass(item) {
  if (item.status === 4) {
    return 'bg-gray-200' // 如果status为4，返回灰色背景
  } else if (item.status === 3) {
    if (item.direction === 1) {
      return 'bg-green-200'
    } else {
      return 'bg-red-200'
    }
  }
  return 'bg-blue-300' // 如果不满足上述条件，不赋予任何背景颜色
}

async function fetchOrder(back_id, new_date) {
  backtest_id.value = back_id
  date.value = new_date
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchOrder + `?backtest_id=${backtest_id.value}&date=${date.value}`
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
  fetchOrder
})

function updateCandle(code) {
  emit('parentMethod', code)
}
</script>
