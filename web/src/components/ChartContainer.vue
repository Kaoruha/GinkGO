<template>
  <div class="h-full" ref="chartLineRef" id="chartLine" />
</template>

<script setup>
import axios from 'axios'
import * as echarts from 'echarts'
import { API_ENDPOINTS } from '../request.js'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DataZoomComponent
} from 'echarts/components'
import { ref, onMounted } from 'vue'

onMounted(() => {
  init()
})

echarts.use([
  LineChart,
  DataZoomComponent,
  CanvasRenderer,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
])

let chartLine = null

let analyzer_id = 'Analyzer ID0012'
let backtest_id = 'Backtest ID001'

const upColor = '#ec0000'
const upBorderColor = '#8A0000'
const downColor = '#00da3c'
const downBorderColor = '#008F28'

let category = [
  '2013/1/25',
  '2013/1/28',
  '2013/1/29',
  '2013/1/30',
  '2013/1/31',
  '2013/2/1',
  '2013/2/4',
  '2013/2/5',
  '2013/2/6',
  '2013/2/7',
  '2013/2/8',
  '2013/2/18',
  '2013/2/19'
]
let data = [
  2320.26, 2300, 2295.35, 2347.22, 2360.75, 2383.43, 2377.41, 2425.92, 2411, 2432.68, 2430.69,
  2416.62, 2441.91, 2420.26
]

function calculateMA(dayCount) {
  var result = []
  for (var i = 0, len = data.length; i < len; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    var sum = 0
    for (var j = 0; j < dayCount; j++) {
      sum += +data[i - j][1]
    }
    result.push(sum / dayCount)
  }
  return result
}

let options = {
  title: {
    text: analyzer_id,
    left: 0
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross'
    }
  },
  legend: {
    data: ['Analyzer', 'MA5', 'MA30']
  },
  grid: {
    left: '5%',
    right: '2%',
    bottom: '40%'
  },
  xAxis: {
    type: 'category',
    data: category,
    boundaryGap: false,
    axisLine: { onZero: false },
    splitLine: { show: false },
    triggerEvent: true,
    min: 'dataMin',
    max: 'dataMax'
  },
  yAxis: {
    type: 'value',
    scale: true,
    splitArea: {
      show: true
    }
  },
  dataZoom: [
    {
      type: 'inside',
      start: 0,
      end: 100
    },
    {
      show: true,
      type: 'slider',
      top: '70%',
      start: 0,
      end: 100
    }
  ],
  series: [
    {
      name: 'Analyzer',
      type: 'line',
      data: data,
      smooth: true
    },
    {
      name: 'MA10',
      type: 'line',
      data: calculateMA(10),
      smooth: true,
      lineStyle: {
        opacity: 0.3
      }
    },
    {
      name: 'MA30',
      type: 'line',
      data: calculateMA(30),
      smooth: true,
      lineStyle: {
        opacity: 0.3
      }
    }
  ]
}

function updateBacktestID(text) {
  backtest_id = text
}
function updateTitle(text) {
  analyzer_id = text
  options.title.text = text
}
function updateRaw(new_data) {
  if (data.length === 0) {
    return
  }
  category = []
  data = []
  for (let i = 0; i < new_data.length; i++) {
    category.push(new_data[i]['timestamp'].split('T')[0])
    data.push(new_data[i]['value'])
  }
  options.xAxis.data = category
  options.series[0].data = data
  options.series[1].data = calculateMA(10)
  options.series[1].name = 'MA5'
  options.series[2].data = calculateMA(30)
  options.series[2].name = 'MA30'
}

async function getData(back_id, ana_id) {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchAnalyzer + `?backtest_id=${back_id}&analyzer_id=${ana_id}`
    )
    const res = response.data
    updateRaw(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

function updateLine(back_id, ana_id, ana_name) {
  updateBacktestID(back_id)
  updateTitle(ana_id)
  getData(back_id, ana_id).then(() => {
    chartLine.setOption(options)
  })
  emit('parentMethod', category[0])
}

const emit = defineEmits(['parentMethod'])

defineExpose({
  updateLine
})

function init() {
  chartLine = echarts.init(document.getElementById('chartLine'))
  chartLine.setOption(options)
  chartLine.on('click', (params) => {
    emit('parentMethod', params.name)
  })
}
</script>
