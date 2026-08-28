<template>
  <div class="csp">
    <!-- 同步范围:supportsAll=false 时隐藏切换(该命令只支持自选) -->
    <div
      v-if="supportsAll"
      class="csp-scope"
    >
      <SegmentedControl
        :model-value="modelValue.scope"
        :options="SCOPE_OPTIONS"
        @update:model-value="onScopeChange"
      />
    </div>

    <!-- effectiveScope:supportsAll=false 时强制 select——切换器隐藏但 scope
         初始值可能是 'all'(宿主默认),不强制则选择器永远不渲染,
         tick 等仅自选命令"无法选择code"(2026-08-19 实测) -->
    <div
      v-if="effectiveScope === 'select'"
      class="csp-picker"
    >
      <div
        v-if="modelValue.codes.length"
        class="picked-row"
      >
        <span
          v-for="c in modelValue.codes"
          :key="c.code"
          class="picked-tag"
        >
          {{ c.code }} {{ c.name }}
          <button
            type="button"
            class="picked-x"
            @click="removeCode(c.code)"
          >✕</button>
        </span>
      </div>
      <input
        v-model="codeQuery"
        type="text"
        class="form-input"
        :placeholder="placeholder"
        @input="onQueryInput"
        @focus="onQueryInput"
        @blur="sugVisible = false"
      >
      <div
        v-if="sugVisible"
        class="sug-box"
      >
        <p
          v-if="sugLoading"
          class="sug-hint"
        >
          搜索中...
        </p>
        <p
          v-else-if="!codeQuery.trim()"
          class="sug-hint"
        >
          输入代码或名称搜索
        </p>
        <p
          v-else-if="suggestions.length === 0"
          class="sug-hint"
        >
          无匹配结果
        </p>
        <template v-else>
          <button
            v-for="s in suggestions"
            :key="s.code"
            type="button"
            class="sug-item"
            :class="{ 'is-picked': isPicked(s.code) }"
            @mousedown.prevent="pickCode(s)"
          >
            <span class="sug-code">{{ s.code }}</span>
            <span class="sug-name">{{ s.name }}</span>
          </button>
          <p class="sug-footer">
            共 {{ sugTotal }} 条{{ sugTotal > suggestions.length ? `，显示前 ${suggestions.length} 条，可输入更精确关键词` : '' }}
          </p>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 代码范围选择器(2026-08-18 自 DataSync 表单抽出):
 * "全市场 / 自选代码"范围切换 + 股票搜索建议 + 已选 chips,整块内聚。
 *
 * 各种命令(bars/ticks/adjustfactor 同步、未来的批量操作入口)声明式复用:
 *   <CodeScopePicker v-model="scope" :supports-all="cmd.supportsAll" />
 * 命令差异由 props 表达(supportsAll=false 只能自选),不再每处各写一份
 * 搜索/建议/chips 逻辑。
 */
import { ref, computed } from 'vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { dataApi } from '@/api/modules/data'
import type { StockInfo } from '@/api/modules/data'

export interface CodeScopeValue {
  scope: 'all' | 'select'
  codes: { code: string; name: string }[]
}

const props = withDefaults(defineProps<{
  modelValue: CodeScopeValue
  /** 命令是否支持全市场(不支持则隐藏范围切换,恒自选) */
  supportsAll?: boolean
  placeholder?: string
}>(), {
  supportsAll: true,
  placeholder: '搜索代码或名称，如 600519 / 平安',
})

const emit = defineEmits<{ 'update:modelValue': [v: CodeScopeValue] }>()

const SCOPE_OPTIONS = [
  { key: 'all', label: '全部市场' },
  { key: 'select', label: '自选代码' },
]

// 视图层生效的 scope:supportsAll=false 的命令恒为自选(不回写宿主数据,
// 提交侧 isAllMarket = supportsAll && scope==='all' 已天然为 false)
const effectiveScope = computed(() => (props.supportsAll ? props.modelValue.scope : 'select'))

function patch(p: Partial<CodeScopeValue>) {
  emit('update:modelValue', { ...props.modelValue, ...p })
}
function onScopeChange(key: string) {
  patch({ scope: key as 'all' | 'select' })
}

// ---- 搜索建议(防抖 + listStocks) ----
const codeQuery = ref('')
const suggestions = ref<StockInfo[]>([])
const sugTotal = ref(0)
const sugLoading = ref(false)
const sugVisible = ref(false)
let sugTimer: ReturnType<typeof setTimeout> | null = null

async function searchStocks() {
  const q = codeQuery.value.trim()
  if (!q) {
    suggestions.value = []
    sugTotal.value = 0
    sugLoading.value = false
    return
  }
  sugLoading.value = true
  try {
    const res: any = await dataApi.listStocks({ query: q, page: 1, page_size: 50 })
    const items = res?.items ?? (Array.isArray(res) ? res : [])
    suggestions.value = items
    sugTotal.value = res?.total ?? items.length
  } catch {
    suggestions.value = []
    sugTotal.value = 0
  } finally {
    sugLoading.value = false
  }
}

function onQueryInput() {
  sugVisible.value = true
  if (sugTimer) clearTimeout(sugTimer)
  sugTimer = setTimeout(searchStocks, 300)
}

function isPicked(code: string) {
  return props.modelValue.codes.some(c => c.code === code)
}
function pickCode(s: StockInfo) {
  if (!isPicked(s.code)) patch({ codes: [...props.modelValue.codes, { code: s.code, name: s.name || '' }] })
  codeQuery.value = ''
  suggestions.value = []
  sugTotal.value = 0
  sugVisible.value = false
}
function removeCode(code: string) {
  patch({ codes: props.modelValue.codes.filter(c => c.code !== code) })
}
</script>

<style scoped>
/* 样式自 DataSync 原样迁入(视觉零变化) */
.csp { display: flex; flex-direction: column; gap: 10px; }
.picked-row { display: flex; flex-wrap: wrap; gap: 6px; }
.picked-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  border: 1px solid hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.08);
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: hsl(var(--primary));
}
.picked-x {
  border: none;
  background: none;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  padding: 0 2px;
  font-size: 11px;
}
.picked-x:hover { color: hsl(var(--error)); }
.csp-picker { position: relative; }
.sug-box {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 30;
  max-height: 240px;
  overflow-y: auto;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  box-shadow: 0 4px 16px hsl(var(--foreground) / 0.12);
  padding: 4px;
}
.sug-hint, .sug-footer {
  padding: 6px 10px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  text-align: center;
}
.sug-item {
  display: flex;
  gap: 10px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: none;
  cursor: pointer;
  text-align: left;
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.sug-item:hover { background: hsl(var(--foreground) / 0.05); }
.sug-item.is-picked { opacity: 0.45; cursor: default; }
.sug-code { font-family: monospace; color: hsl(var(--foreground)); }
.sug-name { color: hsl(var(--muted-foreground)); }
</style>
