<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-3">第三阶段</span>
        模拟交易
        <a-tag color="blue" style="margin-left: 8px">运行中</a-tag>
      </div>
      <div class="page-actions">
        <a-button type="primary" danger>停止</a-button>
        <a-button>刷新</a-button>
      </div>
    </div>
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6"><a-card><a-statistic title="今日盈亏" :value="12500" prefix="¥" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="持仓数量" :value="5" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="可用资金" :value="500000" prefix="¥" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="运行天数" :value="30" suffix="天" /></a-card></a-col>
    </a-row>
    <a-card title="当前持仓">
      <a-table :columns="[{title:'代码'},{title:'名称'},{title:'数量'},{title:'成本'},{title:'现价'},{title:'盈亏'}]" />
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
