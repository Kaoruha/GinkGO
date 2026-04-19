<template>
  <div class="overview-tab">
    <div class="stats-row">
      <div class="stat-card"><div class="stat-label">最新净值</div><div class="stat-value">--</div></div>
      <div class="stat-card"><div class="stat-label">总收益率</div><div class="stat-value">--</div></div>
      <div class="stat-card"><div class="stat-label">最大回撤</div><div class="stat-value">--</div></div>
      <div class="stat-card"><div class="stat-label">夏普比率</div><div class="stat-value">--</div></div>
    </div>
    <div class="empty-hint">选择组合后，概况数据将在此显示</div>
  </div>
</template>

<style scoped>
.stats-row { display: flex; gap: 16px; margin-bottom: 24px; }
.stat-card { flex: 1; background: #1a1a2e; border-radius: 8px; padding: 16px; }
.stat-label { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 4px; }
.stat-value { font-size: 20px; font-weight: 700; color: #fff; }
.empty-hint { color: rgba(255,255,255,0.4); font-size: 13px; padding: 32px 0; text-align: center; }
</style>
