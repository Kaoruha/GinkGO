<template>
  <div class="config-section">
    <div class="section-header">
      <span class="section-title">{{ title }}</span>
      <button
        v-if="removeLabel"
        class="btn-icon text-red"
        title="移除"
        @click="$emit('remove', 0)"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <line
            x1="18"
            y1="6"
            x2="6"
            y2="18"
          />
          <line
            x1="6"
            y1="6"
            x2="18"
            y2="18"
          />
        </svg>
      </button>
    </div>
    <div class="config-list">
      <div
        v-for="(item, index) in items"
        :key="item.uuid"
        class="config-item"
      >
        <div class="item-header">
          <div class="item-info">
            <span class="item-name">{{ item.name }}</span>
            <select
              v-model="item.version"
              class="version-select"
              :disabled="versionsFor(item).length <= 1"
              @change="$emit('change-version', index, ($event.target as HTMLSelectElement).value)"
            >
              <option
                v-for="v in versionsFor(item)"
                :key="v.uuid"
                :value="v.version"
              >
                {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
              </option>
            </select>
          </div>
          <div class="item-actions">
            <template v-if="showWeight">
              <input
                v-model.number="item.weight"
                type="number"
                :min="0"
                :max="100"
                class="weight-input"
              >
              <span class="unit">%</span>
            </template>
            <button
              v-if="removable"
              class="btn-icon text-red"
              title="移除"
              @click="$emit('remove', index)"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              >
                <line
                  x1="18"
                  y1="6"
                  x2="6"
                  y2="18"
                />
                <line
                  x1="6"
                  y1="6"
                  x2="18"
                  y2="18"
                />
              </svg>
            </button>
          </div>
        </div>
        <ParamFields
          :params="item.parameters"
          :config="item.config"
          :id-prefix="`${idPrefix}-${item.uuid}`"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 组件配置 section(标题 + 条目列表)
 *
 * 从 PortfolioFormEditor 5 个同构 section(选股器/仓位/策略/风控/分析器)抽出。
 * items 为父级 formData 的引用:version/weight/config 由本组件与 ParamFields
 * 直接变异(与原 v-model 等价);结构性变更(移除/切版本)走 emit 回父级。
 */
import ParamFields from '@/components/common/ParamFields.vue'

export interface ComponentEntry {
  uuid: string
  name: string
  version?: string
  weight?: number
  parameters?: any[]
  config: Record<string, any>
}

export interface ComponentVersion {
  uuid: string
  version: string
  is_latest?: boolean
}

withDefaults(defineProps<{
  /** section 标题(含计数,如"选股器 (3)") */
  title: string
  items: ComponentEntry[]
  /** 条目可用版本查表(name+type → 版本列表) */
  versionsFor: (item: ComponentEntry) => ComponentVersion[]
  /** 策略条目显示权重输入框 */
  showWeight?: boolean
  /** 条目级移除按钮(数组 section=true) */
  removable?: boolean
  /** header 级移除按钮(单数 section 如 sizer=true) */
  removeLabel?: boolean
  /** ParamFields id 前缀(类型名,保证 boolean switch id 唯一) */
  idPrefix: string
}>(), {
  showWeight: false,
  removable: true,
  removeLabel: false,
})

defineEmits<{
  remove: [index: number]
  'change-version': [index: number, version: string]
}>()
</script>

<style scoped>
/* 样式自 PortfolioFormEditor 原样迁入(视觉零变化) */
.config-section {
  margin-bottom: 12px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: hsl(var(--border));
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  overflow: hidden;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: hsl(var(--card));
}

.item-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.version-select {
  padding: 4px 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
  cursor: pointer;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weight-input {
  width: 60px;
  padding: 4px 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  text-align: center;
}

.item-actions .unit {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}
</style>
