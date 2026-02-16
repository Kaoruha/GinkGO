<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-3">第三阶段</span>
        订单记录
      </div>
    </div>
    <a-card><a-table :columns="[{title:'时间'},{title:'代码'},{title:'方向'},{title:'数量'},{title:'价格'},{title:'状态'}]" /></a-card>
  </div>
</template>
<script setup lang="ts"></script>
