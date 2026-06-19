# ADR-015: web-ui 以 shadcn-vue 为唯一 UI 组件标准栈

**Status:** Accepted
**Date:** 2026-06-19

## Context

web-ui 前端经历了一次 UI 库收敛：从 Ant Design Vue + shadcn-vue 双栈并存，迁移到 shadcn-vue 唯一栈。

- `web-ui/package.json`：`shadcn-vue ^2.4.3` + `reka-ui ^2.9.6`（shadcn-vue 底层，radix-vue 系），**无 `ant-design-vue`**。
- 迁移 commit `b5ef76a3`：清理 Ant Design Vue `<a-*>` 残留，迁 shadcn-vue（`<a-tag>`→`<Badge>`、`<a-card>`→`<Card>`）。
- `a2783bd1` docs(arch-align)：明确"Ant Design Vue 依赖已移除，shadcn-vue 为唯一标准栈"。
- 仓库已深度绑定：~134 个 `.vue` 组件 + ECharts / Lightweight Charts / Monaco，均围绕 shadcn-vue + Tailwind 构建。
- **文档漂移**：`docs/web-ui-spec.md:14` 仍写"Ant Design Vue + shadcn-vue (双 UI 库并存)"——与依赖事实矛盾（本 ADR 同步修正）。

## Decision

1. **shadcn-vue**（底层 reka-ui）为 web-ui **唯一** UI 组件标准栈。
2. Ant Design Vue 全面移除，**禁**新增 `<a-*>` 组件。
3. 新组件一律用 shadcn-vue（源码复制进项目的范式），与 Tailwind 一致。

## Rationale

- **为何 shadcn-vue 而非 Vue 主流的 Element Plus / Naive UI**：shadcn-vue 把组件源码复制进项目，完全可控、可改、与 Tailwind 设计系统一致；代价是放弃 Ant 成熟复杂表格等开箱能力，换取设计系统统一。
- **为何"唯一"而非"并存"**：双库并存导致视觉风格分裂、包体膨胀、维护两套组件 API 与心智模型。
- **已排除 A：保留 Ant 双栈**——风格分裂，违背一致性目标。
- **已排除 B：换 Element Plus / Naive UI**——Vue 主流但同为黑盒依赖，不如 shadcn-vue 源码可控。

## Consequences

- **难逆转**：~134 个 `.vue` + 图表库深度绑定 shadcn-vue / Tailwind，换栈需重写全部组件。
- **反直觉**：Vue 生态惯例是 Element Plus / Naive UI，选 shadcn-vue（React 系 radix 移植）是少数派；新人会问"为何不用 Element Plus"——本 ADR 即该问题的答案锚点。
- **已知遗留（迁移未完全收口，须补）**：`web-ui/src` 下仍有 2 个**运行时** `.vue` 含 `<a-*>` 残留——`layouts/ComponentLayout.vue:49/67`（`<a-tag>`）、`components/data/StatisticCard.vue:2`（`<a-card>`）。依赖已移除，这些组件运行时会因组件未注册而失效 / 降级。**收口动作**：迁这 2 处到 shadcn-vue `Badge` / `Card`。（`StatisticCard.vue.bak` 备份文件、`composables/README.md` 文档示例非运行代码，可忽略。）
- **文档漂移修正**：`docs/web-ui-spec.md:14` 由"双 UI 库并存"改为"shadcn-vue 唯一标准栈"（与本 ADR 同步）。
- **交叉引用**：ADR-002（分层架构在 web-ui 的前端边界；本 ADR 聚焦前端技术栈选型，非分层本身）。

## 判定标准自检

- ① **难逆转**：~134 `.vue` + 图表库深度绑定——满足。
- ② **反直觉**：Vue 生态选 React 系 radix 移植库——满足。
- ③ **真实权衡**：shadcn-vue 源码可控（自维护）vs 成熟库开箱即用——满足。
