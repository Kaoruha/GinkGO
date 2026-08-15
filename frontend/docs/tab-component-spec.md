# 前端 Tab 组件规范

> 状态:待实现 · 2026-08-14 · 分支 `epic-6910-frontend-electron-dual-form`
> 可视化参照:`public/tab-spec-mockup.html`(评审用,实现后删除)

## 1. 背景与问题

全仓 tab 实现分散在 3 个文件、3 种语义,各自手写样式:

| 文件 | 旧 class | 语义 |
|---|---|---|
| `views/portfolio/PortfolioDetail.vue` | `.tab-item` | 路由 tab |
| `views/portfolio/PortfolioList.vue` | `.radio-button` | 状态筛选 |
| `views/portfolio/tabs/BacktestTab.vue` | `.radio-button` + `.inner-tab` | 状态筛选 + 子内容 tab |
| `views/portfolio/tabs/ValidationTab.vue` | `.inner-tab` | 子内容 tab |

**根因事故**:全局 `styles/buttons.less` 做了 `.radio-button.active` 收口(ADR-045),但各页 `<style scoped>` 仍写默认态 `.radio-button { background: transparent }`,编译后 specificity 同级 `(0,2,0)`、dev 模式 scoped 后注入 → **scoped 默认态盖掉全局 active,选中项无高亮**。PortfolioList、BacktestTab 状态筛选均踩此坑(见 `arch_scoped_default_overrides_global_active`)。

**目标**:抽 2 个共享组件,active 样式自包含写进组件内部,废弃全局收口,各页不再手写。

## 2. 规范

### 2.1 二分原则

- **导航类**(切换视图)= Tab,下划线风格 → `TabsNav`
- **筛选类**(过滤数据)= Segmented,胶囊风格 → `SegmentedControl`

禁止用胶囊做导航、用下划线做筛选。

### 2.2 层级与视觉规格

全部颜色走 `design-tokens.css` 的 HSL 变量(active = `--primary`,中性灰,浅色近黑 / 深色近白,非彩色)。

| 层级 | 用途 | 字号 | 字重(默认→active) | 下划线 | padding | 组件 |
|---|---|---|---|---|---|---|
| **L1 路由 tab** | 页面主区切换,走 vue-router | 14px | 500→600 | 2px primary | 12×18 | `TabsNav` 路由模式 |
| **L2 子内容 tab** | 区块内视图切换,纯状态 | 13px | 400→500 | 1px primary | 8×14 | `TabsNav` 受控模式 `size="small"` |
| **筛选分段** | 数据过滤(非导航) | 12px | — | 无 | 6×14 | `SegmentedControl` |

状态色统一:
- 默认 `--muted-foreground`
- hover `--foreground`
- active `--primary`(L1/L2)/ `--primary` 实色填充 + `--primary-foreground` 字(Segmented)

### 2.3 硬规则

1. 导航 vs 筛选不混用(见 2.1)。
2. **active 只写在组件 `<style scoped>` 内**,各页不再手写 `.xxx-tab.active`;废弃 `buttons.less` 全局 `.radio-button.active` 收口。
3. L1→L2 靠规格递减(字号/字重/下划线粗细)表达层级;L2 必须处于 L1 内容区内。
4. 出现第三级 tab 要评审;目前最深 = L1 + L2(PortfolioDetail)。

## 3. 组件 API

### 3.1 `TabsNav`

路径:`components/common/TabsNav.vue`,barrel 导出至 `components/common/index.ts`。

**统一 items,按是否带路由自动分模式:**

```ts
type TabItem = {
  key: string
  label: string
  to?: RouteLocationRaw   // 有 to → 路由模式(router-link);无 → 受控模式(button)
}
// props
items: TabItem[]
modelValue?: string       // 受控模式当前 key
size?: 'default' | 'small'   // default=L1, small=L2
// emits
'update:modelValue': (key: string) => void
```

**active 判定(内部,自包含):**
- 路由项(`<router-link>`):用 vue-router 的 `RouterLink` v-slot `isActive`(或 `route.path` 命中 `to`)。
- 受控项(`<button>`):`modelValue === key`。

**用法示例:**
```vue
<!-- L1 路由 -->
<TabsNav :items="[
  { key:'overview', label:'概况', to:`/portfolios/${id}` },
  { key:'backtests', label:'回测', to:`/portfolios/${id}/backtests` },
]" />

<!-- L2 受控 -->
<TabsNav v-model="activeDetailTab" size="small" :items="[
  { key:'overview', label:'概览' },
  { key:'orders', label:'订单' },
]" />
```

### 3.2 `SegmentedControl`

路径:`components/common/SegmentedControl.vue`。

```ts
type Option = { key: string; label: string }
// props
options: Option[]
modelValue: string
// emits
'update:modelValue': (key: string) => void
```

胶囊容器 `--muted` 背景 + 圆角;active 项 `--primary` 实色填充 + `--primary-foreground` 字。用法:
```vue
<SegmentedControl v-model="filterStatus" :options="statusOptions" />
```

## 4. 迁移计划

1. 新建 `components/common/TabsNav.vue`、`SegmentedControl.vue`,active 样式自包含;加入 `index.ts` barrel。
2. `PortfolioDetail.vue`:`.tab-item` `<router-link>` → `<TabsNav :items>`(L1 路由);删 scoped `.tab-item*` 样式。
3. `BacktestTab.vue` 详情 `.inner-tab` → `<TabsNav v-model size="small">`(L2);状态 `.radio-button` → `<SegmentedControl>`。
4. `ValidationTab.vue`:`.inner-tab` → `<TabsNav v-model size="small">`(L2)。
5. `PortfolioList.vue`:筛选 `.radio-button` → `<SegmentedControl>`。
6. `styles/buttons.less`:`.radio-button.active` 收口段标注废弃(grep 确认无其他引用后删)。
7. 删 `public/tab-spec-mockup.html`(临时评审文件)。
8. 清理各页 scoped 内残留的 `.radio-button` / `.inner-tab` / `.tab-item` 样式块。

## 5. 验证清单

- [ ] PortfolioDetail:L1 各 tab 切换路由后 active 高亮(概况/回测/组件)。
- [ ] BacktestTab 详情:L2(概览/订单/信号)active。
- [ ] ValidationTab:L2(segment/montecarlo/...)active。
- [ ] PortfolioList:Segmented(全部/运行中)active——**此前坏,需修好**。
- [ ] BacktestTab 状态:Segmented active——**此前坏(回测 tab 无高亮),需修好**。
- [ ] light / dark 两主题下对比度达标(WCAG AA UI 3:1)。
- [ ] `buttons.less` 收口废弃后无其他页面回归(grep 全仓 `.radio-button` 引用)。
- [ ] 组合场景(PortfolioDetail L1 + L2 + Segmented 同屏)层级清晰。
