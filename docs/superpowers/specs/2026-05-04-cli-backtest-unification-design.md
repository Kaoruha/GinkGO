# CLI Backtest 命令统一设计

## 背景

当前存在两条独立的回测执行路径：

| | CLI `engine run` | WebUI → Worker |
|---|---|---|
| 配置源 | `engine` 表 + `engine_portfolio_mapping` 表 | `backtest_task` + `config_snapshot` |
| 执行方式 | 本地 `assemble_backtest_engine(engine_id=xxx)` | Kafka → Worker `assemble_backtest_engine(engine_data=...)` |
| 用户 | CLI 用户 | WebUI 用户 |

问题：
1. 两条路径不互通，CLI 无法执行 WebUI 创建的回测
2. `engine` 表无运行时消费者（实盘不用它），仅为 CLI `engine run` 服务
3. 用户需维护 engine + mapping 关系才能用 CLI 跑回测，门槛高

## 目标

1. 新增 `ginkgo backtest` 命令组，统一 CLI 回测入口
2. CLI 和 WebUI 共享 `backtest_task` 表作为唯一配置源
3. `engine run` 标记为 deprecated，引导用户迁移
4. 提取 Worker 通用逻辑供 CLI 复用

## 不在范围内

- 组件配置快照（后续独立设计）
- 实盘引擎管理（`engine` 表保留给实盘）
- `engine` 命令组移除（仅 deprecated）

## 命令设计

### `ginkgo backtest` 命令组

```
ginkgo backtest create   创建回测任务
ginkgo backtest run      执行回测
ginkgo backtest list     列出回测任务
ginkgo backtest cat      查看任务详情
ginkgo backtest edit     修改未运行任务
ginkgo backtest delete   删除任务
```

### `backtest create`

```bash
ginkgo backtest create \
  --portfolio <uuid>       # 必填，portfolio_id
  --start 2024-01-01       # 必填，回测开始日期
  --end 2024-12-31         # 必填，回测结束日期
  [--cash 100000]          # 可选，初始资金，默认 100000
  [--commission 0.0003]    # 可选，手续费率
  [--slippage 0.0001]      # 可选，滑点率
  [--name "my backtest"]   # 可选，任务名称
  [--frequency DAY]        # 可选，频率，默认 DAY
```

行为：
1. 校验 portfolio 存在且有组件绑定
2. 构建 `config_snapshot` JSON（引擎级参数）
3. 调用 `backtest_task_service.create()` 写入 `backtest_task` 表
4. 输出 task_id

`config_snapshot` 结构（与 WebUI 一致）：
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "initial_cash": 100000,
  "commission_rate": 0.0003,
  "slippage_rate": 0.0001,
  "frequency": "DAY",
  "portfolio_uuids": ["bb739b51..."],
  "analyzers": [],
  "broker_type": "backtest"
}
```

### `backtest run`

```bash
ginkgo backtest run <task_id>    # 前台运行
ginkgo backtest run <task_id> --bg  # 后台运行
```

执行流程：
1. 读 `backtest_task` 表 → 解析 `config_snapshot` → `BacktestConfig`
2. 读 `portfolio_file_mapping` + `file` 表 → 组件代码和参数
3. 调用 `assemble_backtest_engine(engine_data=...)`（方法2，与 Worker 一致）
4. `engine.start()` 执行回测
5. Rich 进度条显示实时进度
6. 结果写回 `backtest_task` 表

与 Worker 的区别：
- 不经过 Kafka，本地直接执行
- Rich 终端输出代替 Kafka 进度上报
- 单任务，无多任务调度

### `backtest list`

```bash
ginkgo backtest list [--portfolio <id>] [--status completed] [--page 20]
```

调用 `backtest_task_service.get()` 列出任务，Rich 表格显示。

### `backtest cat`

```bash
ginkgo backtest cat <task_id>
```

显示任务详情：配置参数、状态、执行时间、结果指标（PnL, sharpe, max_drawdown 等）。

### `backtest edit`

```bash
ginkgo backtest edit <task_id> --start 2024-06-01 --end 2024-12-31 --cash 200000
```

限制：只能编辑 `status != completed` 的任务。更新 `config_snapshot` JSON。

### `backtest delete`

```bash
ginkgo backtest delete <task_id>
```

软删除（`is_del=1`）。

## 代码结构

### 新增文件

```
src/ginkgo/client/backtest_cli.py          # CLI 命令定义（typer app）
```

### 修改文件

```
src/ginkgo/client/core_cli.py              # 注册 backtest 子命令
src/ginkgo/client/engine_cli.py            # engine run 加 deprecated 警告
src/ginkgo/workers/backtest_worker/task_processor.py  # 提取通用逻辑
```

### 逻辑复用

从 `task_processor.py` 提取以下方法为独立函数（放在 `task_processor.py` 或新模块）：

| 当前位置（task_processor.py） | 提取为 | 用途 |
|---|---|---|
| `_assemble_engine()` | `build_engine_data(task_config)` | 构建 engine_data dict |
| `_get_portfolio_config_and_components()` | `load_portfolio_components(portfolio_id, initial_cash)` | 加载 portfolio + 组件 |
| `_finalize_results()` | `save_backtest_results(engine, task_id, portfolio_id)` | 统计结果写表 |

CLI `backtest run` 调用这些函数，Worker 继续用 `TaskProcessor` 类但内部也调这些函数。

## `engine run` deprecated 处理

`engine run` 保留但打印警告：
```
⚠️  Deprecated: 'ginkgo engine run' will be removed in a future version.
   Use 'ginkgo backtest run <task_id>' instead.
```

不改变原有逻辑，仅加警告。

## 验证标准

1. `ginkgo backtest create --portfolio bb739b51 --start 2024-01-01 --end 2024-12-31` 成功创建 task
2. `ginkgo backtest run <task_id>` 本地执行回测，结果与 WebUI 创建的同一 portfolio 的回测一致
3. `ginkgo backtest list` 列出所有 task（含 WebUI 创建的）
4. `ginkgo backtest cat <task_id>` 显示完整配置和结果
5. `ginkgo engine run` 打印 deprecated 警告但仍可执行
