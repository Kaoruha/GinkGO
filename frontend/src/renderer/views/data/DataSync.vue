<template>
  <PageLayout>
    <template #meta>
      <span class="updated-at">更新于 {{ lastUpdated || '--' }}</span>
    </template>

    <div class="page-content">
      <!-- ① 数据存量统计行 -->
      <div
        class="stats-grid m-stagger"
        data-testid="sync-stats"
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

            <div
              v-if="showDatePicker"
              class="form-group"
            >
              <label class="form-label">日期范围 <span class="form-hint">留空 = 全量</span></label>
              <div class="date-range">
                <DateField
                  v-model="command.startDate"
                  bordered
                  clearable
                />
                <span class="range-sep">至</span>
                <DateField
                  v-model="command.endDate"
                  bordered
                  clearable
                />
              </div>
            </div>

            <div
              v-if="needsCodes && supportsAll"
              class="form-group"
            >
              <label class="form-label">同步范围 <span class="form-hint">全市场 = 全量同步</span></label>
              <SegmentedControl
                :model-value="scope"
                :options="scopeOptions"
                @update:model-value="onScopeChange"
              />
            </div>

            <div
              v-if="needsCodes && !isAllMarket"
              class="form-group code-picker"
            >
              <label class="form-label">股票代码 <span class="form-hint">已选 {{ selectedCodes.length }} 只</span></label>
              <div
                v-if="selectedCodes.length"
                class="picked-row"
              >
                <span
                  v-for="c in selectedCodes"
                  :key="c.code"
                  class="picked-tag"
                >
                  {{ c.code }} {{ c.name }}
                  <button
                    type="button"
                    class="picked-x"
                    @click="removeCode(c.code)"
                  >✕</button>
                </span>
              </div>
              <input
                v-model="codeQuery"
                type="text"
                class="form-input"
                placeholder="搜索代码或名称，如 600519 / 平安"
                @input="onQueryInput"
                @focus="onQueryInput"
                @blur="sugVisible = false"
              >
              <div
                v-if="sugVisible"
                class="sug-box"
              >
                <p
                  v-if="sugLoading"
                  class="sug-hint"
                >
                  搜索中...
                </p>
                <p
                  v-else-if="!codeQuery.trim()"
                  class="sug-hint"
                >
                  输入代码或名称搜索
                </p>
                <p
                  v-else-if="suggestions.length === 0"
                  class="sug-hint"
                >
                  无匹配结果
                </p>
                <template v-else>
                  <button
                    v-for="s in suggestions"
                    :key="s.code"
                    type="button"
                    class="sug-item"
                    :class="{ 'is-picked': isPicked(s.code) }"
                    @mousedown.prevent="pickCode(s)"
                  >
                    <span class="sug-code">{{ s.code }}</span>
                    <span class="sug-name">{{ s.name }}</span>
                  </button>
                  <p class="sug-footer">
                    共 {{ sugTotal }} 条{{ sugTotal > suggestions.length ? `，显示前 ${suggestions.length} 条，可输入更精确关键词` : '' }}
                  </p>
                </template>
              </div>
            </div>

            <div class="form-actions">
              <button
                type="submit"
                class="btn-primary"
                :disabled="sending"
              >
                {{ sending ? '发送中...' : '发送命令' }}
              </button>
              <button
                type="button"
                class="btn-secondary"
                :disabled="sending"
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
                    +{{ formatNumber(r.records_added) }}<template v-if="r.records_updated > 0"> ~{{ formatNumber(r.records_updated) }}</template><template v-if="r.records_failed > 0"> ✕{{ formatNumber(r.records_failed) }}</template>
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
import { ref, reactive, computed, watch, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import DateField from '@/components/common/DateField.vue'
import { dataApi } from '@/api'
import type { SyncHistoryRecord, StockInfo } from '@/api'
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
const command = reactive({ type: 'bars', startDate: '', endDate: '' })

// 各类型参数契约(后端 /api/v1/data/sync):
// stockinfo 无需 codes(后端固定 code=ALL);bars 支持 codes=["all"] 展开全表(#5866);
// ticks/adjustfactor 必须显式指定 codes,不支持 all;日期仅 bars/ticks 使用
const supportsAll = computed(() => command.type === 'bars')
const needsCodes = computed(() => command.type !== 'stockinfo')
const showDatePicker = computed(() => ['bars', 'ticks'].includes(command.type))
const isAllMarket = computed(() => supportsAll.value && scope.value === 'all')

// 同步范围:all=全市场(bars 传 codes=["all"]) / select=指定代码(搜索选择,免手敲)
const scope = ref<'all' | 'select'>('all')
const sending = ref(false)
const scopeOptions = [
  { key: 'all', label: '全市场' },
  { key: 'select', label: '指定代码' },
]
function onScopeChange(v: string) {
  scope.value = v as 'all' | 'select'
}

// 切到不支持全市场的类型(ticks/adjustfactor)时收回指定代码模式
watch(() => command.type, () => {
  if (!supportsAll.value) scope.value = 'select'
})

// 代码搜索选择器:listStocks(search=) 支持代码/中文名模糊
const codeQuery = ref('')
const suggestions = ref<StockInfo[]>([])
const sugTotal = ref(0)
const sugLoading = ref(false)
const sugVisible = ref(false)
const selectedCodes = ref<{ code: string; name: string }[]>([])
let sugTimer: ReturnType<typeof setTimeout> | null = null

async function searchStocks() {
  const q = codeQuery.value.trim()
  sugVisible.value = true
  if (!q) {
    suggestions.value = []
    sugTotal.value = 0
    return
  }
  sugLoading.value = true
  try {
    const res: any = await dataApi.listStocks({ query: q, page: 1, page_size: 50 })
    const items = res?.items ?? (Array.isArray(res) ? res : [])
    // 请求返回时输入可能已变,过期结果丢弃
    if (codeQuery.value.trim() === q) {
      suggestions.value = items
      sugTotal.value = res?.total ?? items.length
    }
  } catch {
    if (codeQuery.value.trim() === q) {
      suggestions.value = []
      sugTotal.value = 0
    }
  } finally {
    sugLoading.value = false
  }
}

function onQueryInput() {
  if (sugTimer) clearTimeout(sugTimer)
  sugTimer = setTimeout(searchStocks, 300)
}

function isPicked(code: string) {
  return selectedCodes.value.some(c => c.code === code)
}

function pickCode(s: StockInfo) {
  if (!isPicked(s.code)) selectedCodes.value.push({ code: s.code, name: s.name })
  codeQuery.value = ''
  suggestions.value = []
  sugTotal.value = 0
  sugVisible.value = false
}

function removeCode(code: string) {
  selectedCodes.value = selectedCodes.value.filter(c => c.code !== code)
}

const onSubmit = async () => {
  if (sending.value) return

  const params: { type: string; codes?: string[]; start_date?: string; end_date?: string } = {
    type: command.type,
  }
  if (needsCodes.value) {
    if (isAllMarket.value) {
      params.codes = ['all']
    } else {
      if (selectedCodes.value.length === 0) {
        toast.error('请搜索并选择至少一只股票')
        return
      }
      params.codes = selectedCodes.value.map(c => c.code)
    }
  }
  if (showDatePicker.value) {
    if (command.startDate) params.start_date = command.startDate
    if (command.endDate) params.end_date = command.endDate
  }

  sending.value = true
  try {
    const res: any = await dataApi.sync(params)
    // #6071: 后端 bars/ticks 循环单 code 失败被 except 吞、整体仍 200,凭 failed 计数区分
    const failed = Number(res?.failed ?? 0)
    const total = Number(res?.total ?? 0)
    if (failed > 0) {
      toast.warning(`同步完成：${total} 只中 ${failed} 只失败，详情见同步历史`)
    } else if (total > 0) {
      toast.success(`同步命令已完成（${total} 只代码），结果见同步历史`)
    } else {
      toast.success('同步命令已完成，结果见同步历史')
    }
    // 同步在请求内完成、返回时历史已落库,刷新即见 partial/0 条等真实状态
    await Promise.all([fetchHistory(false), fetchStats()])
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    toast.error(`发送失败：${detail}`)
  } finally {
    sending.value = false
  }
}

const clearForm = () => {
  command.startDate = ''
  command.endDate = ''
  codeQuery.value = ''
  suggestions.value = []
  sugTotal.value = 0
  selectedCodes.value = []
  sugVisible.value = false
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

/* 全局 .card 带 overflow:hidden(裁圆角),会剪掉悬浮下拉框,此处放开 */
.two-column-grid .card {
  overflow: visible;
}

/* 双列布局(同 DataOverview) */
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

.date-range .date-field {
  flex: 1;
  min-width: 0;
}

.range-sep {
  font-size: 13px;
  color: hsl(var(--muted-foreground));
}

/* 代码搜索选择器 */
.code-picker {
  position: relative;
}

.picked-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.picked-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.picked-x {
  border: none;
  background: transparent;
  padding: 0;
  color: inherit;
  font-size: 11px;
  cursor: pointer;
  opacity: 0.7;
}

.picked-x:hover {
  opacity: 1;
}

.sug-box {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 10;
  margin-top: 4px;
  max-height: 300px;
  overflow-y: auto;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
}

.sug-footer {
  position: sticky;
  bottom: 0;
  margin: 0;
  padding: 6px 12px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  background: hsl(var(--card));
  border-top: 1px solid hsl(var(--border));
}

.sug-hint {
  margin: 0;
  padding: 10px 12px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.sug-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.sug-item:hover {
  background: hsl(var(--muted) / 0.6);
}

.sug-item.is-picked {
  opacity: 0.5;
}

.sug-code {
  font-size: 13px;
  color: hsl(var(--foreground));
  font-variant-numeric: tabular-nums;
}

.sug-name {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
