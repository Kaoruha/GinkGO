<template>
  <a-card title="策略信号生成器" size="small">
    <a-row :gutter="16">
      <a-col :span="12">
        <a-form-item label="信号类型" name="signalType">
          <a-select v-model:value="form.signalType" size="small">
            <a-select-option value="price_cross">价格交叉</a-select-option>
            <a-select-option value="momentum">动量</a-select-option>
            <a-select-option value="mean_reversion">均值回归</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item label="触发条件" name="trigger">
          <a-select v-model:value="form.trigger" size="small">
            <a-select-option value="above">突破上方</a-select-option>
            <a-select-option value="below">跌破下方</a-select-option>
            <a-select-option value="percent">涨跌幅</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
    </a-row>

    <a-divider />

    <a-form-item label="第一资产">
      <a-select v-model:value="form.asset1" size="small" placeholder="选择">
        <a-select-option value="000001.SZ">平安银行</a-select-option>
        <a-select-option value="000002.SZ">招商银行</a-select-option>
      </a-select>
    </a-form-item>

    <a-form-item label="第二资产">
      <a-select v-model:value="form.asset2" size="small" placeholder="选择">
        <a-select-option value="510300.SH">上证50ETF</a-select-option>
      <a-select-option value="159919.SH">深证100ETF</a-select-option>
      </a-select>
    </a-form-item>

    <a-divider />

    <a-form-item label="价差阈值 (%)" name="threshold">
      <a-input-number v-model:value="form.threshold" :min="0.1" :max="5" :step="0.1" />
    </a-form-item>

    <a-form-item label="开仓价格">
      <a-radio-group v-model:value="form.openPrice" size="small">
        <a-radio-button value="open">开盘价</a-radio-button>
        <a-radio-button value="close">收盘价</a-radio-button>
      <a-radio-button value="mid">中间价</a-radio-button>
      <a-radio-button value="close">收盘价</a-radio-button>
      <a-radio-button value="fixed">固定价格</a-radio-button>
      </a-radio-group>
    </a-form-item>
  </a-card>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'

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
