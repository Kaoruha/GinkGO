<template>
  <div class="factor-selector">
    <div class="card">
      <div class="card-header">
        <h4>因子选择</h4>
        <div class="search-box">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索因子"
            class="search-input"
            @input="handleSearch"
          />
        </div>
      </div>

      <div class="card-body">
        <div class="tabs-header">
          <button
            v-for="tab in categoryTabs"
            :key="tab.key"
            class="tab-button"
            :class="{ active: categoryTab === tab.key }"
            @click="categoryTab = tab.key"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="tab-content">
          <div class="factor-list">
            <div
              v-for="factor in currentFactors"
              :key="factor.name"
              class="factor-item"
              :class="{ selected: selectedFactors.includes(factor.name) }"
              @click="toggleFactor(factor.name)"
            >
              <span class="factor-name">{{ factor.label || factor.name }}</span>
              <span class="factor-category">{{ getCategoryLabel(factor.category) }}</span>
            </div>
            <div v-if="currentFactors.length === 0" class="empty-state">
              <p>暂无因子</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

/**
 * 因子选择器组件
 * 提供因子分类、搜索、多选功能
 */

interface Factor {
  name: string
  label: string
  category: 'technical' | 'fundamental' | 'alternative'
  description?: string
}

interface Props {
  factors: Factor[]
  modelValue?: string[]
  multiple?: boolean
  maxCount?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  multiple: true,
  maxCount: 10,
  loading: false
})

const emit = defineEmits<{
  'update:modelValue': [val: string[]]
}>()

const searchText = ref('')

const categoryTab = ref('all')

const categoryTabs = [
  { key: 'all', label: '全部因子' },
  { key: 'technical', label: '技术因子' },
  { key: 'fundamental', label: '基本面因子' },
  { key: 'alternative', label: '另类因子' }
]

const categoryLabels: Record<string, string> = {
  technical: '技术',
  fundamental: '基本面',
  alternative: '另类'
}

// 按类别分组
const technicalFactors = computed(() =>
  props.factors.filter(f => f.category === 'technical')
)

const fundamentalFactors = computed(() =>
  props.factors.filter(f => f.category === 'fundamental')
)

const alternativeFactors = computed(() =>
  props.factors.filter(f => f.category === 'alternative')
)

// 当前显示的因子列表
const currentFactors = computed(() => {
  let factors: Factor[] = []

  switch (categoryTab.value) {
    case 'all':
      factors = props.factors
      break
    case 'technical':
      factors = technicalFactors.value
      break
    case 'fundamental':
      factors = fundamentalFactors.value
      break
    case 'alternative':
      factors = alternativeFactors.value
      break
  }

  // 关键词搜索
  if (searchText.value) {
    const keyword = searchText.value.toLowerCase()
    factors = factors.filter(f =>
      f.name.toLowerCase().includes(keyword) ||
      f.label?.toLowerCase().includes(keyword)
    )
  }

  return factors
})

// 已选因子
const selectedFactors = computed({
  get: () => props.modelValue || [],
  set: (val: string[]) => emit('update:modelValue', val)
})

const getCategoryLabel = (category: string) => {
  return categoryLabels[category] || category
}

// 搜索处理
const handleSearch = () => {
  // 触发计算属性更新
}

// 切换因子选择
const toggleFactor = (name: string) => {
  const idx = selectedFactors.value.indexOf(name)
  if (idx > -1) {
    selectedFactors.value.splice(idx, 1)
  } else {
    if (props.multiple && selectedFactors.value.length >= (props.maxCount || 10)) {
      console.warn(`最多只能选择${props.maxCount}个因子`)
      return
    }
    selectedFactors.value.push(name)
  }
}
</script>

<style scoped>
.factor-selector {
  min-width: 300px;
}

.card {
  background: hsl(var(--card));
  border-radius: 8px;
  border: 1px solid hsl(var(--border));
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.search-box {
  display: flex;
  align-items: center;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: 4px;
  padding: 6px 12px;
  width: 200px;
}

.search-box svg {
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  color: hsl(var(--foreground));
  font-size: 13px;
  padding: 0;
  margin-left: 8px;
}

.search-input:focus {
  outline: none;
}

.card-body {
  padding: 0;
}

.tabs-header {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid hsl(var(--border));
}

.tab-button {
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-button:hover {
  color: hsl(var(--foreground));
}

.tab-button.active {
  color: hsl(var(--primary));
  border-bottom-color: hsl(var(--primary));
}

.tab-content {
  padding: 12px;
}

.factor-list {
  max-height: 300px;
  overflow-y: auto;
}

.factor-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.factor-item:hover {
  background: hsl(var(--border));
}

.factor-item.selected {
  background: hsl(var(--primary) / 0.1);
  border: 1px solid hsl(var(--primary));
}

.factor-name {
  font-size: 13px;
  color: hsl(var(--foreground));
}

.factor-category {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: hsl(var(--muted-foreground));
}

.empty-state p {
  margin: 0;
  font-size: 13px;
}
</style>
