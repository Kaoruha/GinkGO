# ADR-022: 回测应用用例层（BacktestUseCase Protocol）

- **Status**: Accepted
- **Date**: 2026-07-05
- **Epic**: #6449 `mod:trading` 重构（引入应用用例层收敛回测编排）
- **关联**: ADR-016（backtest id 边界）、ADR-018（backtest assignment 契约）、#6282（preflight 数据预检）、#6483（超时如实报告）

## Context

`BacktestOrchestrator`（`src/ginkgo/trading/services/backtest_orchestrator.py`）已经统一了**引擎执行编排**（流 A：load portfolio → assemble engine → start → wait → aggregate），消除 CLI 与 worker 在引擎层的重复。但**任务编排前置逻辑**（流 B：从 task 对象出发的"用例入口"）仍未收敛：

| 职责 | 原 CLI `run_task` 行号 | 是否下沉前重复 |
|---|---|---|
| `config_snapshot` dict → `BacktestConfig`（11 行字段映射） | backtest_cli.py:185-198 | worker 路径另有等价解析 |
| preflight 数据预检 + 阻断 | backtest_cli.py:204-211 | 仅 CLI 有，worker 依赖服务层守卫 |
| 标 task `running` 状态机更新 | backtest_cli.py:214 | worker 路径另标 |
| UI 输出（rich console） | backtest_cli.py:216-220 | 仅 CLI 应有 |
| `raise typer.Exit(1)` 框架异常 | backtest_cli.py:211, 278 | 仅 CLI 应有 |

问题：
1. **业务逻辑混入 CLI 层**：config 解析、preflight、状态机更新本是用例层职责，散在 CLI 命令函数里，调用方（API/worker）无法复用同一入口。
2. **框架耦合**：preflight 阻断用 `raise typer.Exit(1)`——typer 是 CLI 框架，业务层不应依赖框架异常。`typer.Exit` 继承 `RuntimeError`，被 `except Exception` 吞成 `exit_code=0` 的陷阱（[[arch_typer_exit_swallowed_by_except_exception]]）就源于此耦合。
3. **职责漂移风险**：未来 API 或 worker 要复用"从 task 编排一次回测"这一用例，要么各自重写 config 解析（重复），要么强行调 CLI（不现实）。

`BacktestOrchestrator` 实际上**已经是事实上的 UseCase**——它有 `run()` 入口、聚合 4 个 service、对外暴露 `OrchestratorResult`。本 ADR 把这一事实**显式化**：定义 `BacktestUseCase` Protocol，并把"从 task 出发"的用例入口 `run_from_task` 固化到 Orchestrator 内。

## Decision

### 1. 定义 `BacktestUseCase` Protocol（structural typing）

`src/ginkgo/trading/services/backtest_orchestrator.py`：

```python
@runtime_checkable
class BacktestUseCase(Protocol):
    def run_from_task(
        self,
        task,
        config_snapshot: Optional[Dict] = None,
        progress_callback=None,
        timeout: Optional[float] = None,
    ) -> OrchestratorResult:
        """从 task 对象编排一次回测。"""
        ...
```

- **Protocol 而非抽象基类**：用 structural typing（鸭子类型），`BacktestOrchestrator` 无需显式继承即自动满足。未来若 API 层有别的实现，也不必继承同一基类。
- **`@runtime_checkable`**：让 `isinstance(orchestrator, BacktestUseCase)` 可用，便于依赖注入容器校验。
- **只声明 `run_from_task`**：`run()` 是引擎级原语（CLI/worker 也直接调，签名稳定），不强制在 Protocol 里。Protocol 只锁定"用例入口"这一契约。

### 2. `BacktestOrchestrator.run_from_task` 一站式入口

封装 4 步（按序）：

1. **config 解析**：`config_snapshot`（dict 或 JSON 字符串）→ `BacktestConfig`。下沉 CLI:185-198 的 11 行字段映射。
2. **preflight 数据预检**：调 `preflight_data_coverage` + `build_preflight_warning`。warning 存在时**标 task `failed` + 返回 `OrchestratorResult(success=False, error="preflight blocked: ...")`**——**不抛 typer.Exit**。下沉 CLI:204-211。
3. **标 `running`**：`task_service.update_status(task.uuid, "running")`。下沉 CLI:214。
4. **委派 `run()`**：把 task.uuid / config / task.portfolio_id 传给既有 `run()`，复用流 A 编排。

### 3. 业务层不依赖框架异常（核心约束）

- UseCase 层永远返回 `OrchestratorResult`（业务事实：成功/失败 + 原因），**从不 raise typer.Exit**。
- CLI 是翻译层：收到 `success=False` 时自己 `raise typer.Exit(1)` + `console.print(result.error)`。
- 这让 UseCase 可被 API（HTTP）、worker（异步）、CLI（typer）三种入口无差别调用——内层不知道外层是什么框架。

### 4. CLI `run_task` 薄化

重构后 CLI 仅保留：task 解析（含模糊匹配 UI）→ 构造 orchestrator → 委派 `run_from_task` → 翻译结果为 typer.Exit/console 输出。删除：config 解析（11 行）、preflight 调用、标 running。

## Consequences

**正面**：
- 回测用例入口统一：CLI/API/worker 调 `run_from_task`，config 解析/preflight/状态机不再重复。
- 业务层与框架解耦：UseCase 不知 typer 存在，避开 `typer.Exit` 被 `except Exception` 吞的陷阱。
- Protocol 让"UseCase 契约"显式化、可校验、可替换实现。
- preflight 从 CLI UX 阻断升级为业务用例契约——worker 路径未来也可受益（当前 worker 走 `run()` 直连，不经 `run_from_task`，不在本 ADR 范围）。

**负面 / 权衡**：
- `run_from_task` 在 bg（后台线程）模式下，"标 running"发生在子线程而非主线程——比原 CLI 主线程标 running 稍晚。这是 bg 模式本来的异步语义，可接受。
- `BacktestConfig` 仍是函数级 import（`run_from_task` 内部 import），保持快启——不拖累 orchestrator 模块加载。
- preflight 失败的 UI 文本从原 rich `:warning:` emoji 变成纯 error 字符串——视觉略损失，但与 ADR-021 的"非 TTY plain text"方向一致。

**未收敛点（另开 issue，不在本 ADR 范围）**：
- `BacktestTaskService.start_task`（流 B 的另一半：状态机检查 + 9 表清理 + Kafka 派发）220 行函数体揉合 4 职责，是真正未收敛的窄点。本 ADR 不动它（Kafka 派发是 worker 路径语义，与 UseCase 层正交）。

## Alternatives considered

- **A. 新建 `BacktestUseCase` 类，组合 Orchestrator**：增加一层间接，Orchestrator 已是事实 UseCase，多此一举。**否决**。
- **B. 把 preflight 留在 CLI，不下沉**：worker 路径未来无法复用；且 preflight 是业务用例的一部分（数据不足不应启动回测），归 CLI 不合理。**否决**（用户选择"preflight 也下沉"）。
- **C. `run_from_task` 直接调 `start_task` + 流 A**：把流 B 也并入。范围过大，且 `start_task` 含 Kafka 派发语义，与同步用例入口冲突。**否决**，另开 issue。

## 实证锚点

- `src/ginkgo/trading/services/backtest_orchestrator.py`：Protocol 定义 + `run_from_task` 实现
- `src/ginkgo/client/backtest_cli.py`：CLI 薄化（删除 config 解析/preflight/标 running 11+8+1 行）
- `tests/unit/trading/services/test_backtest_orchestrator.py`：4 个 slice 覆盖 Protocol 符合性 + config 解析 + 标 running + preflight 阻断不抛异常
