<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-2">第二阶段</span>
        走步验证
      </div>
    </div>
    <a-card>
      <a-form layout="inline">
        <a-form-item label="折数"><a-input-number :value="5" :min="2" :max="10" /></a-form-item>
        <a-form-item label="训练比例"><a-input-number :value="0.7" :min="0.5" :max="0.9" :step="0.1" /></a-form-item>
        <a-form-item><a-button type="primary">开始验证</a-button></a-form-item>
      </a-form>
      <a-divider />
      <p>走步验证结果将显示在这里...</p>
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
