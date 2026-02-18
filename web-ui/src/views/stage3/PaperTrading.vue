<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="orange">模拟</a-tag>
        模拟交易
        <a-tag :color="runningStatus === 'running' ? 'green' : 'default'" style="margin-left: 8px">
          {{ runningStatus === 'running' ? '运行中' : '已停止' }}
        </a-tag>
      </div>
      <div class="page-actions">
        <a-button @click="settingsVisible = true">
          <template #icon><SettingOutlined /></template>
          设置
        </a-button>
        <a-button v-if="runningStatus !== 'running'" type="primary" @click="startTrading">启动</a-button>
        <a-button v-else type="primary" danger @click="stopTrading">停止</a-button>
        <a-button @click="refreshData">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-card :loading="loading">
          <a-statistic title="今日盈亏" :value="stats.todayProfit" prefix="¥" :precision="2"
            :value-style="{ color: stats.todayProfit >= 0 ? '#cf1322' : '#3f8600' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading">
          <a-statistic title="持仓数量" :value="stats.positionCount" suffix="只" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading">
          <a-statistic title="可用资金" :value="stats.availableCash" prefix="¥" :precision="2" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card :loading="loading">
          <a-statistic title="运行天数" :value="stats.runningDays" suffix="天" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 当前持仓 -->
    <a-card title="当前持仓" :loading="loading">
      <a-table
        :columns="positionColumns"
        :dataSource="positions"
        :rowKey="(record: Position) => record.uuid"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'code'">
            <span style="font-weight: 600">{{ record.code }}</span>
          </template>
          <template v-else-if="column.key === 'profit'">
            <span :style="{ color: record.profit >= 0 ? '#cf1322' : '#3f8600' }">
              {{ record.profit.toFixed(2) }} ({{ record.profit_pct >= 0 ? '+' : '' }}{{ record.profit_pct }}%)
            </span>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 设置抽屉 -->
    <a-drawer
      v-model:open="settingsVisible"
      title="模拟交易设置"
      placement="right"
      :width="400"
    >
      <a-form layout="vertical">
        <a-form-item label="滑点模型">
          <a-select v-model:value="settings.slippageModel">
            <a-select-option value="fixed">固定滑点</a-select-option>
            <a-select-option value="percent">百分比滑点</a-select-option>
            <a-select-option value="dynamic">动态滑点</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="滑点值">
          <a-input-number v-model:value="settings.slippageValue" :min="0" :step="0.01" style="width: 100%" />
        </a-form-item>
        <a-form-item label="佣金费率 (%)">
          <a-input-number v-model:value="settings.commissionRate" :min="0" :max="100" :step="0.01" style="width: 100%" />
        </a-form-item>
        <a-form-item label="成交延迟 (秒)">
          <a-input-number v-model:value="settings.executionDelay" :min="0" :step="1" style="width: 100%" />
        </a-form-item>
        <a-form-item label="印花税 (%)">
          <a-input-number v-model:value="settings.stampDuty" :min="0" :max="100" :step="0.01" style="width: 100%" />
        </a-form-item>
      </a-form>
      <template #footer>
        <a-button @click="settingsVisible = false">取消</a-button>
        <a-button type="primary" @click="saveSettings">保存</a-button>
      </template>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SettingOutlined, ReloadOutlined } from '@ant-design/icons-vue'
import { positionApi, type Position } from '@/api/modules/order'

const loading = ref(false)
const settingsVisible = ref(false)
const runningStatus = ref('stopped')

const stats = reactive({
  todayProfit: 0,
  positionCount: 0,
  availableCash: 500000,
  runningDays: 0,
})

const positions = ref<Position[]>([])

const settings = reactive({
  slippageModel: 'fixed',
  slippageValue: 0.01,
  commissionRate: 0.03,
  executionDelay: 0,
  stampDuty: 0.1,
})

const positionColumns = [
  { title: '代码', key: 'code', dataIndex: 'code', width: 120 },
  { title: '数量', dataIndex: 'volume', width: 100 },
  { title: '成本', dataIndex: 'cost', width: 100, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '现价', dataIndex: 'price', width: 100, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '市值', dataIndex: 'market_value', width: 120, customRender: ({ text }: { text: number }) => text?.toFixed(2) },
  { title: '盈亏', key: 'profit', width: 160 },
]

const loadPositions = async () => {
  loading.value = true
  try {
    const result = await positionApi.list({ page: 0, size: 100 })
    positions.value = result.data
    stats.positionCount = result.summary?.position_count || 0
  } catch (e: any) {
    console.error('加载持仓失败:', e)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await loadPositions()
  message.success('数据已刷新')
}

const startTrading = () => {
  runningStatus.value = 'running'
  message.success('模拟交易已启动')
}

const stopTrading = () => {
  runningStatus.value = 'stopped'
  message.success('模拟交易已停止')
}

const saveSettings = () => {
  message.success('设置已保存')
  settingsVisible.value = false
}

onMounted(() => {
  loadPositions()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
