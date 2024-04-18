<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import HelloWorld from './components/HelloWorld.vue'
import GinkgoHeader from './components/GinkgoHeader.vue'
</script>

<template>
  <div class="flex flex-col h-screen w-screen">
    <header class="bg-blue-400 h-[60px] z-10 flex items-center">
      <GinkgoHeader></GinkgoHeader>
    </header>
    <main class="flex-1 overflow-y-hidden">
      <RouterView></RouterView>
    </main>
  </div>
</template>

<style scoped></style>
