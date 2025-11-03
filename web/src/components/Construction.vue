<template>
  <div class="w-full px-1">
    <ConstructionItem
      v-model="selected_backtest"
      :title="'Summary'"
      :rtype="'summary'"
    ></ConstructionItem>
    <ConstructionItem
      v-model="selected_backtest"
      :title="'Selector'"
      :rtype="'selector'"
    ></ConstructionItem>
    <ConstructionItem
      v-model="selected_backtest"
      :title="'Sizer'"
      :rtype="'sizer'"
    ></ConstructionItem>
    <ConstructionItem
      v-model="selected_backtest"
      :title="'Strategy'"
      :rtype="'strategy'"
    ></ConstructionItem>
    <ConstructionItem
      v-model="selected_backtest"
      :title="'Risk'"
      :rtype="'risk'"
    ></ConstructionItem>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import ConstructionItem from '../components/ConstructionItem.vue'

const selected_backtest = defineModel()
watch(selected_backtest, (newValue, oldValue) => {
  // console.log("Construction got new backtest, ", newValue)
})
</script>
