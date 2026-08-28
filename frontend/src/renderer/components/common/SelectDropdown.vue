<template>
  <div
    ref="containerRef"
    class="select-dropdown"
  >
    <button
      type="button"
      class="select-trigger"
      @click="toggle"
      @keydown.down.prevent="highlightNext"
      @keydown.up.prevent="highlightPrev"
      @keydown.enter.prevent="selectHighlighted"
      @keydown.esc="close"
    >
      <span class="select-value">{{ currentLabel }}</span>
      <svg
        class="select-caret"
        :class="{ open }"
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      ><polyline points="6 9 12 15 18 9" /></svg>
    </button>
    <Teleport to="body">
      <div
        v-if="open && options.length > 0"
        class="select-dropdown-menu"
        :style="menuStyle"
      >
        <button
          v-for="(opt, idx) in options"
          :key="opt.value"
          type="button"
          class="select-option"
          :class="{ highlighted: idx === highlightIndex, selected: opt.value === modelValue }"
          @click="select(opt)"
          @mouseenter="highlightIndex = idx"
        >
          <span class="option-label">{{ opt.label }}</span>
          <span
            v-if="opt.desc"
            class="option-desc"
          >{{ opt.desc }}</span>
          <svg
            v-if="opt.value === modelValue"
            class="option-check"
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          ><polyline points="20 6 9 17 4 12" /></svg>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

export interface DropdownOption {
  value: string
  label: string
  desc?: string
}

const props = withDefaults(defineProps<{
  modelValue: string
  options?: DropdownOption[]
}>(), {
  options: () => [],
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'change', value: string): void
}>()

const open = ref(false)
const highlightIndex = ref(-1)
const containerRef = ref<HTMLElement | null>(null)
const menuStyle = ref<Record<string, string>>({})

// 选中项 label 展示在触发器上;无匹配(初始空值)退 placeholder 语义
const currentLabel = computed(() =>
  props.options.find(o => o.value === props.modelValue)?.label || props.modelValue || '请选择',
)

function updatePosition() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  menuStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    minWidth: `${Math.max(rect.width, 220)}px`,
  }
}

function toggle() {
  if (open.value) {
    close()
  } else {
    openMenu()
  }
}

function openMenu() {
  open.value = true
  updatePosition()
  // 高亮初始落在当前选中项,↑↓ 从此处延续
  highlightIndex.value = props.options.findIndex(o => o.value === props.modelValue)
}

function close() {
  open.value = false
  highlightIndex.value = -1
}

function highlightNext() {
  if (open.value && props.options.length > 0) {
    highlightIndex.value = (highlightIndex.value + 1) % props.options.length
  } else if (props.options.length > 0) {
    openMenu()
  }
}

function highlightPrev() {
  if (!open.value || props.options.length === 0) return
  highlightIndex.value = highlightIndex.value <= 0
    ? props.options.length - 1
    : highlightIndex.value - 1
}

function selectHighlighted() {
  if (open.value && highlightIndex.value >= 0 && highlightIndex.value < props.options.length) {
    select(props.options[highlightIndex.value])
  }
}

function select(opt: DropdownOption) {
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  close()
}

watch(() => props.modelValue, () => {
  // 外部重置选中值(如切换任务)时收起菜单,避免浮层指向旧位置
  close()
})

function onClickOutside(e: MouseEvent) {
  // Teleport 菜单在 body 下,不在 containerRef 内,须单独放行
  const menu = (e.target as HTMLElement)?.closest?.('.select-dropdown-menu')
  if (menu) return
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    close()
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style>
.select-dropdown { position: relative; }
.select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  min-width: 180px;
  padding: 8px 12px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}
.select-trigger:hover { border-color: hsl(var(--primary) / 0.5); }
.select-trigger:focus-visible { border-color: hsl(var(--primary)); }
.select-value { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.select-caret {
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
  transition: transform 0.15s;
}
.select-caret.open { transform: rotate(180deg); }
.select-dropdown-menu {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  max-height: 280px;
  overflow-y: auto;
  z-index: 1100;
  box-shadow: var(--shadow-md);
  padding: 4px 0;
}
.select-option {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-areas: 'label check' 'desc check';
  column-gap: 8px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s;
}
.select-option.highlighted { background: hsl(var(--border)); }
.option-label {
  grid-area: label;
  font-size: 13px;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* desc 次要淡色:与 label 拉开层次(12px + muted) */
.option-desc {
  grid-area: desc;
  margin-top: 2px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.option-check {
  grid-area: check;
  align-self: center;
  color: hsl(var(--primary));
  flex-shrink: 0;
}
</style>
