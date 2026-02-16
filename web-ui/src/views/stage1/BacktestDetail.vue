<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-1">第一阶段</span>
        回测详情
      </div>
    </div>

    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="总收益" :value="12.5" suffix="%" :value-style="{ color: '#52c41a' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="夏普比率" :value="1.85" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="最大回撤" :value="-8.3" suffix="%" :value-style="{ color: '#f5222d' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card">
          <a-statistic title="胜率" :value="58.6" suffix="%" />
        </a-card>
      </a-col>
    </a-row>

    <a-card title="净值曲线">
      <NetValueChart :data="netValueData" :benchmark-data="benchmarkData" :height="350" />
    </a-card>

    <a-card title="收益分布" style="margin-top: 16px">
      <a-row :gutter="24">
        <a-col :span="12">
          <div style="text-align: center; padding: 20px; color: #999;">月度收益柱状图</div>
        </a-col>
        <a-col :span="12">
          <div style="text-align: center; padding: 20px; color: #999;">收益分布直方图</div>
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NetValueChart } from '@/components/charts'
import type { LineData } from 'lightweight-charts'

// 模拟净值数据
const netValueData = ref<LineData[]>([
  { time: '2023-01-01', value: 1.0 },
  { time: '2023-02-01', value: 1.05 },
  { time: '2023-03-01', value: 1.03 },
  { time: '2023-04-01', value: 1.08 },
  { time: '2023-05-01', value: 1.12 },
  { time: '2023-06-01', value: 1.10 },
  { time: '2023-07-01', value: 1.15 },
  { time: '2023-08-01', value: 1.18 },
  { time: '2023-09-01', value: 1.14 },
  { time: '2023-10-01', value: 1.20 },
  { time: '2023-11-01', value: 1.22 },
  { time: '2023-12-01', value: 1.25 },
])

const benchmarkData = ref<LineData[]>([
  { time: '2023-01-01', value: 1.0 },
  { time: '2023-02-01', value: 1.02 },
  { time: '2023-03-01', value: 1.01 },
  { time: '2023-04-01', value: 1.03 },
  { time: '2023-05-01', value: 1.05 },
  { time: '2023-06-01', value: 1.04 },
  { time: '2023-07-01', value: 1.06 },
  { time: '2023-08-01', value: 1.05 },
  { time: '2023-09-01', value: 1.03 },
  { time: '2023-10-01', value: 1.07 },
  { time: '2023-11-01', value: 1.08 },
  { time: '2023-12-01', value: 1.10 },
])
</script>
