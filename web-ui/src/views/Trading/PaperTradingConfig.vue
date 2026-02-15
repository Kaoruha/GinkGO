<template>
  <div class="paper-config">
    <a-card title="模拟盘配置">
      <a-form
        :model="form"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 14 }"
        @finish="onFinish"
      >
        <a-form-item label="账户名称" name="name" :rules="[{ required: true }]">
          <a-input v-model:value="form.name" placeholder="输入账户名称" />
        </a-form-item>

        <a-form-item label="初始资金" name="initialCapital" :rules="[{ required: true }]">
          <a-input-number
            v-model:value="form.initialCapital"
            :min="100000"
            :step="100000"
            :precision="2"
            style="width: 200px"
          />
          <span style="margin-left: 8px">元</span>
        </a-form-item>

        <a-form-item label="滑点模型" name="slippageModel">
          <a-select v-model:value="form.slippageModel" style="width: 200px">
            <a-select-option value="fixed">固定滑点</a-select-option>
            <a-select-option value="percentage">比例滑点</a-select-option>
            <a-select-option value="none">无滑点</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item v-if="form.slippageModel === 'fixed'" label="滑点值" name="slippageValue">
          <a-input-number
            v-model:value="form.slippageValue"
            :min="0"
            :max="1"
            :step="0.001"
            :precision="3"
            style="width: 200px"
          />
          <span style="margin-left: 8px">元</span>
        </a-form-item>

        <a-form-item v-if="form.slippageModel === 'percentage'" label="滑点比例" name="slippagePct">
          <a-input-number
            v-model:value="form.slippagePct"
            :min="0"
            :max="1"
            :step="0.01"
            :precision="4"
            style="width: 200px"
          />
          <span style="margin-left: 8px">%</span>
        </a-form-item>

        <a-form-item label="手续费率" name="commissionRate">
          <a-input-number
            v-model:value="form.commissionRate"
            :min="0"
            :max="1"
            :step="0.001"
            :precision="4"
            style="width: 200px"
          />
          <span style="margin-left: 8px">%</span>
        </a-form-item>

        <a-form-item label="交易限制">
          <a-checkbox-group v-model:value="form.restrictions">
            <a-checkbox value="t1">T+1限制</a-checkbox>
            <a-checkbox value="limit">涨跌停限制</a-checkbox>
            <a-checkbox value="time">交易时间限制</a-checkbox>
          </a-checkbox-group>
        </a-form-item>

        <a-form-item label="数据源" name="dataSource">
          <a-radio-group v-model:value="form.dataSource">
            <a-radio value="replay">历史回放</a-radio>
            <a-radio value="paper">模拟盘实时</a-radio>
          </a-radio-group>
        </a-form-item>

        <a-form-item v-if="form.dataSource === 'replay'" label="回放开始日期" name="replayDate">
          <a-date-picker v-model:value="form.replayDate" style="width: 200px" />
        </a-form-item>

        <a-form-item :wrapper-col="{ offset: 6, span: 14 }">
          <a-space>
            <a-button type="primary" html-type="submit">创建模拟盘</a-button>
            <a-button @click="$router.back()">返回</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { createPaperAccount } from '@/api/modules/trading'
import type { CreatePaperAccount } from '@/api/modules/trading'

const router = useRouter()

const form = ref<CreatePaperAccount>({
  name: '',
  initial_capital: 1000000,
  slippage_model: 'fixed',
  slippage_value: 0.002,
  slippage_pct: 0.1,
  commission_rate: 0.03,
  restrictions: ['t1', 'limit'],
  data_source: 'paper',
  replay_date: undefined,
})

const onFinish = async (values: CreatePaperAccount) => {
  try {
    const res = await createPaperAccount(values)
    message.success('模拟盘创建成功')
    router.push('/trading/paper')
  } catch (e) {
    message.error('创建模拟盘失败')
  }
}
</script>

<style scoped>
.paper-config {
  padding: 16px;
  max-width: 800px;
}
</style>
