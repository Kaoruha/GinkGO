<template>
  <div class="flex flex-col">
    <table class="min-w-full leading-normal">
      <thead>
        <tr>
          <th v-for="item in columns" :class="td_title_cls">
            {{ item }}
          </th>
        </tr>
      </thead>
      <div class="z-10 absolute select-none" ref="liveposition_dropdown_div">
        <LivePositionDropdown ref="liveposition_dropdown"></LivePositionDropdown>
      </div>
      <tbody>
        <tr
          v-for="item in positions"
          :key="item.id"
          @mouseover="[(hover = item.code)]"
          @mouseleave="hover = null"
          :class="hover === item.code ? bg_hover_color : 'bg-white'"
          @contextmenu.prevent="onLivePositionClick($event, item)"
        >
          <td :class="[td_cls, 'uppercase', item.operation == 'in' ? color_blue : color_red]">
            {{ item.operation }}
          </td>
          <td :class="[td_cls]">
            {{ item.money.toFixed(2) }}
          </td>
          <td :class="[td_cls]">
            {{ item.market }}
          </td>
          <td :class="[td_cls]">
            {{ item.date }}
          </td>
        </tr>
      </tbody>
    </table>
    <Button
      class="bg-blue-50 h-[40px] my-4 text-blue-300 rounded text-sm font-medium hover:text-blue-500 hover:bg-blue-100"
    >
      Add Transfer
    </Button>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import LivePositionDropdown from '../components/dropdown/LivePositionDropDown.vue'

const liveposition_dropdown = ref(null)
const liveposition_dropdown_div = ref(null)

const bg_hover_color = ref('bg-gray-50')
const td_title_cls = ref(
  'px-6 py-2 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider'
)
const td_cls = ref('px-5 py-2 border-b border-gray-200 text-sm select-none')
const color_blue = ref('text-blue-400')
const color_red = ref('text-red-400')
const columns = ['Operation', 'Money', 'Market', 'Date']
const positions = ref([
  { id: 'test123', operation: 'in', money: 100000, market: 'A股', date: '2020-01-01' },
  { id: 'test1232', operation: 'out', money: 50000, market: 'A股', date: '2020-04-01' }
])

const engine_id = defineModel()

const hover = ref(null)
watch(hover, (newValue, oldValue) => {
  // console.log(newValue)
})

function onLivePositionClick(event, item) {
  const offset_x = -4
  const offset_y = -42
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  liveposition_dropdown_div.value.style.top = y + 'px'
  liveposition_dropdown_div.value.style.left = x + 'px'
  liveposition_dropdown.value.simClick()
}

async function getData() {
  console.log('fake get transfer records from', engine_id.value)
}

onMounted(() => {
  getData()
})

watch(engine_id, (newValue, oldValue) => {
  getData()
})

defineExpose({ getData })
</script>
