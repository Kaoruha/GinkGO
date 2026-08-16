<template>
  <div class="maintenance-page">
    <h3>数据清理</h3>
    <p class="desc">扫描并清理孤儿数据：引用断裂的映射/参数/引擎，以及（可选）引用已删组合的回测任务及其 CH 流水。预览不删任何数据。</p>

    <div class="card">
      <div class="opts">
        <label class="opt">
          <input type="checkbox" v-model="includeBacktests" />
          <span>包含孤儿回测（任务引用已删组合 + CH 流水指向已删任务，<strong>量大且不可逆</strong>）</span>
        </label>
      </div>
      <div class="actions">
        <button class="btn-secondary" :disabled="loading" @click="runCleanup(true)">预览（dry-run）</button>
        <button class="btn-danger" :disabled="loading || !previewed" @click="runCleanup(false)">执行清理</button>
      </div>
      <p v-if="!previewed" class="hint">先预览确认各域计数，再执行。</p>
    </div>

    <div v-if="loading" class="loading-center"><div class="spinner"></div></div>

    <template v-if="result">
      <div v-for="(data, domain) in (result.domains as Record<string, any>)" :key="String(domain)" class="card domain-card">
        <h4>{{ domainLabel(String(domain)) }}</h4>
        <template v-if="data && !data.error">
          <div class="kv"><span>待清理</span><strong>{{ countOf(String(domain), data) }}</strong></div>
          <ul v-if="detailListOf(data).length" class="detail-list">
            <li v-for="(d, i) in detailListOf(data)" :key="i">{{ d }}</li>
          </ul>
        </template>
        <p v-else class="err">{{ data?.error || '未知错误' }}</p>
      </div>
      <p v-if="result.errors?.length" class="err">错误：{{ result.errors.join('；') }}</p>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import request from '@/api/request'
import { message } from '@/utils/toast'

const includeBacktests = ref(false)
const loading = ref(false)
const previewed = ref(false)
const result = ref<any>(null)

const DOMAIN_LABELS: Record<string, string> = {
  mappings: '映射关系',
  params: '参数',
  engines: '僵尸引擎',
  orphan_backtests: '孤儿回测',
}

const domainLabel = (d: string) => DOMAIN_LABELS[d] || d
const countOf = (domain: string, data: any) => {
  if (domain === 'orphan_backtests') {
    const ch = data?.ch_global || {}
    return `${data?.mysql_orphan_tasks || 0} 任务 + CH ${Object.values(ch).reduce((a: any, b: any) => a + Number(b), 0)} 行`
  }
  return data?.cleaned_count ?? data?.deleted_count ?? 0
}
const detailListOf = (data: any) => data?.details || data?.cleaning_details || []

const runCleanup = async (dry: boolean) => {
  if (!dry && !confirm(`确定执行清理${includeBacktests.value ? '（含孤儿回测，不可逆）' : ''}？`)) return
  loading.value = true
  result.value = null
  try {
    const res = await request.get('/api/v1/system/cleanup', {
      params: { dry_run: dry, include_backtests: includeBacktests.value },
    } as any)
    result.value = (res as any).data || res
    previewed.value = dry
    message.success(dry ? '预览完成' : '清理完成')
  } catch (e: any) {
    message.error(e?.response?.data?.detail || e?.message || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.maintenance-page { max-width: 720px; }
.desc { color: hsl(var(--muted-foreground)); font-size: 13px; margin-bottom: 16px; }
.card { background: hsl(var(--card)); border: 1px solid hsl(var(--border)); border-radius: var(--radius); padding: 14px; margin-bottom: 12px; }
.card h4 { margin: 0 0 10px; font-size: 13px; }
.opts { margin-bottom: 12px; }
.opt { display: flex; gap: 8px; align-items: flex-start; font-size: 13px; cursor: pointer; }
.actions { display: flex; gap: 10px; }
.btn-secondary, .btn-danger { padding: 6px 16px; border-radius: var(--radius-sm); font-size: 13px; cursor: pointer; border: 1px solid hsl(var(--border)); background: hsl(var(--card)); }
.btn-danger { border-color: hsl(var(--error)); color: hsl(var(--error)); }
.btn-danger:disabled, .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { color: hsl(var(--muted-foreground)); font-size: 12px; margin-top: 8px; }
.domain-card .kv { display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px; }
.detail-list { margin: 0; padding-left: 18px; font-size: 12px; color: hsl(var(--muted-foreground)); }
.err { color: hsl(var(--error)); font-size: 12px; }
.loading-center { display: flex; justify-content: center; padding: 30px; }
.spinner { width: 24px; height: 24px; border: 3px solid hsl(var(--border)); border-top-color: hsl(var(--primary)); border-radius: 50%; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
