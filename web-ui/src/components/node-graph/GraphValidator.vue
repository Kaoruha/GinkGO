<template>
  <div class="graph-validator">
    <div class="validator-header">
      <div
        class="validator-status"
        :class="{ success: isValid, error: !isValid }"
      >
        <svg v-if="isValid" class="status-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <svg v-else class="status-icon" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="15" y1="9" x2="9" y2="15"></line>
          <line x1="9" y1="9" x2="15" y2="15"></line>
        </svg>
        <span class="status-text">{{ isValid ? '验证通过' : '验证失败' }}</span>
      </div>
      <button
        class="btn-icon"
        @click="$emit('close')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>

    <div class="validator-content">
      <!-- Custom -->
      <div
        v-if="errors.length > 0"
        class="error-section"
      >
        <div class="section-header">
          <svg class="section-icon error" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.16L6 14h12l2.47-7.84a2 2 0 0 0 .71-3.16L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="17"></line>
            <line x1="8" y1="13" x2="16" y2="13"></line>
          </svg>
          <span>错误 ({{ errors.length }})</span>
        </div>
        <div class="error-list">
          <div
            v-for="error in errors"
            :key="error.edge_id || error.node_id || error.message"
            class="error-item"
            @click="handleErrorClick(error)"
          >
            <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.16L6 14h12l2.47-7.84a2 2 0 0 0 .71-3.16L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
              <line x1="12" y1="9" x2="12" y2="17"></line>
              <line x1="8" y1="13" x2="16" y2="13"></line>
            </svg>
            <span class="error-message">{{ error.message }}</span>
            <span
              v-if="error.node_id"
              class="tag"
            >
              节点
            </span>
            <span
              v-if="error.edge_id"
              class="tag"
            >
              连接
            </span>
          </div>
        </div>
      </div>

      <!-- Custom -->
      <div
        v-if="warnings.length > 0"
        class="warning-section"
      >
        <div class="section-header">
          <svg class="section-icon warning" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
          <span>警告 ({{ warnings.length }})</span>
        </div>
        <div class="warning-list">
          <div
            v-for="warning in warnings"
            :key="warning"
            class="warning-item"
          >
            <svg class="warning-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span class="warning-message">{{ warning }}</span>
          </div>
        </div>
      </div>

      <!-- Custom -->
      <div
        v-if="errors.length === 0 && warnings.length === 0"
        class="empty-state"
      >
        <svg class="empty-icon" xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <p>节点图配置完全正确</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ValidationResult } from './types'

interface Props {
  validationResult: ValidationResult
}

const props = defineProps<Props>()
const emit = defineEmits(['close', 'error-click'])

const isValid = computed(() => props.validationResult.is_valid)
const errors = computed(() => props.validationResult.errors || [])
const warnings = computed(() => props.validationResult.warnings || [])

// 处理错误点击
const handleErrorClick = (error: any) => {
  emit('error-click', error)
}
</script>

<style scoped>
.graph-validator {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.validator-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a3e;
}

.validator-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.validator-status.success .status-icon {
  color: #52c41a;
}

.validator-status.error .status-icon {
  color: #f5222d;
}

.validator-status .status-icon {
  width: 16px;
  height: 16px;
}

.validator-status .status-text {
  font-weight: 500;
  color: #ffffff;
}

.validator-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.error-section,
.warning-section {
  margin-bottom: 16px;
}

.error-section:last-child,
.warning-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 500;
  color: #ffffff;
}

.section-icon {
  width: 16px;
  height: 16px;
}

.section-icon.error {
  color: #f5222d;
}

.section-icon.warning {
  color: #faad14;
}

.error-list,
.warning-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-item,
.warning-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #2a2a3e;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s;
}

.error-item:hover,
.warning-item:hover {
  background: #3a3a4e;
}

.error-icon,
.warning-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
}

.error-icon {
  color: #f5222d;
}

.warning-icon {
  color: #faad14;
}

.error-message,
.warning-message {
  flex: 1;
  font-size: 12px;
  color: #ffffff;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  background: #3a3a4e;
  color: #8a8a9a;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  width: 48px;
  height: 48px;
  color: #52c41a;
  margin-bottom: 16px;
}

.empty-state p {
  margin: 0;
  color: #52c41a;
  font-size: 14px;
}

.btn-icon {
  padding: 4px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #2a2a3e;
  color: #ffffff;
}
</style>
