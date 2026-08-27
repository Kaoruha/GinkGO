<template>
  <PageLayout>
    <template #title>
      实盘交易
    </template>
    <template #description>
      所有实盘运行实例
    </template>

    <div class="table-container">
      <table
        v-if="portfolios.length"
        class="data-table"
      >
        <thead>
          <tr>
            <th>组合名称</th>
            <th>模式</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in portfolios"
            :key="p.uuid"
            @contextmenu="openPortfolioMenu($event, p)"
          >
            <td>
              <router-link
                :to="`/portfolios/${p.uuid}`"
                class="link"
              >
                {{ p.name || p.uuid?.slice(0, 8) }}
              </router-link>
            </td>
            <td>{{ portfolioModeLabel(p.mode) }}</td>
            <td>{{ formatDate(p.created_at) }}</td>
          </tr>
        </tbody>
      </table>
      <EmptyState
        v-else
        description="暂无实盘实例"
      />
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { portfolioApi } from '@/api/modules/portfolio'
import { portfolioModeLabel } from '@/constants/statusConfig'
import { useRouter } from 'vue-router'
import { message as toast } from '@/utils/toast'
import { useContextMenu } from '@/composables/useContextMenu'
import { formatDate } from '@/utils/format'

const router = useRouter()

/** 行右键菜单(替代操作列链接) */
const { open: openCtxMenu } = useContextMenu()
const openPortfolioMenu = (e: MouseEvent, p: any) => {
  openCtxMenu(e, [
    { label: '查看详情', action: () => router.push(`/portfolios/${p.uuid}`) },
    { label: '复制组合 ID', action: () => { navigator.clipboard.writeText(p.uuid); toast.success('已复制') } },
  ])
}

const portfolios = ref<any[]>([])

const fetchPortfolios = async () => {
  try {
    const res = await portfolioApi.list({ mode: 'LIVE' })
    portfolios.value = res?.items || []
  } catch { /* ignore */ }
}

onMounted(() => fetchPortfolios())
</script>

<style scoped>

/* 字号覆盖:正文 13px(公共基线 14px,见 styles/tables.less) */
.data-table td {
  font-size: 13px;
}

.table-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 16px;
}

.link {
  color: hsl(var(--primary));
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}
</style>
