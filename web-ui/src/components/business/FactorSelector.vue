<template>
  <div class="factor-selector">
    <a-card title="因子选择" size="small">
      <template #extra>
        <a-input-search
          v-model:value="searchText"
          placeholder="搜索因子"
          style="width: 200px"
          allow-clear
          @search="handleSearch"
        />
      </template>

      <a-tabs v-model:active-tab="categoryTab" size="small">
        <a-tab-pane key="all" tab="全部因子">
          <factor-list
            :factors="filteredFactors"
            :multiple="multiple"
            :selected="selectedFactors"
            @update:selected="handleSelect"
          />
        </a-tab-pane>
        <a-tab-pane key="technical" tab="技术因子">
          <factor-list
            :factors="technicalFactors"
            :multiple="multiple"
            :selected="selectedFactors"
            @update:selected="handleSelect"
          />
        </a-tab-pane>
        <a-tab-pane key="fundamental" tab="基本面因子">
          <factor-list
            :factors="fundamentalFactors"
            :multiple="multiple"
            :selected="selectedFactors"
            @update:selected="handleSelect"
          />
        </a-tab-pane>
        <a-tab-pane key="alternative" tab="另类因子">
          <factor-list
            :factors="alternativeFactors"
            :multiple="multiple"
            :selected="selectedFactors"
            @update:selected="handleSelect"
          />
        </a-tab-pane>
      </a-tabs>
    </a-card>
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
  'update:modelValue': string[]
}>()

const searchText = ref('')

const categoryTab = ref('all')

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

// 所有因子
const allFactors = computed(() => props.factors)

// 过滤后的因子列表
const filteredFactors = computed(() => {
  let factors: Factor[] = []

  switch (categoryTab.value) {
    case 'all':
      factors = allFactors.value
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

// 搜索处理
const handleSearch = (value: string) => {
  searchText.value = value
}

// 选择因子
const handleSelect = (selected: string[]) => {
  if (props.multiple) {
    if (selected.length > (props.maxCount || 10)) {
      message.warning(`最多只能选择${props.maxCount}个因子`)
      return
    }
  }
}
</script>

<style scoped>
.factor-selector {
  min-width: 300px;
}

.factor-selector :deep(.ant-card-head-title) {
  font-size: 14px;
  font-weight: 600;
}

.factor-selector :deep(.ant-card-body) {
  padding: 12px;
}

.factor-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.factor-item:hover {
  background: #f0f7fa;
}

.factor-item-name {
  font-size: 13px;
  color: #1a1a1a;
}

.factor-item-category {
  font-size: 11px;
  color: #8c8c8;
}
</style>
