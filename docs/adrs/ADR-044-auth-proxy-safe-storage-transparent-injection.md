# ADR-044: 双形态认证架构（Electron 主进程 auth proxy + safeStorage，浏览器退回 localStorage）

**Status:** Accepted（待实现，PR4）
**Date:** 2026-08-10
**Related:** ADR-042（双形态）、ADR-045（登录页视觉豁免但存储逻辑由此 ADR 改）、ADR-026 §5（CLI JWT 复用先例）

## Context

现有浏览器形态认证（`src/api/request.ts` + `src/composables/useWebSocket.ts`）：

- JWT 存 `localStorage`（`access_token` / `user_info`）。
- axios 请求拦截器（`request.ts:15-17`）从 localStorage 取 token 注入 `Authorization: Bearer`。
- ws 认证（`useWebSocket.ts:20-22`）：token 走 URL query param（`?token=...`）。
- 401（`request.ts:45-55`）：清 localStorage + 重定向 `/login`。

问题：token 存 localStorage 可被任意页面 JS（含第三方脚本 / XSS）读取。浏览器形态下这是常见折中（无更好选项）。但 **Electron 形态有机会做得更标准**：主进程持 token（OS keychain 加密落盘 safeStorage），渲染进程永不接触明文 token，由主进程在请求出口透明注入。

## Decision

1. **Electron 形态 auth proxy**：
   - token 存主进程 `safeStorage`（OS keychain 加密：macOS Keychain / Windows DPAPI / Linux libsecret）。
   - 主进程 `session.webRequest.onBeforeSendHeaders` 拦截渲染进程所有出站请求，**透明注入** `Authorization: Bearer <token>`——渲染进程不持有也不注入 token。
2. **登录逻辑重构**：登录页**视觉保留**（ADR-045），但提交后不写 localStorage，改 IPC → 主进程 → safeStorage 落盘。
3. **登录态查询**：渲染层经 IPC 查主进程（"是否已登录 / 当前用户"），不读 localStorage。
4. **401 / 登出**：主进程清 safeStorage + 通知渲染层重定向登录页。
5. **ws 认证**：后端 WebSocket 端点增加 `Authorization` header 支持（现有仅 query param）；Electron 主进程在 ws 握手时注入 header。备选：主进程把 token 注入 query param（向后兼容，但 token 进 URL 日志，次优）。
6. **浏览器形态退回 localStorage**：浏览器无主进程，不能照搬；渲染层保持现有 localStorage 逻辑不变。
7. **渲染层 auth 抽象接口**（`getToken() / login() / logout() / isAuthenticated()`），双形态各实现——渲染业务代码不直接碰 localStorage 或 IPC。

## Rationale

- **为何主进程持 token 不渲染层**：渲染进程是 XSS 攻击面（加载后端返回内容 / 第三方图表库），token 进渲染层 = 可被 XSS 窃取；主进程持 token + 透明注入，渲染层无明文 token，XSS 无的可窃。safeStorage OS keychain 加密落盘，比 localStorage 明文强。
- **为何 `onBeforeSendHeaders` 透明注入而非渲染层显式注入**：渲染层显式注入（现有 axios 拦截器）= 渲染层持有 token，defeats purpose；透明注入在主进程网络层，渲染层完全不感知 token。
- **为何浏览器退回 localStorage**：浏览器无主进程 / 无 safeStorage，不能照搬 auth proxy；双形态抽象接口隔离，渲染业务代码调 `auth.getToken()` 不关心背后是 localStorage 还是 IPC。
- **为何 ws 要后端改（加 header 支持）**：`onBeforeSendHeaders` 能注入 http header，但 Electron ws 握手 header 注入与浏览器不同；现有后端 ws 仅认 query param。需后端同时支持 header + query（header 优先），让 Electron 走 header、浏览器走 query。备选（主进程注 query）向后兼容但 token 进 URL / 日志，是次优兜底。
- **为何不全部用 query param（最小改动）**：query param token 会进反代日志 / 浏览器历史 / referer，是已知不安全模式；既然上 Electron 就做标准做法（header + keychain）。
- **已排除 A：双形态都用 localStorage**——Electron 的安全收益全丢，白上桌面壳。
- **已排除 B：双形态都 auth proxy**——浏览器无主进程，不可行。

## Consequences

- **三层贯穿改动**：main（safeStorage + onBeforeSendHeaders + IPC handler）/ preload（contextBridge 暴露 auth API）/ renderer（auth 抽象接口 + 登录页存储逻辑改）。
- **后端 ws 认证改造**：WebSocket 端点加 `Authorization` header 解析（与 query param 并存，header 优先）。配套后端 PR。
- **渲染层 auth 抽象**：业务代码从 `localStorage.getItem('access_token')` 改走 `auth.getToken()`，`request.ts` 拦截器在 Electron 形态下移除（主进程已注入）。
- **诚实限制**：auth proxy 仅限 Electron；浏览器形态仍是 localStorage（XSS 风险留存，接受，因浏览器无更好选项）。safeStorage 在 Linux 无 libsecret 时退化为明文（Electron 文档已知限制）。
- **登录页视觉与存储解耦**：登录页 971 行赛博朋克视觉由 ADR-045 豁免保留，本 ADR 只改"提交后写哪"——视觉零动。

## 判定标准自检

- ① **难逆转**：main / preload / renderer + 后端 ws 四点贯穿——满足。
- ② **反直觉**：为何 token 不放渲染层 / 为何浏览器不照搬——本 ADR 即答案。
- ③ **真实权衡**：safeStorage 安全 vs localStorage 简单 vs 双形态兼容——满足。
