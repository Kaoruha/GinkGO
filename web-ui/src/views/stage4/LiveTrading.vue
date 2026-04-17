<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-red">实盘</span>
        实盘监控
        <span class="tag tag-red" style="margin-left: 8px">实盘运行</span>
      </h1>
      <div class="page-actions">
        <button class="btn-danger">紧急停止</button>
        <button class="btn-secondary">刷新</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">总资产</div>
        <div class="stat-value">¥2,150,000</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">今日盈亏</div>
        <div class="stat-value stat-success">¥25,000</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">持仓市值</div>
        <div class="stat-value">¥1,650,000</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">可用资金</div>
        <div class="stat-value">¥500,000</div>
      </div>
    </div>

    <!-- 详情表格 -->
    <div class="tables-grid">
      <div class="card">
        <div class="card-header">
          <h3>持仓明细</h3>
        </div>
        <div class="card-body">
          <p style="color: #8a8a9a; text-align: center; padding: 20px;">暂无持仓数据</p>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <h3>今日委托</h3>
        </div>
        <div class="card-body">
          <p style="color: #8a8a9a; text-align: center; padding: 20px;">暂无委托数据</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// 实盘监控页面 - 占位实现
// 实际数据需要从API获取
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-actions {
  display: flex;
  gap: 12px;
}

/* 按钮 */

/* 标签 */

/* 统计卡片 */

/* 表格网格 */
.tables-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .tables-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-actions {
    width: 100%;
  }
}
</style>
