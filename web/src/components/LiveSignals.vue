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
      <div class="z-10 absolute select-none" ref="livesignals_dropdown_div">
        <LiveSignalsDropdown ref="livesignals_dropdown"></LiveSignalsDropdown>
      </div>
      <tbody>
        <tr
          v-for="item in positions"
          :key="item.id"
          @mouseover="[(hover = item.code)]"
          @mouseleave="hover = null"
          :class="[hover === item.code ? bg_hover_color : 'bg-white']"
          @contextmenu.prevent="onLivePositionClick($event, item)"
        >
          <td :class="td_cls">
            <CheckCircleIcon
              :class="done_list.includes(item.id) ? 'text-green-600' : 'text-gray-300'"
              class="mr-2 h-5 w-5"
              aria-hidden="true"
            />
          </td>
          <td :class="[td_cls]">
            <div>
              {{ item.name }}
            </div>
            <div class="text-gray-400">
              {{ item.code }}
            </div>
          </td>
          <td
            class="uppercase"
            :class="[td_cls, item.direction == 'long' ? color_green : color_red]"
          >
            {{ item.direction }}
          </td>
          <td :class="td_cls">
            {{ item.price }}
          </td>
          <td :class="td_cls">
            {{ item.volume }}
          </td>
          <td :class="td_cls">
            {{ item.source }}
          </td>
          <td :class="td_cls">
            {{ item.time }}
          </td>
        </tr>
      </tbody>
    </table>
    <Button
      class="bg-blue-50 h-[40px] my-4 text-blue-300 rounded text-sm font-medium hover:text-blue-500 hover:bg-blue-100"
    >
      Try Generate Signals
    </Button>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import LiveSignalsDropdown from '../components/dropdown/LiveSignalsDropDown.vue'
import { CheckCircleIcon } from '@heroicons/vue/24/outline'

const livesignals_dropdown = ref(null)
const livesignals_dropdown_div = ref(null)

const bg_hover_color = ref('bg-gray-50')
const td_title_cls = ref(
  'px-6 py-2 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider'
)
const td_cls = ref('px-5 py-2 border-b border-gray-200 text-sm select-none')
const color_green = ref('text-green-600')
const color_red = ref('text-red-400')
const columns = ['Done', 'Name/Code', 'Direction', 'Price', 'Volume', 'Source', 'Create AT']
const positions = ref([
  {
    id: 'testid123',
    code: '000001.SZ',
    name: '平安银行',
    direction: 'long',
    price: 11.51,
    volume: 3000,
    cost: 10.866,
    source: 'Strategy Volume Active',
    time: '2020-01-01 14:43:32'
  },
  {
    id: 'testid223',
    code: '000783.SZ',
    name: '长江证券',
    direction: 'short',
    price: 5.63,
    volume: 3380,
    cost: 1.627,
    source: 'Loss Limit',
    time: '2020-01-01 14:23:32'
  }
  // 更多人员数据...
])

const done_list = ref(['testid123'])
const engine_id = defineModel()

const hover = ref(null)
watch(hover, (newValue, oldValue) => {
  // console.log(newValue)
})

function onLivePositionClick(event, item) {
  console.log(item)
  const offset_x = 4
  const offset_y = -30
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  livesignals_dropdown_div.value.style.top = y + 'px'
  livesignals_dropdown_div.value.style.left = x + 'px'
  livesignals_dropdown.value.simClick()
}

async function getData() {
  console.log('fake get signals ', engine_id.value)
}

onMounted(() => {
  getData()
})
watch(engine_id, (newValue, oldValue) => {
  getData()
})
defineExpose({ getData })
</script>
