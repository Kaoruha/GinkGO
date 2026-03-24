<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-blue">回测</span>
        {{ isCopyMode ? '复制回测' : '创建回测' }}
      </div>
    </div>

    <div class="card">
      <form @submit.prevent="handleSubmit">
        <div class="form-row">
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">任务名称 <span class="required">*</span></label>
              <input
                v-model="form.name"
                type="text"
                placeholder="请输入任务名称"
                class="form-input"
                required
              />
            </div>
          </div>
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">投资组合 <span class="required">*</span></label>
              <select
                v-model="form.portfolio_id"
                class="form-select"
                required
                :disabled="portfolioLoading"
              >
                <option value="">请选择投资组合</option>
                <option v-for="option in portfolioOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>
          </div>
        </div>

        <div class="form-row">
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">开始日期 <span class="required">*</span></label>
              <input
                v-model="form.start_date"
                type="date"
                class="form-input"
                required
              />
            </div>
          </div>
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">结束日期 <span class="required">*</span></label>
              <input
                v-model="form.end_date"
                type="date"
                class="form-input"
                required
              />
            </div>
          </div>
          <div class="form-col">
            <div class="form-group">
              <label class="form-label">初始资金</label>
              <input
                v-model.number="form.initial_cash"
                type="number"
                :min="10000"
                :step="10000"
                class="form-input"
              />
            </div>
          </div>
        </div>

        <div class="form-actions">
          <button type="submit" class="btn btn-primary" :disabled="submitting">
            {{ submitting ? '提交中...' : (isCopyMode ? '创建副本' : '创建回测') }}
          </button>
          <button type="button" class="btn btn-secondary" @click="$router.back()">取消</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { portfolioApi, type Portfolio } from '@/api/modules/portfolio'
import { backtestApi, type BacktestTask } from '@/api/modules/backtest'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

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
    showToast(`加载投资组合失败: ${error.message || '未知错误'}`, 'error')
  } finally {
    portfolioLoading.value = false
  }
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

    showToast(isCopyMode.value ? '回测任务已复制' : '回测任务创建成功')
    // 跳转到回测详情页
    router.push(`/stage1/backtest/${result.uuid}`)
  } catch (error: any) {
    showToast(`创建失败: ${error.message || '未知错误'}`, 'error')
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
  color: #ffffff;
}

/* Card */
.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 24px;
}

/* Form */
.form-row {
  display: flex;
  gap: 24px;
  margin-bottom: 0;
}

.form-col {
  flex: 1;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 6px;
}

.required {
  color: #f5222d;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.form-input:disabled,
.form-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

/* Button */
.btn {
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: transparent;
  border: 1px solid #3a3a4e;
  color: #ffffff;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}
</style>
