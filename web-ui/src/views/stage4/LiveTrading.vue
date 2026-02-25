<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="red">实盘</a-tag>
        
        实盘监控
        <a-tag color="red" style="margin-left: 8px">实盘运行</a-tag>
      </div>
      <div class="page-actions">
        <a-button type="primary" danger>紧急停止</a-button>
        <a-button>刷新</a-button>
      </div>
    </div>
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6"><a-card><a-statistic title="总资产" :value="2150000" prefix="¥" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="今日盈亏" :value="25000" prefix="¥" :value-style="{color:'#52c41a'}" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="持仓市值" :value="1650000" prefix="¥" /></a-card></a-col>
      <a-col :span="6"><a-card><a-statistic title="可用资金" :value="500000" prefix="¥" /></a-card></a-col>
    </a-row>
    <a-row :gutter="16">
      <a-col :span="12"><a-card title="持仓明细"><a-table size="small" /></a-card></a-col>
      <a-col :span="12"><a-card title="今日委托"><a-table size="small" /></a-card></a-col>
    </a-row>
  </div>
</template>
<script setup lang="ts"></script>
