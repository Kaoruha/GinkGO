<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="stage-badge stage-1">第一阶段</span>
        创建回测
      </div>
    </div>

    <a-card>
      <a-form :model="form" layout="vertical" @finish="handleSubmit">
        <a-row :gutter="24">
          <a-col :span="12">
            <a-form-item label="策略名称" name="strategyName" :rules="[{ required: true }]">
              <a-input v-model:value="form.strategyName" placeholder="请输入策略名称" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="选择策略" name="strategyId" :rules="[{ required: true }]">
              <a-select v-model:value="form.strategyId" placeholder="请选择策略">
                <a-select-option value="1">动量策略</a-select-option>
                <a-select-option value="2">均值回归策略</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="24">
          <a-col :span="8">
            <a-form-item label="开始日期" name="startDate" :rules="[{ required: true }]">
              <a-date-picker v-model:value="form.startDate" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="结束日期" name="endDate" :rules="[{ required: true }]">
              <a-date-picker v-model:value="form.endDate" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="初始资金" name="initialCapital" :rules="[{ required: true }]">
              <a-input-number v-model:value="form.initialCapital" :min="10000" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit">开始回测</a-button>
            <a-button @click="$router.back()">取消</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = ref({
  strategyName: '',
  strategyId: undefined,
  startDate: null,
  endDate: null,
  initialCapital: 1000000,
})

const handleSubmit = () => {
  // TODO: 提交回测任务
  router.push('/stage1/backtest')
}
</script>
