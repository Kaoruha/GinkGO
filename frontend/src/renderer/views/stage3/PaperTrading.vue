<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">模拟盘</h1>
      <p class="page-description">所有模拟盘运行实例</p>
    </div>

    <div class="table-container">
      <table v-if="portfolios.length" class="data-table">
        <thead>
          <tr>
            <th>组合名称</th>
            <th>模式</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in portfolios" :key="p.uuid">
            <td>
              <router-link :to="`/portfolios/${p.uuid}`" class="link">{{ p.name || p.uuid?.slice(0, 8) }}</router-link>
            </td>
            <td>{{ p.mode }}</td>
            <td>{{ p.created_at?.replace('T', ' ').slice(0, 19) || '-' }}</td>
            <td>
              <router-link :to="`/portfolios/${p.uuid}`" class="link">查看详情</router-link>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state">暂无模拟盘实例</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api/modules/portfolio'

const portfolios = ref<any[]>([])

const fetchPortfolios = async () => {
  try {
    const res = await portfolioApi.list({ mode: 'PAPER' })
    portfolios.value = res.data || []
  } catch { /* ignore */ }
}

onMounted(() => fetchPortfolios())
</script>

<style scoped>
.page-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 24px;
  background: transparent;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}

.page-description {
  margin: 0;
  font-size: 14px;
  color: #8a8a9a;
}

.table-container {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 13px;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 60px;
  color: #8a8a9a;
}

.link {
  color: #3b82f6;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}
</style>
