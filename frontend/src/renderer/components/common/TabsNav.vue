<template>
  <!--
    TabsNav — 下划线风格导航 tab(规范见 frontend/docs/tab-component-spec.md)
    - 路由模式:items 带 to,渲染 router-link,active = 当前路由 matched 链中"最深匹配"的 tab
      (两难:inclusive isActive 让父路径 to 在子路由也亮——概况会在 /backtests 误激活;
      isExactActive 又让带子路由的 tab(如"回测"有 /:backtestId 详情)在子页失活。
      取 matched 深度最大者:回测列表/详情都选"回测",概况页选"概况",互不串扰)
    - 受控模式:items 不带 to,渲染 button,active = modelValue===key
    - size: default=L1(14px/600/2px) | small=L2(13px/500/1px)
    active 样式自包含,不依赖全局收口。
  -->
  <div class="tabs-nav" :style="sizeVars">
    <template v-if="isRoute">
      <RouterLink
        v-for="item in items"
        :key="item.key"
        :to="item.to!"
        custom
        v-slot="{ navigate }"
      >
        <a class="tab" :class="{ on: activeKey === item.key }" @click="navigate" @keypress.enter.prevent="() => navigate()">{{ item.label }}</a>
      </RouterLink>
    </template>
    <template v-else>
      <button
        v-for="item in items"
        :key="item.key"
        class="tab"
        :class="{ on: modelValue === item.key }"
        @click="emit('update:modelValue', item.key)"
      >{{ item.label }}</button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

interface TabItem {
  key: string
  label: string
  to?: RouteLocationRaw
}

const props = withDefaults(defineProps<{
  items: TabItem[]
  modelValue?: string
  size?: 'default' | 'small'
}>(), { size: 'default' })

const emit = defineEmits<{ 'update:modelValue': [key: string] }>()

// 路由模式:所有 item 都带 to
const isRoute = computed(() => props.items.length > 0 && props.items.every(it => it.to !== undefined))

// 路由模式 active 判定:高亮当前路由 matched 链中"最深的那个 tab"。
// 对每个带 to 的 tab,resolve 出其最深 record 的 path,在当前 route.matched 里查深度,
// 取深度最大者。无任何匹配时返回 ''(无高亮)。
// 解决 isExactActive 对带子路由父路径(如 /backtests 有 /:backtestId)失活、
// isActive 对根父路径(如 /portfolios/:id)在子页误激活的两难。
const route = useRoute()
const router = useRouter()
const activeKey = computed(() => {
  let best = { key: '', depth: -1 }
  for (const item of props.items) {
    if (item.to === undefined) continue
    const resolved = router.resolve(item.to)
    const target = resolved.matched[resolved.matched.length - 1]
    if (!target) continue
    const depth = route.matched.findIndex(r => r.path === target.path)
    if (depth > best.depth) best = { key: item.key, depth }
  }
  return best.key
})

// 层级规格靠 CSS 变量切换(L1 vs L2),样式本身只一份
const sizeVars = computed<Record<string, string>>(() => {
  if (props.size === 'small') {
    return {
      '--tab-fs': '13px',
      '--tab-idle-w': '400',
      '--tab-active-w': '500',
      '--tab-underline': '1px',
      '--tab-pad-y': '8px',
      '--tab-pad-x': '14px',
    }
  }
  return {
    '--tab-fs': '14px',
    '--tab-idle-w': '500',
    '--tab-active-w': '600',
    '--tab-underline': '2px',
    '--tab-pad-y': '12px',
    '--tab-pad-x': '18px',
  }
})
</script>

<style scoped>
.tabs-nav {
  display: flex;
  gap: 2px;
  border-bottom: 1px solid hsl(var(--border));
}

.tab {
  padding: var(--tab-pad-y) var(--tab-pad-x);
  font-size: var(--tab-fs);
  font-weight: var(--tab-idle-w);
  color: hsl(var(--muted-foreground));
  background: none;
  border: none;
  border-bottom: var(--tab-underline) solid transparent;
  margin-bottom: -1px;          /* 覆盖容器下边框,与 active 下划线共线 */
  cursor: pointer;
  text-decoration: none;
  font-family: inherit;
  line-height: 1.4;
  transition: color 0.15s, border-bottom-color 0.15s;
}

.tab:hover {
  color: hsl(var(--foreground));
}

.tab.on {
  color: hsl(var(--primary));
  font-weight: var(--tab-active-w);
  border-bottom-color: hsl(var(--primary));
}
</style>
