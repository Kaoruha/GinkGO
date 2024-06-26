<template>
  <div class="flex h-screen">
    <!-- 左边部分，固定宽度 -->
    <div class="w-[320px] bg-gray-200 px-2 py-2">
      <RecordList ref="recordList" v-model="selected_backtest"></RecordList>
    </div>
    <div class="w-[420px] bg-gray-200 overflow-y-auto px-2 py-2">
      <Construction ref="construction" v-model="selected_backtest"></Construction>
    </div>

    <!-- 右边部分，撑满剩余空间 -->
    <div class="flex-grow pl-2 pt-2 overflow-y-auto">
      <div class="w-full h-[40px]">
        <AnalyzerGourp
          class="z-10"
          ref="analyzers"
          v-model="selected_backtest"
          @parentMethod="handlerAnalyzerSelectUpdate"
        >
        </AnalyzerGourp>
      </div>
      <div class="w-full h-[260px]">
        <ChartContainer
          v-model="selected_backtest"
          ref="chart"
          @parentMethod="handlerDateUpdate"
        ></ChartContainer>
      </div>
      <div class="w-full flex">
        <div class="flex flex-col w-[400px] h-[calc(100vh-370px)]">
          <!-- 上部分，固定高度 -->
          <div>
            <span
              class="cursor-pointer rounded-xl bg-gray-200 hover:bg-yellow-200 w-[40px] px-2 py-1 mr-4 select-none"
              @click="preDate"
            >
              Pre
            </span>
            <span class="font-bold">{{ date }}</span>
            <span
              class="cursor-pointer rounded-xl bg-gray-200 hover:bg-yellow-200 w-[40px] px-2 py-1 ml-4 select-none"
              @click="nextDate"
            >
              Next
            </span>
          </div>
          <!-- 下部分，撑满所有空间 -->
          <div class="flex flex-grow overflow-y-auto">
            <!-- 左侧，占50%宽度 -->
            <div class="w-1/2 overflow-y-auto">
              <SignalList ref="signalList" @parentMethod="handlerCodeUpdate"> </SignalList>
            </div>

            <!-- 右侧，占50%宽度 -->
            <div class="w-1/2 overflow-y-auto">
              <OrderList ref="orderList" @parentMethod="handlerCodeUpdate"> </OrderList>
            </div>
          </div>
        </div>
        <div class="flex-grow h-[calc(100vh-370px)]">
          <CandleChart ref="candle"></CandleChart>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import RecordList from '../components/RecordList.vue'
import Construction from '../components/Construction.vue'
import AnalyzerGourp from '../components/AnalyzerGroup.vue'
import ChartContainer from '../components/ChartContainer.vue'
import CandleChart from '../components/CandleChart.vue'
import TimeSelector from '../components/TimeSelector.vue'
import OrderList from '../components/OrderList.vue'
import SignalList from '../components/SignalList.vue'

const recordsContainer = ref(null)
const recordList = ref(null)
const construction = ref(null)
const chart = ref(null)
const candle = ref(null)
const analyzers = ref(null)
const signalList = ref(null)
const orderList = ref(null)

const selected_backtest = ref(null)
const date = ref(null)
const selected_analyzer = ref(null)

watch(selected_backtest, (newValue, oldValue) => {
  // console.log("Backtest View got new backtest, ", newValue)
})

const analyzer_selected = ref({
  id: 'Test Default ID',
  parameters: ['Test Default Parameters']
})

const handlerAnalyzerSelectUpdate = (analyzer) => {
  if (analyzer == null) {
    console.error('analyzer is null')
    return
  }
  analyzer_selected.value = analyzer
  const backtest_id = selected_backtest.value.uuid
  const analyzer_id = analyzer.id
  const analyzer_name = analyzer.parameters[0]
  chart.value.updateLine(backtest_id, analyzer_id, analyzer_name)
}

const handlerDateUpdate = (new_date) => {
  date.value = new_date
  const backtest_id = selected_backtest.value.uuid
  signalList.value.fetchSignal(backtest_id, date.value)
  orderList.value.fetchOrder(backtest_id, date.value)
}

const handlerCodeUpdate = (code) => {
  candle.value.updateCandle(selected_backtest.value.uuid, code, date.value)
}

function preDate() {
  if (date.value == '') {
    return
  }
  const date_temp = new Date(date.value)
  const new_date = new Date(date_temp.setDate(date_temp.getDate() - 1))
  date.value = new_date.toISOString().split('T')[0]
  handlerDateUpdate(date.value)
}

function nextDate() {
  if (date.value == '') {
    return
  }
  const date_temp = new Date(date.value)
  const new_date = new Date(date_temp.setDate(date_temp.getDate() + 1))
  date.value = new_date.toISOString().split('T')[0]
  handlerDateUpdate(date.value)
}
</script>
