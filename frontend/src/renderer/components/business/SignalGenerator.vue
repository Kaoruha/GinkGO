<template>
  <div class="signal-generator">
    <div class="card">
      <div class="card-header">
        <h4>策略信号生成器</h4>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">信号类型</label>
            <select v-model="form.signalType" class="form-select">
              <option value="price_cross">价格交叉</option>
              <option value="momentum">动量</option>
              <option value="mean_reversion">均值回归</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">触发条件</label>
            <select v-model="form.trigger" class="form-select">
              <option value="above">突破上方</option>
              <option value="below">跌破下方</option>
              <option value="percent">涨跌幅</option>
            </select>
          </div>
        </div>

        <div class="divider"></div>

        <div class="form-group">
          <label class="form-label">第一资产</label>
          <select v-model="form.asset1" class="form-select">
            <option value="">请选择</option>
            <option value="000001.SZ">平安银行</option>
            <option value="000002.SZ">招商银行</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label">第二资产</label>
          <select v-model="form.asset2" class="form-select">
            <option value="">请选择</option>
            <option value="510300.SH">上证50ETF</option>
            <option value="159919.SH">深证100ETF</option>
          </select>
        </div>

        <div class="divider"></div>

        <div class="form-group">
          <label class="form-label">价差阈值 (%)</label>
          <input v-model.number="form.threshold" type="number" min="0.1" max="5" step="0.1" class="form-input" />
        </div>

        <div class="form-group">
          <label class="form-label">开仓价格</label>
          <SegmentedControl
            v-model="form.openPrice"
            :options="[
              { key: 'open', label: '开盘价' },
              { key: 'close', label: '收盘价' },
              { key: 'mid', label: '中间价' },
              { key: 'fixed', label: '固定价格' },
            ]"
          />
        </div>

        <div class="form-actions">
          <button class="btn-primary" @click="generateSignal">生成信号</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'

/**
 * 策略信号生成器组件
 * 用于生成交易信号（配对、动量等）
 */

const form = reactive({
  signalType: 'price_cross',
  trigger: 'above',
  asset1: '000001.SZ',
  asset2: '000002.SZ',
  threshold: 2,
  openPrice: 'open'
})

const emit = defineEmits<{
  generate: [data: typeof form]
}>()

const generateSignal = () => {
  emit('generate', form)
}
</script>

<style scoped>
.signal-generator {
  min-width: 300px;
}

.card {
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  border: 1px solid hsl(var(--border));
}

.card-header {
  padding: 12px 16px;
  border-bottom: 1px solid hsl(var(--border));
}

.card-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.card-body {
  padding: 16px;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 0;
}

.form-group {
  flex: 1;
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
  margin-bottom: 6px;
}

.form-input,
.form-select {
  width: 100%;
  padding: 8px 12px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: hsl(var(--primary));
}

.divider {
  height: 1px;
  background: hsl(var(--border));
  margin: 16px 0;
}

.form-actions {
  margin-top: 8px;
}

</style>
