<template>
  <div
    v-if="visible"
    class="modal-overlay"
    @click.self="close"
  >
    <div class="modal-box">
      <div class="modal-header">
        <h3>部署到模拟盘/实盘</h3>
        <button
          class="btn-close"
          @click="close"
        >
          ×
        </button>
      </div>
      <div class="modal-body">
        <div class="form-item">
          <label>目标模式</label>
          <SegmentedControl
            :model-value="mode"
            :options="[{ key: 'paper', label: '模拟盘' }, { key: 'live', label: '实盘' }]"
            @update:model-value="(v) => (mode = v as 'paper' | 'live')"
          />
        </div>
        <div
          v-if="mode === 'live'"
          class="form-item"
        >
          <label>实盘账号</label>
          <select
            v-model="accountId"
            class="form-select"
          >
            <option value="">
              选择实盘账号
            </option>
            <option
              v-for="acc in liveAccounts"
              :key="acc.uuid"
              :value="acc.uuid"
            >
              {{ acc.name }} ({{ acc.exchange }} - {{ acc.environment }})
            </option>
          </select>
          <p
            v-if="liveAccounts.length === 0"
            class="form-hint"
          >
            暂无可用实盘账号，请先在实盘账号管理中添加
          </p>
        </div>
        <div class="form-item">
          <label>组合名称（可选）</label>
          <input
            v-model="name"
            type="text"
            placeholder="留空自动生成"
            class="form-input"
          >
        </div>
      </div>
      <div class="modal-footer">
        <button
          class="btn-secondary"
          @click="close"
        >
          取消
        </button>
        <button
          class="btn-primary"
          :disabled="deploying || (mode === 'live' && !accountId)"
          @click="handleDeploy"
        >
          {{ deploying ? '部署中...' : '确认部署' }}
        </button>
      </div>
    </div>
    <ConfirmDialog
      v-model:open="liveConfirmOpen"
      title="确认实盘部署"
      description="实盘部署将使用真实资金进行交易,可能产生真实委托与盈亏。此操作不可逆,确定要部署到实盘吗?"
      danger
      confirm-text="确认实盘部署"
      :loading="deploying"
      @confirm="doDeploy"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { deploymentApi, liveAccountApi } from '@/api'
import type { LiveAccount } from '@/api'
import { message } from '@/utils/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

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
const liveConfirmOpen = ref(false)
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
    // 拦截器已拆信封:res 即 {accounts,total,...};旧代码读 res.data.accounts 恒空致下拉无账号
    liveAccounts.value = res?.accounts || res?.data?.accounts || []
  } catch { liveAccounts.value = [] }
}

const handleDeploy = async () => {
  if (deploying.value) return
  if (mode.value === 'live' && !accountId.value) {
    message.warning('请选择实盘账号')
    return
  }
  // 实盘部署涉及真实资金下单,需二次确认;模拟盘直接部署
  if (mode.value === 'live') {
    liveConfirmOpen.value = true
    return
  }
  await doDeploy()
}

const doDeploy = async () => {
  if (deploying.value) return
  deploying.value = true
  try {
    const res: any = await deploymentApi.deploy({
      portfolio_id: props.portfolioId,
      mode: mode.value,
      account_id: mode.value === 'live' ? accountId.value : undefined,
      name: name.value || undefined,
    })
    // 拦截器已拆信封:res 即 {portfolio_id, deployment_id};旧读 res.data.portfolio_id 恒 undefined 致部署成功不跳转
    const newPortfolioId = res?.portfolio_id
    liveConfirmOpen.value = false
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
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
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
  border-bottom: 1px solid hsl(var(--border));
}
.modal-header h3 { margin: 0; color: hsl(var(--foreground)); font-size: 16px; }
.btn-close { background: none; border: none; color: hsl(var(--muted-foreground)); font-size: 18px; cursor: pointer; }
.btn-close:hover { color: hsl(var(--foreground)); }
.modal-body { padding: 20px; }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid hsl(var(--border));
}
.form-item { margin-bottom: 14px; }
.form-item label { display: block; font-size: 12px; color: hsl(var(--muted-foreground)); margin-bottom: 4px; }
.form-input, .form-select {
  width: 100%;
  padding: 7px 10px;
  background: hsl(var(--background));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
}
.form-input:focus, .form-select:focus { border-color: hsl(var(--primary)); outline: none; }
.form-hint { margin: 6px 0 0; font-size: 12px; color: hsl(var(--muted-foreground)); }
.btn-secondary {
  padding: 6px 14px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { background: hsl(var(--secondary)); }
</style>
