<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="cyan">数据</a-tag>
        数据概览
      </div>
      <a-button :loading="refreshing" @click="refreshStats">
        <template #icon><ReloadOutlined /></template>
        刷新统计
      </a-button>
    </div>

    <!-- 统计卡片 -->
    <a-row :gutter="16" style="margin-bottom: 24px">
      <a-col :span="6">
        <a-card class="stat-card" hoverable @click="navigateTo('/data/stocks')">
          <a-statistic title="股票总数" :value="dataStats.totalStocks" :value-style="{ color: '#1890ff' }">
            <template #suffix>
              <StockOutlined style="font-size: 16px; opacity: 0.5" />
            </template>
          </a-statistic>
          <div class="stat-footer">点击查看详情</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable @click="navigateTo('/data/bars')">
          <a-statistic title="K线数据量" :value="dataStats.totalBars" :value-style="{ color: '#52c41a' }">
            <template #suffix>
              <LineChartOutlined style="font-size: 16px; opacity: 0.5" />
            </template>
          </a-statistic>
          <div class="stat-footer">点击查看详情</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable @click="navigateTo('/data/ticks')">
          <a-statistic title="Tick数据量" :value="dataStats.totalTicks" :value-style="{ color: '#fa8c16' }">
            <template #suffix>
              <ThunderboltOutlined style="font-size: 16px; opacity: 0.5" />
            </template>
          </a-statistic>
          <div class="stat-footer">点击查看详情</div>
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card class="stat-card" hoverable @click="navigateTo('/data/adjustfactors')">
          <a-statistic title="复权因子" :value="dataStats.totalAdjustFactors" :value-style="{ color: '#722ed1' }">
            <template #suffix>
              <PercentageOutlined style="font-size: 16px; opacity: 0.5" />
            </template>
          </a-statistic>
          <div class="stat-footer">点击查看详情</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 快捷操作 -->
    <a-card title="快捷操作" style="margin-bottom: 24px">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-button type="dashed" block @click="navigateTo('/data/sync')">
            <template #icon><SyncOutlined /></template>
            数据同步
          </a-button>
        </a-col>
        <a-col :span="6">
          <a-button type="dashed" block>
            <template #icon><CloudDownloadOutlined /></template>
            导入数据
          </a-button>
        </a-col>
        <a-col :span="6">
          <a-button type="dashed" block>
            <template #icon><CloudUploadOutlined /></template>
            导出数据
          </a-button>
        </a-col>
        <a-col :span="6">
          <a-button type="dashed" block>
            <template #icon><SettingOutlined /></template>
            数据源配置
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <!-- 最近更新 -->
    <a-row :gutter="16">
      <a-col :span="12">
        <a-card title="最近同步记录" :loading="loading">
          <a-timeline>
            <a-timeline-item v-for="(item, index) in recentSyncs" :key="index" :color="item.status === 'success' ? 'green' : 'red'">
              <p><strong>{{ item.type }}</strong> - {{ item.code }}</p>
              <p style="color: #8c8c8c; font-size: 12px">{{ item.time }}</p>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-if="recentSyncs.length === 0" description="暂无同步记录" />
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card title="数据源状态" :loading="loading">
          <a-list :data-source="dataSources" size="small">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :title="item.name" :description="item.description" />
                <template #actions>
                  <a-tag :color="item.status === 'online' ? 'green' : 'red'">
                    {{ item.status === 'online' ? '在线' : '离线' }}
                  </a-tag>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  ReloadOutlined,
  StockOutlined,
  LineChartOutlined,
  ThunderboltOutlined,
  PercentageOutlined,
  SyncOutlined,
  CloudDownloadOutlined,
  CloudUploadOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'

const router = useRouter()
const loading = ref(false)
const refreshing = ref(false)

const dataStats = reactive({
  totalStocks: 0,
  totalBars: 0,
  totalTicks: 0,
  totalAdjustFactors: 0
})

const recentSyncs = ref([
  { type: 'K线数据', code: '000001.SZ', time: '2024-02-17 10:30:00', status: 'success' },
  { type: '股票信息', code: '全市场', time: '2024-02-17 09:00:00', status: 'success' },
])

const dataSources = ref([
  { name: 'Tushare', description: 'A股行情数据', status: 'online' },
  { name: 'AKShare', description: '多市场数据', status: 'online' },
  { name: 'BaoStock', description: '证券宝数据', status: 'offline' },
])

const refreshStats = async () => {
  refreshing.value = true
  try {
    // TODO: 调用API获取统计数据
    dataStats.totalStocks = 5420
    dataStats.totalBars = 12500000
    dataStats.totalTicks = 250000000
    dataStats.totalAdjustFactors = 54200
    message.success('统计已刷新')
  } catch (error: any) {
    message.error(`刷新失败: ${error.message}`)
  } finally {
    refreshing.value = false
  }
}

const navigateTo = (path: string) => {
  router.push(path)
}

onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.stat-footer {
  margin-top: 8px;
  font-size: 12px;
  color: #8c8c8c;
}
</style>
