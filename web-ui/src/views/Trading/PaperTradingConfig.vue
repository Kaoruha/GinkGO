<template>
  <div class="paper-config">
    <div class="card">
      <div class="card-header">
        <h3>模拟盘配置</h3>
      </div>
      <div class="card-body">
        <form @submit.prevent="onFinish">
          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">账户名称</label>
              <input v-model="form.name" type="text" placeholder="输入账户名称" class="form-input" required />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">初始资金</label>
              <input v-model.number="form.initialCapital" type="number" min="100000" step="100000" class="form-input" required />
              <span style="margin-left: 8px; color: #8a8a9a;">元</span>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">滑点模型</label>
              <select v-model="form.slippageModel" class="form-select">
                <option value="fixed">固定滑点</option>
                <option value="percentage">比例滑点</option>
                <option value="none">无滑点</option>
              </select>
            </div>
          </div>

          <div v-if="form.slippageModel === 'fixed'" class="form-row">
            <div class="form-group-group">
              <label class="form-label">滑点值</label>
              <input v-model.number="form.slippageValue" type="number" min="0" max="1" step="0.001" class="form-input" />
              <span style="margin-left: 8px; color: #8a8a9a;">元</span>
            </div>
          </div>

          <div v-if="form.slippageModel === 'percentage'" class="form-row">
            <div class="form-group-group">
              <label class="form-label">滑点比例</label>
              <input v-model.number="form.slippagePct" type="number" min="0" max="1" step="0.01" class="form-input" />
              <span style="margin-left: 8px; color: #8a8a9a;">%</span>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">手续费率</label>
              <input v-model.number="form.commissionRate" type="number" min="0" max="1" step="0.001" class="form-input" />
              <span style="margin-left: 8px; color: #8a8a9a;">%</span>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">交易限制</label>
              <div class="checkbox-group">
                <label class="checkbox-label">
                  <input v-model="form.restrictions" type="checkbox" value="t1" />
                  T+1限制
                </label>
                <label class="checkbox-label">
                  <input v-model="form.restrictions" type="checkbox" value="limit" />
                  涨跌停限制
                </label>
                <label class="checkbox-label">
                  <input v-model="form.restrictions" type="checkbox" value="time" />
                  交易时间限制
                </label>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group-group">
              <label class="form-label">数据源</label>
              <div class="radio-group">
                <label class="radio-label">
                  <input v-model="form.dataSource" type="radio" value="replay" />
                  历史回放
                </label>
                <label class="radio-label">
                  <input v-model="form.dataSource" type="radio" value="paper" />
                  模拟盘实时
                </label>
              </div>
            </div>
          </div>

          <div v-if="form.dataSource === 'replay'" class="form-row">
            <div class="form-group-group">
              <label class="form-label">回放开始日期</label>
              <input v-model="form.replayDate" type="date" class="form-input" />
            </div>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary">创建模拟盘</button>
            <button type="button" class="btn-secondary" @click="$router.back()">返回</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
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
    console.log('模拟盘创建成功')
    router.push('/trading/paper')
  } catch (e) {
    console.error('创建模拟盘失败')
  }
}
</script>

<style scoped>
.paper-config {
  padding: 16px;
  max-width: 800px;
  margin: 0 auto;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.form-row {
  margin-bottom: 16px;
}

.form-group-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-label {
  min-width: 120px;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
}

.form-input,
.form-select {
  flex: 1;
  max-width: 300px;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.checkbox-group {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
}

.checkbox-label input[type="checkbox"] {
  cursor: pointer;
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
}

.radio-label input[type="radio"] {
  cursor: pointer;
}

.btn-primary {
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid #2a2a3e;
}

@media (max-width: 768px) {
  .form-group-group {
    flex-direction: column;
    align-items: flex-start;
  }

  .form-input,
  .form-select {
    width: 100%;
    max-width: none;
  }

  .form-actions {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }
}
</style>
