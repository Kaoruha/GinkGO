<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="blue">回测</a-tag>
        {{ isCopyMode ? '复制回测' : '创建回测' }}
      </div>
    </div>

    <a-card>
      <a-form :model="form" layout="vertical" @finish="handleSubmit">
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="任务名称" name="name" :rules="[{ required: true, message: '请输入任务名称' }]">
              <a-input v-model:value="form.name" placeholder="请输入任务名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="投资组合" name="portfolio_id" :rules="[{ required: true, message: '请选择投资组合' }]">
              <a-select
                v-model:value="form.portfolio_id"
                placeholder="请选择投资组合"
                show-search
                :filter-option="filterPortfolio"
                :loading="portfolioLoading"
                :options="portfolioOptions"
                :field-names="{ label: 'label', value: 'value' }"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="8">
            <a-form-item label="开始日期" name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
              <a-date-picker
                v-model:value="form.start_date"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="结束日期" name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
              <a-date-picker
                v-model:value="form.end_date"
                style="width: 100%"
                value-format="YYYY-MM-DD"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="初始资金">
              <a-input-number
                v-model:value="form.initial_cash"
                :min="10000"
                :step="10000"
                :formatter="value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')"
                style="width: 100%"
              />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="submitting">
              {{ isCopyMode ? '创建副本' : '创建回测' }}
            </a-button>
            <a-button @click="$router.back()">取消</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { portfolioApi, type Portfolio } from '@/api/modules/portfolio'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const route = useRoute()

const form = ref({
  name: '',
  portfolio_id: undefined as string | undefined,
  start_date: undefined as string | undefined,
  end_date: undefined as string | undefined,
  initial_cash: 100000,
})

const portfolioLoading = ref(false)
const portfolioOptions = ref<Array<{ label: string; value: string }>>([])
const submitting = ref(false)

// 是否是复制模式
const isCopyMode = computed(() => route.query.copy === 'true')

// 检查是否是复制模式，预填表单
const checkCopyMode = () => {
  if (route.query.copy === 'true') {
    // 复制模式，预填表单
    if (route.query.name) form.value.name = route.query.name as string
    if (route.query.portfolio_id) form.value.portfolio_id = route.query.portfolio_id as string
    if (route.query.start_date) form.value.start_date = route.query.start_date as string
    if (route.query.end_date) form.value.end_date = route.query.end_date as string
    if (route.query.initial_cash) form.value.initial_cash = Number(route.query.initial_cash) as number
  }
}

// 加载投资组合列表
const loadPortfolios = async () => {
  portfolioLoading.value = true
  try {
    const result = await portfolioApi.list()
    portfolioOptions.value = (result.data || []).map((p: Portfolio) => ({
      label: `${p.name} (${p.mode === 0 || p.mode === 'BACKTEST' ? '回测' : p.mode === 1 || p.mode === 'PAPER' ? '模拟' : '实盘'}) - ¥${(p.initial_cash || 0).toLocaleString()}`,
      value: p.uuid
    }))
  } catch (error: any) {
    message.error(`加载投资组合失败: ${error.message || '未知错误'}`)
  } finally {
    portfolioLoading.value = false
  }
}

// 投资组合搜索过滤
const filterPortfolio = (input: string, option: { label: string; value: string }) => {
  return option.label.toLowerCase().includes(input.toLowerCase())
}

// 提交表单
const handleSubmit = async () => {
  submitting.value = true
  try {
    const result = await backtestApi.create({
      name: form.value.name,
      portfolio_id: form.value.portfolio_id,
      start_date: form.value.start_date,
      end_date: form.value.end_date,
      config_snapshot: {
        initial_cash: form.value.initial_cash
      }
    }) as BacktestTask

    message.success(isCopyMode.value ? '回测任务已复制' : '回测任务创建成功')
    // 跳转到回测详情页
    router.push(`/stage1/backtest/${result.uuid}`)
  } catch (error: any) {
    message.error(`创建失败: ${error.message || '未知错误'}`)
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  loadPortfolios()
  checkCopyMode()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
}
</style>
