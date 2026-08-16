<template>
  <!--
    SegmentedControl — 胶囊分段控件(规范见 frontend/docs/tab-component-spec.md)
    用于数据过滤 / 表单单选(非导航)。active 填充 primary 实色,自包含,不依赖全局。
  -->
  <div class="segmented">
    <button
      v-for="opt in options"
      :key="opt.key"
      class="seg-btn"
      :class="{ on: modelValue === opt.key }"
      @click="emit('update:modelValue', opt.key)"
    >
      {{ opt.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
interface Option {
  key: string
  label: string
}

defineProps<{
  options: Option[]
  modelValue: string
}>()

const emit = defineEmits<{ 'update:modelValue': [key: string] }>()
</script>

<style scoped>
.segmented {
  display: inline-flex;
  background: hsl(var(--muted));
  border-radius: var(--radius-lg);
  padding: 3px;
  gap: 2px;
}

.seg-btn {
  padding: 6px 14px;
  font-size: 12px;
  border-radius: var(--radius);
  border: none;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  font-family: inherit;
  line-height: 1.4;
  transition: color 0.15s;
}

.seg-btn:hover {
  color: hsl(var(--foreground));
}

.seg-btn.on {
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-weight: 500;
}
</style>
