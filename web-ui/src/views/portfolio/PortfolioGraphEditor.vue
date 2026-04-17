<template>
  <div class="portfolio-editor">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <button class="btn btn-secondary" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="19" y1="12" x2="5" y2="12"></line>
            <polyline points="12 19 5 12 12 5"></polyline>
          </svg>
          返回
        </button>
        <h1>{{ isEditMode ? '编辑投资组合' : '创建投资组合' }}</h1>
      </div>
      <button class="btn btn-primary" :disabled="saving" @click="handleSave">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
          <polyline points="17 21 17 13 7 13 7 21"></polyline>
          <polyline points="7 3 7 8 15 8"></polyline>
        </svg>
        {{ saving ? '保存中...' : (isEditMode ? '保存' : '创建') }}
      </button>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>基本信息</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">组合名称 <span class="required">*</span></label>
            <input v-model="formData.name" type="text" class="form-input" placeholder="请输入组合名称" />
          </div>
          <div class="form-group">
            <label class="form-label">运行模式</label>
            <select v-model="formData.mode" class="form-select" :disabled="isEditMode">
              <option value="BACKTEST">回测</option>
              <option value="PAPER">模拟</option>
              <option value="LIVE">实盘</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">初始资金</label>
            <div class="input-prefix-wrapper">
              <span class="input-prefix">¥</span>
              <input v-model.number="formData.initial_cash" type="number" :min="1000" :max="100000000" :step="10000" class="form-input" />
            </div>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">描述</label>
          <textarea v-model="formData.desc" class="form-textarea" placeholder="组合描述（可选）" :rows="2"></textarea>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>策略配置</h3>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="form-label">选择策略</label>
          <select v-model="formData.strategy_id" class="form-select" placeholder="请选择策略">
            <option value="">请选择策略</option>
            <option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
              {{ s.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>仓位管理</h3>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="form-label">选择仓位组件</label>
          <select v-model="formData.sizer_id" class="form-select">
            <option value="">请选择仓位组件</option>
            <option v-for="s in sizers" :key="s.uuid" :value="s.uuid">
              {{ s.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <h3>风险控制</h3>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="form-label">选择风控组件（可多选）</label>
          <div class="multi-select">
            <label v-for="r in risks" :key="r.uuid" class="checkbox-label">
              <input
                type="checkbox"
                :value="r.uuid"
                v-model="formData.risk_ids"
              />
              <span>{{ r.name }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

interface ComponentSummary {
  uuid: string
  name: string
  component_type: string
}

const router = useRouter()
const route = useRoute()

const saving = ref(false)
const strategies = ref<ComponentSummary[]>([])
const sizers = ref<ComponentSummary[]>([])
const risks = ref<ComponentSummary[]>([])

const formData = reactive({
  name: '',
  mode: 'BACKTEST',
  initial_cash: 100000,
  desc: '',
  strategy_id: undefined as string | undefined,
  sizer_id: undefined as string | undefined,
  risk_ids: [] as string[]
})

const isEditMode = computed(() => !!route.params.uuid)

const loadComponents = async () => {
  try {
    // Mock data - replace with actual API call
    strategies.value = []
    risks.value = []
    sizers.value = []
  } catch (e: any) {
    showToast(`加载组件失败: ${e.message}`, 'error')
  }
}

const loadPortfolio = async () => {
  if (!isEditMode.value) return
  try {
    // Mock data - replace with actual API call
    formData.name = 'Test Portfolio'
    formData.mode = 'BACKTEST'
    formData.initial_cash = 100000
  } catch (e: any) {
    showToast(`加载组合失败: ${e.message}`, 'error')
  }
}

const handleSave = async () => {
  if (!formData.name) {
    showToast('请输入组合名称', 'warning')
    return
  }
  if (!formData.strategy_id) {
    showToast('请选择策略', 'warning')
    return
  }

  saving.value = true
  try {
    const data = {
      name: formData.name,
      mode: formData.mode,
      initial_cash: formData.initial_cash,
      desc: formData.desc,
      strategy_id: formData.strategy_id,
      sizer_id: formData.sizer_id,
      risk_ids: formData.risk_ids
    }

    if (isEditMode.value) {
      // Mock API call
      showToast('保存成功')
    } else {
      // Mock API call
      showToast('创建成功')
      router.push('/portfolio')
    }
  } catch (e: any) {
    showToast(`操作失败: ${e.message}`, 'error')
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  router.push('/portfolio')
}

onMounted(() => {
  loadComponents()
  loadPortfolio()
})
</script>

<style scoped>
.portfolio-editor {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 20px;
  color: #ffffff;
}

/* Card */

/* Form */

.form-group:last-child {
  margin-bottom: 0;
}

.required {
  color: #f5222d;
}

.form-input:disabled,
.form-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.input-prefix-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-prefix-wrapper .form-input {
  padding-left: 28px;
}

/* Multi Select Checkbox */
.multi-select {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.checkbox-label:hover {
  border-color: #1890ff;
}

.checkbox-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.checkbox-label span {
  font-size: 13px;
  color: #ffffff;
}

/* Button */

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

</style>
