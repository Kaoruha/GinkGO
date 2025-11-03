<template>
  <VueDatePicker
    v-model="date"
    class="bg-white rounded-xl text-left shadow-md sm:text-sm"
  ></VueDatePicker>
</template>

<script setup>
import { ref, watch } from 'vue'
import VueDatePicker from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

const emit = defineEmits(['parentMethod'])
let date = ref(null)

watch(date, (newValue, oldValue) => {
  console.log(date.value)
  emit('parentMethod', date.value)
})
</script>
