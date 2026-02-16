<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-2">第二阶段</span>
        蒙特卡洛模拟
      </div>
    </div>
    <a-card>
      <a-row :gutter="16">
        <a-col :span="6"><a-statistic title="VaR (95%)" :value="-3.2" suffix="%" /></a-col>
        <a-col :span="6"><a-statistic title="CVaR (95%)" :value="-4.8" suffix="%" /></a-col>
        <a-col :span="6"><a-statistic title="模拟次数" :value="10000" /></a-col>
        <a-col :span="6"><a-statistic title="损失概率" :value="15.3" suffix="%" /></a-col>
      </a-row>
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
