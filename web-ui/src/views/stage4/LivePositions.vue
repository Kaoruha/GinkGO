<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-4">第四阶段</span>
        持仓管理
      </div>
    </div>
    <a-card>
      <a-table :columns="[{title:'代码'},{title:'名称'},{title:'持仓量'},{title:'可用量'},{title:'成本价'},{title:'现价'},{title:'市值'},{title:'盈亏'},{title:'操作'}]" />
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
