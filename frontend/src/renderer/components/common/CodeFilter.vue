<template>
  <div v-if="codes.length > 0" class="code-filter">
    <button
      class="chip"
      :class="{ active: selected.length === 0 }"
      @click="$emit('update:selected', [])"
    >全部</button>
    <button
      v-for="c in codes"
      :key="c"
      class="chip"
      :class="{ active: selected.includes(c) }"
      @click="toggle(c)"
    >{{ c }}</button>
    <span v-if="selected.length > 0" class="hint">{{ selected.length }}/{{ codes.length }}</span>
  </div>
</template>

<script setup lang="ts">
/**
 * 标的代码多选筛选器:信号/订单/持仓记录三表共用。
 * 空 selected = 不过滤(全部);toggle 一个 code = 单看;多个 = 组合看。
 * 纯前端过滤(数据已全量在内存),无后端往返。
 */
const props = defineProps<{
  codes: string[]          // 全量候选(由调用方从数据派生去重)
  selected: string[]       // 选中集(v-model:selected)
}>()

const emit = defineEmits<{ (e: 'update:selected', v: string[]): void }>()

const toggle = (code: string) => {
  const next = props.selected.includes(code)
    ? props.selected.filter(c => c !== code)
    : [...props.selected, code]
  emit('update:selected', next)
}
</script>

<style scoped>
.code-filter {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.chip {
  padding: 2px 10px;
  border: 1px solid hsl(var(--border));
  border-radius: 999px;
  background: hsl(var(--card));
  color: hsl(var(--muted-foreground));
  font-size: 11px;
  font-family: monospace;
  cursor: pointer;
  transition: all 0.15s;
}
.chip:hover { border-color: hsl(var(--primary) / 0.5); color: hsl(var(--foreground)); }
/* 选中态样式自包含:全局 .active 可能被 scoped 默认态覆盖(记忆:radio-button 教训) */
.chip.active {
  background: hsl(var(--primary) / 0.12);
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
  font-weight: 600;
}
.hint { font-size: 11px; color: hsl(var(--muted-foreground)); margin-left: 4px; }
</style>
