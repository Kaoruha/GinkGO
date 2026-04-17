<template>
  <div class="portfolio-builder-container">
    <div class="page-header">
      <h1 class="page-title">因子组合构建器</h1>
      <div class="header-actions">
        <button class="btn-secondary" @click="goBack">返回</button>
        <button class="btn-primary" @click="savePortfolio">保存组合</button>
      </div>
    </div>

    <div class="card factors-card">
      <div class="card-header">
        <h3>已选因子</h3>
      </div>
      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>因子名称</th>
                <th>IC</th>
                <th>权重</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in selectedFactors" :key="record.key">
                <td>{{ record.name }}</td>
                <td>{{ record.ic }}</td>
                <td>
                  <input v-model.number="record.weight" type="range" min="0" max="1" step="0.1" class="slider" />
                  <span class="slider-value">{{ record.weight.toFixed(1) }}</span>
                </td>
                <td>
                  <a class="action-link" @click="removeFactor(record)">移除</a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div class="card config-card">
      <div class="card-header">
        <h3>组合配置</h3>
      </div>
      <div class="card-body">
        <div class="form-group">
          <label class="form-label">组合名称</label>
          <input v-model="portfolioName" type="text" placeholder="请输入组合名称" class="form-input" />
        </div>
        <div class="form-group">
          <label class="form-label">组合描述</label>
          <textarea v-model="portfolioDesc" placeholder="请输入组合描述" class="form-textarea" rows="3"></textarea>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const portfolioName = ref('')
const portfolioDesc = ref('')
const selectedFactors = ref<any[]>([
  { key: '1', name: '动量因子', ic: 0.05, weight: 0.5 },
  { key: '2', name: '价值因子', ic: 0.03, weight: 0.5 }
])

const goBack = () => {
  router.back()
}

const removeFactor = (record: any) => {
  selectedFactors.value = selectedFactors.value.filter(f => f.key !== record.key)
}

const savePortfolio = () => {
  if (!portfolioName.value) {
    console.warn('请输入组合名称')
    return
  }
  console.log('组合保存成功')
  router.push('/research')
}
</script>

<style scoped>
.portfolio-builder-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
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
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.table-wrapper {
  overflow-x: auto;
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
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.slider {
  width: 100px;
  vertical-align: middle;
  margin-right: 8px;
}

.slider-value {
  color: #ffffff;
  font-size: 14px;
}

.action-link {
  color: #1890ff;
  cursor: pointer;
  text-decoration: none;
  transition: color 0.2s;
}

.action-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .slider {
    width: 80px;
  }
}
</style>
