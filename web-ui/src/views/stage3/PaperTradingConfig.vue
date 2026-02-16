<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-3">第三阶段</span>
        模拟交易配置
      </div>
    </div>
    <a-card>
      <a-form layout="vertical">
        <a-form-item label="滑点模型"><a-select><a-select-option>固定滑点</a-select-option></a-select></a-form-item>
        <a-form-item label="滑点值"><a-input-number :value="0.01" /></a-form-item>
        <a-form-item><a-button type="primary">保存配置</a-button></a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
<script setup lang="ts"></script>
