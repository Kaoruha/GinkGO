# PR1: web-ui→frontend 重命名 + serve webui→serve web Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把前端目录 `web-ui/` 重命名为 `frontend/`，CLI 命令 `ginkgo serve webui` 改为 `ginkgo serve web`，参数 `--webui-port` 改为 `--web-port`，同步全仓引用锚点（功能/容器/配置/用户文档/注释），历史 ADR 与 specs 不动。

**Architecture:** 纯重命名重构，零行为变更——端口 5173 不变、短旗 `-w` 不变、目录用 `git mv` 保留历史。改动分 6 个串行 task：CLI 核心（TDD 红-绿）→ 目录 mv + 路径同步 → 容器 → 配置 → 用户文档 → 注释 + 全量验证。决策权威为 [ADR-042](../../adrs/ADR-042-dual-form-browser-electron-frontend-rename.md)。

**Tech Stack:** Python 3 + typer（CLI）、Docker（docker-compose/Dockerfile）、Vue 3 + Vite（前端，本 PR 只动目录名/包名）、git mv。

## Global Constraints

- **端口不变**：Web UI 端口恒为 `5173`，`serve all` 的 API 端口恒为 `8000`。
- **短旗保留**：`--web-port` 保留 `-w` 短旗（原 `--webui-port -w`）；`serve web` 的 `--host/-h`、`--port/-p`、`--open/-o` 不变。
- **git mv 保留历史**：目录用 `git mv web-ui frontend`，禁用 `rm + add`（保 blame 历史）。
- **历史记录不动**：不改 `docs/adrs/ADR-015-webui-shadcn-vue.md`、`ADR-025`（旧 ADR 文件名与正文，历史不可变）；不改 `docs/adrs/ADR-04[2-5]*.md`（本次决策正文，引用 web-ui 是决策描述）；不改 `specs/`（已完成的历史规格）、`.specify/`（specify 工具产物）。
- **测试 OOM 铁律**：禁止单进程跑全量 `tests/`（Base.metadata 累积致 OOM）。本 plan 验证只用 `pytest tests/unit/client/test_serve_cli.py`（单文件 smoke）+ `python -m py_compile`，**不跑全量**。
- **Python 环境**：`/home/kaoru/.ginkgo/.venv/bin/python`（下文记作 `$PY`）；包管理用 `uv`（frozen lock）。
- **提交规范**：每个 task 一次 commit，message 引用 `Refs #6910`（**不**用 Closes/Fixes，避免关闭 epic）；末尾加 `Co-Authored-By: Claude <noreply@anthropic.com>`。
- **分支**：`epic-6910-frontend-electron-dual-form`（已建，已含 ADR commit `59b927d5`）。

---

## File Structure

| 文件 | 责任 | 本 PR 动作 |
|---|---|---|
| `src/ginkgo/client/serve_cli.py` | CLI 命令定义（serve web/all） | 改命令名/函数名/参数/路径字符串 |
| `tests/unit/client/test_serve_cli.py` | serve CLI 单元测试 | 改断言（TDD 锚点）+ 新增 --web-port 断言 |
| `web-ui/` → `frontend/` | Vue 前端工程 | `git mv`（Task 2） |
| `docker-compose.yml` | 容器编排 | service/image/container_name |
| `.conf/Dockerfile.web` | 前端镜像构建 | COPY 路径 |
| `.gitignore` | 忽略规则 | 路径前缀 |
| `frontend/package.json`（mv 后） | npm 包定义 | name 字段 |
| `api/verify_api_paths.sh` | API 路径校验脚本 | FRONTEND_API_DIR |
| `CLAUDE.md` / `AGENTS.md` / `README.md` / `frontend/README.md` | 用户手册 | 命令引用 |
| `api/*.py` 注释 / `remote/services.py` 注释 / `api/*.md` / `frontend/docs/*` | 代码注释 + 活跃文档 | 引用文本 |

---

## Task 1: CLI 命令 + 参数重命名（TDD 红-绿）

**Files:**
- Modify: `tests/unit/client/test_serve_cli.py:7,52,70-76`（+ 新增 serve all --web-port 断言测试）
- Modify: `src/ginkgo/client/serve_cli.py:96-108,165-176,185,252,260,270`

**Interfaces:**
- Produces: CLI 子命令 `serve web`（原 `serve webui`）；参数 `serve all --web-port`（原 `--webui-port`，短旗 `-w` 保留，默认 5173）。Task 2 依赖本 task 后 serve_cli.py 已用新命令名。
- 注意：本 task **不**动 `webui_path` 变量与 `"web-ui"` 路径字符串（留 Task 2 与 git mv 同步）。本 task 后 `serve web` 命令存在但内部仍指向 `web-ui/` 目录（目录还在，可跑）。

- [ ] **Step 1: 改测试到期望新行为（红）**

修改 `tests/unit/client/test_serve_cli.py`：

文件顶部 docstring L7：
```python
# 改前
- webui: 启动 Web UI 开发服务器 (Vue 3 + Vite)
# 改后
- web: 启动 Web UI 开发服务器 (Vue 3 + Vite)
```

L52（root help 断言，`webui`→`web`，并加 not 断言锁死旧名消失）：
```python
# 改前
        assert "webui" in result.output
# 改后
        assert "web" in result.output
        assert "webui" not in result.output
```

L70-76（`test_serve_webui_help_shows_options` → `test_serve_web_help_shows_options`，调用 `["web", "--help"]`）：
```python
# 改后（整段替换 L70-76）
    def test_serve_web_help_shows_options(self, runner):
        """serve web --help 显示 host/port/open 选项"""
        result = runner.invoke(serve_cli.app, ["web", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.output or "-h" in result.output
        assert "--port" in result.output or "-p" in result.output
        assert "--open" in result.output or "-o" in result.output
```

在 `TestServeHelp` 类末尾（L76 后）新增 serve all --web-port 断言测试：
```python
    def test_serve_all_help_shows_web_port_option(self, runner):
        """serve all --help 显示 --web-port（非 --webui-port）选项"""
        result = runner.invoke(serve_cli.app, ["all", "--help"])
        assert result.exit_code == 0
        assert "--web-port" in result.output
        assert "--webui-port" not in result.output
```

- [ ] **Step 2: 跑测试验证它失败（红）**

Run: `$PY -m pytest tests/unit/client/test_serve_cli.py -v`
Expected: FAIL —— `test_serve_web_help_shows_options`（`["web","--help"]` 命令不存在，exit_code≠0）、`test_serve_root_help...`（`"webui" not in` 断言失败，旧名还在）、`test_serve_all_help_shows_web_port_option`（`--web-port` 不存在）。

- [ ] **Step 3: 改 serve_cli.py 命令名 + 函数名 + docstring（L96-108）**

```python
# L96 改前
@app.command("webui")
# L96 改后
@app.command("web")

# L97 改前
def serve_webui(
# L97 改后
def serve_web(

# L106-108 docstring 改前
      ginkgo serve webui
      ginkgo serve webui --port 3000
      ginkgo serve webui --open
# L106-108 docstring 改后
      ginkgo serve web
      ginkgo serve web --port 3000
      ginkgo serve web --open
```

- [ ] **Step 4: 改 serve_all 的 --webui-port 参数 + webui_port 变量（L168,185,252,260,270）**

```python
# L168 改前
    webui_port: int = typer.Option(5173, "--webui-port", "-w", help="Web UI port"),
# L168 改后
    web_port: int = typer.Option(5173, "--web-port", "-w", help="Web UI port"),

# L175 docstring 改前
      ginkgo serve all --api-port 8080 --webui-port 3000
# L175 docstring 改后
      ginkgo serve all --api-port 8080 --web-port 3000

# L185 改前
        f"[dim]Web UI Port:[/dim] {webui_port}",
# L185 改后
        f"[dim]Web UI Port:[/dim] {web_port}",

# L252 改前
            env["PORT"] = str(webui_port)
# L252 改后
            env["PORT"] = str(web_port)

# L260 改前
            console.print(f"[green]:white_check_mark: Web UI started at http://0.0.0.0:{webui_port}[/green]")
# L260 改后
            console.print(f"[green]:white_check_mark: Web UI started at http://0.0.0.0:{web_port}[/green]")

# L270 改前
    console.print(f"[dim]Web UI:[/dim] http://localhost:{webui_port}")
# L270 改后
    console.print(f"[dim]Web UI:[/dim] http://localhost:{web_port}")
```

- [ ] **Step 5: 跑测试验证它通过（绿）**

Run: `$PY -m pytest tests/unit/client/test_serve_cli.py -v`
Expected: PASS（12+ tests，含新增 `test_serve_all_help_shows_web_port_option`）。

- [ ] **Step 6: py_compile smoke**

Run: `$PY -m py_compile src/ginkgo/client/serve_cli.py && echo OK`
Expected: `OK`（无语法错误）。

- [ ] **Step 7: Commit**

```bash
git add src/ginkgo/client/serve_cli.py tests/unit/client/test_serve_cli.py
git commit -m "refactor(client): serve webui→serve web, --webui-port→--web-port (PR1/6, #6910)

- @app.command(\"web\") 替代 \"webui\"，serve_web 替代 serve_webui
- serve all 参数 --webui-port→--web-port（短旗 -w 不变，默认 5173）
- 测试断言同步：serve web --help + --web-port + webui not in

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: git mv web-ui→frontend + serve_cli.py 路径硬编码同步

**Files:**
- Rename: `web-ui/` → `frontend/`（`git mv`）
- Modify: `src/ginkgo/client/serve_cli.py:114-115,117,118,122,131,141,160`（`webui_path` 变量 + `"web-ui"` 字符串）
- Modify: `src/ginkgo/client/serve_cli.py:209,217,218,256`（serve_all 内 `webui_path` + `"web-ui"`）

**Interfaces:**
- Consumes: Task 1 后的 serve_cli.py（新命令名已就位）。
- Produces: 前端目录正式名 `frontend/`；serve_cli.py 用 `frontend_path` 变量指向 `"frontend"` 目录。后续 task（容器/配置/文档）引用此新目录名。

**关键**：`git mv` 与 serve_cli.py 路径字符串必须**同一 commit 原子改动**——否则 mv 后 serve 命令找不到目录（中间态断裂）。

- [ ] **Step 1: git mv 目录**

Run: `git mv web-ui frontend`
Expected: 无输出（成功）；`git status` 显示 renamed: `web-ui → frontend`。

- [ ] **Step 2: 改 serve_webui 内 webui_path → frontend_path（L114-160）**

`serve_cli.py` 的 `serve_web` 函数内（原 L114-160），变量名 `webui_path` 全改 `frontend_path`，路径字符串 `"web-ui"` 改 `"frontend"`：

```python
# L114-115 改前
    # 获取 web-ui 目录路径
    webui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "web-ui")
# 改后
    # 获取 frontend 目录路径
    frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "frontend")
```

L117-160 内所有 `webui_path` 引用改 `frontend_path`（共 L117,118,122,131,141,160 六处，纯变量名替换，逻辑不动）。

- [ ] **Step 3: 改 serve_all 内 webui_path → frontend_path（L209-256）**

```python
# L209 改前
    webui_path = os.path.join(base_path, "web-ui")
# 改后
    frontend_path = os.path.join(base_path, "frontend")
```

L217,218,256 内 `webui_path` 引用改 `frontend_path`（三处）。

- [ ] **Step 4: 跑测试验证路径改对（绿）**

Run: `$PY -m pytest tests/unit/client/test_serve_cli.py -v`
Expected: PASS（12+ tests）。路径相关测试（mock os.path.exists）不依赖真实目录名，应仍 pass；若存在断言路径含 "web-ui" 的测试，需同步改 "frontend"（grep 确认：`grep -n web-ui tests/unit/client/test_serve_cli.py` 应无残留）。

- [ ] **Step 5: 验证 serve 命令能找到新目录**

Run: `$PY -c "from ginkgo.client import serve_cli; import os; print(os.path.exists(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(serve_cli.__file__)))), 'frontend')))"`
Expected: `True`（frontend 目录存在）。

- [ ] **Step 6: py_compile + grep 残留**

Run: `$PY -m py_compile src/ginkgo/client/serve_cli.py && grep -n "webui_path\|\"web-ui\"" src/ginkgo/client/serve_cli.py`
Expected: `OK` 后 grep **无输出**（serve_cli.py 内 webui_path 变量与 "web-ui" 字符串清零）。

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(client): git mv web-ui→frontend + serve_cli 路径同步 (PR1/6, #6910)

- git mv web-ui frontend（保留 blame 历史）
- serve_cli.py webui_path→frontend_path，\"web-ui\"→\"frontend\"
- 原子改动：mv 与路径字符串同 commit，避免中间态断裂

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: 容器/构建配置（docker-compose + Dockerfile.web）

**Files:**
- Modify: `.conf/Dockerfile.web:10,16`
- Modify: `docker-compose.yml:64-66`（+ 任何 `depends_on: [webui]` 引用）

**Interfaces:**
- Consumes: Task 2 后目录名 `frontend/`。
- Produces: docker service 名 `web`（原 `webui`）；镜像构建 COPY 从 `frontend/` 取。CI/部署若有 `docker-compose up webui` 引用需同步（本 task grep 确认）。

- [ ] **Step 1: 改 Dockerfile.web COPY 路径**

```dockerfile
# .conf/Dockerfile.web L10 改前
COPY web-ui/package.json web-ui/pnpm-lock.yaml ./
# 改后
COPY frontend/package.json frontend/pnpm-lock.yaml ./

# L16 改前
COPY web-ui/ ./
# 改后
COPY frontend/ ./
```

- [ ] **Step 2: 改 docker-compose.yml service 名 + image + container_name**

```yaml
# docker-compose.yml L64-66 改前
  webui:
    image: ginkgo/webui:latest
    container_name: ginkgo-web-ui
# 改后
  web:
    image: ginkgo/web:latest
    container_name: ginkgo-frontend
```

- [ ] **Step 3: grep docker-compose 内对 webui service 的引用**

Run: `grep -n "webui" docker-compose.yml`
Expected: 若有 `depends_on: - webui` 或 `webui:` 其他引用，全部改 `web`；若无残留，跳过。

- [ ] **Step 4: 验证 compose 配置语法**

Run: `docker compose -f docker-compose.yml config --quiet 2>&1 | head -5`（若 docker 不可用，跳过此步并在 report 注明）
Expected: 无错误（service 名合法、无悬空 depends_on）。

- [ ] **Step 5: Commit**

```bash
git add .conf/Dockerfile.web docker-compose.yml
git commit -m "refactor(docker): webui service→web + COPY frontend (PR1/6, #6910)

- Dockerfile.web COPY web-ui/→frontend/
- docker-compose service webui→web, image ginkgo/web, container ginkgo-frontend

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: 配置/脚本（.gitignore + package.json name + verify_api_paths.sh）

**Files:**
- Modify: `.gitignore:20,238,241`
- Modify: `frontend/package.json:2`（mv 后路径）
- Modify: `api/verify_api_paths.sh:65`

**Interfaces:**
- Consumes: Task 2 后 `frontend/` 目录、`frontend/package.json`。
- Produces: npm 包名 `ginkgo-frontend`（原 `ginkgo-web-ui`）；.gitignore 忽略 `frontend/node_modules` `frontend/dist`；校验脚本指向 `frontend/src/api/modules`。

- [ ] **Step 1: 改 .gitignore**

```gitignore
# .gitignore L20 改前
/lib/      # 锚定仓库根：仅忽略 Python 构建产物，勿误伤 web-ui/src/lib（shadcn-vue 源码）
# 改后
/lib/      # 锚定仓库根：仅忽略 Python 构建产物，勿误伤 frontend/src/lib（shadcn-vue 源码）

# L238 改前
web-ui/node_modules/
# 改后
frontend/node_modules/

# L241 改前
web-ui/dist/
# 改后
frontend/dist/
```

- [ ] **Step 2: 改 frontend/package.json name**

```json
// frontend/package.json L2 改前
  "name": "ginkgo-web-ui",
// 改后
  "name": "ginkgo-frontend",
```

- [ ] **Step 3: 改 verify_api_paths.sh**

```bash
# api/verify_api_paths.sh L65 改前
FRONTEND_API_DIR="../web-ui/src/api/modules"
# 改后
FRONTEND_API_DIR="../frontend/src/api/modules"
```

- [ ] **Step 4: 验证路径存在**

Run: `test -d frontend/node_modules && echo "gitignore target exists"; test -f frontend/package.json && grep '"name"' frontend/package.json; test -d frontend/src/api/modules && echo "FRONTEND_API_DIR target exists"`
Expected: 三个路径均存在，name 显示 `"ginkgo-frontend"`。

- [ ] **Step 5: Commit**

```bash
git add .gitignore frontend/package.json api/verify_api_paths.sh
git commit -m "chore: 配置锚点 web-ui→frontend (PR1/6, #6910)

- .gitignore: frontend/node_modules + frontend/dist
- frontend/package.json name ginkgo-frontend
- verify_api_paths.sh FRONTEND_API_DIR frontend

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: 用户文档命令引用（CLAUDE.md / AGENTS.md / README.md / frontend/README.md）

**Files:**
- Modify: `CLAUDE.md:68`
- Modify: `AGENTS.md:36`
- Modify: `README.md:70`
- Modify: `frontend/README.md:12`（mv 后）

**Interfaces:**
- Consumes: Task 1 后命令名 `serve web`。
- Produces: 用户手册命令清单统一为 `ginkgo serve web`。

- [ ] **Step 1: 改 CLAUDE.md**

```markdown
# CLAUDE.md L68 改前
ginkgo serve webui                            # Web UI (:5173)
# 改后
ginkgo serve web                            # Web UI (:5173)
```

- [ ] **Step 2: 改 AGENTS.md / README.md / frontend/README.md**

```markdown
# AGENTS.md L36 改前
ginkgo serve webui                    # Web界面
# 改后
ginkgo serve web                    # Web界面

# README.md L70 改前
ginkgo serve webui    # Vue dev server on :5173
# 改后
ginkgo serve web    # Vue dev server on :5173

# frontend/README.md L12 改前
启动命令：`ginkgo serve webui`
# 改后
启动命令：`ginkgo serve web`
```

- [ ] **Step 3: grep 用户文档无残留**

Run: `grep -n "serve webui\|--webui-port" CLAUDE.md AGENTS.md README.md frontend/README.md`
Expected: **无输出**（四处用户文档命令引用清零）。

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md AGENTS.md README.md frontend/README.md
git commit -m "docs: 用户手册 serve webui→serve web (PR1/6, #6910)

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: 代码注释 + 活跃文档 + 全量验证

**Files:**
- Modify: `src/ginkgo/client/serve_cli.py:114`（注释，若 Task 2 未改全）
- Modify: `src/ginkgo/client/remote/services.py:9`（注释）
- Modify: `api/api/accounts.py:4` / `api/api/file.py:3` / `api/models/accounts.py:4`（注释）
- Modify: `tests/api/test_file_router.py:11` / `tests/api/test_backtest_pagination.py:1`（注释）
- Modify: `api/API_VERSIONING.md` / `api/docs/sse_backtest_progress.md` / `api/docs/UNIFIED_API_RESPONSE.md` / `api/MIGRATION_SUMMARY.md`
- Modify: `frontend/docs/*` / `frontend/src/composables/README.md`（mv 后）

**Interfaces:**
- Consumes: Task 1-5 后全仓已无功能性 web-ui 引用。
- Produces: 注释/活跃文档与目录新名一致；全仓 grep 仅历史 ADR/specs 残留（合规）。

**不改（Global Constraints 锁定）**：`docs/adrs/ADR-015*`、`ADR-025*`、`ADR-04[2-5]*`、`docs/adrs/README.md`（ADR-015 索引）、`specs/**`、`.specify/**`。

- [ ] **Step 1: 改代码注释（5 文件）**

逐文件把注释中的 `web-ui` 改 `frontend`：
- `serve_cli.py:114` 注释（若 Task 2 已改可跳过，grep 确认）
- `remote/services.py:9`：`远端 REST 面向 web-ui` → `远端 REST 面向 frontend`
- `api/api/accounts.py:4` / `api/api/file.py:3` / `api/models/accounts.py:4`：`前端 web-ui/src/api/modules/...` → `前端 frontend/src/api/modules/...`
- `tests/api/test_file_router.py:11` / `tests/api/test_backtest_pagination.py:1`：注释 `web-ui` → `frontend`

- [ ] **Step 2: 改活跃文档（api/*.md + frontend/docs/* + composables/README）**

用 sed 批量替换（排除历史）：
```bash
# api 活跃文档
sed -i 's/web-ui/frontend/g' api/API_VERSIONING.md api/docs/sse_backtest_progress.md api/docs/UNIFIED_API_RESPONSE.md api/MIGRATION_SUMMARY.md
# frontend 自身文档（mv 后路径）
sed -i 's/web-ui/frontend/g' frontend/docs/*.md frontend/src/composables/README.md
```
Run 后 `git diff --stat` 确认改动范围合理。

- [ ] **Step 3: 全仓 grep 残留审计**

Run:
```bash
grep -rln "web-ui\|serve webui\|--webui-port" . 2>/dev/null \
  | grep -vE 'node_modules|/dist/|\.venv|\.git/|__pycache__|package-lock|\.superpowers/'
```
Expected: 仅剩 `docs/adrs/ADR-015*`、`ADR-025*`、`ADR-04[2-5]*`、`docs/adrs/README.md`、`specs/**`、`.specify/**`（历史记录，Global Constraints 锁定不改）。**若出现其他文件，逐一处理或上报**。

- [ ] **Step 4: py_compile 全量 smoke（不跑 pytest 全量，遵 OOM 铁律）**

Run:
```bash
$PY -m py_compile src/ginkgo/client/serve_cli.py src/ginkgo/client/remote/services.py api/api/accounts.py api/api/file.py api/models/accounts.py && echo "py_compile OK"
$PY -m pytest tests/unit/client/test_serve_cli.py -v 2>&1 | tail -5
```
Expected: `py_compile OK`；serve_cli 单元测试 PASS（12+ tests）。

- [ ] **Step 5: 实跑 serve web --help（最终 smoke）**

Run: `$PY -m ginkgo.client.ginkgo_cli serve web --help 2>&1 | head -15`（或 `ginkgo serve web --help` 若 ginkgo 在 PATH）
Expected: 输出 `serve web` 帮助，含 `--host`/`--port`/`--open`；**无** `webui` 字样。

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: 注释+活跃文档 web-ui→frontend 残留收口 (PR1/6, #6910)

- 代码注释: remote/services, api/accounts|file|models, tests/api
- 活跃文档: api/*.md, frontend/docs/*, composposables/README
- 全仓 grep 残留仅历史 ADR/specs（Global Constraints 锁定）
- 验证: py_compile OK + serve_cli 单测 PASS + serve web --help smoke

Refs #6910

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage**（对照 ADR-042 Decision §1-4）：
- §1 双形态共存：本 PR 只重命名，双形态抽象层在 PR2-4（本 PR 不涉及，符合 scope）。✓
- §2 目录重命名 web-ui→frontend：Task 2 `git mv`。✓
- §3 CLI serve webui→serve web + --webui-port→--web-port + ~60 锚点：Task 1（CLI）+ Task 3-6（锚点）。✓
- §4 Electron 打包走 npm 不进 CLI：本 PR 不涉及（PR3）。✓
- ADR-042 "约 60 文件锚点"：实际功能锚点 ~40 处（serve_cli/docker/config/docs/comments），历史 ADR/specs ~20 文件锁定不改——与 ADR 的"同步替换"一致（ADR 正文 web-ui 是决策描述，非待替换锚点）。✓

**2. Placeholder scan**：每步含实际 file:line + 改前/改后代码或实际命令；无 TBD/TODO/"适当处理"。✓

**3. Type consistency**：命令名统一 `web`（serve_cli + 测试 + 文档）；参数统一 `--web-port` / 变量 `web_port`（serve_all 内全改）；路径变量统一 `frontend_path`（serve_web + serve_all 内全改）；目录统一 `frontend/`。函数名 `serve_web`（原 `serve_webui`）。✓
