# ADR-042: 前端双形态架构（浏览器 + Electron 桌面壳共存）与 web-ui→frontend 重命名

**Status:** Accepted（待实现，PR1-PR6）
**Date:** 2026-08-10
**Related:** ADR-015（shadcn-vue 前端栈不变）、ADR-026（client 模式，远端形态先例）

## Context

`web-ui/` 现状是纯 Vue 3 浏览器应用（Vite 6 + vue-router history 模式），开发期靠 Vite 代理 `/api→:8000`、`/ws→ws://:8000` 连后端。

新需求：要一个**桌面端形态**——本地一键启动、原生窗口、OS 集成（safeStorage / 托盘等）。硬约束：**后端分离**（Ginkgo 后端 + TB 级数据库不可能塞进 Electron），桌面端只是连远程/独立后端的前端壳。

由此两个方向：

- 纯 Electron（弃浏览器形态）——丢失"浏览器即开即用 / 远程访问 / 无安装"。
- 双形态共存——同一套 Vue 源码，既跑浏览器（dev server / 静态托管）又跑 Electron 桌面壳。

命名问题：一旦在 `web-ui/` 内加入 Electron 代码（main / preload），"web-ui"名不副实；且双形态共存需要中性名。

## Decision

1. **双形态共存**：Vue 源码一套，形态差异（认证 / 运行时配置 / 资源加载）抽象到接口，浏览器与 Electron 各实现。Electron 仅是连分离后端的前端壳，**不打包后端**。
2. **目录重命名** `web-ui/` → `frontend/`（双形态中性名）。
3. **CLI 命令** `ginkgo serve webui` → `ginkgo serve web`（保持命令有效，端口不变 5173）；`--webui-port` → `--web-port`；约 60 个文件锚点（Python / docs / ADR / scripts / package.json）同步替换。
4. **Electron 打包走 npm 层独立命令**（`npm run build:electron` 一类），**不进 ginkgo CLI**——CLI 只负责启动 dev server（浏览器形态）。

## Rationale

- **为何双形态而非纯 Electron**：保留浏览器形态便于开发热更、远程访问、无安装即用；纯 Electron 弃浏览器收益为零、反增打包负担。
- **为何双形态而非纯 Web**：桌面端原生窗口 / OS keychain / 本地配置文件 / 离线壳是 Web 给不了的；用户明确要桌面形态。
- **为何重命名 web-ui→frontend**：含 Electron 代码后"web-ui"名不副实（自相矛盾）；双形态共存用中性名 `frontend` 诚实。`frontend` 是业界对"前端工程目录"最中性的命名（vs `client` 与 ADR-026 client 模式撞名、vs `app` 过宽）。
- **为何 `serve web` 保留命令**：兼容既有用法，仅短名化（webui→web）；Electron 打包是前端构建产物，归 npm 层而非 ginkgo CLI。
- **已排除 A：纯 Electron 弃浏览器**——丢浏览器收益。
- **已排除 B：保持 web-ui 名 + 内嵌 Electron**——名实不符，自相矛盾。

## Consequences

- **双形态抽象层维护成本**：认证（ADR-044）/ 运行时配置 / 资源加载 三处需双实现 + 接口隔离，渲染层不直接依赖具体形态。
- **重命名波及面**：~60 文件锚点替换（`serve_cli.py` 硬编码 "web-ui"×2、`remote/services.py` 注释、docs / ADR、scripts、package.json name）。CI / e2e 测试若有路径断言须同步。
- **CONTEXT.md 不动**：CONTEXT 是后端领域词汇表（Entity / DTO / Mapper / Time），前端 / Electron 部署术语不属于此。
- **诚实限制**：双形态意味着同一缺陷可能要在两套实现里各修一次（抽象层是减少而非消除此成本）。

## 判定标准自检

- ① **难逆转**：目录重命名 60 锚点 + 双形态抽象层贯穿全栈——满足。
- ② **反直觉**：为何不纯 Electron / 不纯 Web / 为何重命名——新人会问，本 ADR 即答案锚点。
- ③ **真实权衡**：双形态维护成本 vs 浏览器收益 vs 纯 Electron 简单——满足。
