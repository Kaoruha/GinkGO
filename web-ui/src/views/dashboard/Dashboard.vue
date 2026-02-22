<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        概览
      </div>
    </div>

    <div class="page-content">
      <!-- 系统状态卡片 -->
      <a-row :gutter="16" style="margin-bottom: 24px">
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="运行中 Portfolio" :value="3" suffix="个">
              <template #prefix><PlayCircleOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="今日回测" :value="12" suffix="次">
              <template #prefix><RocketOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="活跃 Worker" :value="4" suffix="个">
              <template #prefix><ClusterOutlined /></template>
            </a-statistic>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card class="stat-card">
            <a-statistic title="系统状态" value="正常">
              <template #prefix><CheckCircleOutlined style="color: #52c41a" /></template>
            </a-statistic>
          </a-card>
        </a-col>
      </a-row>

      <!-- 4阶段概览 -->
      <a-row :gutter="16">
        <a-col :span="6">
          <a-card title="回测" :bordered="false" class="stage-card stage-1">
            <a-statistic title="已完成回测" :value="156" />
            <a-statistic title="最佳收益" :value="23.5" suffix="%" :value-style="{ color: '#52c41a' }" />
            <div style="margin-top: 16px">
              <a-button type="link" @click="$router.push('/stage1/backtest')">进入回测</a-button>
            </div>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="验证" :bordered="false" class="stage-card stage-2">
            <a-statistic title="待验证" :value="8" />
            <a-statistic title="通过验证" :value="42" :value-style="{ color: '#52c41a' }" />
            <div style="margin-top: 16px">
              <a-button type="link" @click="$router.push('/stage2/walkforward')">进入验证</a-button>
            </div>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="模拟" :bordered="false" class="stage-card stage-3">
            <a-statistic title="运行中" :value="2" />
            <a-statistic title="累计收益" :value="5.8" suffix="%" :value-style="{ color: '#52c41a' }" />
            <div style="margin-top: 16px">
              <a-button type="link" @click="$router.push('/stage3/paper')">进入模拟</a-button>
            </div>
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="实盘" :bordered="false" class="stage-card stage-4">
            <a-statistic title="运行中" :value="1" />
            <a-statistic title="今日盈亏" :value="2.3" suffix="%" :value-style="{ color: '#52c41a' }" />
            <div style="margin-top: 16px">
              <a-button type="link" @click="$router.push('/stage4/live')">进入实盘</a-button>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 占位：最近活动 -->
      <a-card title="最近活动" style="margin-top: 24px">
        <p>最近活动列表...</p>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  PlayCircleOutlined,
  RocketOutlined,
  ClusterOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons-vue'
</script>

<style lang="less" scoped>
.stage-card {
  &.stage-1 {
    border-top: 3px solid #1890ff;
  }
  &.stage-2 {
    border-top: 3px solid #52c41a;
  }
  &.stage-3 {
    border-top: 3px solid #fa8c16;
  }
  &.stage-4 {
    border-top: 3px solid #f5222d;
  }
}
</style>
