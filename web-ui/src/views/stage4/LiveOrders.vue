<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-4">第四阶段</span>
        订单管理
      </div>
    </div>
    <a-card>
      <a-table :columns="[{title:'委托时间'},{title:'代码'},{title:'方向'},{title:'委托量'},{title:'成交量'},{title:'价格'},{title:'状态'},{title:'操作'}]" />
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
