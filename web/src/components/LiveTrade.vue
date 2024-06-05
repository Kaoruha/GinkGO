<template>
  <div class="flex flex-col">
    <LiveRecordForm
      ref="live_record_form"
      v-model="selected_record"
      @confirmMethod="HandleTraderConfirmSubmit"
    ></LiveRecordForm>
    <ConfirmDialog
      ref="del_traderecord_dialog"
      @confirmMethod="delTradeRecord(selected_record.record_id)"
      :title="'Remove the Record'"
      :confirm_btn_text="'DELETE'"
      :msg="'Remove?'"
    >
    </ConfirmDialog>
    <table class="min-w-full leading-normal">
      <thead>
        <tr>
          <th v-for="item in columns" :class="td_title_cls">
            {{ item }}
          </th>
        </tr>
      </thead>
      <div class="z-10 absolute select-none" ref="livetrade_dropdown_div">
        <LiveTradeDropdown
          ref="livetrade_dropdown"
          @edit="live_record_form?.openModal()"
          @delete="del_traderecord_dialog?.openModal()"
        ></LiveTradeDropdown>
      </div>
      <tbody>
        <tr
          v-for="item in trade_records"
          :key="item.id"
          @mouseover="[(hover = item.code)]"
          :class="hover === item.code ? bg_hover_color : 'bg-white'"
          @contextmenu.prevent="onLiveRecordClick($event, item)"
        >
          <td :class="td_cls">
            <div class="text-gray-400">
              {{ item.timestamp }}
            </div>
            <div :class="[item.direction == 'LONG' ? color_green : color_red]">
              {{ item.direction }}
            </div>
          </td>
          <td :class="[td_cls]">
            <div>
              {{ item.name }}
            </div>
            <div class="text-gray-400">
              {{ item.code }}
            </div>
          </td>
          <td :class="td_cls">
            {{ item.price.toFixed(2) }}
          </td>
          <td :class="td_cls">
            {{ item.volume }}
          </td>
          <td :class="td_cls">
            {{ (item.price * item.volume).toFixed(2) }}
          </td>
          <td :class="td_cls">
            {{ item.fee.toFixed(2) }}
          </td>
          <td :class="td_cls">
            {{ item.desc }}
          </td>
        </tr>
      </tbody>
    </table>
    <Button
      class="bg-blue-50 h-[40px] my-4 text-blue-300 rounded text-sm font-medium hover:text-blue-500 hover:bg-blue-100"
      @click="CleanSelectedRecord(), live_record_form?.openModal()"
    >
      Add Record
    </Button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import axios from 'axios'
import { API_ENDPOINTS } from '../request.js'
import LiveTradeDropdown from '../components/dropdown/LiveTradeDropDown.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import LiveRecordForm from '../components/TradeRecordForm.vue'

const livetrade_dropdown = ref(null)
const livetrade_dropdown_div = ref(null)
const del_traderecord_dialog = ref(null)
const live_record_form = ref(null)

const bg_hover_color = ref('bg-gray-50')
const td_title_cls = ref(
  'px-6 py-2 border-b-2 border-gray-200 bg-gray-100 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider'
)
const td_cls = ref('px-5 py-2 border-b border-gray-200 text-sm select-none')
const color_green = ref('text-green-600')
const color_red = ref('text-red-400')
const columns = ['Timestamp', 'Name/Code', 'Price', 'Volume', 'Total', 'Fee', 'Description']
const trade_records = ref([
  {
    timestamp: '2020-01-03 12:23:32',
    direction: 'LONG',
    id: 'testid123',
    code: '000001.SZ',
    name: '平安银行',
    price: 11.52,
    volume: 3000,
    fee: 5
  },
  {
    timestamp: '2020-01-03 12:42:00',
    id: 'testid223',
    direction: 'SHORT',
    code: '000783.SZ',
    name: '长江证券',
    price: 5.63,
    volume: 3300,
    fee: 6.1
  }
  // 更多数据...
])

const engine_id = defineModel()

const selected_record = ref({
  record_id: 'default_id',
  code: 'default_code',
  direction: 'LONG',
  date: '',
  price: 0,
  volume: 0,
  comission: 0,
  fee: 0
})

function CleanSelectedRecord() {
  selected_record.value.record_id = ''
  selected_record.value.code = ''
  selected_record.value.direction = 'LONG'
  selected_record.value.date = ''
  selected_record.value.price = 0
  selected_record.value.volume = 0
  selected_record.value.comission = 0
  selected_record.value.fee = 0
}

watch(selected_record, (newValue, oldValue) => {
  // console.log('Live Trade Component, Selected Record Update:')
})

const hover = ref(null)
watch(hover, (newValue, oldValue) => {
  // console.log("Hover changed", newValue)
})

function onLiveRecordClick(event, item) {
  const offset_x = 4
  const offset_y = -30
  if (item != null) {
    selected_record.value.record_id = item.id
    selected_record.value.code = item.code
    selected_record.value.direction = item.direction
    selected_record.value.date = item.timestamp
    selected_record.value.price = item.price
    selected_record.value.volume = item.volume
    selected_record.value.comission = item.comission
    selected_record.value.fee = item.fee
  }
  var x = event.clientX + offset_x
  var y = event.clientY + offset_y
  livetrade_dropdown_div.value.style.top = y + 'px'
  livetrade_dropdown_div.value.style.left = x + 'px'
  livetrade_dropdown.value.simClick()
}

function HandleTraderConfirmSubmit() {
  const eid: string = engine_id.value
  const rid: string = selected_record.value.record_id
  const code: string = selected_record.value.code
  const direction: string = selected_record.value.direction
  const date: string = selected_record.value.date
  const price: number = selected_record.value.price
  const volume: comission = selected_record.value.volume
  const comission: number = selected_record.value.comission
  const fee: number = selected_record.value.fee
  if (rid == '') {
    addTradeRecord(eid, code, direction, date, price, volume, comission, fee)
  } else {
    updateTradeRecord(rid, code, direction, date, price, volume, comission, fee)
  }
}

async function getData(id: string) {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchTradeRecord + `?id=${id}`)
    const res = response.data
    if (res.length === 0) {
      console.log('No Order records found.')
      return
    }
    for (let i = 0; i < res.length; i++) {
      const item = {
        timestamp: (res[i].timestamp as string).replace("T"," "),
        direction: res[i].direction == '1' ? 'LONG' : 'SHORT',
        id: res[i].uuid as string,
        code: res[i].code as string,
        name: res[i].name as string,
        price: res[i].transaction_price as number,
        volume: res[i].volume as number,
        fee: res[i].fee as number
      }
      trade_records.value.push(item)
    }
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

function RefreshRecord() {
  trade_records.value.length = 0
  getData(engine_id.value)
}

async function addTradeRecord(
  eid: string,
  code: string,
  direction: string,
  date: string,
  price: number,
  volume: number,
  comission: number,
  fee: number
) {
    console.log(price)
  try {
    const response = await axios.post(
      API_ENDPOINTS.addTradeRecord +
        `?id=${eid}&code=${code}&direction=${direction}&date=${date}&price=${price}&volume=${volume}&comission=${comission}&fee=${fee}`
    )
    const res = response.data
  RefreshRecord()
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function updateTradeRecord(
  rid: string,
  code: string,
  direction: string,
  date: string,
  price: number,
  volume: number,
  comission: number,
  fee: number
) {
  try {
    const response = await axios.post(
      API_ENDPOINTS.updateTradeRecord +
        `?id=${rid}&code=${code}&direction=${direction}&date=${date}&price=${price}&volume=${volume}&fee=${fee}`
    )
    const res = response.data
  RefreshRecord()
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}
async function delTradeRecord(id) {
  try {
    const response = await axios.post(API_ENDPOINTS.delTradeRecord + `?id=${id}`)
    const res = response.data
    console.log(res)
  trade_records.value.length = 0
  getData(engine_id.value)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}
onMounted(() => {
  RefreshRecord()
})

watch(engine_id, (newValue, oldValue) => {
  RefreshRecord()
})
defineExpose({ getData })
</script>
