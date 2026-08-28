<template>
  <PageLayout>
    <template #title>
      数据概览
    </template>
    <template #actions>
      <button
        class="btn-primary"
        :disabled="refreshing"
        @click="refreshStats"
      >
        <svg
          v-if="!refreshing"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path d="M21 2v6h-6" />
          <path d="M3 12a9 9 0 0 1 15-6.7L21 8" />
          <path d="M3 22v-6h6" />
          <path d="M21 12a9 9 0 0 1-15 6.7L3 16" />
        </svg>
        <svg
          v-else
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          class="spin"
        >
          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
        </svg>
        {{ refreshing ? '刷新中...' : '刷新统计' }}
      </button>
    </template>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div
        class="stat-card stat-blue stat-clickable"
        title="点击浏览股票信息"
        @click="goBrowser('stocks')"
      >
        <div class="stat-icon">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <rect
              x="2"
              y="7"
              width="20"
              height="14"
              rx="2"
              ry="2"
            />
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            股票总数
          </div>
          <div class="stat-value">
            {{ formatNumber(dataStats.totalStocks) }}
          </div>
        </div>
      </div>

      <div
        class="stat-card stat-green stat-clickable"
        title="点击浏览K线数据"
        @click="goBrowser('bars')"
      >
        <div class="stat-icon">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <path d="M3 3v18h18" />
            <path d="M18 17V9" />
            <path d="M13 17V5" />
            <path d="M8 17v-3" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            K线数据量
          </div>
          <div class="stat-value">
            {{ formatNumber(dataStats.totalBars) }}
          </div>
        </div>
      </div>

      <div
        class="stat-card stat-orange stat-clickable"
        title="点击浏览 Tick 数据"
        @click="goBrowser('ticks')"
      >
        <div class="stat-icon">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <polygon points="13,2 3,14 12,14 11,22 21,10 12,10" />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            Tick数据量
          </div>
          <div class="stat-value">
            {{ formatNumber(dataStats.totalTicks) }}
          </div>
        </div>
      </div>

      <div
        class="stat-card stat-purple stat-clickable"
        title="点击浏览复权因子"
        @click="goBrowser('adjust')"
      >
        <div class="stat-icon">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line
              x1="12"
              y1="20"
              x2="12"
              y2="10"
            />
            <line
              x1="18"
              y1="20"
              x2="18"
              y2="4"
            />
            <line
              x1="6"
              y1="20"
              x2="6"
              y2="16"
            />
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-label">
            复权因子
          </div>
          <div class="stat-value">
            {{ formatNumber(dataStats.totalAdjustFactors) }}
          </div>
        </div>
      </div>
    </div>

    <!-- 最近更新 -->
    <div class="two-column-grid">
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            最近同步记录
          </h3>
          <!-- 动线打通(2026-08-20):概览只留摘要,失败排查/筛选/详情去同步页 -->
          <RouterLink
            class="view-all"
            to="/data/sync"
          >
            查看全部 →
          </RouterLink>
        </div>
        <div class="card-body">
          <div
            v-if="recentSyncs.length > 0"
            class="timeline"
          >
            <div
              v-for="(item, index) in recentSyncs"
              :key="index"
              class="timeline-item"
              @contextmenu="openSyncMenu($event, item)"
            >
              <div
                class="timeline-dot"
                :class="item.status"
              />
              <div class="timeline-content">
                <div class="timeline-title">
                  {{ item.type }} - {{ item.code }}
                </div>
                <div class="timeline-time">
                  {{ item.time }}
                </div>
              </div>
            </div>
          </div>
          <EmptyState
            v-else
            description="暂无同步记录"
          />
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">
            数据源状态
          </h3>
        </div>
        <div class="card-body">
          <div class="data-sources">
            <div
              v-for="source in dataSources"
              :key="source.name"
              class="data-source-item"
            >
              <div class="source-info">
                <div class="source-name">
                  {{ source.name }}
                </div>
                <div class="source-desc">
                  {{ source.description }}
                </div>
              </div>
              <span
                class="tag"
                :class="source.status === 'online' ? 'tag-green' : 'tag-red'"
              >
                {{ source.status === 'online' ? '在线' : '离线' }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import PageLayout from '@/components/common/PageLayout.vue'
import { formatCompact, formatDate } from '@/utils/format'
import { SYNC_TYPE_CONFIG } from '@/constants/statusConfig'
import { dataApi } from '@/api'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import { useAsyncAction } from '@/composables/useAsyncAction'

// refreshing 由 useAsyncAction 的 running 提供(见 refreshStats)

const dataStats = reactive({
  totalStocks: 0,
  totalBars: 0,
  totalTicks: 0,
  totalAdjustFactors: 0
})

interface SyncRecord {
  type: string
  code: string
  time: string
  status: string
}

/** 同步记录右键菜单(本页无行操作,给复制类) */
const { open: openCtxMenu } = useContextMenu()
const openSyncMenu = (e: MouseEvent, item: SyncRecord) => {
  openCtxMenu(e, [
    { label: '复制同步类型', action: () => { navigator.clipboard.writeText(item.type); toast.success('已复制') } },
    { label: '复制代码', action: () => { navigator.clipboard.writeText(item.code); toast.success('已复制') } },
  ])
}

const recentSyncs = ref<SyncRecord[]>([])

interface DataSource {
  name: string
  description: string
  status: string
}

const dataSources = ref<DataSource[]>([])

const formatTime = (iso: string | null): string =>
  iso ? formatDate(iso) : '--'

const { running: refreshing, run: refreshStats } = useAsyncAction(async () => {
  const [statsRes, sourcesRes, syncHistoryRes] = await Promise.allSettled([
    dataApi.getStats(),
    dataApi.getSources(),
    dataApi.getSyncHistory({ page: 1, page_size: 10 }),
  ])

  if (statsRes.status === 'fulfilled') {
    const stats = (statsRes.value as any)?.data ?? statsRes.value
    dataStats.totalStocks = stats.total_stocks ?? 0
    dataStats.totalBars = stats.total_bars ?? 0
    dataStats.totalTicks = stats.total_ticks ?? 0
    dataStats.totalAdjustFactors = stats.total_adjust_factors ?? 0
  }

  if (sourcesRes.status === 'fulfilled') {
    const raw = (sourcesRes.value as any)?.data ?? sourcesRes.value
    const list: DataSource[] = (Array.isArray(raw) ? raw : []).map((s: any) => ({
      name: s.name,
      description: s.description || '',
      status: s.status === 'active' ? 'online' : 'offline',
    }))
    dataSources.value = list
  }

  if (syncHistoryRes.status === 'fulfilled') {
    const raw = (syncHistoryRes.value as any)?.data ?? []
    const items: any[] = Array.isArray(raw) ? raw : []
    recentSyncs.value = items.map((s: any) => ({
      type: SYNC_TYPE_CONFIG[s.sync_type]?.label ?? s.sync_type,
      code: s.code,
      time: formatTime(s.completed_at || s.started_at),
      status: s.status,
    }))
  }
}, { success: false })

const formatNumber = (num: number): string => formatCompact(num, 1)

// 枢纽导航(2026-08-18):统计卡=数据资产入口,点击直达浏览器对应类型
const router = useRouter()
const goBrowser = (type: string) => {
  router.push({ path: '/data/browser', query: { type } })
}

onMounted(() => {
  refreshStats()
})
</script>

<style scoped>
/* 统计卡片:结构/图标位基础走全局 cards.less,此处仅色变体(2026-08-19 顶条删除,对齐全站统计卡无顶条形态) */

/* 枢纽卡:可点击直达数据浏览器,hover 反馈 + 右上角浏览提示 */
.stat-clickable { cursor: pointer; transition: border-color 0.15s, transform 0.15s; }
.stat-clickable:hover {
  border-color: hsl(var(--primary) / 0.5);
  transform: translateY(-2px);
}
.stat-clickable::after {
  content: '浏览 →';
  position: absolute;
  right: 10px;
  top: 8px;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  opacity: 0;
  transition: opacity 0.15s;
}
.stat-clickable:hover::after { opacity: 1; color: hsl(var(--primary)); }

/* 图标位基础走全局 .stat-icon(cards.less),此处仅色变体 */

.stat-blue .stat-icon { background: hsl(var(--primary) / 0.1); color: hsl(var(--primary)); }
.stat-green .stat-icon { background: hsl(var(--success) / 0.1); color: hsl(var(--success)); }
.stat-orange .stat-icon { background: hsl(var(--warning) / 0.1); color: hsl(var(--warning)); }
.stat-purple .stat-icon { background: hsl(var(--secondary-foreground) / 0.1); color: hsl(var(--secondary-foreground)); }

/* 卡片结构(card-header/card-body)/标题排版/双列网格走全局 cards.less(2026-08-19 对齐全站) */

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
  background: hsl(var(--border));
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
  border: 2px solid hsl(var(--card));
}

.timeline-dot.success {
  background: hsl(var(--success));
}

.timeline-dot.running {
  background: hsl(var(--warning));
}

.timeline-dot.partial {
  background: hsl(var(--warning));
}

.timeline-dot.failed {
  background: hsl(var(--error));
}

/* queued/lost(2026-08-18 派发即落库):无色则空心点不可辨 */
.timeline-dot.queued,
.timeline-dot.lost {
  background: hsl(var(--muted-foreground) / 0.5);
}

.timeline-content {
  padding-left: 8px;
}

.timeline-title {
  font-size: 14px;
  color: hsl(var(--foreground));
  margin-bottom: 4px;
}

.timeline-time {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}
/* 数据源列表 */
.data-sources {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.data-source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: hsl(var(--muted));
  border-radius: var(--radius-sm);
}

.source-info {
  flex: 1;
}

.source-name {
  font-size: 14px;
  color: hsl(var(--foreground));
  margin-bottom: 4px;
}

.source-desc {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 在线/离线标签走全局 tags.less .tag 体系(2026-08-19 收口,弃自定义 status-tag) */

/* 卡头"查看全部"链接(视觉同 Dashboard .list-link):概览摘要 → 同步页全量 */
.view-all {
  font-size: 14px;
  font-weight: 400;
  color: hsl(var(--primary));
}

.view-all:hover {
  text-decoration: underline;
}
</style>
