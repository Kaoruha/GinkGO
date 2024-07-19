<template>
  <div class="w-full h-full">
    <iframe :src="jupyter_url" frameborder="0" class="w-full h-full"></iframe>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const jupyter_url = 'http://localhost:8888/lab'
</script>
