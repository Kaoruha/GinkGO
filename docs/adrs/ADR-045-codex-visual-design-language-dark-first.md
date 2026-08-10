# ADR-045: 视觉设计语言（Codex 中性灰 · 深色优先 · Inter/JetBrains Mono · 紧凑密度 · 双主题登录页）

**Status:** Accepted（待实现，PR5 视觉 token + PR6 布局骨架）
**Date:** 2026-08-10
**Related:** ADR-015（shadcn-vue 栈不变，仅重设 token）、ADR-042（双形态，浅色形态主要为浏览器）、ADR-044（登录页存储逻辑改但视觉由此 ADR 管）

## Context

`web-ui/` 视觉现状：

- 亮色 + Ant Design 蓝（`--primary: 221.2 83.2% 53.3%`，项目从 antd 迁来，留兼容色）。
- `design-tokens.css` 已定义双主题 token（`:root` 亮 + `.dark` 暗），`tailwind.config.js` 已 `darkMode:['class']` 且颜色全接 `hsl(var(--token))`——**双主题基础设施齐备**。
- 但 `grep dark:` 全仓零命中：组件层是**纯亮色实现**，暗色 token 从未启用。
- 字体"野生状态"：`index.html` 未引 Web 字体，`font-family` 仅零散出现在组件（`monospace` / `Silkscreen` / `Fira Code`），正文用浏览器默认。
- 登录页 `Login.vue` 是 971 行**赛博朋克终端风**定制页（BIOS 启动日志 / 像素 / 粒子 / 股票跑马灯 / 故障艺术字 / 终端命令行 / 像素输入框），深色系 + 霓虹强调。

需求：桌面端模仿 **Codex 桌面端**视觉。约束：① 登录页风格尽可能保留；② 量化刚性——涨绿跌红语义色不可删（lightweight-charts / echarts 在用）。

## Decision

1. **主题模式**：深色优先 + 可切浅色（补全所有组件 `dark:` 变体，默认挂 `<html class="dark">`，保留浅色 token + 主题切换器）。
2. **色彩基调**：Codex 中性灰——去蓝调、纯中性深灰阶（背景 `#0d0d0d` 类）、强调色降至低饱和或无品牌色、圆角收 6px（`--radius`）、涨跌语义色保留但克制（仅在数字 / 图表用）。
3. **字体**：UI 正文 **Inter** + 系统中文回退（macOS PingFang SC / Win 微软雅黑 / Linux Noto Sans CJK）；等宽 **JetBrains Mono**（量化表格数字对齐 / 代码）；monaco-editor 内置字体不变；随 Electron 打包（~5MB）。
4. **信息密度**：紧凑 Codex 风（按钮 ~28px / 输入 ~30px / 表格行 ~36px / 间距收紧）。
5. **登录页双主题**：
   - 深色版 = 现赛博朋克终端风**稍降饱和**融入整体中性灰。
   - 浅色版 = **新建**（终端风浅色化，结构保留 / 配色转浅）。
6. **沿用 shadcn-vue**（ADR-015），仅重设 `design-tokens.css` token 值，**不换 UI 库**。

## Rationale

- **为何深色优先可切浅色（不 dark-only）**：Codex 桌面端是纯深色，但 shadcn 标准是双主题 token + class 切换，现有基础设施已就绪（`:root`+`.dark`）；保留浅色灵活性，默认深色贴合 Codex。dark-only 最省事但不可逆地放弃浅色选项。
- **为何中性灰去蓝（不保留 Ant Design 蓝）**：Codex 桌面端几乎无品牌色（纯中性灰 + 微弱点缀）；保留蓝在深色下残留 Ant Design 气质、不像 Codex。代价：所有 primary 按钮 / 链接重设色，与 antd 迁移残留彻底决裂。
- **为何 Inter 不系统栈（Codex 用 Söhne 私有）**：Codex 桌面端 UI 用 Söhne、等宽用 Söhne Mono——均为 OpenAI 私有字体（Klim Type Foundry 付费授权），无法直接打包。Inter 是公认最接近 Söhne 的开源等价（几何无衬线、x-height 近似）；JetBrains Mono 接近 Söhne Mono。中文回退系统字体（Inter 无中文 glyph，Codex 中文也系统回退）。现状字体野生，正好补齐。
- **为何紧凑密度**：量化仪表盘表格密集，紧凑一屏容纳最多信息；Codex 桌面端偏紧凑。代价：中文标签在紧凑控件需调试字重 / 行高。
- **为何登录页双主题不豁免保留原样**：用户要"稍作颜色改动融入整体 + 现登录效果作深色版 + 补浅色版"。登录页本就深色系（赛博朋克终端黑底），与 Codex 深色主基调**无亮 / 暗冲突**，张力只是"霓虹 vs 中性灰"的氛围差异——深色版降饱和融入即可。浅色版新建以匹配双主题。
- **为何涨跌语义色保留**：量化刚性（涨绿跌红是领域语言），克制使用（仅在数字 / 图表）不删除。
- **已排除 A：dark-only**——放弃浅色灵活性，与双主题基础设施浪费。
- **已排除 B：保留 Ant Design 蓝深色化**——残留 antd 气质，不像 Codex。
- **已排除 C：登录页重做 Codex 化**——毁 971 行定制心血，违反"尽可能保留"约束。

## Consequences

- **工作量集中**：全组件补 `dark:` 变体（PR5 主体工作）；字体打包配置（Inter + JetBrains Mono ~5MB）；登录页双主题改造（深色降饱和 + 浅色新建）。
- **与 ADR-015 一致**：不换 UI 库，仅重设 `design-tokens.css` token 值（`:root` 浅色 + `.dark` 深色重定义），shadcn-vue 组件自动继承新 token。
- **登录页赛博朋克 ≠ 主 app 中性灰**：两种美学共存是**刻意氛围设计**（登录炫酷 → 工作专注，专业工具常见手法），非视觉不一致。
- **Codex 视觉是公开印象值**：本 ADR 写定时未取得 Codex 桌面端精确视觉参数（架构文 403），具体 hex 值在 PR5 实现时由看过截图的用户校准；本 ADR 只定大方向（中性灰 / 深色优先 / 紧凑）。
- **诚实限制**：紧凑密度 + 中性灰对中文长标签（如"策略验证" / "参数寻优"）需实测调字重；浅色版登录页的终端风浅色化无现成范式，需设计探索。

## 判定标准自检

- ① **难逆转**：全组件 dark: 变体 + 字体打包 + 971 行登录页双主题改造——满足。
- ② **反直觉**：自用量化工具为何模仿 AI 对话工具视觉 / 登录页赛博朋克 + 主 app 中性灰为何混搭——本 ADR 即答案。
- ③ **真实权衡**：Codex 美学 vs 量化语义色刚需 vs Ant Design 蓝迁移成本 vs 971 行登录页保留——满足。
