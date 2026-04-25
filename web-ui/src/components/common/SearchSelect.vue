<template>
  <div ref="containerRef" class="search-select">
    <div class="search-input-wrap">
      <input
        ref="inputRef"
        v-model="query"
        class="search-input"
        :placeholder="placeholder"
        @focus="onFocus"
        @keydown.down.prevent="highlightNext"
        @keydown.up.prevent="highlightPrev"
        @keydown.enter.prevent="selectHighlighted"
        @keydown.esc="close"
      />
      <svg class="search-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
    </div>
    <Teleport to="body">
      <div v-if="open && (filteredOptions.length > 0 || loading)" class="search-select-dropdown" :style="dropdownStyle">
        <div v-if="loading" class="dropdown-loading">搜索中...</div>
        <div
          v-for="(opt, idx) in filteredOptions"
          :key="opt.value"
          class="dropdown-item"
          :class="{ highlighted: idx === highlightIndex, disabled: isDisabled(opt) }"
          @click="selectItem(opt)"
          @mouseenter="highlightIndex = idx"
        >
          <span class="item-label">{{ opt.label }}</span>
          <svg v-if="isDisabled(opt)" class="item-check" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'

export interface SearchOption {
  value: string
  label: string
  data?: any
}

const props = withDefaults(defineProps<{
  placeholder?: string
  searchFn?: (query: string) => Promise<SearchOption[]>
  options?: SearchOption[]
  excludeValues?: string[]
}>(), {
  placeholder: '输入关键词搜索...',
  options: () => [],
  excludeValues: () => [],
})

const emit = defineEmits<{
  (e: 'select', option: SearchOption): void
}>()

const query = ref('')
const open = ref(false)
const loading = ref(false)
const highlightIndex = ref(-1)
const containerRef = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

function updatePosition() {
  if (!containerRef.value) return
  const rect = containerRef.value.getBoundingClientRect()
  dropdownStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 4}px`,
    left: `${rect.left}px`,
    width: `${rect.width}px`,
  }
}

const fetchedOptions = ref<SearchOption[]>([])

const filteredOptions = computed(() => {
  const source = props.searchFn ? fetchedOptions.value : props.options
  return source.filter(o => !props.excludeValues.includes(o.value))
})

async function doSearch(q: string) {
  if (!props.searchFn) return
  loading.value = true
  try {
    fetchedOptions.value = await props.searchFn(q)
    highlightIndex.value = -1
  } catch {
    fetchedOptions.value = []
  } finally {
    loading.value = false
  }
}

const debouncedSearch = useDebounceFn(doSearch, 300)

watch(query, (q) => {
  if (props.searchFn) {
    debouncedSearch(q)
  }
  highlightIndex.value = -1
})

watch(open, (v) => {
  if (v) updatePosition()
})

function onFocus() {
  open.value = true
  if (props.searchFn) {
    doSearch('')
  }
}

function isDisabled(opt: SearchOption) {
  return props.excludeValues.includes(opt.value)
}

function highlightNext() {
  if (filteredOptions.value.length === 0) return
  highlightIndex.value = (highlightIndex.value + 1) % filteredOptions.value.length
}

function highlightPrev() {
  if (filteredOptions.value.length === 0) return
  highlightIndex.value = highlightIndex.value <= 0
    ? filteredOptions.value.length - 1
    : highlightIndex.value - 1
}

function selectHighlighted() {
  if (highlightIndex.value >= 0 && highlightIndex.value < filteredOptions.value.length) {
    selectItem(filteredOptions.value[highlightIndex.value])
  }
}

function selectItem(opt: SearchOption) {
  if (isDisabled(opt)) return
  emit('select', opt)
  query.value = ''
  open.value = false
}

function close() {
  open.value = false
  query.value = ''
}

function onClickOutside(e: MouseEvent) {
  if (containerRef.value && !containerRef.value.contains(e.target as Node)) {
    close()
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>

<style>
.search-select { position: relative; }
.search-input-wrap { position: relative; display: flex; align-items: center; }
.search-input {
  width: 100%;
  padding: 8px 12px 8px 32px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}
.search-input:focus { border-color: #1890ff; }
.search-input::placeholder { color: #6a6a7a; }
.search-icon {
  position: absolute;
  left: 10px;
  color: #6a6a7a;
  pointer-events: none;
}
.search-select-dropdown {
  background: #1a1a2e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  max-height: 240px;
  overflow-y: auto;
  z-index: 1100;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.dropdown-loading {
  padding: 12px;
  text-align: center;
  color: #6a6a7a;
  font-size: 13px;
}
.dropdown-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
  color: #fff;
  transition: background 0.1s;
}
.dropdown-item.highlighted { background: #2a2a3e; }
.dropdown-item.disabled {
  color: #5a5a6a;
  cursor: default;
  background: none;
}
.item-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.item-check { color: #52c41a; flex-shrink: 0; }
</style>
