<template>
  <PageLayout>
    <template #title>
      数据同步 <span class="demo-badge">演示稿</span>
    </template>
    <template #meta>
      <span class="updated-at">更新于 {{ lastUpdated || '--' }}</span>
    </template>

    <div class="page-content">
      <!-- ① 数据存量统计行 -->
      <div
        class="stats-grid m-stagger"
        data-testid="demo-stats"
      >
        <div
          v-for="s in statCards"
          :key="s.label"
          class="stat-card"
        >
          <div
            class="stat-icon"
            v-html="s.icon"
          />
          <div class="stat-content">
            <div class="stat-label">
              {{ s.label }}
            </div>
            <div
              v-if="!loading"
              class="stat-value"
            >
              {{ s.value }}<span
                v-if="s.suffix"
                class="stat-suffix"
              > {{ s.suffix }}</span>
            </div>
            <div
              v-else
              class="stat-value"
            >
              --
            </div>
          </div>
        </div>
      </div>

      <div class="two-column-grid">
        <!-- ② 发送同步命令 -->
        <div class="card">
          <h3 class="card-title">
            发送同步命令
          </h3>
          <form
            class="sync-form"
            @submit.prevent="onSubmit"
          >
            <div class="form-group">
              <label class="form-label">命令类型</label>
              <select
                v-model="command.type"
                class="form-select"
              >
                <option value="bars">
                  K线数据
                </option>
                <option value="ticks">
                  Tick数据
                </option>
                <option value="stockinfo">
                  股票信息
                </option>
                <option value="adjustfactor">
                  复权因子
                </option>
              </select>
            </div>

            <div class="form-group">
              <label class="form-label">日期范围 <span class="form-hint">留空 = 全量</span></label>
              <div class="date-range">
                <input
                  v-model="command.startDate"
                  type="date"
                  class="form-input"
                >
                <span class="range-sep">至</span>
                <input
                  v-model="command.endDate"
                  type="date"
                  class="form-input"
                >
              </div>
            </div>

            <div class="form-group">
              <label class="form-label">股票代码</label>
              <textarea
                v-model="command.codes"
                class="form-textarea"
                rows="4"
                placeholder="输入股票代码，每行一个&#10;例如：&#10;000001.SZ&#10;000002.SZ"
              />
            </div>

            <div class="form-actions">
              <button
                type="submit"
                class="btn-primary"
              >
                发送命令
              </button>
              <button
                type="button"
                class="btn-secondary"
                @click="clearForm"
              >
                清空
              </button>
            </div>
          </form>
        </div>

        <!-- ③ 同步历史（服务端落库记录） -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">
              同步历史 <span class="history-total">共 {{ total }} 条</span>
            </h3>
            <button
              class="btn-small"
              @click="fetchHistory(false)"
            >
              刷新
            </button>
          </div>

          <div class="filter-row">
            <SegmentedControl
              :model-value="typeFilter"
              :options="typeOptions"
              @update:model-value="onFilterChange"
            />
          </div>

          <p
            v-if="historyLoading && records.length === 0"
            class="loading-text"
          >
            加载中...
          </p>
          <p
            v-else-if="listError"
            class="error-text"
          >
            {{ listError }}
          </p>

          <template v-else-if="records.length > 0">
            <div class="hist-table">
              <div class="hist-row hist-head">
                <span class="c-type">类型</span>
                <span class="c-code">代码</span>
                <span class="c-status">状态</span>
                <span class="c-dur">耗时</span>
                <span class="c-rec">处理量</span>
                <span class="c-time">完成时间</span>
              </div>
              <div
                v-for="r in records"
                :key="r.uuid"
                class="hist-row"
                :title="r.error_message || ''"
              >
                <span class="c-type"><span
                  class="tag"
                  :class="typeTagClass(r.sync_type)"
                >{{ typeLabel(r.sync_type) }}</span></span>
                <span class="c-code">{{ r.code }}</span>
                <span class="c-status"><span
                  class="st-dot"
                  :class="'st-' + r.status"
                />{{ statusLabel(r.status) }}</span>
                <span class="c-dur">{{ formatDuration(r.duration_ms) }}</span>
                <span class="c-rec">
                  <span class="rec-main">{{ formatNumber(r.records_processed) }}</span>
                  <span
                    class="rec-detail"
                    :class="{ 'rec-fail': r.records_failed > 0 }"
                  >
                    +{{ formatNumber(r.records_added) }}<template v-if="r.records_updated > 0"> ~{{ formatNumber(r.records_updated) }}</template><template v-if="r.records_failed > 0"> ✕{{ r.records_failed }}</template>
                  </span>
                </span>
                <span
                  class="c-time"
                  :title="r.completed_at || r.started_at || ''"
                >{{ formatRelativeTime(r.completed_at || r.started_at) }}</span>
              </div>
            </div>
            <div
              v-if="hasMore"
              class="load-more"
            >
              <button
                class="btn-small"
                :disabled="historyLoading"
                @click="loadMore"
              >
                {{ historyLoading ? '加载中...' : '加载更多' }}
              </button>
            </div>
          </template>
          <EmptyState
            v-else
            description="暂无同步记录"
          />
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { dataApi } from '@/api'
import type { SyncHistoryRecord } from '@/api'
import { formatRelativeTime, formatCompact } from '@/utils/format'
import { SYNC_TYPE_CONFIG, SYNC_STATUS_CONFIG } from '@/constants/statusConfig'
import { message as toast } from '@/utils/toast'

// ===== ① 存量统计 =====
const loading = ref(true)
const lastUpdated = ref('')
const stats = reactive({ stocks: 0, bars: 0, ticks: 0, adjustFactors: 0, latest: '' })

const ICONS = {
  stock: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="m8 10 2.5 2.5L16 7"/></svg>',
  bars: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>',
  tick: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>',
  factor: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 17 9 11l4 4 8-8"/><path d="M17 7h4v4"/></svg>',
}

const statCards = computed(() => [
  { label: '股票信息', value: formatNumber(stats.stocks), suffix: '只', icon: ICONS.stock },
  { label: 'K线数据', value: formatNumber(stats.bars), suffix: '条', icon: ICONS.bars },
  { label: 'Tick数据', value: formatNumber(stats.ticks), suffix: '条', icon: ICONS.tick },
  { label: '复权因子', value: formatNumber(stats.adjustFactors), suffix: '条', icon: ICONS.factor },
])

// ===== ② 命令表单 =====
const command = reactive({ type: 'bars', codes: '', startDate: '', endDate: '' })

const onSubmit = () => {
  if (!command.codes.trim()) {
    toast.error('请输入股票代码')
    return
  }
  // 演示稿只验证交互,不实际发送同步命令
  toast.success('演示页:命令已校验通过(不实际发送)')
}

const clearForm = () => {
  command.codes = ''
  command.startDate = ''
  command.endDate = ''
}

// ===== ③ 同步历史 =====
const records = ref<SyncHistoryRecord[]>([])
const total = ref(0)
const page = ref(0)
const PAGE_SIZE = 20
const historyLoading = ref(false)
const listError = ref('')
const typeFilter = ref('')

const typeOptions = [
  { key: '', label: '全部' },
  { key: 'bars', label: 'K线' },
  { key: 'ticks', label: 'Tick' },
  { key: 'stockinfo', label: '股票' },
  { key: 'adjustfactor', label: '复权' },
]

const hasMore = computed(() => records.value.length < total.value)

const typeLabel = (t: string) => SYNC_TYPE_CONFIG[t]?.label ?? t
const typeTagClass = (t: string) => SYNC_TYPE_CONFIG[t]?.tagClass ?? 'tag-gray'
const statusLabel = (s: string) => SYNC_STATUS_CONFIG[s]?.label ?? s

async function fetchHistory(append = false) {
  if (append) page.value += 1
  else page.value = 1
  historyLoading.value = true
  listError.value = ''
  try {
    const params: any = { page: page.value, page_size: PAGE_SIZE }
    if (typeFilter.value) params.sync_type = typeFilter.value
    const res: any = await dataApi.getSyncHistory(params)
    const items = res?.items ?? (Array.isArray(res) ? res : [])
    records.value = append ? [...records.value, ...items] : items
    total.value = res?.total ?? items.length
  } catch (e: any) {
    const st = e?.response?.status
    listError.value = st ? `同步历史加载失败(HTTP ${st})` : '同步历史加载失败,请检查网络后重试'
    if (!append) { records.value = []; total.value = 0 }
  } finally {
    historyLoading.value = false
  }
}

function onFilterChange(v: string) {
  typeFilter.value = v
  fetchHistory(false)
}

function loadMore() {
  fetchHistory(true)
}

// ===== 格式化 =====
function formatNumber(n: number | null | undefined): string {
  return formatCompact(n, 1)
}

function formatDuration(ms: number | null | undefined): string {
  if (!ms || ms <= 0) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m${Math.round((ms % 60000) / 1000)}s`
}

async function fetchStats() {
  loading.value = true
  try {
    const data = await dataApi.getStats()
    stats.stocks = data.total_stocks || 0
    stats.bars = data.total_bars || 0
    stats.ticks = data.total_ticks || 0
    stats.adjustFactors = data.total_adjust_factors || 0
    stats.latest = data.latest_update || ''
  } finally {
    loading.value = false
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  }
}

onMounted(() => {
  fetchStats()
  fetchHistory(false)
})
</script>

<style scoped>
.demo-badge {
  display: inline-block;
  vertical-align: middle;
  margin-left: 8px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: hsl(var(--warning) / 0.15);
  color: hsl(var(--warning));
  font-size: 12px;
  font-weight: 500;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.updated-at {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 存量统计(全局 stats-grid 4列/stat-card 已有,补图标位) */
.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--muted));
  border-radius: var(--radius-lg);
  color: hsl(var(--muted-foreground));
  flex-shrink: 0;
}

.stat-suffix {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
  font-weight: 400;
}

/* 双列布局(同 DataSync/DataOverview) */
.two-column-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  align-items: start;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

/* 表单 */
.sync-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-hint {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  font-weight: 400;
  margin-left: 6px;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range .form-input {
  flex: 1;
  min-width: 0;
}

.range-sep {
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

.form-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

/* 历史卡 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.history-total {
  font-size: 12px;
  font-weight: 400;
  color: hsl(var(--muted-foreground));
  margin-left: 8px;
}

.filter-row {
  margin-bottom: 12px;
}

.loading-text,
.error-text {
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  margin: 0;
  padding: 16px 0;
  text-align: center;
}

.error-text {
  color: hsl(var(--error-fg));
}

.hist-table {
  display: flex;
  flex-direction: column;
}

.hist-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 9px 0;
  border-bottom: 1px solid hsl(var(--border));
  font-size: 13px;
}

.hist-row:last-child {
  border-bottom: none;
}

.hist-head {
  position: sticky;
  top: 0;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.c-type { flex: 0 0 48px; }
.c-code { flex: 0 0 84px; font-variant-numeric: tabular-nums; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-status { flex: 0 0 64px; display: inline-flex; align-items: center; gap: 5px; }
.c-dur { flex: 0 0 52px; text-align: right; color: hsl(var(--muted-foreground)); font-variant-numeric: tabular-nums; }
.c-rec { flex: 1; min-width: 0; display: inline-flex; align-items: baseline; gap: 8px; justify-content: flex-end; }
.c-time { flex: 0 0 84px; text-align: right; color: hsl(var(--muted-foreground)); font-size: 12px; white-space: nowrap; }

.st-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.st-dot.st-success { background: hsl(var(--success-fg)); }
.st-dot.st-partial { background: hsl(var(--warning)); }
.st-dot.st-failed { background: hsl(var(--error-fg)); }
.st-dot.st-running { background: hsl(var(--primary)); }

.rec-main {
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

.rec-detail {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-variant-numeric: tabular-nums;
}

.rec-detail.rec-fail {
  color: hsl(var(--error-fg));
}

.load-more {
  display: flex;
  justify-content: center;
  padding-top: 12px;
}
</style>
