<template>
  <PageLayout>
    <div class="page-content">
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

            <!-- 代码范围选择(2026-08-18 抽为通用组件,各命令复用):
                 supportsAll 随命令类型联动,ticks 等不支持全市场的命令自动只剩自选 -->
            <div
              v-if="needsCodes"
              class="form-group"
            >
              <label class="form-label">
                同步范围
                <span class="form-hint">
                  {{ supportsAll ? '全市场 = 全量同步' : '该命令仅支持自选代码' }}
                  <template v-if="codeScope.scope === 'select'">· 已选 {{ codeScope.codes.length }} 只</template>
                </span>
              </label>
              <CodeScopePicker
                v-model="codeScope"
                :supports-all="supportsAll"
              />
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
            <SegmentedControl
              :model-value="sourceFilter"
              :options="sourceOptions"
              @update:model-value="onSourceChange"
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
              <template
                v-for="r in records"
                :key="r.uuid"
              >
                <div
                  class="hist-row hist-clickable"
                  :class="{ 'hist-active': expandedUuid === r.uuid }"
                  :title="r.error_message ? '点击查看错误详情' : '点击展开详情'"
                  @click="toggleRecord(r.uuid)"
                >
                  <span class="c-type"><span
                    class="tag"
                    :class="typeTagClass(r.sync_type)"
                  >{{ typeLabel(r.sync_type) }}</span><span
                    v-if="r.trigger_source"
                    class="tag src-tag"
                    :class="'src-' + (r.trigger_source || 'other')"
                  >{{ sourceLabel(r.trigger_source) }}</span></span>
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
                <!-- 展开详情:错误全文/起止/策略(错误只有 hover title 不可拷贝,失败排障需要全文) -->
                <div
                  v-if="expandedUuid === r.uuid"
                  class="hist-detail"
                >
                  <div class="detail-grid">
                    <span>开始 {{ r.started_at || '-' }}</span>
                    <span>完成 {{ r.completed_at || '-' }}</span>
                    <span>策略 {{ r.sync_strategy || '-' }}</span>
                    <span>任务 {{ r.uuid.slice(0, 8) }}</span>
                  </div>
                  <pre
                    v-if="r.error_message"
                    class="detail-error"
                  >{{ r.error_message }}</pre>
                  <span
                    v-else
                    class="detail-ok"
                  >无错误信息</span>
                </div>
              </template>
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
import DateField from '@/components/common/DateField.vue'
import { dataApi } from '@/api'
import type { SyncHistoryRecord } from '@/api'
import CodeScopePicker from '@/components/data/CodeScopePicker.vue'
import { formatRelativeTime, formatCompact } from '@/utils/format'
import { SYNC_TYPE_CONFIG, SYNC_STATUS_CONFIG } from '@/constants/statusConfig'
import { message as toast } from '@/utils/toast'

// ===== ① 命令表单 =====
const command = reactive({ type: 'bars', startDate: '', endDate: '' })

// 各类型参数契约(后端 /api/v1/data/sync):
// stockinfo 无需 codes(后端固定 code=ALL);bars 支持 codes=["all"] 展开全表(#5866);
// ticks/adjustfactor 必须显式指定 codes,不支持 all;日期仅 bars/ticks 使用
const supportsAll = computed(() => command.type === 'bars')
const needsCodes = computed(() => command.type !== 'stockinfo')
const showDatePicker = computed(() => ['bars', 'ticks'].includes(command.type))
const sending = ref(false)

// 代码范围选择(2026-08-18 抽为通用组件 CodeScopePicker):scope+codes 整体 v-model
const codeScope = ref<{ scope: 'all' | 'select'; codes: { code: string; name: string }[] }>({
  scope: 'all',
  codes: [],
})
const isAllMarket = computed(() => supportsAll.value && codeScope.value.scope === 'all')

// 同步范围:all=全市场(bars 传 codes=["all"]) / select=指定代码(搜索选择,免手敲)
const onSubmit = async () => {
  if (sending.value) return

  const params: { type: string; codes?: string[]; start_date?: string; end_date?: string } = {
    type: command.type,
  }
  if (needsCodes.value) {
    if (isAllMarket.value) {
      params.codes = ['all']
    } else {
      if (codeScope.value.codes.length === 0) {
        toast.error('请搜索并选择至少一只股票')
        return
      }
      params.codes = codeScope.value.codes.map(c => c.code)
    }
  }
  if (showDatePicker.value) {
    if (command.startDate) params.start_date = command.startDate
    if (command.endDate) params.end_date = command.endDate
  }

  sending.value = true
  try {
    const res: any = await dataApi.sync(params)
    // 2026-08-18 异步化:API 仅转发 Kafka 命令到 data-worker,秒回受理数;
    // 执行结果由 worker 落 data_sync_record,稍后刷新同步历史可见
    const dispatched = Number(res?.dispatched ?? 0)
    const total = Number(res?.total ?? 0)
    if (dispatched > 0 && dispatched < total) {
      toast.warning(`命令已派发 ${dispatched}/${total} 只(部分派发失败)，执行进度见同步历史`)
    } else if (total > 0) {
      toast.success(`同步命令已派发至 data-worker（${total} 只代码），进度见同步历史`)
    } else {
      toast.success('同步命令已派发至 data-worker，进度见同步历史')
    }
    // worker 消费有延迟:先刷一次(受理态),3s 后再刷一次(执行结果陆续落库)
    await fetchHistory(false)
    setTimeout(() => { fetchHistory(false) }, 3000)
  } catch (e: any) {
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    toast.error(`发送失败：${detail}`)
  } finally {
    sending.value = false
  }
}

const clearForm = () => {
  codeScope.value = { scope: 'all', codes: [] }
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
    if (sourceFilter.value) params.trigger_source = sourceFilter.value
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

// 来源筛选(2026-08-18):定时任务每晚全市场 ~5584 条会刷屏,手动记录需可分离
const sourceFilter = ref('')
const sourceOptions = [
  { key: '', label: '全部来源' },
  { key: 'web', label: 'Web' },
  { key: 'cli', label: 'CLI' },
  { key: 'scheduled', label: '定时' },
]
function onSourceChange(v: string) {
  sourceFilter.value = v
  fetchHistory(false)
}
const SOURCE_LABELS: Record<string, string> = { web: 'Web', cli: 'CLI', scheduled: '定时', other: '其他' }
const sourceLabel = (t?: string) => SOURCE_LABELS[t || 'other'] || t || '-' 

// 历史行展开(2026-08-18):错误全文/起止时间/策略——错误只放 title tooltip 不可读不可拷贝
const expandedUuid = ref<string | null>(null)
function toggleRecord(uuid: string) {
  expandedUuid.value = expandedUuid.value === uuid ? null : uuid
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

onMounted(() => {
  fetchHistory(false)
})
</script>

<style scoped>
.page-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 图标位/双列网格/卡片标题基础走全局 cards.less(2026-08-19 收口) */

/* 全局 .card 带 overflow:hidden(裁圆角),会剪掉悬浮下拉框,此处放开 */
.two-column-grid .card {
  overflow: visible;
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

/* 行展开交互:点击切详情,选中态左缘高亮 */
.hist-clickable { cursor: pointer; transition: background 0.12s; }
.hist-clickable:hover { background: hsl(var(--foreground) / 0.03); }
.hist-active {
  background: hsl(var(--primary) / 0.06);
  box-shadow: inset 2px 0 0 hsl(var(--primary));
}
.hist-detail {
  padding: 8px 12px;
  background: hsl(var(--foreground) / 0.02);
  border-bottom: 1px solid hsl(var(--border));
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}
.detail-grid { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 6px; }
.detail-error {
  margin: 0;
  padding: 8px 10px;
  background: hsl(var(--error) / 0.06);
  border: 1px solid hsl(var(--error) / 0.25);
  border-radius: var(--radius-sm);
  color: hsl(var(--error));
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 160px;
  overflow-y: auto;
}
.detail-ok { font-size: 12px; }

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
.src-tag { font-size: 10px; margin-left: 4px; padding: 1px 5px; }
.src-cli {
  color: hsl(var(--secondary-foreground));
  background: hsl(var(--secondary-foreground) / 0.08);
  border: 1px solid hsl(var(--secondary-foreground) / 0.3);
}
.src-web {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.08);
  border: 1px solid hsl(var(--primary) / 0.25);
}
.src-scheduled {
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted-foreground) / 0.08);
  border: 1px solid hsl(var(--border));
}
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
/* queued/lost(2026-08-20 对齐概览 timeline-dot):派发即落库的两端状态,缺色则无点 */
.st-dot.st-queued,
.st-dot.st-lost { background: hsl(var(--muted-foreground) / 0.5); }

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
