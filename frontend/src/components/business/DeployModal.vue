<template>
  <div v-if="visible" class="modal-overlay" @click.self="close">
    <div class="modal-box">
      <div class="modal-header">
        <h3>部署到模拟盘/实盘</h3>
        <button class="btn-close" @click="close">×</button>
      </div>
      <div class="modal-body">
        <div class="form-item">
          <label>目标模式</label>
          <div class="radio-group">
            <button class="radio-button" :class="{ active: mode === 'paper' }" @click="mode = 'paper'">模拟盘</button>
            <button class="radio-button" :class="{ active: mode === 'live' }" @click="mode = 'live'">实盘</button>
          </div>
        </div>
        <div v-if="mode === 'live'" class="form-item">
          <label>实盘账号</label>
          <select v-model="accountId" class="form-select">
            <option value="">选择实盘账号</option>
            <option v-for="acc in liveAccounts" :key="acc.uuid" :value="acc.uuid">
              {{ acc.name }} ({{ acc.exchange }} - {{ acc.environment }})
            </option>
          </select>
          <p v-if="liveAccounts.length === 0" class="form-hint">暂无可用实盘账号，请先在实盘账号管理中添加</p>
        </div>
        <div class="form-item">
          <label>组合名称（可选）</label>
          <input v-model="name" type="text" placeholder="留空自动生成" class="form-input" />
        </div>
      </div>
      <div class="modal-footer">
        <button class="btn-secondary" @click="close">取消</button>
        <button class="btn-primary" :disabled="deploying || (mode === 'live' && !accountId)" @click="handleDeploy">
          {{ deploying ? '部署中...' : '确认部署' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { deploymentApi, liveAccountApi } from '@/api'
import type { LiveAccount } from '@/api'
import { message } from '@/utils/toast'

const props = defineProps<{
  visible: boolean
  portfolioId: string
}>()

const emit = defineEmits<{
  (e: 'update:visible', val: boolean): void
  (e: 'success', portfolioId: string): void
}>()

const mode = ref<'paper' | 'live'>('paper')
const accountId = ref('')
const name = ref('')
const deploying = ref(false)
const liveAccounts = ref<LiveAccount[]>([])

const close = () => emit('update:visible', false)

watch(() => props.visible, (val) => {
  if (val) {
    mode.value = 'paper'
    accountId.value = ''
    name.value = ''
    loadLiveAccounts()
  }
})

const loadLiveAccounts = async () => {
  try {
    const res: any = await liveAccountApi.getAccounts({ page: 1, page_size: 100, status: 'enabled' })
    liveAccounts.value = res?.data?.accounts || []
  } catch { liveAccounts.value = [] }
}

const handleDeploy = async () => {
  if (deploying.value) return
  if (mode.value === 'live' && !accountId.value) {
    message.warning('请选择实盘账号')
    return
  }
  deploying.value = true
  try {
    const res: any = await deploymentApi.deploy({
      portfolio_id: props.portfolioId,
      mode: mode.value,
      account_id: mode.value === 'live' ? accountId.value : undefined,
      name: name.value || undefined,
    })
    const newPortfolioId = res?.data?.portfolio_id
    close()
    message.success('部署成功')
    emit('success', newPortfolioId || '')
  } catch (e: any) {
    message.error('部署失败: ' + (e?.message || e))
  } finally {
    deploying.value = false
  }
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-box {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 480px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}
.modal-header h3 { margin: 0; color: #fff; font-size: 16px; }
.btn-close { background: none; border: none; color: #8a8a9a; font-size: 18px; cursor: pointer; }
.btn-close:hover { color: #fff; }
.modal-body { padding: 20px; }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px;
  border-top: 1px solid #2a2a3e;
}
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 12px; color: #8a8a9a; margin-bottom: 4px; }
.form-input, .form-select {
  width: 100%;
  padding: 7px 10px;
  background: #0f0f1a;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
}
.form-input:focus, .form-select:focus { border-color: #1890ff; outline: none; }
.form-hint { margin: 6px 0 0; font-size: 12px; color: #8a8a9a; }
.radio-group {
  display: inline-flex;
  background: #2a2a3e;
  border-radius: 4px;
  padding: 2px;
}
.radio-button {
  padding: 5px 12px;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.radio-button:hover { color: #fff; }
.radio-button.active { background: #1890ff; color: #fff; }
.btn-primary {
  padding: 6px 14px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-primary:hover { background: #40a9ff; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary {
  padding: 6px 14px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { background: #3a3a4e; }
</style>
