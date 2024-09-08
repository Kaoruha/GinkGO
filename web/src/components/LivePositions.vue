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
          <td :class="[td_cls]">
            <div>
              {{ item.name }}
            </div>
            <div class="text-gray-400">
              {{ item.code }}
            </div>
          </td>
          <td :class="td_cls">
            {{ item.price }}
          </td>
          <td :class="[td_cls, item.change > 0 ? color_green : color_red]">
            {{ item.change.toFixed(2) }}({{ (item.change_pct * 100).toFixed(2) }}%)
          </td>
          <td :class="td_cls">
            {{ (item.price * item.position).toFixed(2) }}
          </td>
          <td :class="td_cls">
            {{ item.position }}
          </td>
          <td :class="td_cls">
            {{ item.cost.toFixed(2) }}
          </td>
          <td :class="[td_cls, item.unrealized > 0 ? color_green : color_red]">
            {{ item.unrealized.toFixed(2) }}({{ (item.unrealized_pct * 100).toFixed(2) }}%)
          </td>
        </tr>
      </tbody>
    </table>
    <Button
      class="bg-blue-50 h-[40px] my-4 text-blue-300 rounded text-sm font-medium hover:text-blue-500 hover:bg-blue-100"
      @click = "resetPositions(engine_id)"
    >
      Refresh Positions
    </Button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import LivePositionDropdown from '../components/dropdown/LivePositionDropDown.vue'
import { API_ENDPOINTS } from '../request.js'
import axios from 'axios'

const liveposition_dropdown = ref(null)
const liveposition_dropdown_div = ref(null)

const bg_hover_color = ref('bg-gray-50')
const td_title_cls = ref(
  'px-6 py-2 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider'
)
const td_cls = ref('px-5 py-2 border-b border-gray-200 text-sm select-none')
const color_green = ref('text-green-600')
const color_red = ref('text-red-400')
const columns = [
  'Name/Code',
  'Price',
  'Change',
  'Market Value',
  'Volume',
  'Cost',
  'Unrealized Gain/Loss'
]
const positions = ref([
  {
    id: 'testid123',
    code: '000001.SZ',
    name: '平安银行',
    price: 11.51,
    change: 0.2,
    change_pct: 0.117,
    position: 3000,
    cost: 10.866,
    unrealized: 1932.0,
    unrealized_pct: 0.0593
  },
  {
    id: 'testid223',
    code: '000783.SZ',
    name: '长江证券',
    price: 5.63,
    change: -0.12,
    change_pct: -0.0209,
    position: 3380,
    cost: 1.627,
    unrealized: 13529.13,
    unrealized_pct: 2.4597
  }
  // 更多人员数据...
])

const engine_id = defineModel()

const hover = ref(null)
watch(hover, (newValue, oldValue) => {
  // console.log(newValue)
})

function onLivePositionClick(event, item) {
  const offset_x = 4
  const offset_y = -30
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  liveposition_dropdown_div.value.style.top = y + 'px'
  liveposition_dropdown_div.value.style.left = x + 'px'
  liveposition_dropdown.value.simClick()
}

async function resetPositions(id:string){
  try {
    const response = await axios.get(API_ENDPOINTS.resetLivePositions + `?id=${id}`)
    const res = response.data
    getData(engine_id.value)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function getData(id: string) {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchLivePositions + `?id=${id}`)
    const res = response.data
    if (res.length === 0) {
      console.log('No Order records found.')
      return
    }
    positions.value = []
    for (let i = 0; i < res.length; i++) {
      const item = {
        code: res[i].code,
        code_name: res[i].code_name,
        name: res[i].code_name,
        price: res[i].price,
        change: res[i].change,
        change_pct: res[i].change_pct,
        position: res[i].volume,
        cost: res[i].cost,
        unrealized: res[i].unrealized,
        unrealized_pct: res[i].unrealized_pct
      }

      positions.value.push(item)
    }
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

watch(engine_id, (newValue, oldValue) => {
  positions.value.length = 0
  getData(engine_id.value)
})

onMounted(() => {
  positions.value.length = 0
  getData(engine_id.value)
})

defineExpose({ getData })
</script>
