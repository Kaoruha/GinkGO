<template>
  <div class="portfolio-editor">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <a-button @click="goBack">
          <ArrowLeftOutlined /> 返回
        </a-button>
        <h1>{{ isEditMode ? '编辑投资组合' : '创建投资组合' }}</h1>
      </div>
      <a-button type="primary" :loading="saving" @click="handleSave">
        <SaveOutlined /> {{ isEditMode ? '保存' : '创建' }}
      </a-button>
    </div>

    <a-card title="基本信息" style="margin-bottom: 16px">
      <a-form :model="formData" :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="组合名称" required>
          <a-input v-model:value="formData.name" placeholder="请输入组合名称" />
        </a-form-item>
        <a-form-item label="运行模式">
          <a-select v-model:value="formData.mode" :disabled="isEditMode">
            <a-select-option value="BACKTEST">回测</a-select-option>
            <a-select-option value="PAPER">模拟</a-select-option>
            <a-select-option value="LIVE">实盘</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="初始资金">
          <a-input-number v-model:value="formData.initial_cash" :min="1000" :max="100000000" :step="10000" style="width: 200px">
            <template #prefix>¥</template>
          </a-input-number>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="formData.desc" placeholder="组合描述（可选）" :rows="2" />
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="策略配置" style="margin-bottom: 16px">
      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="选择策略">
          <a-select v-model:value="formData.strategy_id" placeholder="请选择策略" show-search :filter-option="filterOption">
            <a-select-option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
              {{ s.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="仓位管理" style="margin-bottom: 16px">
      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="选择仓位组件">
          <a-select v-model:value="formData.sizer_id" placeholder="请选择仓位组件" allow-clear>
            <a-select-option v-for="s in sizers" :key="s.uuid" :value="s.uuid">
              {{ s.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="风险控制">
      <a-form :label-col="{ span: 4 }" :wrapper-col="{ span: 16 }">
        <a-form-item label="选择风控组件">
          <a-select v-model:value="formData.risk_ids" mode="multiple" placeholder="请选择风控组件（可多选）">
            <a-select-option v-for="r in risks" :key="r.uuid" :value="r.uuid">
              {{ r.name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons-vue'
import { componentsApi, type ComponentSummary } from '@/api/modules/components'
import { portfolioApi } from '@/api/modules/portfolio'

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

const filterOption = (input: string, option: any) => {
  return option.children?.[0]?.children?.toLowerCase().includes(input.toLowerCase())
}

const loadComponents = async () => {
  try {
    const [strategiesRes, risksRes, sizersRes] = await Promise.all([
      componentsApi.getStrategies(),
      componentsApi.getRisks(),
      componentsApi.getSizers()
    ])
    strategies.value = strategiesRes
    risks.value = risksRes
    sizers.value = sizersRes
  } catch (e: any) {
    message.error(`加载组件失败: ${e.message}`)
  }
}

const loadPortfolio = async () => {
  if (!isEditMode.value) return
  try {
    const portfolio = await portfolioApi.get(route.params.uuid as string)
    formData.name = portfolio.name
    formData.mode = portfolio.mode
    formData.initial_cash = portfolio.initial_cash
  } catch (e: any) {
    message.error(`加载组合失败: ${e.message}`)
  }
}

const handleSave = async () => {
  if (!formData.name) {
    message.warning('请输入组合名称')
    return
  }
  if (!formData.strategy_id) {
    message.warning('请选择策略')
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
      await portfolioApi.update(route.params.uuid as string, data)
      message.success('保存成功')
    } else {
      const result = await portfolioApi.create(data)
      message.success('创建成功')
      router.push(`/portfolio/${result.uuid}`)
    }
  } catch (e: any) {
    message.error(`操作失败: ${e.message}`)
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
}
</style>
