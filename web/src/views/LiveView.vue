<template>
  <div class="flex h-screen">
    <!-- 左边部分，固定宽度 -->
    <div class="w-[320px] bg-gray-200 px-2 py-2" ref="recordsContainer">
      <LiveList ref="live_list" @parentMethod="handlerLiveUpdate"></LiveList>
    </div>

    <!-- 右边部分，撑满剩余空间 -->
    <div class="flex-grow pl-2 pt-2 overflow-y-auto">
      <LiveWindow ref="live_window"></LiveWindow>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LiveList from '../components/LiveList.vue'
import LiveWindow from '../components/LiveWindow.vue'

const live_list = ref(null)
const live_window = ref(null)

const raw = ref({})
const date = ref('')

const handlerLiveUpdate = (record) => {
  live_window.value.updateEngineID(record.engine_id)
}
</script>
