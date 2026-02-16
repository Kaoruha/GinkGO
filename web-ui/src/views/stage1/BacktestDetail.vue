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
      <div class="chart-container">
        <div style="color: #999; text-align: center; padding: 100px 0;">净值曲线图表</div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
// 回测详情页面
</script>
