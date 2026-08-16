<template>
  <div class="page-title">
    <!-- 返回:路由式(router-link)或函数式(button + emit back),二选一。
         统一位置(标题行最左)与样式,替代各页 back-link / back-btn / btn-text 三派漂移 -->
    <router-link
      v-if="backTo"
      :to="backTo"
      class="page-back"
    >
      <span
        class="page-back-arrow"
        aria-hidden="true"
      >←</span>
      <span
        v-if="backLabel"
        class="page-back-label"
      >{{ backLabel }}</span>
    </router-link>
    <button
      v-else-if="backAction"
      type="button"
      class="page-back"
      @click="emit('back')"
    >
      <span
        class="page-back-arrow"
        aria-hidden="true"
      >←</span>
      <span
        v-if="backLabel"
        class="page-back-label"
      >{{ backLabel }}</span>
    </button>
    <!-- 标题前分类 tag(验证 / API / Tick 等页面类型标识) -->
    <slot name="prefix" />
    <!-- 主标题文字 -->
    <span class="page-title-text">{{ title }}</span>
    <!-- 标题后附加(少用) -->
    <slot />
  </div>
</template>

<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'

/**
 * 标准页面标题:封装「返回 + 分类tag + 主标题」统一结构。
 * 主标题字号/字重/flex 布局走全局 .page-title(main.css @layer components)。
 * 放 PageLayout 的 #title slot 内使用,消除各页 back-link/back-btn/tag 拼接漂移。
 *
 * 用法:
 *   <template #title>
 *     <PageTitle title="组合名" back-to="/portfolios" back-label="组合列表" />
 *   </template>
 */
defineProps<{
  /** 主标题文字 */
  title: string
  /** 路由式返回:传则渲染 router-link(优先于 backAction) */
  backTo?: RouteLocationRaw
  /** 函数式返回:传 true 渲染 button,点击 emit back */
  backAction?: boolean
  /** 返回文字,留空则只显示箭头 */
  backLabel?: string
}>()

const emit = defineEmits<{ back: [] }>()
</script>

<style scoped>
/* .page-title 容器(flex / gap / 20px / 600)走全局 main.css,此处不重复声明避免漂移。
   仅补返回元素与标题文字的局部样式。 */
.page-back {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: hsl(var(--muted-foreground));
  text-decoration: none;
  font-size: 14px;
  font-weight: 400;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  white-space: nowrap;
  transition: color 0.15s;
}
.page-back:hover {
  color: hsl(var(--foreground));
}
.page-back-arrow {
  font-size: 16px;
  line-height: 1;
}
.page-title-text {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
