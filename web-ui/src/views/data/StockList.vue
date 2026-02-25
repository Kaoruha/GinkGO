<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="blue">股票</a-tag>
        股票信息
      </div>
      <a-space>
        <a-input-search
          v-model:value="searchKeyword"
          placeholder="搜索代码或名称"
          style="width: 250px"
          @search="loadStocks"
          allow-clear
        />
        <a-button :loading="loading" @click="loadStocks">
          <template #icon><ReloadOutlined /></template>
          刷新
        </a-button>
        <a-button type="primary" @click="syncStockInfo">
          <template #icon><SyncOutlined /></template>
          同步数据
        </a-button>
      </a-space>
    </div>

    <!-- 统计 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="股票总数" :value="pagination.total" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="沪市" :value="exchangeStats.sh" />
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card size="small">
          <a-statistic title="深市" :value="exchangeStats.sz" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 股票表格 -->
    <a-card>
      <a-table
        :columns="columns"
        :data-source="stockList"
        :loading="loading"
        :pagination="pagination"
        row-key="code"
        :custom-row="customRow"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'code'">
            <a @click.stop="viewStockDetail(record)">{{ record.code }}</a>
          </template>
          <template v-if="column.dataIndex === 'name'">
            <span>{{ record.name }}</span>
            <a-tag v-if="record.is_st" color="red" style="margin-left: 4px">ST</a-tag>
          </template>
          <template v-if="column.dataIndex === 'exchange'">
            <a-tag :color="record.exchange === 'SH' ? 'blue' : 'green'">
              {{ record.exchange === 'SH' ? '沪市' : '深市' }}
            </a-tag>
          </template>
          <template v-if="column.dataIndex === 'list_date'">
            {{ record.list_date || '-' }}
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 股票详情抽屉 -->
    <a-drawer
      v-model:open="detailDrawerVisible"
      :title="currentStock?.name"
      width="500"
      placement="right"
    >
      <a-descriptions v-if="currentStock" :column="1" bordered size="small">
        <a-descriptions-item label="代码">{{ currentStock.code }}</a-descriptions-item>
        <a-descriptions-item label="名称">{{ currentStock.name }}</a-descriptions-item>
        <a-descriptions-item label="交易所">{{ currentStock.exchange }}</a-descriptions-item>
        <a-descriptions-item label="类型">{{ currentStock.type || '-' }}</a-descriptions-item>
        <a-descriptions-item label="行业">{{ currentStock.industry || '-' }}</a-descriptions-item>
        <a-descriptions-item label="上市日期">{{ currentStock.list_date || '-' }}</a-descriptions-item>
      </a-descriptions>
      <a-divider />
      <a-space>
        <a-button type="primary" @click="syncSingleStock">
          <template #icon><SyncOutlined /></template>
          同步K线数据
        </a-button>
        <a-button @click="viewBarData">
          <template #icon><LineChartOutlined /></template>
          查看K线
        </a-button>
      </a-space>
    </a-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { ReloadOutlined, SyncOutlined, LineChartOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const loading = ref(false)
const searchKeyword = ref('')
const detailDrawerVisible = ref(false)
const currentStock = ref<any>(null)

const stockList = ref<any[]>([])
const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const exchangeStats = reactive({
  sh: 0,
  sz: 0
})

const columns = [
  { title: '代码', dataIndex: 'code', width: 120 },
  { title: '名称', dataIndex: 'name', width: 150 },
  { title: '交易所', dataIndex: 'exchange', width: 100 },
  { title: '类型', dataIndex: 'type', width: 100 },
  { title: '行业', dataIndex: 'industry', width: 150 },
  { title: '上市日期', dataIndex: 'list_date', width: 120 }
]

const loadStocks = async () => {
  loading.value = true
  try {
    // TODO: 调用API获取股票列表
    stockList.value = [
      { code: '000001.SZ', name: '平安银行', exchange: 'SZ', type: 'A股', industry: '银行', list_date: '1991-04-03' },
      { code: '000002.SZ', name: '万科A', exchange: 'SZ', type: 'A股', industry: '房地产', list_date: '1991-01-29' },
      { code: '600000.SH', name: '浦发银行', exchange: 'SH', type: 'A股', industry: '银行', list_date: '1999-11-10' },
      { code: '600519.SH', name: '贵州茅台', exchange: 'SH', type: 'A股', industry: '白酒', list_date: '2001-08-27' },
    ]
    pagination.total = stockList.value.length
    exchangeStats.sh = stockList.value.filter(s => s.exchange === 'SH').length
    exchangeStats.sz = stockList.value.filter(s => s.exchange === 'SZ').length
  } catch (error: any) {
    message.error(`加载失败: ${error.message}`)
  } finally {
    loading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  loadStocks()
}

const viewStockDetail = (stock: any) => {
  currentStock.value = stock
  detailDrawerVisible.value = true
}

// 表格行点击配置
const customRow = (record: any) => ({
  style: { cursor: 'pointer' },
  onClick: () => viewStockDetail(record),
})

const syncStockInfo = () => {
  message.info('同步股票信息...')
}

const syncSingleStock = () => {
  message.info(`同步 ${currentStock.value?.code} K线数据...`)
}

const viewBarData = () => {
  if (currentStock.value) {
    router.push(`/data/bars?code=${currentStock.value.code}`)
  }
}

onMounted(() => {
  loadStocks()
})
</script>

<style scoped>
.page-container {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 20px;
  font-weight: 600;
}

/* 可点击表格行样式 */
:deep(.ant-table-tbody > tr) {
  cursor: pointer;
  transition: background-color 0.2s;
}

:deep(.ant-table-tbody > tr:hover) {
  background-color: #e6f4ff;
}
</style>
