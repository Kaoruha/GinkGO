<template>
  <div class="validation-tab">
    <TabsNav
      v-model="activeSub"
      size="small"
      :items="subTabs"
      class="validation-subtabs"
    />

    <div class="sub-tab-content">
      <SegmentStability
        v-if="activeSub === 'segment'"
        :portfolio-id="portfolioId"
      />
      <MonteCarlo
        v-else-if="activeSub === 'montecarlo'"
        :portfolio-id="portfolioId"
      />
      <WalkForward v-else-if="activeSub === 'walkforward'" />
      <Sensitivity v-else-if="activeSub === 'sensitivity'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import TabsNav from '@/components/common/TabsNav.vue'
import SegmentStability from '@/views/portfolio/validation/SegmentStability.vue'
import MonteCarlo from '@/views/portfolio/validation/MonteCarlo.vue'
import WalkForward from '@/views/portfolio/validation/WalkForward.vue'
import Sensitivity from '@/views/portfolio/validation/Sensitivity.vue'

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

.validation-subtabs { margin-bottom: 16px; }

.sub-tab-content {
  flex: 1;
  overflow: auto;
}
</style>
