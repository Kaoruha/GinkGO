<template>
  <div>
    <LiveSummary v-model="live_engine_id"></LiveSummary>
    <div class="mt-4">
      <TabGroup>
        <TabList class="flex rounded-xl w-[480px] h-[26px]">
          <Tab v-for="category in categories" as="template" :key="category" v-slot="{ selected }">
            <button
              @click="tab_switch"
              :class="[
                'w-full rounded-lg text-sm font-medium leading-5',
                'ring-white/60 focus:outline-none focus:ring-2',
                selected
                  ? 'bg-blue-200 text-blue-700'
                  : 'text-blue-300 hover:bg-white/[0.12] hover:text-blue-500'
              ]"
            >
              {{ category }}
            </button>
          </Tab>
        </TabList>

        <TabPanels class="mt-2">
          <TabPanel>
            <LiveSignals ref="live_signals" v-model="live_engine_id"></LiveSignals>
          </TabPanel>
          <TabPanel>
            <LivePositions ref="live_positions" v-model="live_engine_id"></LivePositions>
          </TabPanel>
          <TabPanel>
            <LiveTrade ref="live_trade_records" v-model="live_engine_id"></LiveTrade>
          </TabPanel>
          <TabPanel>
            <LiveTransfer ref="live_transfer_records" v-model="live_engine_id"></LiveTransfer>
          </TabPanel>
        </TabPanels>
      </TabGroup>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { TabGroup, TabList, Tab, TabPanels, TabPanel } from '@headlessui/vue'
import LiveSignals from '../components/LiveSignals.vue'
import LivePositions from '../components/LivePositions.vue'
import LiveTrade from '../components/LiveTrade.vue'
import LiveTransfer from '../components/LiveTransfer.vue'
import LiveSummary from '../components/LiveSummary.vue'

const categories = ref(['Signals', 'Positions', 'TradeRecords', 'TransferRecords'])

// Preset class
const title_cls = ref('col-span-1 row-span-1 text-gray-500')
const value_cls = ref('col-span-1 row-span-1 text-gray-800 font-medium')
const color_green = ref('text-green-600')
const color_red = ref('text-red-400')

// ref
const live_signals = ref(null)
const live_positions = ref(null)
const live_trade_records = ref(null)
const live_transfer_records = ref(null)

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

function tab_switch() {
  // console.log("Tab Switch.")
}

const live_engine_id = ref(null)

function updateEngineID(id) {
  live_engine_id.value = id
}

async function getLiveSummary(id) {}

watch(live_engine_id, (newValue, oldValue) => {
  // console.log("new engine id")
  // console.log(live_engine_id.value)
})

defineExpose({ updateEngineID })
</script>
