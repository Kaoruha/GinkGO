# Electron 双形态 + Codex 视觉全量落地 实施计划 (PR2-6 合并)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `frontend/` 从纯浏览器 Vue 应用改造为 Electron + 浏览器双形态桌面应用(连分离后端的前端壳),并落地 Codex 中性灰深色优先视觉语言,完整实现 ADR-042/043/044/045。

**Architecture:** electron-vite 三段式(`src/main` + `src/preload` + `src/renderer`),Vue 源码挪 `src/renderer/`。Electron 主进程持 token(safeStorage)+ 透明注入 `Authorization` header;浏览器形态退回 localStorage;渲染层经 auth 抽象接口隔离。视觉先修复 token 接线断层(`design-tokens.css`+`main.css` 实际未进 bundle),再迁移组件 hex→token,落地 Codex 中性灰。

**Tech Stack:** Electron + electron-vite + electron-builder;Vue 3.4 + Vite 6.4 + vue-router(hash)+ shadcn-vue + tailwind 3.4;safeStorage(OS keychain);Inter + JetBrains Mono。后端 Python/FastAPI(`verify_token` 复用)。

## Global Constraints

- **后端分离不打包**:Electron 只做连远程/独立后端的前端壳(ADR-042 §1)
- **electron-vite 三段式**:`src/main` + `src/preload` + `src/renderer`(ADR-043 §1-2)
- **app:// 协议**(非 `file://`)+ `loadURL('app://./index.html')`(ADR-043 §3)
- **hash 路由** `createWebHashHistory`(ADR-043 §4)
- **electron-builder 未签名本地包**(dmg/nsis/AppImage,无签名无公证)(ADR-043 §5)
- **运行时配置**:`userData/config.json` + preload `contextBridge` 注入 `window.appConfig` + **重启生效**(ADR-043 §6)
- **端口 5173 不变**(PR1 已锁)
- **浏览器形态必须保持可用**(双形态共存,非 Electron-only)
- **Electron auth**:main `safeStorage` 持 token + `session.webRequest.onBeforeSendHeaders` 透明注入;浏览器退回 localStorage(ADR-044 §1-7)
- **渲染层 auth 抽象接口** `getToken()/login()/logout()/isAuthenticated()`,双形态各实现(ADR-044 §7)
- **后端 ws**:header(优先)+ query(兼容)并存,复用 `verify_token`(ADR-044 §5)
- **登录页视觉保留**,仅改"提交后写哪"(ADR-044 §2)
- **深色优先 + 可切浅色**(默认 `<html class="dark">`)(ADR-045 §1)
- **Codex 中性灰去蓝**;**涨绿跌红语义色保留**(克制使用)(ADR-045 §2)
- **Inter**(正文)+ **JetBrains Mono**(等宽数字/代码),随 Electron 打包(ADR-045 §3)
- **紧凑密度**:按钮 ~28px / 输入 ~30px / 表格行 ~36px(ADR-045 §4)
- **登录页双主题**:深色版降饱和 + 浅色版新建(ADR-045 §5)
- **沿用 shadcn-vue**,仅重设 token 值(ADR-045 §6)
- **token 接线必须先修复**:`design-tokens.css` + `main.css`(含 `@tailwind`)须进 bundle(探查发现当前 main.ts 只 import index.less,token 体系未加载)
- Python 解释器:`/home/kaoru/.ginkgo/.venv/bin/python`
- 不擅自改后端 Base 类(本 plan 不碰 BaseCRUD/BaseService)
- 前端测试 `vitest`,后端只跑单测(不跑全量 tests/,OOM 铁律)
- commit 引用 `Refs #6910`(不 Closes,epic 未关);epic 子工作直接 commit 不开子 PR
- 分支:`epic-6910-frontend-electron-dual-form`(PR1 已在其上)

---

## File Structure

**新建(Create):**
- `frontend/electron.vite.config.ts` — electron-vite 三段式构建配置
- `frontend/electron-builder.yml` — 未签名打包配置
- `frontend/src/main/index.ts` — Electron 主进程入口(BrowserWindow + app:// + auth)
- `frontend/src/main/auth.ts` — safeStorage + onBeforeSendHeaders + IPC login/logout
- `frontend/src/main/protocol.ts` — app:// 自定义协议注册
- `frontend/src/main/config.ts` — userData/config.json 运行时配置读写
- `frontend/src/preload/index.ts` — contextBridge 暴露 window.appConfig + window.auth
- `frontend/src/renderer/src/composables/useAuth.ts` — 双形态 auth 抽象接口
- `frontend/src/renderer/src/utils/isElectron.ts` — 形态判定(window.appConfig 存在性)
- `frontend/src/renderer/src/assets/fonts/` — Inter + JetBrains Mono 字体文件
- `frontend/src/renderer/src/styles/fonts.css` — @font-face 声明

**迁移(git mv,保 blame):**
- `frontend/src/{App.vue,main.ts,vite-env.d.ts,api,components,composables,constants,layouts,lib,router,stores,styles,types,utils,views}` → `frontend/src/renderer/`
- `frontend/index.html` → `frontend/src/renderer/index.html`

**修改(Modify):**
- `frontend/package.json` — 加 electron 依赖 + scripts
- `frontend/vite.config.ts` — 浏览器形态 root/alias 指向 src/renderer
- `frontend/src/renderer/src/router/index.ts` — createWebHistory → createWebHashHistory
- `frontend/src/renderer/src/api/request.ts` — baseURL/401/token 注入形态分支
- `frontend/src/renderer/src/composables/useWebSocket.ts` — URL 用 window.appConfig
- `frontend/src/renderer/src/main.ts` — import design-tokens.css + main.css(接线修复)
- `frontend/src/renderer/src/styles/design-tokens.css` — Codex 中性灰值
- `frontend/src/renderer/src/styles/{index.less,main.css}` — 去硬编码 hex→token
- `frontend/src/renderer/src/views/auth/Login.vue` — 存储逻辑改 + 双主题
- `frontend/src/renderer/src/components/**` — hex→token 迁移 + dark: 变体
- `api/core/config.py` — CORS_ORIGINS 加 app://
- `api/websocket/handlers/{portfolio,system}_handler.py` — ws header 支持

---

## Task 1: electron-vite 三段式目录迁移 + 依赖接入

**Files:**
- Create: `frontend/electron.vite.config.ts`
- Migrate: `frontend/src/*` → `frontend/src/renderer/*`(git mv)
- Migrate: `frontend/index.html` → `frontend/src/renderer/index.html`
- Modify: `frontend/package.json`(加依赖 + scripts)
- Modify: `frontend/vite.config.ts`(浏览器形态 root/alias 指向 renderer)
- Modify: `frontend/tsconfig.json`(include 改 src/renderer)

**Interfaces:**
- Produces: `frontend/src/renderer/`(Vue 源码新位)+ `frontend/src/main/` `frontend/src/preload/` 占位目录(空,Task 2/3 填);浏览器形态 `npm run dev` 仍能起 5173。

- [ ] **Step 1: git mv Vue 源码到 src/renderer**

```bash
cd /home/kaoru/Ginkgo/frontend
mkdir -p src/main src/preload
# 先移出再建 renderer,避免循环
git mv src/App.vue src/main.ts src/vite-env.d.ts src/api src/components src/composables src/constants src/layouts src/lib src/router src/stores src/styles src/types src/utils src/views tmp_renderer
mkdir -p src/renderer
git mv tmp_renderer/* src/renderer/
rmdir tmp_renderer
git mv index.html src/renderer/index.html
```
Run 后 `git status` 确认全 rename(保 blame)。

- [ ] **Step 2: 改 vite.config.ts(浏览器形态指向 renderer)**

`frontend/vite.config.ts` 改:
- `root: 'src/renderer'`(浏览器形态根)
- `resolve.alias '@' → resolve(__dirname, 'src/renderer')`
- `server.proxy` 不变(/api /ws 仍指 :8000)
- `build.outDir: 'dist'`(相对 root,即 src/renderer/dist)
- `base: './'`(相对路径,为后续 app:// 打包铺垫)

- [ ] **Step 3: 改 tsconfig.json include**

`frontend/tsconfig.json` 的 `include` 由 `["src/**/*"]` 改 `["src/renderer/**/*","src/main/**/*","src/preload/**/*"]`,`paths` 的 `@/*` 指向 `src/renderer/*`。

- [ ] **Step 4: 建 electron.vite.config.ts**

```ts
// frontend/electron.vite.config.ts
import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: { index: resolve('src/main/index.ts') } } }
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: { rollupOptions: { input: { index: resolve('src/preload/index.ts') } } }
  },
  renderer: {
    root: 'src/renderer',
    plugins: [vue()],
    resolve: { alias: { '@': resolve('src/renderer') } },
    build: { rollupOptions: { input: resolve('src/renderer/index.html') } }
  }
})
```

- [ ] **Step 5: package.json 加依赖 + scripts**

```jsonc
// devDependencies 加:
"electron": "^33.0.0",
"electron-vite": "^2.3.0",
"electron-builder": "^25.1.0",
"vite-plugin-static-copy": "^2.0.0"  // 字体打包用(Task 10)

// scripts 加:
"dev:electron": "electron-vite dev",
"build:electron": "electron-vite build && electron-builder",
"preview:electron": "electron-vite preview"
```
Run `npm install`(或项目用 pnpm 则 `pnpm install`——按现有 lockfile 判断;package.json 无 packageManager 字段,查 pnpm-lock.yaml 存在则用 pnpm)。

- [ ] **Step 6: 占位 main/preload(让 dev:electron 能起,Task 2/3 填实)**

`frontend/src/main/index.ts`(最小骨架,Task 2 替换):
```ts
import { app, BrowserWindow } from 'electron'
const createWindow = () => {
  const win = new BrowserWindow({ width: 1280, height: 800 })
  if (process.env['ELECTRON_RENDERER_URL']) win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  else win.loadFile('out/renderer/index.html')
}
app.whenReady().then(createWindow)
app.on('window-all-closed', () => process.platform !== 'darwin' && app.quit())
```
`frontend/src/preload/index.ts`:`export {}`(占位)

- [ ] **Step 7: 验证浏览器形态不破**

Run:
```bash
cd /home/kaoru/Ginkgo/frontend
npm run build 2>&1 | tail -5   # 浏览器形态构建仍过(vite.config root=renderer)
npx vue-tsc --noEmit 2>&1 | tail -5   # TS 编译过
```
Expected: build 成功生成 `src/renderer/dist`;vue-tsc 无新增错误(原有错误数不增)。

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "refactor(frontend): Vue 源码挪 src/renderer + electron-vite 三段式骨架 (PR2/Task1, #6910)

- git mv src/* → src/renderer/*(保 blame)
- electron.vite.config.ts 三段式(main/preload/renderer)
- package.json 加 electron/electron-vite/electron-builder 依赖 + dev:electron/build:electron
- 浏览器形态 vite.config root 指向 renderer,dev/build 不破

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Electron main 进程骨架 + app:// 协议

**Files:**
- Modify: `frontend/src/main/index.ts`(替换占位)
- Create: `frontend/src/main/protocol.ts`

**Interfaces:**
- Consumes: Task 1 的三段式骨架。
- Produces: Electron 形态 `npm run dev:electron` 能起窗,加载 `app://./index.html`(生产)或 vite dev server(开发);`window.location.origin` 稳定(非 null)。

- [ ] **Step 1: 写 protocol.ts(app:// 注册)**

```ts
// frontend/src/main/protocol.ts
import { protocol, net } from 'electron'
import { join } from 'path'

export function registerAppProtocol() {
  // 注册为标准/特权 scheme:有稳定 origin、支持 fetch、localStorage
  protocol.registerSchemesAsPrivileged([
    {
      scheme: 'app',
      privileges: {
        standard: true,
        secure: true,
        supportFetchAPI: true,
        stream: true,
        bypassCSP: false,
      },
    },
  ])
}
```
注:`registerSchemesAsPrivileged` 必须在 `app.ready` **之前**调用。

- [ ] **Step 2: 写 index.ts(BrowserWindow + loadURL)**

```ts
// frontend/src/main/index.ts
import { app, BrowserWindow, shell } from 'electron'
import { join } from 'path'
import { registerAppProtocol } from './protocol'

registerAppProtocol()  // app.ready 前

const isDev = !!process.env['ELECTRON_RENDERER_URL']

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,  // preload 用 Node(safeStorage/config),sandbox 需另配
    },
  })

  // 外链用系统浏览器
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (isDev) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL']!)
    win.webContents.openDevTools()
  } else {
    win.loadURL('app://./index.html')
  }
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => process.platform !== 'darwin' && app.quit())
app.on('activate', () => BrowserWindow.getAllWindows().length === 0 && createWindow())
```

- [ ] **Step 3: 验证 dev:electron 能起窗**

Run:
```bash
cd /home/kaoru/Ginkgo/frontend
timeout 30 npm run dev:electron 2>&1 | head -20 &
sleep 15
# 看是否有 Electron 窗口进程 + vite renderer dev server 起来
pgrep -af "electron" | head -3 || echo "NO electron process"
```
Expected: electron-vite dev 起 3 段(main/preload/renderer)HMR,Electron 窗口打开加载 dev server URL。无 crash。(headless 环境可能需 xvfb;若 DISPLAY 无,记录为"需图形环境验证",commit 仍可提交——配置正确性由代码审查保证。)

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(electron): main 进程骨架 + app:// 自定义协议 (PR2/Task2, #6910)

- protocol.ts: registerSchemesAsPrivileged 注册 app scheme(稳定 origin)
- index.ts: BrowserWindow + contextIsolation + preload,dev loadURL / prod app://./index.html
- 外链走系统浏览器

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: preload + 运行时配置(window.appConfig)

**Files:**
- Modify: `frontend/src/preload/index.ts`
- Create: `frontend/src/main/config.ts`

**Interfaces:**
- Consumes: Task 2 的主进程。
- Produces: `window.appConfig`(preload 注入,含 `apiBase`/`wsBase`);`userData/config.json` 读写;Electron 形态重启生效。渲染层 `window.appConfig?.apiBase` 可读。

- [ ] **Step 1: 写 config.ts(userData/config.json 读写)**

```ts
// frontend/src/main/config.ts
import { app } from 'electron'
import { join } from 'path'
import { readFileSync, writeFileSync, existsSync } from 'fs'

export interface AppConfig {
  apiBase: string    // 例 'http://localhost:8000'
  wsBase: string     // 例 'ws://localhost:8000'
}

const DEFAULT: AppConfig = {
  apiBase: 'http://localhost:8000',
  wsBase: 'ws://localhost:8000',
}

export function getConfigPath() {
  return join(app.getPath('userData'), 'config.json')
}

export function loadConfig(): AppConfig {
  const p = getConfigPath()
  if (!existsSync(p)) return DEFAULT
  try {
    return { ...DEFAULT, ...JSON.parse(readFileSync(p, 'utf-8')) }
  } catch {
    return DEFAULT
  }
}

export function saveConfig(cfg: Partial<AppConfig>) {
  const merged = { ...loadConfig(), ...cfg }
  writeFileSync(getConfigPath(), JSON.stringify(merged, null, 2))
  // 重启生效(ADR-043 §6):不热重载
}
```

- [ ] **Step 2: 写 preload/index.ts(contextBridge 注入 appConfig)**

```ts
// frontend/src/preload/index.ts
import { contextBridge, ipcRenderer } from 'electron'
import { loadConfig } from '../main/config'

const config = loadConfig()

contextBridge.exposeInMainWorld('appConfig', {
  apiBase: config.apiBase,
  wsBase: config.wsBase,
  isElectron: true as const,
  // auth API 在 Task 7 补
})
```

- [ ] **Step 3: 加 window.appConfig 类型声明**

`frontend/src/renderer/src/vite-env.d.ts` 追加:
```ts
interface AppConfig {
  apiBase: string
  wsBase: string
  isElectron: true
}
interface Window {
  appConfig?: AppConfig
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(electron): preload contextBridge 注入 window.appConfig + 运行时配置 (PR2/Task3, #6910)

- config.ts: userData/config.json 读写,DEFAULT localhost:8000,重启生效(ADR-043 §6)
- preload: contextBridge.exposeInMainWorld appConfig(apiBase/wsBase/isElectron)
- vite-env.d.ts: Window.appConfig 类型

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: hash 路由 + 3 处 file:// 修复

**Files:**
- Modify: `frontend/src/renderer/src/router/index.ts`(L1, L183-186)
- Modify: `frontend/src/renderer/src/api/request.ts`(L4, L15-17, L53)
- Modify: `frontend/src/renderer/src/composables/useWebSocket.ts`(L18-23)

**Interfaces:**
- Consumes: Task 3 的 `window.appConfig`。
- Produces: hash 路由(file://app:// 下刷新不 404);apiBase/wsBase 双形态可配;401 重定向 hash 模式。

- [ ] **Step 1: router 改 hash**

`frontend/src/renderer/src/router/index.ts`:
- L1:`import { createRouter, createWebHistory, createWebHashHistory, RouteRecordRaw } from 'vue-router'`
- L184:`history: createWebHashHistory()`(替换 `createWebHistory()`)

- [ ] **Step 2: request.ts baseURL + 401**

`frontend/src/renderer/src/api/request.ts`:
- L4 改:
```ts
const baseURL = window.appConfig?.apiBase || import.meta.env.VITE_API_BASE_URL || ''
```
- L53 改:`window.location.href = '/login'` → `window.location.hash = '#/login'`
- L15-17 token 注入暂留(Electron 形态在 Task 8 移除,本 task 不动避免破坏浏览器形态)。

- [ ] **Step 3: useWebSocket.ts URL**

`frontend/src/renderer/src/composables/useWebSocket.ts` L18-23 改:
```ts
function getWebSocketUrl(): string {
  const cfg = window.appConfig
  if (cfg?.wsBase) {
    // Electron 形态:用配置的 wsBase
    const token = localStorage.getItem('access_token')  // Task 8 改 auth.getToken()
    let url = `${cfg.wsBase}/ws/portfolio`
    if (token) url += `?token=${encodeURIComponent(token)}`
    return url
  }
  // 浏览器形态:原逻辑
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = localStorage.getItem('access_token')
  let url = `${protocol}//${window.location.host}/ws/portfolio`
  if (token) url += `?token=${encodeURIComponent(token)}`
  return url
}
```

- [ ] **Step 4: 前端单测验证**

```bash
cd /home/kaoru/Ginkgo/frontend
npx vitest run 2>&1 | tail -10
```
Expected: 现有测试不破(router/api 测试若有 history 断言需同步改 hash,record 在 report)。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(frontend): hash 路由 + apiBase/wsBase 双形态 + 401 hash 重定向 (PR2/Task4, #6910)

- router: createWebHistory → createWebHashHistory(app:///file:// 刷新不 404)
- request.ts: baseURL 取 window.appConfig?.apiBase;401 改 location.hash
- useWebSocket: URL 优先 window.appConfig.wsBase,浏览器形态回退原逻辑

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: 后端 CORS app:// + ws Authorization header

**Files:**
- Modify: `api/core/config.py`(L35-43 CORS_ORIGINS 默认)
- Modify: `api/websocket/handlers/portfolio_handler.py`(L25-35)
- Modify: `api/websocket/handlers/system_handler.py`(L25-35)

**Interfaces:**
- Consumes: 探查事实——`verify_token`(`api/middleware/auth.py:149`)共用;ws handler 握手前 `close(1008)`。
- Produces: ws 端点认 header(优先)+ query(兼容);CORS 默认含 `app://`。后端单测覆盖。

- [ ] **Step 1: 写 token 提取 helper(复用模式)**

在 `api/websocket/handlers/portfolio_handler.py` 顶部(或新建 `api/websocket/handlers/_auth.py` 共用),加:
```python
def _extract_ws_token(websocket: WebSocket) -> Optional[str]:
    """ADR-044 §5: header 优先(Electron 主进程注入),query 兼容(浏览器)"""
    auth = websocket.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:]
    return websocket.query_params.get("token")
```
若新建 `_auth.py`,system_handler 也 import 复用。

- [ ] **Step 2: portfolio_handler L25 改**

`api/websocket/handlers/portfolio_handler.py`:
- L25 `token = websocket.query_params.get("token")` → `token = _extract_ws_token(websocket)`
- 其余(L27 close 1008 / L31 verify_token / L34)不变
- docstring L20 `token 通过 query param 传入` → `token 通过 Authorization header(优先)或 query param 传入`

- [ ] **Step 3: system_handler 对称改**(同 portfolio,L25 + docstring)

- [ ] **Step 4: CORS_ORIGINS 加 app://**

`api/core/config.py` L37-42 默认列表追加 `"app://"`(Electron 自定义协议 origin):
```python
default=[
    "http://localhost:5173",
    "http://localhost:3000",
    "http://192.168.50.12:5173",
    "http://192.168.50.12:3000",
    "app://",   # ADR-044 Electron 双形态
],
```

- [ ] **Step 5: 后端单测**

新建 `tests/unit/api/websocket/test_ws_auth_header.py`(或追加现有 ws 测试):
```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

@pytest.mark.asyncio
async def test_ws_token_from_header_takes_priority():
    """header token 优先于 query param"""
    # 构造 websocket mock:headers 有 Authorization,query 有不同 token
    # 断言 _extract_ws_token 返回 header 的 token

@pytest.mark.asyncio
async def test_ws_token_fallback_to_query():
    """无 header 时回退 query param(浏览器兼容)"""

@pytest.mark.asyncio
async def test_ws_missing_token_closes_1008():
    """header 和 query 都无 token → close(1008)"""
```
Run:
```bash
cd /home/kaoru/Ginkgo
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/unit/api/websocket/test_ws_auth_header.py -v 2>&1 | tail -10
```
Expected: 3 tests PASS。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(api): ws Authorization header 支持 + CORS app:// (PR4/Task5, #6910)

- _extract_ws_token: header(Bearer)优先,query param 兼容回退(ADR-044 §5)
- portfolio/system handler 对称改,verify_token 复用
- CORS_ORIGINS 默认加 app://(Electron 自定义协议 origin)
- 单测: header 优先 / query 回退 / 缺 token close 1008

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: electron-builder 未签名打包配置

**Files:**
- Create: `frontend/electron-builder.yml`
- Modify: `frontend/package.json`(build:electron script Task 1 已加)

**Interfaces:**
- Consumes: Task 1-5 的双形态骨架。
- Produces: `npm run build:electron` 产出未签名 dmg(macOS)/ nsis(Windows)/ AppImage(Linux)。

- [ ] **Step 1: 写 electron-builder.yml**

```yaml
# frontend/electron-builder.yml
appId: org.ginkgo.desktop
productName: Ginkgo
directories:
  output: release
files:
  - out/**/*
  - package.json
mac:
  target: dmg
  # 未签名:无 identity,无 notarize(ADR-043 §5 自用)
win:
  target: nsis
linux:
  target: AppImage
nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
# 依赖 out/ 由 electron-vite build 产出
```

- [ ] **Step 2: 验证 build:electron 前半段(electron-vite build)**

```bash
cd /home/kaoru/Ginkgo/frontend
npx electron-vite build 2>&1 | tail -10
ls -la out/main out/preload out/renderer 2>&1 | head -10
```
Expected:`out/{main,preload,renderer}` 三段产物生成(main/index.js、preload/index.js、renderer/index.html + assets)。(electron-builder 实际打包下载 ~100MB electron 二进制 + 跨平台包,headless/Linux 环境只验证 AppImage 能起构建,完整打包产物需图形 OS 验收。)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(electron): electron-builder 未签名打包配置 (PR3/Task6, #6910)

- electron-builder.yml: dmg/nsis/AppImage 未签名(ADR-043 §5 自用)
- build:electron = electron-vite build + electron-builder
- 产物 out/{main,preload,renderer}

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: main 进程 auth(safeStorage + onBeforeSendHeaders + IPC)

**Files:**
- Modify: `frontend/src/main/index.ts`(挂 auth)
- Create: `frontend/src/main/auth.ts`

**Interfaces:**
- Consumes: Task 2 主进程、Task 5 后端 ws header 支持。
- Produces: 主进程 safeStorage 持 token;`onBeforeSendHeaders` 透明注入 `Authorization: Bearer`;IPC `auth:login`/`auth:logout`/`auth:getToken`/`auth:isAuthenticated`。

- [ ] **Step 1: 写 auth.ts**

```ts
// frontend/src/main/auth.ts
import { app, ipcMain, safeStorage, session } from 'electron'
import { readFileSync, writeFileSync, existsSync } from 'fs'
import { join } from 'path'

const TOKEN_FILE = () => join(app.getPath('userData'), 'token.enc')

function canUseSafeStorage() {
  return safeStorage.isEncryptionAvailable()
}

export function getToken(): string | null {
  const p = TOKEN_FILE()
  if (!existsSync(p)) return null
  try {
    const buf = readFileSync(p)
    // safeStorage 加密可用则解密,否则(Linux 无 libsecret)退化为明文读取
    return canUseSafeStorage() ? safeStorage.decryptString(buf) : buf.toString('utf-8')
  } catch {
    return null
  }
}

export function setToken(token: string | null) {
  const p = TOKEN_FILE()
  if (!token) {
    existsSync(p) && require('fs').unlinkSync(p)
    return
  }
  const buf = canUseSafeStorage() ? safeStorage.encryptString(token) : Buffer.from(token, 'utf-8')
  writeFileSync(p, buf)
}

/** 透明注入:渲染进程所有出站请求自动带 Authorization */
export function installAuthInterceptor() {
  session.defaultSession.webRequest.onBeforeSendHeaders((details, cb) => {
    const token = getToken()
    if (token && details.url.startsWith('http')) {
      details.requestHeaders['Authorization'] = `Bearer ${token}`
    }
    cb({ requestHeaders: details.requestHeaders })
  })
  // 401 响应:清 token + 通知渲染层
  session.defaultSession.webRequest.onHeadersReceived((details, cb) => {
    if (details.statusCode === 401) {
      setToken(null)
      // 通知所有窗口重定向登录(渲染层监听)
      for (const win of require('electron').BrowserWindow.getAllWindows()) {
        win.webContents.send('auth:unauthorized')
      }
    }
    cb({})
  })
}

export function registerAuthIpc() {
  ipcMain.handle('auth:login', (_e, token: string) => { setToken(token); return true })
  ipcMain.handle('auth:logout', () => { setToken(null); return true })
  ipcMain.handle('auth:getToken', () => getToken())
  ipcMain.handle('auth:isAuthenticated', () => getToken() !== null)
}
```

- [ ] **Step 2: index.ts 挂 auth**

`frontend/src/main/index.ts` `app.whenReady().then(...)` 前加:
```ts
import { registerAuthIpc, installAuthInterceptor } from './auth'
// whenReady 回调里,createWindow 前:
registerAuthIpc()
installAuthInterceptor()
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(electron): main auth safeStorage + onBeforeSendHeaders 透明注入 (PR4/Task7, #6910)

- auth.ts: safeStorage 持 token(OS keychain,Linux 无 libsecret 退明文)
- onBeforeSendHeaders: 渲染层出站请求透明注入 Authorization(渲染层不持 token)
- onHeadersReceived: 401 清 token + send auth:unauthorized
- IPC: auth:login/logout/getToken/isAuthenticated

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: preload auth API + renderer useAuth 抽象 + 登录页存储改

**Files:**
- Modify: `frontend/src/preload/index.ts`(加 auth)
- Create: `frontend/src/renderer/src/utils/isElectron.ts`
- Create: `frontend/src/renderer/src/composables/useAuth.ts`
- Modify: `frontend/src/renderer/src/views/auth/Login.vue`(存储逻辑)
- Modify: `frontend/src/renderer/src/api/request.ts`(token 注入形态分支)
- Modify: `frontend/src/renderer/src/composables/useWebSocket.ts`(token 来源)

**Interfaces:**
- Consumes: Task 7 IPC。
- Produces: 渲染层 `useAuth()` 统一 API,双形态隔离;登录页提交后 Electron→IPC/safeStorage,浏览器→localStorage;request.ts Electron 形态移除拦截器(主进程注入);**登录页视觉零改**。

- [ ] **Step 1: isElectron.ts**

```ts
// frontend/src/renderer/src/utils/isElectron.ts
export const isElectron = !!window.appConfig?.isElectron
```

- [ ] **Step 2: preload 加 auth API**

`frontend/src/preload/index.ts` 追加:
```ts
contextBridge.exposeInMainWorld('auth', {
  login: (token: string) => ipcRenderer.invoke('auth:login', token),
  logout: () => ipcRenderer.invoke('auth:logout'),
  getToken: () => ipcRenderer.invoke('auth:getToken'),
  isAuthenticated: () => ipcRenderer.invoke('auth:isAuthenticated'),
  onUnauthorized: (cb: () => void) => ipcRenderer.on('auth:unauthorized', cb),
})
```
`vite-env.d.ts` 加 `Window.auth` 类型。

- [ ] **Step 3: useAuth.ts 抽象**

```ts
// frontend/src/renderer/src/composables/useAuth.ts
import { isElectron } from '@/utils/isElectron'

export const auth = {
  async login(token: string) {
    if (isElectron) return window.auth!.login(token)
    localStorage.setItem('access_token', token)
  },
  async logout() {
    if (isElectron) return window.auth!.logout()
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
  },
  async getToken(): Promise<string | null> {
    if (isElectron) return window.auth!.getToken()
    return localStorage.getItem('access_token')
  },
  async isAuthenticated(): Promise<boolean> {
    if (isElectron) return window.auth!.isAuthenticated()
    return !!localStorage.getItem('access_token')
  },
}
```

- [ ] **Step 4: Login.vue 存储逻辑改(视觉不动)**

`frontend/src/renderer/src/views/auth/Login.vue` 找到登录提交成功后写 localStorage 处(script 区 L136-449),改:
- `localStorage.setItem('access_token', ...)` → `await auth.login(token)`
- `localStorage.setItem('user_info', ...)` → Electron 形态也经 IPC 存(或 user_info 仍 localStorage 非敏感;决策:user_info 可留 localStorage,仅 token 走 safeStorage)
- import `import { auth } from '@/composables/useAuth'`
- **template/style 零改**

- [ ] **Step 5: request.ts 形态分支**

`frontend/src/renderer/src/api/request.ts` L13-22 拦截器改:
```ts
service.interceptors.request.use(
  (config) => {
    // Electron 形态:主进程 onBeforeSendHeaders 已注入,渲染层不持 token
    if (isElectron) return config
    const token = localStorage.getItem('access_token')
    if (token && config.headers) config.headers['Authorization'] = `Bearer ${token}`
    return config
  },
  (error) => Promise.reject(error)
)
```
顶部 `import { isElectron } from '@/utils/isElectron'`。
401 L51-53:`localStorage.removeItem` 包 `if (!isElectron)`(Electron 由主进程 onHeadersReceived 处理 + send unauthorized)。

- [ ] **Step 6: useWebSocket token 来源**

`useWebSocket.ts` getWebSocketUrl 里 `localStorage.getItem('access_token')` 改 `await auth.getToken()`(函数改 async);connect 处 await。Electron 形态 ws 走 header(主进程 onBeforeSendHeaders 对 ws 握手也注入——验证:Electron `webRequest` 对 ws 握手生效,则 query token 可省;若不生效保留 query 兜底)。

- [ ] **Step 7: 前端单测**

```bash
cd /home/kaoru/Ginkgo/frontend
npx vitest run 2>&1 | tail -10
```
为 useAuth 写 `__tests__/useAuth.spec.ts`:mock window.auth / localStorage,测双形态 login/logout/getToken 分支。

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat(auth): 渲染层 useAuth 双形态抽象 + 登录页存储改 + request 形态分支 (PR4/Task8, #6910)

- isElectron.ts: window.appConfig.isElectron 判定
- preload: contextBridge window.auth(login/logout/getToken/isAuthenticated/onUnauthorized)
- useAuth.ts: 双形态抽象(Electron IPC / 浏览器 localStorage)
- Login.vue: 提交走 auth.login(视觉零改,ADR-044 §2)
- request.ts: Electron 形态移除拦截器(主进程透明注入)
- useWebSocket: token 走 auth.getToken()

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: token 接线修复 + Codex design-tokens 值

**Files:**
- Modify: `frontend/src/renderer/src/main.ts`(import design-tokens.css + main.css)
- Modify: `frontend/src/renderer/src/styles/design-tokens.css`(Codex 中性灰值)
- Modify: `frontend/src/renderer/src/styles/index.less`(去硬编码深色背景)

**Interfaces:**
- Consumes: 探查事实——`main.ts` 只 import index.less;design-tokens.css/main.css 未进 bundle;index.less L18-19 硬编码 `#0f0f1a`。
- Produces: token 体系 + tailwind 真正进 bundle;`:root` 浅色 + `.dark` 深色用 Codex 中性灰值;默认 `<html class="dark">`。

- [ ] **Step 1: main.ts 接线修复**

`frontend/src/renderer/src/main.ts` L5 改:
```ts
import './styles/main.css'        // 含 @tailwind base/components/utilities
import './styles/design-tokens.css' // token :root + .dark
import './styles/index.less'       // 业务 less(去硬编码 hex,见 Step 3)
```

- [ ] **Step 2: design-tokens.css Codex 中性灰值**

`:root`(浅色)与 `.dark`(深色)全 token 重设为 Codex 中性灰(去 Ant Design 蓝 `221.2 83.2% 53.3%`)。**值待用户截图校准**(ADR-045 Consequences §),先用 Codex 公开印象值占位,验收时调:
```css
:root {
  --background: 0 0% 98%;            /* 浅灰白 */
  --foreground: 0 0% 10%;            /* 近黑 */
  --card: 0 0% 100%;
  --card-foreground: 0 0% 10%;
  --primary: 0 0% 9%;                /* 中性灰主色(去蓝) */
  --primary-foreground: 0 0% 98%;
  --secondary: 0 0% 92%;
  --muted: 0 0% 94%;
  --muted-foreground: 0 0% 40%;
  --accent: 0 0% 92%;
  --destructive: 0 72% 51%;
  --border: 0 0% 88%;
  --input: 0 0% 88%;
  --ring: 0 0% 9%;
  --radius: 0.375rem;                /* 6px 紧凑(ADR-045 §4) */
  /* 涨跌语义色保留(ADR-045):仅数字/图表用 */
  --success: 142 71% 45%;  /* 涨绿 */
  --warning: 38 92% 50%;
  --error: 0 72% 51%;      /* 跌红 */
  --info: 0 0% 40%;        /* 去蓝,改中性 */
}
.dark {
  --background: 0 0% 5%;             /* Codex 近黑 #0d0d0d 类 */
  --foreground: 0 0% 93%;
  --card: 0 0% 7%;
  --card-foreground: 0 0% 93%;
  --primary: 0 0% 93%;
  --primary-foreground: 0 0% 9%;
  --secondary: 0 0% 14%;
  --muted: 0 0% 12%;
  --muted-foreground: 0 0% 55%;
  --accent: 0 0% 14%;
  --destructive: 0 62% 50%;
  --border: 0 0% 16%;
  --input: 0 0% 16%;
  --ring: 0 0% 70%;
}
```

- [ ] **Step 3: index.less 去硬编码**

`frontend/src/renderer/src/styles/index.less` L18-19:
```less
html, body {
  /* 删除 color:#fff; background:#0f0f1a 硬编码 */
  @apply bg-background text-foreground;
}
```
全文件其余裸 hex(`#cf1322` 等)→ `@apply text-error`/`text-success` 或 `hsl(var(--token))`。

- [ ] **Step 4: 默认深色**

`frontend/src/renderer/index.html` `<html>` 加 `class="dark"`(ADR-045 §1 深色优先默认)。

- [ ] **Step 5: 验证 token 生效**

```bash
cd /home/kaoru/Ginkgo/frontend
npm run build 2>&1 | tail -5
# dev 起来肉眼验:背景应为 Codex 深灰(非 #0f0f1a 偏蓝紫)
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(visual): token 接线修复 + Codex 中性灰 design-tokens (PR5/Task9, #6910)

- main.ts: import main.css(@tailwind)+design-tokens.css(修复接线断层)
- design-tokens.css: Codex 中性灰去蓝(:root 浅 + .dark 深),--radius 6px
- index.less: 去硬编码 #0f0f1a → bg-background
- index.html: <html class=dark> 深色优先默认
- 涨绿跌红语义色保留(克制使用)
- 注: hex 值待用户截图校准(ADR-045 Consequences)

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: 字体 Inter + JetBrains Mono 打包接入

**Files:**
- Create: `frontend/src/renderer/src/assets/fonts/{Inter-*.woff2, JetBrainsMono-*.woff2}`
- Create: `frontend/src/renderer/src/styles/fonts.css`
- Modify: `frontend/src/renderer/src/main.ts`(import fonts.css)
- Modify: `frontend/src/renderer/src/styles/design-tokens.css` 或 tailwind.config.js(font-family)

**Interfaces:**
- Consumes: Task 9 token 接线。
- Produces: 正文 Inter + 等宽 JetBrains Mono,随 Electron 打包(~5MB),离线可用。

- [ ] **Step 1: 取字体文件**

Inter(Variable)+ JetBrains Mono 从 Google Fonts / rsms.me 下载 woff2(Regular/Medium/Bold 子集,含中文回退不打包 Inter 中文 glyph)。放 `src/renderer/src/assets/fonts/`。**license**:Inter 是 SIL OFL,JetBrains Mono 是 OFL——`src/renderer/src/assets/fonts/LICENSE` 落盘两份。

- [ ] **Step 2: fonts.css @font-face**

```css
/* frontend/src/renderer/src/styles/fonts.css */
@font-face {
  font-family: 'Inter';
  src: url('./assets/fonts/Inter-Variable.woff2') format('woff2-variations');
  font-weight: 100 900;
  font-display: swap;
}
@font-face {
  font-family: 'JetBrains Mono';
  src: url('./assets/fonts/JetBrainsMono-Variable.woff2') format('woff2-variations');
  font-weight: 100 800;
  font-display: swap;
}
```

- [ ] **Step 3: main.ts import + font-family**

`main.ts` 加 `import './styles/fonts.css'`。
`tailwind.config.js` `fontFamily`:
```js
fontFamily: {
  sans: ['Inter', '-apple-system', 'PingFang SC', 'Microsoft YaHei', 'Noto Sans CJK SC', 'sans-serif'],
  mono: ['JetBrains Mono', 'monospace'],
}
```
`design-tokens.css` `body` 或 index.less body 设 `font-family: 'Inter', ...`。

- [ ] **Step 4: 验证 + Commit**

```bash
cd /home/kaoru/Ginkgo/frontend
npm run build 2>&1 | tail -3
ls -la src/renderer/dist/assets/*.woff2  # 字体进产物
```
```bash
git add -A
git commit -m "feat(visual): Inter + JetBrains Mono 字体打包接入 (PR5/Task10, #6910)

- assets/fonts: Inter Variable + JetBrains Mono Variable(woff2,~5MB)
- fonts.css @font-face + LICENSE(OFL)
- tailwind fontFamily: sans=Inter+中文系统回退, mono=JetBrains Mono
- 随 Electron 打包离线可用(ADR-045 §3)

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: 全组件 hex→token 迁移

**Files:**
- Modify: `frontend/src/renderer/src/components/**`(所有裸 hex)
- Modify: `frontend/src/renderer/src/views/**`

**Interfaces:**
- Consumes: Task 9 token 体系生效。
- Produces: 全仓组件无裸 hex 颜色,统一走 `hsl(var(--token))` / tailwind color class。

- [ ] **Step 1: grep 全仓裸 hex**

```bash
cd /home/kaoru/Ginkgo/frontend/src/renderer
grep -rnE '#[0-9a-fA-F]{3,8}\b' src/ --include='*.vue' --include='*.less' --include='*.css' --include='*.ts' \
  | grep -vE 'node_modules|/assets/fonts|design-tokens.css' > /tmp/hex-audit.txt
wc -l /tmp/hex-audit.txt   # 基线
```

- [ ] **Step 2: 逐文件迁移(规则)**

对每条命中:
- 背景/前景/边框色 → 对应 token(`bg-background`/`text-foreground`/`border-border`/`bg-card`/`bg-muted`/`bg-accent`/`text-muted-foreground`)
- 语义(涨跌/警告/错误)→ `text-success`/`text-error`/`text-warning`(保留语义克制)
- 仅图表内部(lightweight-charts/echarts)硬编码色 → 保留(图表配色复杂,单独配置),record 在 report
- 主题相关 → 补 `dark:` 变体(若该 hex 是亮色专属)

抽样起点(探查已确认):`StatCard.vue` L60-79、`index.less` 剩余、stage-badge。

- [ ] **Step 3: 验证 hex 清零(非图表)**

```bash
grep -rnE '#[0-9a-fA-F]{3,8}\b' src/ --include='*.vue' --include='*.less' \
  | grep -vE 'design-tokens.css|/assets/' \
  | grep -vE 'chartOption|echarts|lightweight' | wc -l
```
Expected: 0(图表内部 hex 单独 record)。

- [ ] **Step 4: vitest + build 不破**

```bash
npx vitest run 2>&1 | tail -5
npm run build 2>&1 | tail -3
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(visual): 全组件 hex→token 迁移 (PR6/Task11, #6910)

- grep 全仓裸 hex → hsl(var(--token))/tailwind class
- 背景前景边框/语义色统一接 token(涨跌语义保留)
- 图表内部配色保留(单独 record)
- 配 ADR-045 token 体系生效前提

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 12: dark: 变体补全 + 紧凑密度

**Files:**
- Modify: `frontend/src/renderer/src/components/**`、`views/**`(补 dark: 变体)
- Modify: `frontend/src/renderer/tailwind.config.js`(紧凑密度 spacing)

**Interfaces:**
- Consumes: Task 11 token 接线。
- Produces: 双主题可用(浅/深色切换无破);紧凑 Codex 密度。

- [ ] **Step 1: 紧凑密度 token**

`tailwind.config.js` 或 design-tokens.css 收紧:
- 按钮 `h-7`(28px)/ 输入 `h-[30px]` / 表格行 `leading-9`(36px)
- shadcn-vue 组件 size variant 调(若组件 props 有 size,改默认 default→sm)

- [ ] **Step 2: 补 dark: 变体**

对组件中"浅色硬编码但 token 已接"处补 `dark:` 变体;对 `bg-white`/`text-black`/`bg-gray-*` 改 token class。grep `bg-white|text-black|bg-gray|text-gray` 全仓迁移到 token。

- [ ] **Step 3: 主题切换器**

新建 `frontend/src/renderer/src/composables/useTheme.ts`:
```ts
export function setTheme(t: 'dark' | 'light') {
  document.documentElement.classList.toggle('dark', t === 'dark')
  localStorage.setItem('theme', t)
}
export function initTheme() {
  const saved = localStorage.getItem('theme') as 'dark'|'light' | null
  document.documentElement.classList.toggle('dark', saved ? saved === 'dark' : true) // 默认深色
}
```
`main.ts` 调 `initTheme()`;settings 页加切换 UI(若 settings 视图存在)。

- [ ] **Step 4: 验证双主题**

dev 模式手动切 `.dark` on/off,肉眼验无破(背景/文字/边框/卡片都随主题变)。

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat(visual): dark: 变体补全 + 紧凑密度 + 主题切换器 (PR6/Task12, #6910)

- 紧凑密度: 按钮28/输入30/行36(ADR-045 §4)
- 补 dark: 变体,bg-white/gray-* → token
- useTheme: setTheme/initTheme,默认深色,localStorage 持久
- 双主题切换无破

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 13: 登录页双主题(深色降饱和 + 浅色新建)

**Files:**
- Modify: `frontend/src/renderer/src/views/auth/Login.vue`(style 区 L451-971)

**Interfaces:**
- Consumes: Task 12 主题切换。
- Produces: 登录页深色版(现赛博朋克降饱和融入中性灰)+ 浅色版(终端风浅色化,结构保留)。**视觉改动仅此 task**。

- [ ] **Step 1: 深色版降饱和**

`Login.vue` `<style scoped>` 内霓虹色(`#00ff88`/`#0ff`/`#ff00ff` 类)降饱和度/亮度,向 Codex 中性灰靠拢(保留终端结构,只调色)。具体值待用户校准。

- [ ] **Step 2: 浅色版新建**

登录页浅色化:根容器浅色背景 + 深色文字 + 终端元素浅色化。用 `:root:not(.dark)` 选择器或 `dark:` 分支。结构(BIOS/粒子/跑马灯/故障字/终端/像素输入)保留,配色转浅。

- [ ] **Step 3: 验证**

切深/浅主题,登录页双版本都正常,视觉与主 app 中性灰基调协调(登录炫酷→工作专注,ADR-045 Consequences §刻意氛围设计)。

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat(visual): 登录页双主题(深色降饱和+浅色新建) (PR6/Task13, #6910)

- 深色版: 赛博朋克霓虹降饱和融入 Codex 中性灰
- 浅色版: 终端风浅色化,结构保留(BIOS/粒子/跑马灯/故障字/终端)
- 视觉与主 app 协调(登录炫酷→工作专注,ADR-045 刻意氛围)
- 具体色值待用户校准

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage**(对照 ADR-042/043/044/045):
- ADR-042 §1 双形态共存:Task 1-8(浏览器形态 Task 1/4 保持 + Electron Task 1-8)。✓
- ADR-042 §2 重命名:PR1 已完成。✓
- ADR-042 §4 Electron 打包走 npm:Task 6 `build:electron`,不进 ginkgo CLI。✓
- ADR-043 §1 electron-vite:Task 1。✓
- ADR-043 §2 src/renderer:Task 1。✓
- ADR-043 §3 app://:Task 2。✓
- ADR-043 §4 hash 路由:Task 4。✓
- ADR-043 §5 未签名包:Task 6。✓
- ADR-043 §6 运行时配置:Task 3。✓
- ADR-043 3 处 file://:Task 4(request/useWebSocket/401)。✓
- ADR-043 后端 CORS:Task 5。✓
- ADR-044 §1 auth proxy:Task 7。✓
- ADR-044 §2 登录逻辑改:Task 8。✓
- ADR-044 §5 ws header:Task 5。✓
- ADR-044 §7 auth 抽象:Task 8。✓
- ADR-045 §1 深色优先:Task 9/12。✓
- ADR-045 §2 Codex 中性灰:Task 9/11。✓
- ADR-045 §3 Inter+JetBrains Mono:Task 10。✓
- ADR-045 §4 紧凑密度:Task 12。✓
- ADR-045 §5 登录页双主题:Task 13。✓
- ADR-045 §6 沿用 shadcn-vue:Task 9 仅重设 token。✓
- **token 接线断层修复**:Task 9 Step 1(探查发现的 ADR 前提缺陷)。✓

**2. Placeholder scan**:每步含 file:line / 实际命令 / 代码。视觉 task(Task 9/11/13)因色值需用户校准,标"待校准"但给 Codex 公开印象值占位(非空 TODO)。✓

**3. Type consistency**:`window.appConfig`(Task 3/4)、`window.auth`(Task 7/8)、`auth.login/getToken`(Task 8)跨 task 命名一致;`isElectron`(Task 8)全形态判定统一;config.ts `AppConfig`(Task 3)与 preload 注入字段(apiBase/wsBase)一致。✓

**风险/待校准项**(验收时确认):
- ADR-045 具体 hex 值:Task 9/11/13 用 Codex 公开印象值占位,需用户截图校准(ADR-045 Consequences 明示)
- Electron `webRequest` 对 ws 握手是否注入 header:Task 8 Step 6 验证,不生效则 query 兜底
- electron-builder 跨平台打包产物:Task 6 headless/Linux 验证 build,完整 dmg/nsis 需对应 OS 验收
- Task 1 git mv 规模大(~30 顶层项),rename 检测需 `git status` 抽验
