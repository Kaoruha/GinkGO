<template>
  <div class="h-full" id="chartCandle" />
</template>

<script setup>
import axios from 'axios'
import * as echarts from 'echarts'
import { API_ENDPOINTS } from '../request.js'
import { CanvasRenderer } from 'echarts/renderers'
import { CandlestickChart, LineChart } from 'echarts/charts'
import { UniversalTransition } from 'echarts/features'
import {
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  MarkPointComponent,
  MarkAreaComponent,
  MarkLineComponent
} from 'echarts/components'

import VChart, { THEME_KEY } from 'vue-echarts'
import { ref, onMounted } from 'vue'

onMounted(() => {
  init()
})

echarts.use([
  TitleComponent,
  TooltipComponent,
  GridComponent,
  LegendComponent,
  DataZoomComponent,
  CandlestickChart,
  LineChart,
  CanvasRenderer,
  MarkPointComponent,
  MarkAreaComponent,
  MarkLineComponent,
  UniversalTransition
])

let chartCandle = null

const downColor = '#D05E62'
const downBorderColor = '#D05E62'
const upColor = '#38726C'
const upBorderColor = '#38726C'
const buyColor = '#69A794'
const sellColor = '#ED5A65'

let title = '上证指数123'
// Each item: open，close，lowest，highest
let raw = [
  ['2013/2/22', 2322.94, 2314.16, 2308.76, 2330.88],
  ['2013/2/25', 2320.62, 2325.82, 2315.01, 2338.78],
  ['2013/2/26', 2313.74, 2293.34, 2289.89, 2340.71],
  ['2013/2/27', 2297.77, 2313.22, 2292.03, 2324.63],
  ['2013/2/28', 2322.32, 2365.59, 2308.92, 2366.16],
  ['2013/3/1', 2364.54, 2359.51, 2330.86, 2369.65],
  ['2013/3/4', 2332.08, 2273.4, 2259.25, 2333.54],
  ['2013/3/5', 2274.81, 2326.31, 2270.1, 2328.14],
  ['2013/3/6', 2333.61, 2347.18, 2321.6, 2351.44],
  ['2013/3/7', 2340.44, 2324.29, 2304.27, 2352.02],
  ['2013/3/8', 2326.42, 2318.61, 2314.59, 2333.67],
  ['2013/3/11', 2314.68, 2310.59, 2296.58, 2320.96],
  ['2013/3/12', 2309.16, 2286.6, 2264.83, 2333.29],
  ['2013/3/13', 2282.17, 2263.97, 2253.25, 2286.33],
  ['2013/3/14', 2255.77, 2270.28, 2253.31, 2276.22],
  ['2013/3/15', 2269.31, 2278.4, 2250, 2312.08],
  ['2013/3/18', 2267.29, 2240.02, 2239.21, 2276.05],
  ['2013/3/19', 2244.26, 2257.43, 2232.02, 2261.31],
  ['2013/3/20', 2257.74, 2317.37, 2257.42, 2317.86],
  ['2013/3/21', 2318.21, 2324.24, 2311.6, 2330.81],
  ['2013/3/22', 2321.4, 2328.28, 2314.97, 2332],
  ['2013/3/25', 2334.74, 2326.72, 2319.91, 2344.89],
  ['2013/3/26', 2318.58, 2297.67, 2281.12, 2319.99],
  ['2013/3/27', 2299.38, 2301.26, 2289, 2323.48],
  ['2013/3/28', 2273.55, 2236.3, 2232.91, 2273.55],
  ['2013/3/29', 2238.49, 2236.62, 2228.81, 2246.87]
]
let data0 = splitData(raw)

function splitData(rawData) {
  const categoryData = []
  const values = []
  for (var i = 0; i < rawData.length; i++) {
    categoryData.push(rawData[i].splice(0, 1)[0])
    values.push(rawData[i])
  }
  return {
    categoryData: categoryData,
    values: values
  }
}
function calculateMA(dayCount) {
  var result = []
  for (var i = 0, len = data0.values.length; i < len; i++) {
    if (i < dayCount) {
      result.push('-')
      continue
    }
    var sum = 0
    for (var j = 0; j < dayCount; j++) {
      sum += +data0.values[i - j][1]
    }
    result.push((sum / dayCount).toFixed(2))
  }
  return result
}

let options = {
  title: {
    text: title,
    left: 0
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: {
      type: 'cross'
    }
  },
  legend: {
    data: ['日K', 'MA5', 'MA10', 'MA20', 'MA30']
  },
  grid: {
    left: '4%',
    right: '4%',
    bottom: '20%'
  },
  xAxis: {
    type: 'category',
    data: data0.categoryData,
    boundaryGap: false,
    axisLine: { onZero: false },
    splitLine: { show: false },
    min: 'dataMin',
    max: 'dataMax'
  },
  yAxis: {
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
      top: '85%',
      start: 50,
      end: 100
    }
  ],
  series: [
    {
      name: '日K',
      type: 'candlestick',
      data: data0.values,
      itemStyle: {
        color: upColor,
        color0: downColor,
        borderColor: upBorderColor,
        borderColor0: downBorderColor
      },
      markArea: {
        itemStyle: {
          color: 'rgba(255, 173, 177, 0.4)'
        },
        data: [
          [
            {
              name: 'Morning Peak',
              xAxis: '2013/2/22'
            },
            {
              xAxis: '2013/2/28'
            }
          ],
          [
            {
              name: 'Evening Peak',
              xAxis: '2013/3/6'
            },
            {
              xAxis: '2013/3/12'
            }
          ]
        ]
      },
      markPoint: {
        label: {
          formatter: function (param) {
            return param != null ? Math.round(param.value) + '' : ''
          }
        },
        data: [
          {
            name: 'Mark',
            coord: ['2013/3/18', 2340],
            value: 2340,
            itemStyle: {
              color: downColor
            }
          },
          {
            name: 'Mark',
            coord: ['2013/3/18', 2240],
            value: 2240,
            itemStyle: {
              color: upColor
            }
          }
        ],
        tooltip: {
          formatter: function (param) {
            return param.name + '<br>' + (param.data.coord || '')
          }
        }
      }
    },
    {
      name: 'MA5',
      type: 'line',
      data: calculateMA(5),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA10',
      type: 'line',
      data: calculateMA(10),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA20',
      type: 'line',
      data: calculateMA(20),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    },
    {
      name: 'MA30',
      type: 'line',
      data: calculateMA(30),
      smooth: true,
      lineStyle: {
        opacity: 0.5
      }
    }
  ]
}

function updateTitle(text) {
  title = text
  options.title.text = title
}

function updateRaw(data) {
  raw = []
  for (let i = 0; i < data.length; i++) {
    let time = data[i].timestamp
    time = time.split('T')[0]
    let open = data[i].open.toFixed(2)
    let close = data[i].close.toFixed(2)
    let high = data[i].high.toFixed(2)
    let low = data[i].low.toFixed(2)
    raw.push([time, open, close, low, high])
  }
  data0 = splitData(raw)
  options.xAxis = {
    type: 'category',
    data: data0.categoryData,
    boundaryGap: false,
    axisLine: { onZero: false },
    splitLine: { show: false },
    min: 'dataMin',
    max: 'dataMax'
  }
  options.series[0].data = data0.values
  options.series[1].data = calculateMA(5)
  options.series[1].name = 'MA5'
  options.series[2].data = calculateMA(10)
  options.series[2].name = 'MA10'
  options.series[3].data = calculateMA(20)
  options.series[3].name = 'MA20'
  options.series[4].data = calculateMA(30)
  options.series[4].name = 'MA30'
}

function updateCandle(back_id, code, date) {
  updateStockInfo(code).then((result) => {
    updateTitle(title)
  })
  updateChart(code, date).then((result) => {
    chartCandle.setOption(options)
  })
  getSignals(back_id, code).then((result) => {
    chartCandle.setOption(options)
  })
  getOrderFilleds(back_id, code).then((result) => {})
}

async function updateStockInfo(code) {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchStockInfo + `?code=${code}`)
    const res = response.data
    if (res == null) {
      console.log('Get nothing about ', code)
      return
    }
    updateTitle(res.code + ' ' + res.code_name + ' ' + res.industry)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function updateChart(code, date) {
  try {
    const response = await axios.get(API_ENDPOINTS.fetchDaybar + `?code=${code}&date=${date}`)
    const res = response.data
    updateRaw(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function getSignals(back_id, code) {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchSignal + `?code=${code}&backtest_id=${back_id}`
    )
    const res = response.data
    updateSignalMarks(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

async function getOrderFilleds(back_id, code) {
  try {
    const response = await axios.get(
      API_ENDPOINTS.fetchOrderFilled + `?code=${code}&backtest_id=${back_id}`
    )
    const res = response.data
    updateOrderMarks(res)
  } catch (error) {
    console.error('请求API时出错:', error)
  }
}

function updateOrderMarks(signals) {
  options.series[0].markPoint.data = []
  for (var i = 0; i < signals.length; i++) {
    const atom = signals[i]
    const date = atom.timestamp.split('T')[0]
    const price = atom.transaction_price
    const volume = atom.volume
    let item1 = {
      name: 'Mark',
      coord: [date, price],
      value: volume,
      itemStyle: {
        color: sellColor
      }
    }
    if (atom.direction == 1) {
      item1.itemStyle.color = buyColor
    } else {
    }
    options.series[0].markPoint.data.push(item1)
  }
}

function updateSignalMarks(signals) {
  options.series[0].markArea.data = []
  console.log(signals)
  let array = []
  let tag = 1
  let period = []
  for (var i = 0; i < signals.length; i++) {
    let atom = signals[i]
    const date = atom.timestamp.split('T')[0]
    console.log(atom.direction, tag, date)
    if (atom.direction == tag) {
      if (tag == 1) {
        period[0] = date
      } else {
        period[1] = date
        array.push(period)
        console.log('Push,', period)
        period = []
      }
      tag = tag * -1
    }
    continue
  }
  console.log(array)
  for (var i = 0; i < array.length; i++) {
    let item = [
      {
        name: 'Signal LONG',
        xAxis: array[i][0]
      },
      {
        xAxis: array[i][1]
      }
    ]
    options.series[0].markArea.data.push(item)
  }
}

defineExpose({
  updateCandle
})

function init() {
  chartCandle = echarts.init(document.getElementById('chartCandle'))
  chartCandle.setOption(options)
}
</script>
