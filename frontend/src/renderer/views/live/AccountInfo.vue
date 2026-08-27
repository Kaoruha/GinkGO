<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import AccountCard from '@/components/live/AccountCard.vue'
import { Button } from '@/components/ui/button'
import { RefreshCw, Wallet, AlertCircle, DollarSign, Coins, Clock, Activity } from 'lucide-vue-next'
import { liveAccountApi } from '@/api'
import { usePolling } from '@/composables'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import { formatFixed } from '@/utils/format'
import type { AccountData } from '@/types/live'

/** 账户卡片右键菜单(替代卡片内刷新按钮) */
const { open: openCtxMenu } = useContextMenu()
const openAccountInfoMenu = (e: MouseEvent, account: AccountData) => {
  openCtxMenu(e, [
    { label: '刷新', action: () => refreshAccount(account.uuid) },
    { label: '复制账户 ID', action: () => { navigator.clipboard.writeText(account.uuid); toast.success('已复制') } },
  ])
}

// 状态
const accounts = ref<AccountData[]>([])
const loading = ref(true)
const refreshing = ref(false)
// 列表加载失败(后端 500/网络断):须与"暂无账户"空态区分,否则误导用户去配账号
const listError = ref('')
const accountLoadingStates = ref<Record<string, { balance: boolean; positions: boolean }>>({})

// 统计数据
const totalEquity = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.balance) {
      const value = parseFloat(acc.balance.total_equity || '0')
      return sum + (isNaN(value) ? 0 : value)
    }
    return sum
  }, 0)
})

const totalAvailable = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.balance) {
      const value = parseFloat(acc.balance.available_balance || '0')
      return sum + (isNaN(value) ? 0 : value)
    }
    return sum
  }, 0)
})

const totalPositions = computed(() => {
  return accounts.value.reduce((sum, acc) => {
    if (acc.positions && Array.isArray(acc.positions)) {
      return sum + acc.positions.length
    }
    return sum
  }, 0)
})

// 加载账户信息（首次加载）
const loadAccountInfo = async () => {
  listError.value = ''
  try {
    // 拦截器已拆信封:resolve 即 payload,code!==0 会 reject(同 AccountConfig.fetchAccounts)
    const response = await liveAccountApi.getAccounts()
    // 分页响应中，账号列表在 accounts 中
    const accountList = response?.accounts || []

    // 创建账户对象（保持引用稳定）
    const newAccounts: AccountData[] = accountList.map((account: any) => ({
      uuid: account.uuid,
      name: account.name,
      exchange: account.exchange,
      environment: account.environment,
      status: account.status,
      balance: undefined,
      positions: undefined,
      last_update: undefined,
      error: undefined
    }))

    accounts.value = newAccounts

    // 初始化加载状态
    accountLoadingStates.value = {}
    newAccounts.forEach(account => {
      accountLoadingStates.value[account.uuid] = { balance: true, positions: true }
    })

    // 异步加载每个账户的详细信息（不阻塞 UI）
    Promise.all(
      newAccounts.map(account => updateAccountDetails(account))
    ).finally(() => {
      loading.value = false
    })
  } catch (error) {
    console.error('Failed to load account info:', error)
    listError.value = (error as any)?.message || '账户列表加载失败，请稍后重试'
    loading.value = false
  }
}

// 设置账户的 balance/positions 加载状态(updateAccountDetails 三处复用)
const setAccountLoading = (accountId: string, balance: boolean, positions: boolean) => {
  const state = accountLoadingStates.value[accountId]
  if (state) {
    state.balance = balance
    state.positions = positions
  }
}

// 在 accounts 数组中替换指定账户(合并 patch,返回索引;触发响应式更新)
const replaceAccount = (accountId: string, patch: Partial<AccountData>) => {
  const index = accounts.value.findIndex(a => a.uuid === accountId)
  if (index !== -1) {
    accounts.value[index] = { ...accounts.value[index], ...patch }
  }
  return index
}

// 更新单个账户的详细信息（通过替换对象触发响应式更新）
const updateAccountDetails = async (account: AccountData) => {
  const accountId = account.uuid
  setAccountLoading(accountId, true, true)

  try {
    const [balanceRes, positionsRes] = await liveAccountApi.getAccountInfo(accountId)

    // 创建更新后的账户对象
    const updatedAccount: AccountData = {
      ...account,
      last_update: new Date().toISOString(),
      error: undefined
    }

    // 拦截器已拆信封:resolve 即业务 payload,失败走 catch
    updatedAccount.balance = balanceRes

    // 合并现货持仓（币币余额）和合约持仓
    const contractPositions = positionsRes?.positions || []
    const spotPositions = (balanceRes as any)?.spot_positions || []
    updatedAccount.positions = [...spotPositions, ...contractPositions]

    // 在数组中找到索引并替换整个对象，触发响应式更新
    replaceAccount(accountId, updatedAccount)

    // 清除加载状态
    setAccountLoading(accountId, false, false)
  } catch (e: any) {
    // 透传后端真实错误(如 "API key doesn't exist")让用户知晓配置问题;
    // 用 warn 替代 error,避免每 10s 轮询在 console 刷红(账户配置问题非代码故障)
    const backendMsg = e?.response?.data?.message as string | undefined
    const friendly = backendMsg?.includes('API key')
      ? '账户 API key 未配置或无效,请在「账号配置」中设置'
      : (backendMsg || e?.message || '加载失败')
    console.warn(`[${accountId}] 账户信息加载失败:`, friendly)
    replaceAccount(accountId, { error: friendly })
    setAccountLoading(accountId, false, false)
  }
}

// 刷新单个账户
const refreshAccount = async (accountId: string) => {
  const account = accounts.value.find(a => a.uuid === accountId)
  if (!account) return

  await updateAccountDetails(account)
}

// 刷新全部（只更新数据，不重新创建对象）
const refreshAll = async () => {
  refreshing.value = true
  try {
    // 只更新每个账户的数据，不重新加载账号列表
    await Promise.all(
      accounts.value.map(account => updateAccountDetails(account))
    )
  } finally {
    refreshing.value = false
  }
}

// 组件挂载:首次加载账号列表(loadAccountInfo 拉账号列表,区别于 refreshAll 只刷已有账号数据)
onMounted(() => {
  loadAccountInfo()
})

// 每 10 秒刷新已有账号数据(usePolling 封装 setInterval + onUnmounted 清理 + 可见性暂停)
usePolling(refreshAll, 10000)
</script>

<template>
  <PageLayout>
    <template #title>
      <div class="page-icon">
        <Wallet class="w-6 h-6" />
      </div>
      实盘账户信息
    </template>
    <template #description>
      实时监控账户余额与持仓
    </template>
    <template #actions>
      <Button
        variant="outline"
        size="sm"
        :disabled="refreshing"
        class="refresh-button"
        @click="refreshAll"
      >
        <RefreshCw :class="['w-4 h-4 mr-2', refreshing && 'animate-spin']" />
        刷新
      </Button>
    </template>

    <!-- 加载状态：仅首次加载且无账户时显示 -->
    <div
      v-if="loading && accounts.length === 0"
      class="loading-state"
    >
      <div class="loading-spinner" />
      <p>加载账户信息...</p>
    </div>

    <!-- 加载失败:区别于空态,提供重试 -->
    <div
      v-else-if="!loading && listError"
      class="empty-state"
    >
      <AlertCircle class="w-16 h-16 mx-auto mb-4 opacity-30" />
      <p class="empty-text">
        {{ listError }}
      </p>
      <Button
        variant="outline"
        size="sm"
        class="mt-4"
        @click="loadAccountInfo"
      >
        重试
      </Button>
    </div>

    <!-- 空状态 -->
    <div
      v-else-if="!loading && accounts.length === 0"
      class="empty-state"
    >
      <Wallet class="w-16 h-16 mx-auto mb-4 opacity-30" />
      <p class="empty-text">
        暂无实盘账户
      </p>
      <p class="empty-hint">
        请先配置实盘账号
      </p>
    </div>

    <!-- 账户内容 -->
    <div
      v-else
      class="account-content"
    >
      <!-- 全局统计卡片 -->
      <div class="stats-section">
        <div class="stats-grid">
          <div class="stat-card primary">
            <div class="stat-icon">
              <DollarSign class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">
                总权益
              </div>
              <div class="stat-value">
                ${{ formatFixed(totalEquity) }}
              </div>
            </div>
          </div>

          <div class="stat-card success">
            <div class="stat-icon">
              <Coins class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">
                可用余额
              </div>
              <div class="stat-value">
                ${{ formatFixed(totalAvailable) }}
              </div>
            </div>
          </div>

          <div class="stat-card info">
            <div class="stat-icon">
              <Activity class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">
                持仓数量
              </div>
              <div class="stat-value">
                {{ totalPositions }}
              </div>
            </div>
          </div>

          <div class="stat-card neutral">
            <div class="stat-icon">
              <Clock class="w-5 h-5" />
            </div>
            <div class="stat-content">
              <div class="stat-label">
                账户数量
              </div>
              <div class="stat-value">
                {{ accounts.length }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 账户卡片列表(余额/持仓/骨架屏在 AccountCard 内) -->
      <div class="accounts-section">
        <AccountCard
          v-for="account in accounts"
          :key="account.uuid"
          :account="account"
          :loading="accountLoadingStates[account.uuid]"
          @contextmenu="openAccountInfoMenu"
        />
      </div>
    </div>
  </PageLayout>
</template>

<style scoped>
.page-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary)) 100%);
  border-radius: var(--radius-lg);
  color: white;
}

.refresh-button {
  border-color: hsl(var(--border));
  color: hsl(var(--muted-foreground));
}

.refresh-button:hover:not(:disabled) {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: hsl(var(--muted-foreground));
}

.empty-text {
  font-size: 16px;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
}

/* 账户内容 */
.account-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片 */
.stats-section {
  margin-bottom: 8px;
}

/* 图标位基础走全局 cards.less,此处仅本页配色 */
.stat-icon {
  background: hsl(var(--border));
  color: hsl(var(--primary));
}

.stat-card.primary .stat-icon {
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary)) 100%);
  color: white;
}

.stat-card.success .stat-icon {
  background: linear-gradient(135deg, hsl(var(--success)) 0%, hsl(var(--success)) 100%);
  color: white;
}

.stat-card.info .stat-icon {
  background: linear-gradient(135deg, hsl(var(--primary)) 0%, hsl(var(--primary)) 100%);
  color: white;
}

.stat-card.neutral .stat-icon {
  background: linear-gradient(135deg, hsl(var(--muted-foreground)) 0%, hsl(var(--muted-foreground) / 0.8) 100%);
  color: white;
}

.stat-content {
  flex: 1;
}

/* 账户卡片列表 */
.accounts-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
