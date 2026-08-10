# ADR-043: Electron 桌面壳技术选型（electron-vite + 自定义 app:// 协议 + hash 路由 + 未签名本地安装包）

**Status:** Accepted（待实现，PR3）
**Date:** 2026-08-10
**Related:** ADR-042（双形态）、ADR-044（auth proxy 依赖主进程 / preload）

## Context

ADR-042 定了双形态 + Electron 壳。本 ADR 收口 Electron 壳的具体技术选型，涉及五个互相耦合的维度，每个都有反直觉陷阱：

1. **构建工具**：electron-vite vs vite-plugin-electron vs electron-forge。
2. **资源加载协议**：Vue SPA 打包后在 Electron 里加载，`file://` vs 自定义协议 `app://`。
3. **路由模式**：vue-router `createWebHistory` vs `createWebHashHistory`。
4. **签名分发**：签名 + 公证 vs 未签名本地安装包。
5. **目录约定**：Vue 源码留 `src/` vs 挪 `src/renderer/`（electron-vite 三段式）。

现状（`web-ui/`）：Vite 6.4.3 + `createWebHistory` + Vite 代理 `/api`+`/ws`。打包后代理失效（代理仅 dev server），Electron 须用运行时配置替代（见 Decision §6）。

## Decision

1. **electron-vite**（官方推荐构建工具，三段式约定 `src/main` + `src/preload` + `src/renderer`，主 / preload / renderer 统一 HMR + 构建）。
2. **Vue 源码挪 `src/renderer/`**（全跟随 electron-vite 三段式约定，不混排）。
3. **自定义协议 `app://` + `loadURL`**（非 `file://`）——注册自定义 scheme，`loadURL('app://./index.html')`。
4. **hash 路由** `createWebHashHistory`（替换现有 `createWebHistory`）。
5. **electron-builder 未签名本地安装包**（dmg / nsis / AppImage，无代码签名 + 无公证）。
6. **运行时配置**：后端地址等存 `userData/config.json`，preload `contextBridge` 注入 `window.appConfig`，**重启生效**（不热重载）。

## Rationale

- **为何 electron-vite 而非 vite-plugin-electron / electron-forge**：electron-vite 是当前最主流约定（三段式 + 统一 HMR + 官方文档完善）；vite-plugin-electron 是插件式混排（Vue 留 src/、main / preload 散落），约定弱；electron-forge 偏打包编排而非开发体验。选最标准约定降低后续维护歧义。
- **为何 `app://` 而非 `file://`**：`file://` 下 `window.location.origin` 是 `null`——致 (a) CORS 预检失败、(b) `localStorage` / `sessionStorage` 在某些 Chromium 版本受限、(c) `useWebSocket.ts:18-23` 用 `window.location.host` 拼 ws URL 得到空 host。自定义 `app://` 协议给页面一个稳定 origin，规避以上。代价：须注册 scheme + 后端 `CORS_ORIGINS` 加 `app://` 来源。
- **为何 hash 路由**：`file://` / `app://` 下 history 模式刷新会 404（无服务端兜底路由）；hash 路由（`#/path`）不依赖服务端，桌面壳必备。代价：URL 带 `#`（桌面端无感）。
- **为何未签名本地安装包**：自用项目，代码签名需付费证书（Apple Developer ID / Windows EV 证书）+ 公证流程（notarization），成本与自用场景不匹配。未签名安装包首次启动需手动信任（macOS 右键开 / Windows SmartScreen 跳过）。诚实限制：不可分发给陌生用户（会被系统拦截）。
- **为何 Vue 挪 `src/renderer/`**：全跟随 electron-vite 三段式约定（main / preload / renderer 平级），优于"Vue 留 src/、Electron 散落别处"的混排。
- **为何运行时配置不热重载**：后端地址变更涉及 ws 重连 + axios baseURL 重置 + 已发请求在途，热重载竞态复杂；重启生效最简单可靠（用户改设置 → 提示重启）。

## Consequences

- **绑定 electron-vite 约定**：换构建工具须重做目录结构（main / preload / renderer 三段式）。
- **3 处 `file://` 错误点须修**（PR3）：
  - `src/composables/useWebSocket.ts:18-23`：ws URL 拼接改用 `window.appConfig?.apiBase`，备选 `window.location.host`。
  - `src/api/request.ts:4`：baseURL 改 `window.appConfig?.apiBase || VITE_API_BASE_URL || ''`。
  - `src/api/request.ts:53`：401 重定向 `window.location.href='/login'` → `window.location.hash='/login'`（hash 模式）。
- **后端 CORS**：`api/main.py` / `middleware/cors.py` 的 `settings.CORS_ORIGINS` 须加 `app://` 来源（配置驱动，改动小）。
- **token 注入耦合**：现有 `request.ts:15-17` axios 拦截器从 localStorage 取 token 注入——在 auth proxy（ADR-044）下须移除（主进程透明注入），本 ADR 仅记录此耦合点。

## 判定标准自检

- ① **难逆转**：绑定 electron-vite 三段式 + hash 路由 + app:// 协议，换任一维度须重做壳——满足。
- ② **反直觉**：为何不用 file:// / 为何 hash / 为何不签名——每个都有反直觉陷阱，本 ADR 即答案。
- ③ **真实权衡**：构建工具 / 协议 / 路由 / 签名四维各有真实备选与取舍——满足。
