<template>
  <div class="portfolio-builder-container">
    <div class="page-header">
      <h1 class="page-title">因子组合构建器</h1>
      <a-space>
        <a-button @click="goBack">返回</a-button>
        <a-button type="primary" @click="savePortfolio">保存组合</a-button>
      </a-space>
    </div>

    <a-card class="factors-card">
      <template #title>已选因子</template>
      <a-table
        :columns="factorColumns"
        :data-source="selectedFactors"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'weight'">
            <a-slider v-model:value="record.weight" :min="0" :max="1" :step="0.1" />
          </template>
          <template v-if="column.dataIndex === 'action'">
            <a @click="removeFactor(record)">移除</a>
          </template>
        </template>
      </a-table>
    </a-card>

    <a-card class="config-card">
      <template #title>组合配置</template>
      <a-form layout="vertical">
        <a-form-item label="组合名称">
          <a-input v-model:value="portfolioName" placeholder="请输入组合名称" />
        </a-form-item>
        <a-form-item label="组合描述">
          <a-textarea v-model:value="portfolioDesc" placeholder="请输入组合描述" :rows="3" />
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

const router = useRouter()

const portfolioName = ref('')
const portfolioDesc = ref('')
const selectedFactors = ref<any[]>([
  { key: '1', name: '动量因子', ic: 0.05, weight: 0.5 },
  { key: '2', name: '价值因子', ic: 0.03, weight: 0.5 }
])

const factorColumns = [
  { title: '因子名称', dataIndex: 'name', width: 200 },
  { title: 'IC', dataIndex: 'ic', width: 100 },
  { title: '权重', dataIndex: 'weight', width: 200 },
  { title: '操作', dataIndex: 'action', width: 100 }
]

const goBack = () => {
  router.back()
}

const removeFactor = (record: any) => {
  selectedFactors.value = selectedFactors.value.filter(f => f.key !== record.key)
}

const savePortfolio = () => {
  if (!portfolioName.value) {
    message.warning('请输入组合名称')
    return
  }
  message.success('组合保存成功')
  router.push('/research')
}
</script>

<style scoped>
.portfolio-builder-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0;
}

.factors-card,
.config-card {
  margin-bottom: 24px;
  border-radius: 8px;
}
</style>
