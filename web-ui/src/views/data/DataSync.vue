<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">数据同步</div>
    </div>

    <a-row :gutter="16">
      <!-- 发送命令 -->
      <a-col :span="12">
        <a-card title="发送同步命令">
          <a-form layout="vertical">
            <a-form-item label="命令类型">
              <a-select v-model:value="command.type" style="width: 100%">
                <a-select-option value="BAR_SNAPSHOT">K线快照 (BAR_SNAPSHOT)</a-select-option>
                <a-select-option value="TICK">Tick数据 (TICK)</a-select-option>
                <a-select-option value="STOCKINFO">股票信息 (STOCKINFO)</a-select-option>
                <a-select-option value="ADJUSTFACTOR">复权因子 (ADJUSTFACTOR)</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="股票代码">
              <a-textarea
                v-model:value="command.codes"
                :rows="4"
                placeholder="输入股票代码，每行一个&#10;例如：&#10;000001.SZ&#10;000002.SZ"
              />
            </a-form-item>

            <a-form-item label="同步参数">
              <a-checkbox v-model:checked="command.fullSync">全量同步</a-checkbox>
              <a-checkbox v-model:checked="command.overwrite" style="margin-left: 16px">覆盖已有数据</a-checkbox>
            </a-form-item>

            <a-form-item>
              <a-space>
                <a-button type="primary" @click="sendCommand" :loading="sending">
                  发送命令
                </a-button>
                <a-button @click="clearForm">清空</a-button>
              </a-space>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 命令历史 -->
      <a-col :span="12">
        <a-card title="已发送命令">
          <template #extra>
            <a-button size="small" @click="clearHistory">清空历史</a-button>
          </template>
          <a-timeline v-if="commandHistory.length > 0">
            <a-timeline-item v-for="(cmd, index) in commandHistory" :key="index" :color="cmd.success ? 'green' : 'red'">
              <p><strong>{{ cmd.type }}</strong> - {{ cmd.time }}</p>
              <p>代码: {{ cmd.codes.slice(0, 50) }}{{ cmd.codes.length > 50 ? '...' : '' }}</p>
              <p>状态: {{ cmd.success ? '成功' : '失败' }}</p>
            </a-timeline-item>
          </a-timeline>
          <a-empty v-else description="暂无命令记录" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 同步状态概览 -->
    <a-card title="数据同步状态" style="margin-top: 16px">
      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic title="K线数据" :value="syncStatus.bar_count" suffix="条" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="Tick数据" :value="syncStatus.tick_count" suffix="条" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="股票信息" :value="syncStatus.stock_count" suffix="只" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="最后同步" :value="syncStatus.last_sync" />
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { dataApi } from '@/api'

interface CommandRecord {
  type: string
  codes: string
  time: string
  success: boolean
}

const sending = ref(false)
const commandHistory = ref<CommandRecord[]>([])

const command = reactive({
  type: 'BAR_SNAPSHOT',
  codes: '',
  fullSync: false,
  overwrite: false,
})

const syncStatus = reactive({
  bar_count: 0,
  tick_count: 0,
  stock_count: 0,
  last_sync: '-',
})

const sendCommand = async () => {
  if (!command.codes.trim()) {
    message.warning('请输入股票代码')
    return
  }

  sending.value = true
  const codes = command.codes.split('\n').map(c => c.trim()).filter(c => c)

  try {
    const response = await dataApi.sync({
      type: command.type,
      codes,
      full: command.fullSync,
      overwrite: command.overwrite,
    })

    commandHistory.value.unshift({
      type: command.type,
      codes: codes.join(', '),
      time: new Date().toLocaleString('zh-CN'),
      success: response.status === 'success',
    })

    message.success('命令已发送')
  } catch (e: any) {
    commandHistory.value.unshift({
      type: command.type,
      codes: codes.join(', '),
      time: new Date().toLocaleString('zh-CN'),
      success: false,
    })
    message.error('发送失败: ' + (e.message || '未知错误'))
  } finally {
    sending.value = false
  }
}

const clearForm = () => {
  command.codes = ''
  command.fullSync = false
  command.overwrite = false
}

const clearHistory = () => {
  commandHistory.value = []
}

const fetchSyncStatus = async () => {
  try {
    const data = await dataApi.getStatus()
    syncStatus.bar_count = data.bar_count || 0
    syncStatus.tick_count = data.tick_count || 0
    syncStatus.stock_count = data.stock_count || 0
    syncStatus.last_sync = data.last_sync || '-'
  } catch (e) {
    console.error('获取同步状态失败:', e)
  }
}

onMounted(() => {
  fetchSyncStatus()
})
</script>

<style scoped>
.page-container {
  padding: 0;
}

.page-header {
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
}
</style>
