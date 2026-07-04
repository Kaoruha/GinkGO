# ADR-021: CLI 输出层契约（TTY 守卫 + --format/--limit + 序列化规范）

- **Status**: Accepted
- **Date**: 2026-07-04
- **Epic**: #6575 `epic: CLI 输出层统一`
- **关联**: #6493（CLI 功能链路 epic，正交）、#6492（CLI 死代码清理，正交）、PR #6537（stockinfo 非 TTY 阻塞热修）

## Context

PR #6537 修复 `data get stockinfo` 非 TTY 阻塞时暴露了一个系统性问题：**CLI 输出层无契约**。35 个 CLI 文件（17347 行）各自为政，具体乱象（全仓实证）：

| 维度 | 现状 | 实证 |
|---|---|---|
| TTY 守卫 | 5 处 `Prompt/Confirm` 散落 4 文件，仅 `data_cli` 1 处有 `isatty()` 守卫（#6537 刚修） | `param_cli`/`cache_cli`/`kafka_cli×2` 非 TTY 静默走 `default=False`，kafka 删除确认形同虚设 |
| Console 配置 | 20 文件 2 种配置混用 | 10 用 `Console(emoji=True, legacy_windows=False)`，10 用 `Console()` 默认 |
| emoji shortcode | 1688 处 | `:x:`(432)/`:white_check_mark:`(202)/`:information:`(182)...，rich `emoji=False` 会保留 `:x:` 原文（更糟） |
| exit code | `Exit(1)` 一统天下 312 处 | 参数错误/业务失败/超时全混 1，CI 无法分流；`Exit(0)` 滥用 20 处（成功强退反模式）；`Exit(2)` 仅 3 次 |
| stderr 分流 | `stderr=True` 全仓零用 | 错误全走 stdout，`--format json` 时无法与数据 JSON 区分 |
| ServiceResult 字段 | `.error` 与 `.message` 双轨 | 调用方各取一个（`adjustfactor` 取 `message`，其他取 `error`） |
| 序列化 | 仅 `comparison_cli` 用 `default=str` 兜底 | datetime 输出非 ISO8601（空格分隔）、`Decimal` 抛 `TypeError`、UUID 显示 hex/带横线不一 |
| 翻页 | 表现层翻页（全量加载后切片） | `data_cli:189` `total_pages = (len(df)+page_size-1)//page_size`，非服务端分页，百万行 OOM |
| 进度条 | `cache_cli`/`kafka_cli` 用 rich `Progress`/`Live`；`backtest run` 默认同步阻塞 | 非 TTY 刷行污染日志；JSON 模式无约定 |

无 `NO_COLOR` / `--no-color` 支持；无 `--format json` 机器可读输出；`typer.Exit` 被 `except Exception` 吞过（`data_cli:473` 注释为证，[[arch_typer_exit_caught_by_except]]）。

**驱动因素**：Ginkgo 主用户是脚本/Worker/CI（回测 worker 调 CLI、定时任务、CI 流水线），**程序化可读输出 > 人手敲终端**。现状让人读勉强可用、机读几乎不可能。

## Decision

### 10 维输出层契约

#### 1. 输出格式（`--format`）
- 取值 `text` / `json` 二选；默认 `auto`（TTY=rich table 彩色，非 TTY=plain text）
- `json` 模式：stdout 永远输出合法 JSON（成功=数据对象，失败=错误对象），机器可读
- 与 `validation_cli` 已有 `--format text/json/markdown` 惯例对齐

#### 2. 交互方式（TTY 推断 + 显式覆盖）
- 默认 `sys.stdin.isatty()` 推断（人=交互，管道=非交互）
- `--interactive` / `--no-interactive` 双向 flag 覆盖（docker `-it` 风格）
- `--format json` 隐含 `--no-interactive`（机器不需要翻页）

#### 3. 危险操作确认（TTY 守卫）
- `Confirm` 必须加 TTY 守卫：非 TTY 时 **拒绝执行**（不静默走 default=False）
- E3 迁移 `param_cli`/`cache_cli`/`kafka_cli×2` 共 4 处遗留 `Confirm`
- 提供 `safe_confirm()` helper：TTY=正常 Confirm，非 TTY=raise 或显式 `--yes` 跳过

#### 4. 分页参数（`--limit` 新增 + `--page-size` 保留）
- `--limit N`：截断输出条数，**按数据类型默认 order**：
  - `day`/`tick` = `tail`（最新行情，交易员关心近期）
  - `stockinfo`/`adjustfactor` = `head`（全量列表）
- `--page-size N`：仅交互翻页每页大小（保留，向后兼容）
- 两者独立，不再双关

#### 5. 错误输出契约（A1 分流）
- **JSON 错误对象走 stdout**（stdout 永远是合法 JSON，无论成败）；人读诊断走 stderr
- TTY 模式：错误走 stderr（rich 红框）；JSON 模式：`{success:false,error:{...}}` 走 stdout
- ServiceResult 新增 `code: Optional[str]` 字段（向后兼容，默认 `None`），承载结构化错误码（`NOT_FOUND`/`VALIDATION_ERROR`/`BAD_PARAMS`/`TIMEOUT`/`INTERNAL`）
- `.message` 字段废弃（保留不删防破坏），CLI 统一读 `.error`；29 处 `result.message` 迁移到 `.error`（或走 `format_result()` helper）

错误对象 schema：
```json
{"success": false, "error": {"code": "STOCK_NOT_FOUND", "message": "...", "details": {}}, "data": null, "warnings": []}
```

**实现注记（E1 决策 #6576，方案 A 选定）**：`code` 由 `ServiceResult` 承载为 `code: Optional[str] = None` 字段（非 CLI 层 message 反推）。理由：
1. **贯穿调用链**：ServiceResult 是 service 层标准化返回（全仓 436 处 `.success/.failure` 调用），error code 必须在错误产生源头（service/CRUD）就打上，沿调用链自然流到 CLI 映射 exit code；CLI 反推已丢源头语义。
2. **向后兼容零破坏**：默认 `None`，436 处旧调用零改动；新代码按需 `ServiceResult.failure(error="...", code="NOT_FOUND")`。
3. **避免字符串匹配反模式**：方案 B（CLI 从 message 反推 code）依赖文本匹配，i18n / 措辞调整 / 动态拼接即崩，反模式不可接受。
4. **exit code 语义来源**：第 6 维约定的 exit code 1/2/124 分流，语义来源即 `code` 字段（`BAD_PARAMS`→2、`TIMEOUT`→124、其余→1），无 code 字段则 exit code 无分流依据。
5. **落地节奏**：E1（本 issue）只决策 + 字段定义；E2 落 `format_result()` helper 读 code；E5 推广 portfolio/backtest list。分阶段减风险，初版不动 436 处旧调用。

#### 6. 退出码（POSIX 体系）
| code | 含义 | 触发 | 对应 error.code |
|---|---|---|---|
| 0 | 成功 | 正常 return（不 Exit） | success:true |
| 1 | 业务失败 | 数据缺失/校验失败/服务报错 | NOT_FOUND / VALIDATION_ERROR |
| 2 | 参数错误 | typer 参数校验失败 | BAD_PARAMS |
| 124 | 超时 | 回测/同步超时（GNU `timeout` 惯例） | TIMEOUT |
| 130 | 用户中断 | SIGINT | （不输出 JSON） |

- 312 处 `Exit(1)` 重归类（参数错误→2，超时→124）
- 20 处 `Exit(0)` 在 E6 清理为普通 `return`（跳过 typer 收尾的反模式）
- `typer.Exit` 与 `sys.exit` 统一为 `typer.Exit`（避免 Exception 子类被吞陷阱）

#### 7. 彩色 / Emoji 控制（三层）
- **Layer 1** 自动检测（默认）：TTY=彩色+emoji，非 TTY=plain
- **Layer 2** `NO_COLOR` 环境变量（[no-color.org](https://no-color.org) 业界标准）
- **Layer 3** `--no-color` flag（显式覆盖，优先级最高）
- 保留 unicode emoji（`:x:`→`❌`），**禁用 `Console(emoji=False)`**（会保留 `:x:` 原文，更糟）
- E6 统一 `make_console()` 工厂：`Console(emoji=isatty, color_system=None if NO_COLOR else "auto", legacy_windows=False)`

#### 8. 进度条 / 进度流
- **短任务**（list/get/create）：JSON 模式静默，结束输出一个 JSON
- **长程任务**（`backtest run` 默认同步阻塞 / `serve *` / `kafka monitor`）：JSON 模式 **stderr NDJSON 进度事件流 + stdout 最终单个结果 JSON**
  ```
  {"event":"progress","progress":0.5,"current_date":"2025-06-01","stage":"RUNNING"}
  {"event":"log","level":"warning","msg":"..."}
  {"event":"result","success":true,"data":{...}}
  ```
- 核心契约：**进度永远走 stderr，结果永远走 stdout**（TTY=rich Progress 走 stderr，JSON=NDJSON 走 stderr）
- JSON 模式禁用所有 rich 渲染（Progress/Live/Table），靠 `disable=not isatty or format=='json'`
- `transient=True` 默认（完成后清除，cache_cli 已验证的好习惯）

#### 9. 空结果契约（list/get 二分）
- **list 类**（`backtest/portfolio/engine list`）：空 = 正常，exit 0
  ```json
  {"success":true,"data":[],"count":0,"warnings":[],"metadata":{}}
  ```
- **get 类**（`portfolio get <id>` / `backtest cat <id>`）：未找到 = 错误，exit 1
  ```json
  {"success":false,"error":{"code":"NOT_FOUND","message":"..."},"data":null,"warnings":[]}
  ```
- `count` 字段帮 `jq 'select(.count > 0)'` 快速判定；分页元信息（total/limit/offset）放 `metadata`

#### 10. 序列化规范（统一 GinkgoJSONEncoder）
```python
class GinkgoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)): return obj.isoformat()       # ISO8601（T 分隔）
        if isinstance(obj, Decimal): return str(obj)                       # 保留精度
        if isinstance(obj, UUID): return str(obj)                          # 带横线显示
        if isinstance(obj, BaseModel): return obj.model_dump(mode="json")  # pydantic
        if hasattr(obj, '__table__'): return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}  # SQLAlchemy
        if hasattr(obj, 'to_dict'): return obj.to_dict()                   # DataFrame 用 to_dict('records')
        return super().default(obj)
```

| 类型 | JSON 表示 | 理由 |
|---|---|---|
| datetime/date | ISO8601 `2025-06-01T12:00:00+08:00` | 跨语言解析标准（`str(datetime)` 是空格分隔，非 ISO） |
| Decimal | `str` | JSON 无 Decimal，float 在金融场景丢精度（`1.005→1.0049999...`），与 [[ADR-005]] 序列化对称同精神 |
| UUID | 带横线 `xxxxxxxx-xxxx-...` | 用户面向；与库内 hex 存储（[[arch_uuid_storage_no_dashes]]）分层 |
| pydantic Model | `model_dump(mode="json")` | pydantic 原生 JSON-safe |
| SQLAlchemy Model | 列字典 | ORM 标准手法 |
| DataFrame | `to_dict('records')` 数组 | 每行一对象，jq 友好 |

### 翻页条款（补充）
- `--page-size N`：**表现层交互翻页**，仅 TTY + 非 JSON 模式生效；JSON 模式忽略
- `--limit N` + `--offset N`：客户端分页，直通 `service.list(page_size=N, page=offset/N+1)`，所有模式生效
- **三层分页概念**：表现层翻页（--page-size，全量加载后切片显示）/ 截断（--limit，head/tail）/ 服务端分页（service.list page 参数，查一次取一页）
- 表现层翻页不解决"查询 OOM"（全量加载后才切片），百万级数据靠服务端分页

### Epic 落地结构

| # | 子 issue | 类型 | 依赖 | 范围 |
|---|---|---|---|---|
| E1 | 立 ADR-021（本篇）+ ServiceResult 加 code 字段决策 | docs | — | 阻塞全部 |
| E2 | `cli_utils` helper（make_console/make_progress/GinkgoJSONEncoder/format_result/safe_confirm/is_interactive） | refactor | E1 | 基础设施 |
| E3 | 迁移 param/cache/kafka×2 的 Confirm 加 TTY 守卫 | fix | E2 | 🔴 安全最高优先 |
| E4 | `data get` 落地 --format/--limit + 按类型 order + 核实 adjustfactor 截断 | refactor | E2 | 试点，涵盖 #6537 |
| E5 | portfolio/backtest/component list 接入 --format | refactor | E4 | 推广 |
| E6 | 统一 console 工厂 + 全局 --format callback + Exit(0) 清理 + NDJSON 进度流 | refactor | E5 | 收尾 |

依赖链：`E1 → E2 → (E3 ∥ E4) → E5 → E6`

## Rationale

### 为什么 A1（错误 JSON 走 stdout）而非 A2（走 stderr）
- Ginkgo 主用户是脚本/Worker/CI，**程序化错误处理 > pipeline fail-fast**
- `--format json` 的契约应是"stdout 永远是合法 JSON"，`jq` 永远能工作（kubectl/docker/gh/terraform 惯例）
- 成败信号由 exit code 承载，stdout 不必靠"空"二次表达

### 为什么 exit code 细分（0/1/2/124）而非二元
- exit code 是 shell/CI 的"通用语言"（`case $?` / `returncode` / Actions `if: failure()`），不解析输出
- 细分让 CI 据错误类型自动分流（超时重试 / 参数错误告警 / 业务失败记录）
- exit code（粗粒度 4 类）与 JSON error.code（细粒度 N 类）是双通道，协同非冗余

### 为什么 Decimal 用 str 而非 float
- 金融场景 float 编译期丢精度（`0.1+0.2=0.30000004`），worth/total_value 涉资金不可接受
- str 保留原文，`jq tonumber` 转换成本低于精度丢失
- 与 [[ADR-005]] 组件参数序列化对称同精神——序列化不能丢信息

### 为什么保留 unicode emoji 而非换纯文本前缀
- 1688 处 shortcode 全量替换工作量爆炸，初版不划算
- 现代 CI 终端 UTF-8 支持 unicode emoji（`❌✅`），`legacy_windows=False` 兜底 Windows
- 高频 `:x:`/`:white_check_mark:`（634 处占 38%）可在 E6 后渐进替换，不阻塞初版

### 为什么 list 空 = exit 0 但 get 未找到 = exit 1
- 对齐 REST：`GET /items` 空列表 200+`[]`，`GET /items/999` 未找到 404
- list 空=查询成功无数据（CI 可继续），get 未找到=资源不存在（CI 应告警），语义不同

### 为什么翻页用三层概念拆分
- 现状 `--page-size` 双关（stockinfo 翻页 / day·tick 当 limit），且 head/tail 不一致（stockinfo=head，day/tick=tail）
- 拆 `--limit`（截断）/ `--page-size`（翻页）/ service page（服务端）后语义干净，每参数单一职责

## Consequences

### 向后兼容
- `--page-size` 保留（仅交互翻页语义，旧脚本 `--page-size 5` 在非 TTY 退化 head 仍工作）
- ServiceResult 加 `code` 默认 `None`，538 处 `success/failure` 调用不破坏
- `.message` 字段保留不删（仅 CLI 不输出），避免破坏 service 层调用方

### Breaking change
- exit code 细分：依赖 `Exit(1)` 的脚本行为不变（业务失败仍 1），但参数错误/超时现在能返 2/124（脚本可选择性利用）
- 29 处 `result.message` → `result.error` 迁移（CLI 层，service 层不动）
- `Console()` 默认配置变 `make_console()`（emoji 跟随 isatty），非 TTY 输出 emoji 渲染行为微调

### 工作量
- E2 helper：~200 行（cli_utils.py）
- E3 迁移：4 处 Confirm
- E4 data get：~5 分支（stockinfo/day/tick/adjustfactor/sources）+ adjustfactor 截断核实
- E6 收尾：312 处 Exit(1) 重归类 + 20 处 Exit(0) 清理 + 10 个 console 实例化改工厂

## Out of Scope（显式排除，防 scope creep）
- **i18n / 中英混杂统一**：success/Error/绿色对勾混用，体量大，单独议题
- **`--quiet`/`--verbose` 等级**：`--format json` 已隐含 quiet，初版够用
- **配置持久化**（`ginkgo config set output.format json`）：等 flag 稳定后再加
- **`--width` 显式表格宽度**：非 TTY 固定 200 暂够（[[test_rich_table_width_clirunner]] 踩过）
- **1688 处 emoji shortcode 全量替换**：仅动高频 `:x:`/`:white_check_mark:`，其余渐进
- **服务端游标分页**（百万级深翻页 `WHERE id > cursor`）：属 service/CRUD 层 epic，本 epic 仅约定 CLI 层 `--limit/--offset` 直通 service page 参数
