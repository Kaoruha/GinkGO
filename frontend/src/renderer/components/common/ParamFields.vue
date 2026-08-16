<template>
  <div
    v-if="params && params.length > 0"
    class="item-params"
  >
    <div
      v-for="param in params"
      :key="param.name"
      class="param-row"
    >
      <label class="param-label">{{ param.label || param.name }}</label>
      <!-- number:千分位展示,focus 转裸值编辑,blur 写回并恢复千分位 -->
      <input
        v-if="param.type === 'number'"
        :value="formatNumber(config[param.name] ?? 0)"
        type="text"
        inputmode="decimal"
        class="param-input"
        @focus="e => setInputValue(e, config[param.name] ?? '')"
        @blur="e => { config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(config[param.name])) }"
      >
      <div
        v-else-if="param.type === 'boolean'"
        class="switch-container"
      >
        <input
          :id="`${idPrefix}-${param.name}`"
          v-model="config[param.name]"
          type="checkbox"
          class="switch-input"
        >
        <label
          :for="`${idPrefix}-${param.name}`"
          class="switch-label"
        />
      </div>
      <select
        v-else-if="param.type === 'select'"
        v-model="config[param.name]"
        class="param-select"
      >
        <option
          v-for="opt in param.options"
          :key="opt"
          :value="opt"
        >
          {{ opt }}
        </option>
      </select>
      <input
        v-else
        v-model="config[param.name]"
        type="text"
        class="param-input"
      >
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 四型动态参数行(number/boolean/select/text)
 *
 * 从 PortfolioFormEditor 5 个组件 section 的同构参数区抽出。
 * config 为引用共享:内部直接变异(与原 v-model="item.config[param.name]"
 * 等价),父级 formData 同步感知。
 */

interface ParamDef {
  name: string
  label?: string
  type?: string
  options?: string[]
  default?: any
}

defineProps<{
  params?: ParamDef[]
  config: Record<string, any>
  /** boolean switch 的 dom id 前缀,同页多组件实例须唯一 */
  idPrefix: string
}>()

// 千分位格式化(整数)
const formatNumber = (value: number) => {
  return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

const parseNumber = (value: string) => {
  return parseFloat(value.replace(/,/g, '')) || 0
}

const setInputValue = (e: FocusEvent, value: any) => {
  ;(e.target as HTMLInputElement).value = String(value ?? '')
}

const getInputValue = (e: FocusEvent) => (e.target as HTMLInputElement).value
</script>

<style scoped>
/* 样式自 PortfolioFormEditor 原样迁入(视觉零变化) */
.item-params {
  padding: 8px 12px;
  background: hsl(var(--border));
  border-top: 1px solid hsl(var(--secondary));
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.param-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  min-width: 80px;
}

.param-input,
.param-select {
  flex: 1;
  padding: 4px 8px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 12px;
}

.param-input:focus,
.param-select:focus {
  border-color: hsl(var(--primary));
  outline: none;
}

/* boolean 开关 */
.switch-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-input {
  display: none;
}

.switch-label {
  position: relative;
  width: 36px;
  height: 18px;
  background: hsl(var(--secondary));
  border-radius: 9999px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-label::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: hsl(var(--card));
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked + .switch-label {
  background: hsl(var(--primary));
}

.switch-input:checked + .switch-label::after {
  transform: translateX(18px);
}
</style>
