<template>
  <div class="w-full px-1">
    <ConstructionItem :title="'Summary'" :raw="props.raw" :rtype="'summary'"></ConstructionItem>
    <ConstructionItem :title="'Selector'" :raw="props.raw" :rtype="'selector'"></ConstructionItem>
    <ConstructionItem :title="'Sizer'" :raw="props.raw" :rtype="'sizer'"></ConstructionItem>
    <ConstructionItem :title="'Strategy'" :raw="props.raw" :rtype="'strategy'"></ConstructionItem>
    <ConstructionItem :title="'Risk'" :raw="props.raw" :rtype="'risk'"></ConstructionItem>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ConstructionItem from '../components/ConstructionItem.vue'

const props = defineProps({
  raw: {
    type: Object,
    default: {}
  }
})
</script>
