<template>
  <div class="components-tab">
    <div
      v-if="loading"
      class="loading-center"
    >
      <div class="spinner" />
    </div>
    <div
      v-else-if="!portfolio"
      class="empty-hint"
    >
      无法加载组合信息
    </div>
    <div v-else>
      <div
        v-for="group in componentGroups"
        :key="group.key"
        class="component-group"
      >
        <h4 class="group-title">
          {{ group.label }}
        </h4>
        <div
          v-if="group.items.length === 0"
          class="empty-hint"
        >
          未配置
        </div>
        <div
          v-else
          class="component-cards"
        >
          <div
            v-for="item in group.items"
            :key="item.uuid"
            class="component-card"
          >
            <div class="comp-name">
              {{ item.name }}
            </div>
            <div
              v-if="item.config"
              class="comp-config"
            >
              <div
                v-for="(val, key) in item.config"
                :key="key"
                class="config-row"
              >
                <span class="config-key">{{ key }}</span>
                <span
                  class="config-val"
                  :title="`原始值：${rawVal(val)}`"
                >{{ fmtVal(val) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { portfolioApi } from '@/api'

const route = useRoute()
const portfolioId = computed(() => route.params.id as string)

const portfolio = ref<any>(null)
const loading = ref(true)

// 参数值格式化:绑定参数按 ADR-020 以 JSON 字符串存储,原样展示会带转义引号
// (`[ \"000001.SZ\" ]`)。解析后展示:数组→顿号连接,标量→原值,解析失败→原样。
function fmtVal(v: unknown): string {
  if (v == null) return '-'
  if (typeof v === 'string') {
    const s = v.trim()
    if ((s.startsWith('[') && s.endsWith(']')) || (s.startsWith('{') && s.endsWith('}'))) {
      try {
        const parsed = JSON.parse(s)
        if (Array.isArray(parsed)) return parsed.map(x => fmtVal(x)).join('、') || '(空)'
        if (typeof parsed === 'object') return JSON.stringify(parsed)
        return String(parsed)
      } catch { /* 非合法 JSON,原样展示 */ }
    }
    return v
  }
  if (Array.isArray(v)) return v.map(x => fmtVal(x)).join('、') || '(空)'
  if (typeof v === 'object') return JSON.stringify(v)
  return String(v)
}
const rawVal = (v: unknown) => (typeof v === 'object' ? JSON.stringify(v) : String(v ?? '-'))

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
    portfolio.value = res
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
  color: hsl(var(--muted-foreground));
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 8px 0;
}
.component-cards { display: flex; flex-wrap: wrap; gap: 8px; }
.component-card {
  background: hsl(var(--muted) / 0.4);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius);
  padding: 10px 14px;
  min-width: 200px;
}
.comp-name {
  font-size: 14px;
  font-weight: 500;
  color: hsl(var(--foreground));
  margin-bottom: 4px;
}
.comp-config { margin-top: 6px; }
.config-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  padding: 2px 0;
}
.config-key { color: hsl(var(--muted-foreground) / 0.8); flex-shrink: 0; }
.config-val {
  color: hsl(var(--muted-foreground));
  font-family: monospace;
  max-width: 62%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
.empty-hint { color: hsl(var(--muted-foreground)); font-size: 13px; }
.loading-center { display: flex; justify-content: center; padding: 40px; }
.spinner {
  width: 24px; height: 24px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
