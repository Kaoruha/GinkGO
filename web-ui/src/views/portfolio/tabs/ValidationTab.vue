<template>
  <div class="validation-tab">
    <div class="sub-tab-bar">
      <button
        v-for="sub in subTabs"
        :key="sub.key"
        class="sub-tab-item"
        :class="{ active: activeSub === sub.key }"
        @click="activeSub = sub.key"
      >
        {{ sub.label }}
      </button>
    </div>

    <div class="sub-tab-content">
      <SegmentStability v-if="activeSub === 'segment'" :portfolio-id="portfolioId" />
      <MonteCarlo v-else-if="activeSub === 'montecarlo'" :portfolio-id="portfolioId" />
      <WalkForward v-else-if="activeSub === 'walkforward'" />
      <Sensitivity v-else-if="activeSub === 'sensitivity'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import SegmentStability from '@/views/portfolio/validation/SegmentStability.vue'
import MonteCarlo from '@/views/portfolio/validation/MonteCarlo.vue'
import WalkForward from '@/views/stage2/WalkForward.vue'
import Sensitivity from '@/views/stage2/Sensitivity.vue'

const route = useRoute()
const portfolioId = route.params.id as string
const activeSub = ref('segment')

const subTabs = [
  { key: 'segment', label: '分段稳定性' },
  { key: 'montecarlo', label: '蒙特卡洛' },
  { key: 'walkforward', label: 'Walk Forward' },
  { key: 'sensitivity', label: '敏感性分析' },
]
</script>

<style scoped>
.validation-tab {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.sub-tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.sub-tab-item {
  padding: 8px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: rgba(255, 255, 255, 0.5);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.sub-tab-item:hover {
  color: rgba(255, 255, 255, 0.8);
}

.sub-tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.sub-tab-content {
  flex: 1;
  overflow: auto;
}
</style>
