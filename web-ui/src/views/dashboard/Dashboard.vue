<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">概览</div>
    </div>

    <div class="page-content">
      <!-- 系统状态卡片 -->
      <div class="stats-grid" data-testid="stats-grid">
        <div class="stat-card" data-testid="stat-portfolio">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polygon points="10,8 16,12 10,16"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">运行中 Portfolio</div>
            <div class="stat-value">3 <span class="stat-suffix">个</span></div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-backtest">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
              <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
              <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
              <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">今日回测</div>
            <div class="stat-value">12 <span class="stat-suffix">次</span></div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-worker">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">活跃 Worker</div>
            <div class="stat-value">4 <span class="stat-suffix">个</span></div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-system">
          <div class="stat-icon success">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">系统状态</div>
            <div class="stat-value text-success">正常</div>
          </div>
        </div>
      </div>

      <!-- 4阶段概览 -->
      <div class="stages-grid" data-testid="stages-grid">
        <div class="stage-card stage-1" data-testid="stage-backtest">
          <div class="stage-header">
            <h3>回测</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">已完成回测</span>
              <span class="stat-number">156</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">最佳收益</span>
              <span class="stat-number text-success">23.5%</span>
            </div>
          </div>
          <button @click="$router.push('/stage1/backtest')" class="stage-link" data-testid="stage-link-backtest">
            进入回测 →
          </button>
        </div>

        <div class="stage-card stage-2" data-testid="stage-validation">
          <div class="stage-header">
            <h3>验证</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">待验证</span>
              <span class="stat-number">8</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">通过验证</span>
              <span class="stat-number text-success">42</span>
            </div>
          </div>
          <button @click="$router.push('/stage2/walkforward')" class="stage-link" data-testid="stage-link-validation">
            进入验证 →
          </button>
        </div>

        <div class="stage-card stage-3" data-testid="stage-paper">
          <div class="stage-header">
            <h3>模拟</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">运行中</span>
              <span class="stat-number">2</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">累计收益</span>
              <span class="stat-number text-success">5.8%</span>
            </div>
          </div>
          <button @click="$router.push('/stage3/paper')" class="stage-link" data-testid="stage-link-paper">
            进入模拟 →
          </button>
        </div>

        <div class="stage-card stage-4" data-testid="stage-live">
          <div class="stage-header">
            <h3>实盘</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">运行中</span>
              <span class="stat-number">1</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">今日盈亏</span>
              <span class="stat-number text-success">2.3%</span>
            </div>
          </div>
          <button @click="$router.push('/stage4/live')" class="stage-link" data-testid="stage-link-live">
            进入实盘 →
          </button>
        </div>
      </div>

      <!-- 最近活动 -->
      <div class="activity-card">
        <h3>最近活动</h3>
        <p>最近活动列表...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片网格 */

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  border-radius: 8px;
  color: #00ff88;
}

.stat-icon.success {
  color: #52c41a;
}

.stat-content {
  flex: 1;
}

.stat-suffix {
  font-size: 14px;
  color: #8a8a9a;
  font-weight: 400;
}

.text-success {
  color: #52c41a !important;
}

/* 阶段卡片网格 */
.stages-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stage-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.stage-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.stage-card.stage-1 {
  border-top: 3px solid #1890ff;
}

.stage-card.stage-2 {
  border-top: 3px solid #52c41a;
}

.stage-card.stage-3 {
  border-top: 3px solid #fa8c16;
}

.stage-card.stage-4 {
  border-top: 3px solid #f5222d;
}

.stage-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.stage-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stage-stat .stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.stage-stat .stat-number {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

.stage-link {
  width: 100%;
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #1890ff;
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  transition: color 0.2s;
}

.stage-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

/* 活动卡片 */
.activity-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.activity-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.activity-card p {
  color: #8a8a9a;
  margin: 0;
}
</style>
