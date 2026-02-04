<template>
  <div class="graph-validator">
    <div class="validator-header">
      <div class="validator-status" :class="{ success: isValid, error: !isValid }">
        <CheckCircleOutlined v-if="isValid" class="status-icon" />
        <CloseCircleOutlined v-else class="status-icon" />
        <span class="status-text">{{ isValid ? '验证通过' : '验证失败' }}</span>
      </div>
      <a-button type="text" size="small" @click="$emit('close')">
        <CloseOutlined />
      </a-button>
    </div>

    <div class="validator-content">
      <!-- 错误列表 -->
      <div v-if="errors.length > 0" class="error-section">
        <div class="section-header">
          <ExclamationCircleOutlined class="section-icon error" />
          <span>错误 ({{ errors.length }})</span>
        </div>
        <div class="error-list">
          <div
            v-for="error in errors"
            :key="error.edge_id || error.node_id || error.message"
            class="error-item"
            @click="handleErrorClick(error)"
          >
            <WarningOutlined class="error-icon" />
            <span class="error-message">{{ error.message }}</span>
            <a-tag v-if="error.node_id" size="small">节点</a-tag>
            <a-tag v-if="error.edge_id" size="small">连接</a-tag>
          </div>
        </div>
      </div>

      <!-- 警告列表 -->
      <div v-if="warnings.length > 0" class="warning-section">
        <div class="section-header">
          <InfoCircleOutlined class="section-icon warning" />
          <span>警告 ({{ warnings.length }})</span>
        </div>
        <div class="warning-list">
          <div v-for="warning in warnings" :key="warning" class="warning-item">
            <InfoCircleOutlined class="warning-icon" />
            <span class="warning-message">{{ warning }}</span>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="errors.length === 0 && warnings.length === 0" class="empty-state">
        <CheckCircleOutlined class="empty-icon" />
        <p>节点图配置完全正确</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  CloseOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons-vue'
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

<style scoped lang="less">
.graph-validator {
  display: flex;
  flex-direction: column;
  height: 100%;

  .validator-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #e8e8e8;

    .validator-status {
      display: flex;
      align-items: center;
      gap: 8px;

      &.success {
        .status-icon {
          color: #52c41a;
        }
      }

      &.error {
        .status-icon {
          color: #ff4d4f;
        }
      }

      .status-icon {
        font-size: 16px;
      }

      .status-text {
        font-weight: 500;
      }
    }
  }

  .validator-content {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;

    .error-section,
    .warning-section {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      font-weight: 500;

      .section-icon {
        font-size: 16px;

        &.error {
          color: #ff4d4f;
        }

        &.warning {
          color: #faad14;
        }
      }
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
      background: #fff;
      border-radius: 4px;
      cursor: pointer;

      &:hover {
        background: #f5f5f5;
      }

      .error-icon,
      .warning-icon {
        flex-shrink: 0;
      }

      .error-icon {
        color: #ff4d4f;
      }

      .warning-icon {
        color: #faad14;
      }

      .error-message,
      .warning-message {
        flex: 1;
        font-size: 12px;
      }
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 40px 20px;
      text-align: center;

      .empty-icon {
        font-size: 48px;
        color: #52c41a;
        margin-bottom: 16px;
      }

      p {
        margin: 0;
        color: #52c41a;
        font-size: 14px;
      }
    }
  }
}
</style>
