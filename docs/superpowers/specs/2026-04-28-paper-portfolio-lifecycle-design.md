# Paper Portfolio 生命周期管理设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 修复 PAPER/LIVE portfolio 部署后无法运行的断裂链路，补全从 deploy → run → stop → delete 的完整生命周期管理。

**Architecture:** Service 层封装完整业务方法（含 Kafka 通知），Worker 侧负责 RUNNING/STOPPED 状态转换，统一 Kafka 消息格式为 ControlCommand DTO。

**Tech Stack:** Python, dependency_injector, Kafka (GinkgoProducer/Consumer), Vue 3 + Ant Design Vue

---

## 缺陷分析

### 当前链路断裂

API `POST /api/v1/deploy/` 部署流程：
```
用户点击部署 → Saga → DeploymentService.deploy() → 创建 DB 记录 → 返回成功
                                    ↑
                               到此结束，无后续
```

- 不发送 Kafka deploy 命令，PaperTradingWorker 不知道有新 portfolio
- portfolio `state` 永远停留在 `INITIALIZED(0)`
- 前端显示"未启动"

### CLI 消息格式 Bug

CLI `_send_deploy_notification()` 发送：
```python
{"command": "deploy", "portfolio_id": "xxx", "timestamp": "..."}
```
Worker 读取 `params.get("portfolio_id")` → 读不到，portfolio_id 在顶层而非 params 内。

### 缺失的保护

`portfolio_service.delete()` 不检查运行状态，可以删除正在 Worker 中运行的 portfolio，导致内存中残留僵尸 portfolio。

---

## 设计

### 1. 统一 Kafka 消息格式

**改造 `ControlCommand`（`src/ginkgo/messages/control_command.py`）**

现有 `ControlCommand` dataclass 无人使用，字段名与实际 Kafka 消费格式不匹配。

**改动要点：**
- 主字段 `command_type` → `command: str`（与 Worker 消费端对齐）
- 移除 `target_id`，portfolio_id 统一放 `params` 内
- `to_dict()` 输出格式：`{"command": "...", "params": {...}, "timestamp": "..."}`
- 新增工厂方法：
  - `ControlCommand.deploy(portfolio_id)` → `{"command": "deploy", "params": {"portfolio_id": "xxx"}, "timestamp": "..."}`
  - `ControlCommand.unload(portfolio_id)` → `{"command": "unload", "params": {"portfolio_id": "xxx"}, "timestamp": "..."}`
  - `ControlCommand.daily_cycle()` → `{"command": "paper_trading", "params": {}, "timestamp": "..."}`
- 新增 `from_dict()` 解析，Worker 消费端统一使用

**所有发送方改用 `ControlCommand` 工厂方法：**
- `DeploymentService.deploy()` — 使用 `ControlCommand.deploy()`
- `PortfolioService.stop()` — 使用 `ControlCommand.unload()`
- `api/trading.py` start/stop — 改用 Service 方法，不再直接构造 dict
- `portfolio_cli.py` — 改用 Service 方法，删除 `_send_deploy_notification()` / `_send_unload_command()`

### 2. Portfolio 生命周期状态机

```
INITIALIZED(0)  ← 创建时（已有）
       ↓  Worker _handle_deploy()
RUNNING(1)
       ↓  PortfolioService.stop() 设 STOPPING(3) → Worker _handle_unload() 设 STOPPED(4)
STOPPED(4)
       ↓  PortfolioService.delete() 检查通过后删除
（软删除）
```

**状态转换责任划分：**

| 转换 | 执行者 | 原因 |
|------|--------|------|
| → STOPPING(3) | `PortfolioService.stop()` | 调用方表达停止意图 |
| → RUNNING(1) | `PaperTradingWorker._handle_deploy()` | Worker 确认 portfolio 实际加载成功 |
| → STOPPED(4) | `PaperTradingWorker._handle_unload()` | Worker 确认 portfolio 实际卸载完成 |

### 3. Service 层方法设计

**DeploymentService.deploy()（改动）：**
- 现有 8 步 DB 操作不变
- 第 8 步之后新增第 9 步：发 Kafka deploy 命令通知 Worker
- 使用 `ControlCommand.deploy(new_portfolio_id)` 构造消息
- 延迟导入 `GinkgoProducer` 发送

**PortfolioService.stop()（新增）：**
- 校验 portfolio 存在
- 校验 mode 是 PAPER/LIVE（BACKTEST 不走这条路径）
- 校验 state 不是 STOPPED
- 更新 DB `state=STOPPING(3)`
- 发 Kafka unload 命令（`ControlCommand.unload(portfolio_id)`）
- 延迟导入 `GinkgoProducer` 发送

**PortfolioService.delete()（改动）：**
- 在执行删除前新增检查
- `mode` 为 PAPER/LIVE 且 `state` 为 RUNNING/STOPPING → 返回 ServiceResult.error()

**Kafka 依赖方式：**
- Service 方法内 `from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer` 延迟导入
- 不注入构造函数（避免 DI 容器膨胀，与 Worker 中的使用模式一致）

### 4. API 层改动

**api/trading.py 的 start/stop 端点废弃：**
- 现有 `POST /api/v1/paper-trading/{account_id}/start` 和 `stop` 合并到 portfolio API
- trading.py 保留路由但标记 deprecated，内部转发到 portfolio Service 方法

**api/portfolio.py（统一入口）：**
- 新增 `POST /{uuid}/start` 端点，对 PAPER/LIVE portfolio 发 Kafka deploy 命令（使用 ControlCommand.deploy()）
- 新增 `POST /{uuid}/stop` 端点，调用 `portfolio_service.stop()`
- delete 端点不变（Service 层已内含状态检查，错误会通过 ServiceResult 返回）

### 5. CLI 改动

**portfolio_cli.py：**
- 删除 `_send_deploy_notification()` / `_send_unload_command()` 辅助函数
- deploy 子命令调用 `DeploymentService.deploy()`（已含 Kafka 通知）
- stop 子命令调用 `PortfolioService.stop()`（已含 Kafka 通知）
- CLI 不再直接构造 Kafka 消息

**deploy_cli.py：** 无需改动，已调 `DeploymentService.deploy()`

### 6. Worker 改动

**PaperTradingWorker：**
- `_handle_deploy()` 加载成功后：调用 `portfolio_service.update(portfolio_id, state=RUNNING)`
- `_handle_unload()` 卸载成功后：调用 `portfolio_service.update(portfolio_id, state=STOPPED)`
- 消息解析改用 `ControlCommand.from_dict()`

### 7. 前端改动

**Portfolio 详情页：**
- PAPER/LIVE 组合显示"停止"按钮（state=RUNNING 时可用）
- 删除按钮在 RUNNING/STOPPING 状态时禁用或提示

---

## 不涉及的部分

- TaskTimer Cron 逻辑不变（仍发 `paper_trading` 命令触发日循环）
- Worker 启动时全量加载逻辑不变
- REPLAY/LIVE_PAPER 模式切换逻辑不变
- 偏差检测逻辑不变
- BACKTEST 模式的 portfolio 不受影响
