<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">数据同步</div>
    </div>

    <div class="two-column-grid">
      <!-- 发送命令 -->
      <div class="card">
        <h3 class="card-title">发送同步命令</h3>
        <form @submit.prevent="sendCommand" class="sync-form">
          <div class="form-group">
            <label class="form-label">命令类型</label>
            <select v-model="command.type" class="form-select">
              <option value="BAR_SNAPSHOT">K线快照 (BAR_SNAPSHOT)</option>
              <option value="TICK">Tick数据 (TICK)</option>
              <option value="STOCKINFO">股票信息 (STOCKINFO)</option>
              <option value="ADJUSTFACTOR">复权因子 (ADJUSTFACTOR)</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">股票代码</label>
            <textarea
              v-model="command.codes"
              class="form-textarea"
              rows="4"
              placeholder="输入股票代码，每行一个&#10;例如：&#10;000001.SZ&#10;000002.SZ"
            ></textarea>
          </div>

          <div class="form-group">
            <label class="checkbox-label">
              <input type="checkbox" v-model="command.fullSync" class="checkbox" />
              全量同步
            </label>
            <label class="checkbox-label">
              <input type="checkbox" v-model="command.overwrite" class="checkbox" />
              覆盖已有数据
            </label>
          </div>

          <div class="form-actions">
            <button type="submit" class="btn-primary" :disabled="sending">
              {{ sending ? '发送中...' : '发送命令' }}
            </button>
            <button type="button" class="btn-secondary" @click="clearForm">清空</button>
          </div>
        </form>
      </div>

      <!-- 命令历史 -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">已发送命令</h3>
          <button class="btn-small" @click="clearHistory">清空历史</button>
        </div>
        <div v-if="commandHistory.length > 0" class="timeline">
          <div v-for="(cmd, index) in commandHistory" :key="index" class="timeline-item">
            <div class="timeline-dot" :class="cmd.success ? 'success' : 'error'"></div>
            <div class="timeline-content">
              <div class="timeline-title">{{ cmd.type }}</div>
              <div class="timeline-time">{{ cmd.time }}</div>
              <div class="timeline-codes">代码: {{ truncateText(cmd.codes, 50) }}</div>
              <div class="timeline-status" :class="cmd.success ? 'success' : 'error'">
                状态: {{ cmd.success ? '成功' : '失败' }}
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p>暂无命令记录</p>
        </div>
      </div>
    </div>

    <!-- 同步状态概览 -->
    <div class="card">
      <h3 class="card-title">数据同步状态</h3>
      <div class="stats-grid-four">
        <div class="stat-item">
          <div class="stat-value">{{ formatNumber(syncStatus.bar_count) }}</div>
          <div class="stat-label">K线数据 <span class="stat-suffix">条</span></div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ formatNumber(syncStatus.tick_count) }}</div>
          <div class="stat-label">Tick数据 <span class="stat-suffix">条</span></div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ formatNumber(syncStatus.stock_count) }}</div>
          <div class="stat-label">股票信息 <span class="stat-suffix">只</span></div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ syncStatus.last_sync }}</div>
          <div class="stat-label">最后同步</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
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
    console.warn('请输入股票代码')
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

    console.log('命令已发送')
  } catch (e: any) {
    commandHistory.value.unshift({
      type: command.type,
      codes: codes.join(', '),
      time: new Date().toLocaleString('zh-CN'),
      success: false,
    })
    console.error('发送失败:', e.message || '未知错误')
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

const truncateText = (text: string, maxLength: number): string => {
  return text.length > maxLength ? text.slice(0, maxLength) + '...' : text
}

const formatNumber = (num: number): string => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  } else if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

onMounted(() => {
  fetchSyncStatus()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

/* 两列网格 */
.two-column-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

/* 卡片 */
.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

/* 表单 */
.sync-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.form-select,
.form-textarea {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-family: inherit;
}

.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #1890ff;
}

.form-textarea {
  resize: vertical;
  min-height: 100px;
}

.checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #ffffff;
  cursor: pointer;
  margin-right: 16px;
}

.checkbox {
  width: 16px;
  height: 16px;
  accent-color: #1890ff;
}

/* 按钮 */
.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.btn-primary {
  padding: 8px 20px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 20px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #5a5a6e;
}

.btn-small {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover {
  border-color: #5a5a6e;
}

/* 时间线 */
.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: #2a2a3e;
}

.timeline-item {
  position: relative;
  padding-bottom: 16px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #1a1a2e;
}

.timeline-dot.success {
  background: #52c41a;
}

.timeline-dot.error {
  background: #f5222d;
}

.timeline-content {
  padding-left: 8px;
}

.timeline-title {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 4px;
}

.timeline-time {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.timeline-codes {
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.timeline-status {
  font-size: 12px;
}

.timeline-status.success {
  color: #52c41a;
}

.timeline-status.error {
  color: #f5222d;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #8a8a9a;
}

.empty-state svg {
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
}

/* 统计网格 */
.stats-grid-four {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.stat-suffix {
  font-size: 10px;
  margin-left: 4px;
}
</style>
