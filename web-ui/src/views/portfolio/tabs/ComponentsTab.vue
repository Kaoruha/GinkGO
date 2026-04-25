<template>
  <div class="components-tab">
    <div v-if="loading" class="loading-center"><div class="spinner"></div></div>
    <div v-else-if="!portfolio" class="empty-hint">无法加载组合信息</div>
    <div v-else>
      <div v-for="group in componentGroups" :key="group.key" class="component-group">
        <h4 class="group-title">{{ group.label }}</h4>
        <div v-if="group.items.length === 0" class="empty-hint">未配置</div>
        <div v-else class="component-cards">
          <div v-for="item in group.items" :key="item.uuid" class="component-card">
            <div class="comp-name">{{ item.name }}</div>
            <div v-if="item.config" class="comp-config">
              <div v-for="(val, key) in item.config" :key="key" class="config-row">
                <span class="config-key">{{ key }}</span>
                <span class="config-val">{{ val }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useRoute } from 'vue-router'
import { portfolioApi } from '@/api'

const route = useRoute()
const portfolioId = computed(() => route.params.id as string)

const portfolio = ref<any>(null)
const loading = ref(true)

const componentGroups = computed(() => {
  if (!portfolio.value) return []
  const p = portfolio.value
  return [
    { key: 'strategies', label: '策略', items: p.strategies || [] },
    { key: 'selectors', label: '选股器', items: p.selectors || [] },
    { key: 'sizers', label: '仓位管理', items: p.sizers || [] },
    { key: 'risk_managers', label: '风控', items: p.risk_managers || [] },
    { key: 'analyzers', label: '分析器', items: p.analyzers || [] },
  ]
})

onMounted(async () => {
  try {
    const res = await portfolioApi.get(portfolioId.value)
    portfolio.value = res.data || res
  } catch (e) {
    console.error('Failed to load portfolio:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.components-tab { padding: 0; }
.component-group { margin-bottom: 20px; }
.group-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255,255,255,0.6);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
}
.component-cards { display: flex; flex-wrap: wrap; gap: 8px; }
.component-card {
  background: rgba(255,255,255,0.04);
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  padding: 10px 14px;
  min-width: 200px;
}
.comp-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
}
.comp-config { margin-top: 6px; }
.config-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 2px 0;
}
.config-key { color: rgba(255,255,255,0.4); }
.config-val { color: rgba(255,255,255,0.7); font-family: monospace; }
.empty-hint { color: rgba(255,255,255,0.3); font-size: 13px; }
.loading-center { display: flex; justify-content: center; padding: 40px; }
.spinner {
  width: 24px; height: 24px;
  border: 2px solid #2a2a3e;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
