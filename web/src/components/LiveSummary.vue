<template>
  <div class="h-[100px] flex">
    <div class="w-[240px]">
      <div class="text-gray-500">Total Market Value</div>
      <div class="py-2 text-4xl font-black" :class="color_red">{{ market_value.toFixed(2) }}</div>
    </div>
    <div class="flex-grow">
      <div class="grid grid-cols-3 grid-rows-2 h-[100px] items-center">
        <!-- 第一行的六个单元格 -->
        <div :class="title_cls">
          今日盈利
          <div :class="['font-medium', today_profit > 0 ? color_green : color_red]">
            {{ today_profit.toFixed(2) }}({{ (today_profit_change * 100).toFixed(2) }}%)
          </div>
        </div>
        <div :class="title_cls">
          浮动盈亏
          <div :class="['font-medium', float_profit > 0 ? color_green : color_red]">
            {{ float_profit.toFixed(2) }}({{ (float_profit_change * 100).toFixed(2) }}%)
          </div>
        </div>
        <div :class="title_cls">
          累计盈亏
          <div :class="['font-medium', total_profit > 0 ? color_green : color_red]">
            {{ total_profit.toFixed(2) }}({{ (total_profit_change * 100).toFixed(2) }}%)
          </div>
        </div>
        <!-- 第二行的六个单元格 -->
        <div :class="title_cls">
          总资产
          <div :class="value_cls">
            {{ total_assets.toFixed(2) }}
          </div>
        </div>
        <div :class="title_cls">
          现金
          <div :class="value_cls">
            {{ cash }}
          </div>
        </div>
        <div :class="title_cls">
          本金
          <div :class="value_cls">
            {{ principal }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
const title_cls = ref('col-span-1 row-span-1 text-gray-500')
const value_cls = ref('col-span-1 row-span-1 text-gray-800 font-medium')
const color_green = ref('text-green-600')
const color_red = ref('text-red-400')
// Summary
const market_value = ref(123000)
const today_profit = ref(-223.12)
const today_profit_change = ref(-0.0058)
const float_profit = ref(111.42)
const float_profit_change = ref(0.3874)
const total_profit = ref(3111.42)
const total_profit_change = ref(0.2274)
const total_assets = ref(1000)
const cash = ref(10000)
const principal = ref(100000)
const engine_id = defineModel()
watch(engine_id, (newValue, oldValue) => {
  console.log('summary get new engine id')
  // TODO Update
  // console.log(live_engine_id.value)
})
</script>
