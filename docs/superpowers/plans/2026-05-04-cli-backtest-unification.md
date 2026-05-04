# CLI Backtest 命令统一实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `ginkgo backtest` 命令组，统一 CLI 回测入口，与 WebUI 共享 `backtest_task` 表，复用 Worker 逻辑。

**Architecture:** 新建 `backtest_cli.py` 定义 typer app（6 个命令），从 `task_processor.py` 提取通用函数供 CLI 复用。`engine run` 标记 deprecated。CLI 注册遵循 `main.py` 中 `_main_app.add_typer()` 模式。

**Tech Stack:** Python 3.12, Typer, Rich, SQLAlchemy (via DI container)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/ginkgo/client/backtest_cli.py` | Create | CLI 命令定义（typer app，6 个命令） |
| `src/ginkgo/workers/backtest_worker/task_helpers.py` | Create | 从 task_processor 提取的通用函数 |
| `src/ginkgo/workers/backtest_worker/task_processor.py` | Modify | 内部调用改为 task_helpers |
| `src/ginkgo/client/engine_cli.py` | Modify | engine run 加 deprecated 警告 |
| `main.py` | Modify | 注册 backtest 子命令 |

---

### Task 1: 提取通用逻辑到 task_helpers.py

**Files:**
- Create: `src/ginkgo/workers/backtest_worker/task_helpers.py`
- Modify: `src/ginkgo/workers/backtest_worker/task_processor.py`

从 `task_processor.py` 提取 3 个纯函数到 `task_helpers.py`，Worker 内部改为调用这些函数。

- [ ] **Step 1: 创建 task_helpers.py — build_engine_data**

```python
# src/ginkgo/workers/backtest_worker/task_helpers.py
"""
从 TaskProcessor 提取的通用回测逻辑，供 CLI 和 Worker 复用。
"""

from typing import Dict, Any
from ginkgo.libs import GLOG


def build_engine_data(config) -> Dict[str, Any]:
    """
    将 BacktestConfig 转换为 EngineAssemblyService 需要的 engine_data dict。

    Args:
        config: BacktestConfig 实例（含 start_date, end_date, initial_cash 等）

    Returns:
        engine_data dict
    """
    return {
        "name": f"BacktestEngine_{config.start_date}_{config.end_date}",
        "backtest_start_date": config.start_date,
        "backtest_end_date": config.end_date,
        "initial_capital": config.initial_cash,
        "commission_rate": config.commission_rate,
        "slippage_rate": config.slippage_rate,
        "broker": "backtest",
        "frequency": config.frequency,
    }
```

- [ ] **Step 2: 添加 load_portfolio_components 函数**

在 task_helpers.py 中追加：

```python
from ginkgo.data.containers import container as data_container
from ginkgo.enums import FILE_TYPES


def load_portfolio_components(portfolio_id: str, task_uuid: str = "cli") -> Dict[str, Any]:
    """
    从数据库获取 Portfolio 的组件配置。

    Args:
        portfolio_id: Portfolio UUID
        task_uuid: 任务标识（用于日志前缀）

    Returns:
        components dict，结构：{"strategies": [...], "sizers": [...], ...}

    Raises:
        ValueError: Portfolio 不存在或无组件
    """
    portfolio_service = data_container.services.portfolio_service()
    portfolio_result = portfolio_service.load_portfolio_with_components(portfolio_id=portfolio_id)
    if not portfolio_result.is_success() or not portfolio_result.data:
        raise ValueError(f"Portfolio {portfolio_id} not found in database")

    # 获取文件映射
    file_mapping_crud = data_container.cruds.portfolio_file_mapping()
    mappings = file_mapping_crud.find(
        filters={"portfolio_id": portfolio_id, "is_del": False}
    )
    if not mappings:
        raise ValueError(
            f"Portfolio {portfolio_id} has no component configured. "
            f"Please bind at least one strategy before running backtest."
        )

    components = {
        "strategies": [],
        "sizers": [],
        "selectors": [],
        "risk_managers": [],
        "analyzers": [],
    }

    type_mapping = {
        FILE_TYPES.STRATEGY.value: "strategies",
        FILE_TYPES.SIZER.value: "sizers",
        FILE_TYPES.SELECTOR.value: "selectors",
        FILE_TYPES.RISKMANAGER.value: "risk_managers",
        FILE_TYPES.ANALYZER.value: "analyzers",
    }

    file_crud = data_container.cruds.file()

    for mapping in mappings:
        component_type = mapping.type
        category = type_mapping.get(component_type)
        if category and category in components:
            component_name = ""
            try:
                file_records = file_crud.find(filters={"uuid": mapping.file_id})
                if file_records and len(file_records) > 0:
                    component_name = file_records[0].name
            except Exception as e:
                GLOG.ERROR(f"[{task_uuid[:8]}] Failed to get file name: {e}")

            components[category].append({
                "file_id": mapping.file_id,
                "mapping_uuid": mapping.uuid,
                "name": component_name,
                "type": component_type,
            })

    if not components.get("strategies"):
        raise ValueError(
            f"Portfolio {portfolio_id} has no strategy configured. "
            f"Please bind at least one strategy before running backtest."
        )

    strategy_names = [c["name"] for c in components["strategies"] if c.get("name")]
    GLOG.INFO(f"[{task_uuid[:8]}] Assembly: strategies={strategy_names}")
    return components


def build_portfolio_config(portfolio_id: str, portfolio_data, initial_cash: float) -> Dict[str, Any]:
    """
    从数据库结果提取 Portfolio 配置。

    Args:
        portfolio_id: Portfolio UUID
        portfolio_data: portfolio_service 返回的数据对象
        initial_cash: 初始资金

    Returns:
        portfolio_config dict
    """
    return {
        "uuid": portfolio_id,
        "name": portfolio_data.name if hasattr(portfolio_data, "name") else f"Portfolio_{portfolio_id[:8]}",
        "cash": float(portfolio_data.cash) if hasattr(portfolio_data, "cash") else initial_cash,
        "initial_capital": initial_cash,
    }
```

- [ ] **Step 3: 修改 task_processor.py 使用 task_helpers**

在 `task_processor.py` 顶部添加导入：

```python
from ginkgo.workers.backtest_worker.task_helpers import (
    build_engine_data,
    load_portfolio_components,
    build_portfolio_config,
)
```

替换 `_assemble_engine` 方法中 `engine_data` 构建部分（约 L179-189）：

```python
        # 1. 构建引擎配置（委托到 task_helpers）
        engine_data = build_engine_data(self.task.config)
        engine_data["name"] = f"BacktestEngine_{self.task.task_uuid[:8]}"
        engine_data["task_id"] = self.task.task_uuid
```

替换 `_get_portfolio_config_and_components` 方法体（约 L233-267）：

```python
    def _get_portfolio_config_and_components(self) -> tuple:
        portfolio_service = self._portfolio_service
        portfolio_result = portfolio_service.load_portfolio_with_components(
            portfolio_id=self.task.portfolio_uuid
        )
        if not portfolio_result.is_success() or not portfolio_result.data:
            raise ValueError(f"Portfolio {self.task.portfolio_uuid} not found in database")

        config = build_portfolio_config(
            self.task.portfolio_uuid,
            portfolio_result.data,
            self.task.config.initial_cash,
        )
        components = load_portfolio_components(self.task.portfolio_uuid, self.task.task_uuid)
        GLOG.INFO(f"[{self.task.task_uuid[:8]}] Loaded portfolio {self.task.portfolio_uuid} from database")
        return config, components
```

删除 `_extract_portfolio_config_from_db` 和 `_get_portfolio_components_from_db` 两个方法（已被 task_helpers 替代）。

- [ ] **Step 4: 验证 Worker 仍能正常运行**

Run: `ginkgo worker status`
Expected: Worker 正常启动，无 ImportError

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/workers/backtest_worker/task_helpers.py src/ginkgo/workers/backtest_worker/task_processor.py
git commit -m "refactor: extract backtest helpers from TaskProcessor for CLI reuse"
```

---

### Task 2: 创建 backtest_cli.py — list 和 cat 命令

**Files:**
- Create: `src/ginkgo/client/backtest_cli.py`

先实现只读命令（list/cat），风险最低，可独立验证。

- [ ] **Step 1: 创建 backtest_cli.py 基础结构和 list 命令**

```python
# src/ginkgo/client/backtest_cli.py
"""
Backtest CLI Commands - 统一回测命令入口

提供 backtest 生命周期管理：create / run / list / cat / edit / delete
"""

import json
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

console = Console(emoji=True, legacy_windows=False)
app = typer.Typer(help=":chart_with_upwards_trend: Backtest task management", rich_markup_mode="rich")


@app.command("list")
def list_tasks(
    portfolio: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio UUID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending/running/completed/failed)"),
    page_size: int = typer.Option(20, "--page-size", help="Items per page"),
    page: int = typer.Option(0, "--page", help="Page number"),
):
    """:clipboard: List backtest tasks."""
    from ginkgo.data.containers import container

    service = container.services.backtest_task_service()
    result = service.list(page=page, page_size=page_size, portfolio_id=portfolio, status=status)

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    data = result.data
    tasks = data.get("data", [])
    total = data.get("total", 0)

    if not tasks:
        console.print(":memo: No backtest tasks found.")
        return

    table = Table(title=":chart_with_upwards_trend: Backtest Tasks")
    table.add_column("UUID", style="dim", width=12)
    table.add_column("Name", style="bold", width=20)
    table.add_column("Portfolio", width=12)
    table.add_column("Status", width=12)
    table.add_column("Progress", width=8)
    table.add_column("Created", width=19)

    for task in tasks:
        uuid_str = task.uuid[:12] if hasattr(task, "uuid") else str(task.get("uuid", ""))[:12]
        name = task.name if hasattr(task, "name") else task.get("name", "")
        portfolio_id = (task.portfolio_id[:12] if hasattr(task, "portfolio_id")
                        else str(task.get("portfolio_id", ""))[:12])
        status_val = task.status if hasattr(task, "status") else task.get("status", "")
        progress = task.progress if hasattr(task, "progress") else task.get("progress", 0)
        created = str(task.create_at)[:19] if hasattr(task, "create_at") else ""

        # 状态颜色
        status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(status_val, "white")

        table.add_row(
            uuid_str,
            name[:20],
            portfolio_id,
            f"[{status_style}]{status_val}[/{status_style}]",
            f"{progress:.0%}" if isinstance(progress, (int, float)) else str(progress),
            created,
        )

    console.print(table)
    console.print(f"\n  Total: {total} tasks (Page {page}, size {page_size})")
```

- [ ] **Step 2: 添加 cat 命令**

追加到 backtest_cli.py：

```python
@app.command("cat")
def cat_task(
    task_id: str = typer.Argument(help="Task UUID"),
):
    """:mag: Show backtest task details."""
    from ginkgo.data.containers import container

    service = container.services.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    task = result.data

    # 基本信息
    info_lines = []
    info_lines.append(f"[bold]UUID:[/bold]         {task.uuid}")
    info_lines.append(f"[bold]Name:[/bold]         {task.name}")
    info_lines.append(f"[bold]Portfolio:[/bold]    {task.portfolio_id}")
    status_val = task.status
    status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(status_val, "white")
    info_lines.append(f"[bold]Status:[/bold]       [{status_style}]{status_val}[/{status_style}]")
    info_lines.append(f"[bold]Created:[/bold]      {task.create_at}")

    if hasattr(task, "started_at") and task.started_at:
        info_lines.append(f"[bold]Started:[/bold]      {task.started_at}")
    if hasattr(task, "completed_at") and task.completed_at:
        info_lines.append(f"[bold]Completed:[/bold]    {task.completed_at}")

    console.print(Panel("\n".join(info_lines), title=f":mag: Task {task.uuid[:12]}"))

    # 配置信息
    if hasattr(task, "config_snapshot") and task.config_snapshot:
        try:
            config = json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot
            config_lines = []
            config_lines.append(f"[bold]Start Date:[/bold]     {config.get('start_date', 'N/A')}")
            config_lines.append(f"[bold]End Date:[/bold]       {config.get('end_date', 'N/A')}")
            config_lines.append(f"[bold]Initial Cash:[/bold]   {config.get('initial_cash', 'N/A')}")
            config_lines.append(f"[bold]Commission:[/bold]     {config.get('commission_rate', 'N/A')}")
            config_lines.append(f"[bold]Slippage:[/bold]       {config.get('slippage_rate', 'N/A')}")
            config_lines.append(f"[bold]Frequency:[/bold]      {config.get('frequency', 'N/A')}")
            console.print(Panel("\n".join(config_lines), title=":gear: Configuration"))
        except (json.JSONDecodeError, TypeError):
            console.print(f"[dim]Config snapshot: {task.config_snapshot[:200]}")

    # 结果信息
    if hasattr(task, "result") and task.result:
        try:
            result_data = json.loads(task.result) if isinstance(task.result, str) else task.result
            result_lines = []
            for key, value in result_data.items():
                if isinstance(value, float):
                    result_lines.append(f"[bold]{key}:[/bold] {value:.4f}")
                else:
                    result_lines.append(f"[bold]{key}:[/bold] {value}")
            if result_lines:
                console.print(Panel("\n".join(result_lines), title=":bar_chart: Results"))
        except (json.JSONDecodeError, TypeError):
            console.print(f"[dim]Result: {str(task.result)[:200]}")
```

- [ ] **Step 3: 在 main.py 注册 backtest 子命令**

在 `main.py` L132 的 import 行添加 `backtest_cli`：

```python
from ginkgo.client import data_cli, engine_cli, portfolio_cli, param_cli, kafka_cli, worker_cli, mongo_cli, user_cli, group_cli, templates_cli, notify_cli, livecore_cli, execution_cli, scheduler_cli, tasktimer_cli, config_cli, serve_cli, logging_cli, deploy_cli, backtest_cli
```

在 L151 之后（`deploy_cli` 行之后）添加：

```python
    _main_app.add_typer(backtest_cli.app, name="backtest", help=":chart_with_upwards_trend: Backtest task management")
```

- [ ] **Step 4: 验证 list 和 cat 命令**

Run: `ginkgo backtest list`
Expected: Rich 表格显示回测任务列表（含 WebUI 创建的任务）

Run: `ginkgo backtest cat <existing_task_id>`
Expected: Panel 显示任务详情（配置 + 结果）

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/client/backtest_cli.py main.py
git commit -m "feat: add ginkgo backtest list/cat commands"
```

---

### Task 3: 添加 backtest create 命令

**Files:**
- Modify: `src/ginkgo/client/backtest_cli.py`

- [ ] **Step 1: 添加 create 命令**

在 backtest_cli.py 中（`cat` 命令之前）添加：

```python
@app.command("create")
def create_task(
    portfolio: str = typer.Option(..., "--portfolio", "-p", help="Portfolio UUID (required)"),
    start: str = typer.Option(..., "--start", help="Backtest start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="Backtest end date (YYYY-MM-DD)"),
    cash: float = typer.Option(100000, "--cash", help="Initial capital (default: 100000)"),
    commission: float = typer.Option(0.0003, "--commission", help="Commission rate"),
    slippage: float = typer.Option(0.0001, "--slippage", help="Slippage rate"),
    frequency: str = typer.Option("DAY", "--frequency", help="Frequency (DAY/HOUR/MINUTE)"),
    name: Optional[str] = typer.Option(None, "--name", help="Task name"),
):
    """:plus: Create a backtest task."""
    from ginkgo.data.containers import container

    # 校验 portfolio 存在
    portfolio_service = container.services.portfolio_service()
    portfolio_result = portfolio_service.get_by_id(portfolio)
    if not portfolio_result.is_success():
        console.print(f":x: Portfolio not found: {portfolio}")
        raise typer.Exit(1)

    # 校验 portfolio 有组件绑定
    try:
        from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components
        load_portfolio_components(portfolio, "cli-create")
    except ValueError as e:
        console.print(f":x: {e}")
        raise typer.Exit(1)

    # 构建 config_snapshot（与 WebUI 一致）
    config_snapshot = {
        "start_date": start,
        "end_date": end,
        "initial_cash": cash,
        "commission_rate": commission,
        "slippage_rate": slippage,
        "frequency": frequency,
        "portfolio_uuids": [portfolio],
        "analyzers": [],
        "broker_type": "backtest",
    }

    task_name = name or f"Backtest {start}~{end}"

    service = container.services.backtest_task_service()
    result = service.create(
        name=task_name,
        portfolio_id=portfolio,
        config_snapshot=config_snapshot,
    )

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    task = result.data
    task_uuid = task.uuid if hasattr(task, "uuid") else str(task)
    console.print(f":white_check_mark: Backtest task created: [bold green]{task_uuid}[/bold green]")
    console.print(f"   Run with: [cyan]ginkgo backtest run {task_uuid}[/cyan]")
```

- [ ] **Step 2: 验证 create 命令**

Run: `ginkgo backtest create --portfolio bb739b51f0634fb0b4403298443b516d --start 2024-01-01 --end 2024-12-31`
Expected: 输出 task_id，`ginkgo backtest list` 可见新任务

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/client/backtest_cli.py
git commit -m "feat: add ginkgo backtest create command"
```

---

### Task 4: 添加 backtest run 命令

**Files:**
- Modify: `src/ginkgo/client/backtest_cli.py`

核心命令：读取 backtest_task → 构建引擎 → 本地执行 → 写回结果。

- [ ] **Step 1: 添加 run 命令**

在 backtest_cli.py 中添加：

```python
@app.command("run")
def run_task(
    task_id: str = typer.Argument(help="Task UUID to run"),
    bg: bool = typer.Option(False, "--bg", help="Run in background"),
):
    """:rocket: Run a backtest task locally."""
    import threading
    from ginkgo.data.containers import container
    from ginkgo.workers.backtest_worker.models import BacktestConfig
    from ginkgo.workers.backtest_worker.task_helpers import (
        build_engine_data,
        load_portfolio_components,
        build_portfolio_config,
    )
    from ginkgo.trading.services._assembly.task_engine_builder import TaskEngineBuilder
    from ginkgo.libs import GinkgoLogger
    from ginkgo.trading.time.clock import now as clock_now
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

    service = container.services.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    task = result.data

    # 解析 config_snapshot → BacktestConfig
    import json as _json
    config_snapshot = _json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot
    config = BacktestConfig(
        start_date=config_snapshot.get("start_date", "2024-01-01"),
        end_date=config_snapshot.get("end_date", "2024-12-31"),
        initial_cash=config_snapshot.get("initial_cash", 100000),
        commission_rate=config_snapshot.get("commission_rate", 0.0003),
        slippage_rate=config_snapshot.get("slippage_rate", 0.0001),
        frequency=config_snapshot.get("frequency", "DAY"),
    )

    portfolio_uuid = task.portfolio_id

    # 更新状态为 running
    service.update_status(task.uuid, "running")

    console.print(f":rocket: Starting backtest: [bold]{task.name}[/bold]")
    console.print(f"   Period: {config.start_date} ~ {config.end_date}")
    console.print(f"   Capital: {config.initial_cash}")
    console.print(f"   Portfolio: {portfolio_uuid[:12]}")
    console.print()

    try:
        # 1. 构建 engine_data
        engine_data = build_engine_data(config)
        engine_data["name"] = f"BacktestEngine_{task.uuid[:8]}"
        engine_data["task_id"] = task.uuid

        # 2. 加载 portfolio 配置和组件
        portfolio_service = container.services.portfolio_service()
        portfolio_result = portfolio_service.load_portfolio_with_components(portfolio_id=portfolio_uuid)
        if not portfolio_result.is_success():
            raise ValueError(f"Portfolio {portfolio_uuid} not found")

        portfolio_config = build_portfolio_config(
            portfolio_uuid, portfolio_result.data, config.initial_cash
        )
        components = load_portfolio_components(portfolio_uuid, task.uuid)

        # 3. 构建 portfolio mappings
        portfolio_mapping = type("PortfolioMapping", (), {"portfolio_id": portfolio_uuid})()
        portfolio_mappings = [portfolio_mapping]
        portfolio_configs = {portfolio_uuid: portfolio_config}
        portfolio_components_dict = {portfolio_uuid: components}

        # 4. 创建 logger
        now = clock_now().strftime("%Y%m%d%H%M%S")
        logger = GinkgoLogger(
            logger_name=f"backtest_{task.uuid[:8]}",
            file_names=[f"bt_{task.uuid[:8]}_{now}"],
            console_log=False,
        )

        # 5. 装配引擎
        assembly_service = container.services.engine_assembly_service()
        progress_value = [0.0]

        def on_progress(progress, current_date, current_time=None):
            progress_value[0] = progress

        assembly_result = assembly_service.assemble_backtest_engine(
            engine_id=task.uuid,
            engine_data=engine_data,
            portfolio_mappings=portfolio_mappings,
            portfolio_configs=portfolio_configs,
            portfolio_components=portfolio_components_dict,
            logger=logger,
            progress_callback=on_progress,
        )

        if not assembly_result.success:
            raise RuntimeError(f"Engine assembly failed: {assembly_result.error}")

        engine = assembly_result.data

        # 6. 执行回测
        if bg:
            # 后台运行
            def _run_in_thread():
                try:
                    engine.start()
                    _save_results(service, task.uuid, engine, portfolio_uuid)
                    console.print(f":white_check_mark: Backtest completed: {task.uuid[:12]}")
                except Exception as e:
                    service.update_status(task.uuid, "failed", error_message=str(e))
                    console.print(f":x: Backtest failed: {e}")

            thread = threading.Thread(target=_run_in_thread, daemon=True)
            thread.start()
            console.print(f":hourglass: Backtest running in background (thread)")
        else:
            # 前台运行，带进度条
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console,
            ) as progress:
                prog_task = progress.add_task("Running backtest...", total=100)

                def _progress_wrapper(p, cd, ct=None):
                    on_progress(p, cd, ct)
                    progress.update(prog_task, completed=int(p * 100))

                engine._progress_callback = _progress_wrapper
                engine.start()

            # 7. 保存结果
            _save_results(service, task.uuid, engine, portfolio_uuid)
            console.print(f":white_check_mark: Backtest completed: [bold green]{task.uuid[:12]}[/bold green]")

    except Exception as e:
        service.update_status(task.uuid, "failed", error_message=str(e))
        console.print(f":x: Backtest failed: {e}")
        raise typer.Exit(1)


def _save_results(service, task_uuid: str, engine, portfolio_id: str):
    """保存回测结果到 backtest_task 表。"""
    try:
        # 从引擎获取基本结果
        result_data = {
            "status": "completed",
        }

        # 尝试从 analyzer 获取详细指标
        try:
            from ginkgo.data.containers import container
            analyzer_crud = container.cruds.analyzer_record()
            records = analyzer_crud.find(
                filters={"portfolio_id": portfolio_id, "source": 15},
            )
            if records:
                import pandas as pd
                df = records.to_dataframe() if hasattr(records, "to_dataframe") else pd.DataFrame()
                if not df.empty and "net_value" in df.columns:
                    result_data["final_net_value"] = float(df["net_value"].iloc[-1])
                    result_data["total_return"] = (float(df["net_value"].iloc[-1]) / 100000 - 1)
                if not df.empty and "pnl" in df.columns:
                    result_data["total_pnl"] = float(df["pnl"].sum())
        except Exception:
            pass

        service.update_status(
            task_uuid,
            "completed",
        )
        # 将结果 JSON 存入 result 字段
        import json
        service.update(task_uuid, result=json.dumps(result_data))

    except Exception as e:
        from ginkgo.libs import GLOG
        GLOG.ERROR(f"Failed to save results for {task_uuid[:8]}: {e}")
```

- [ ] **Step 2: 验证 run 命令**

Run: `ginkgo backtest run <task_id_from_create>`
Expected: 进度条运行，完成后 `ginkgo backtest cat <task_id>` 显示结果

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/client/backtest_cli.py
git commit -m "feat: add ginkgo backtest run command with local execution"
```

---

### Task 5: 添加 edit 和 delete 命令

**Files:**
- Modify: `src/ginkgo/client/backtest_cli.py`

- [ ] **Step 1: 添加 edit 命令**

追加到 backtest_cli.py（`_save_results` 之前）：

```python
@app.command("edit")
def edit_task(
    task_id: str = typer.Argument(help="Task UUID to edit"),
    start: Optional[str] = typer.Option(None, "--start", help="New start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, "--end", help="New end date (YYYY-MM-DD)"),
    cash: Optional[float] = typer.Option(None, "--cash", help="New initial capital"),
    commission: Optional[float] = typer.Option(None, "--commission", help="New commission rate"),
    slippage: Optional[float] = typer.Option(None, "--slippage", help="New slippage rate"),
    name: Optional[str] = typer.Option(None, "--name", help="New task name"),
):
    """:pencil2: Edit an uncompleted backtest task."""
    import json
    from ginkgo.data.containers import container

    service = container.services.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    task = result.data

    # 检查状态
    status_val = task.status if hasattr(task, "status") else ""
    if status_val == "completed":
        console.print(":x: Cannot edit a completed task.")
        raise typer.Exit(1)

    # 更新 config_snapshot
    config_snapshot = json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot

    if start:
        config_snapshot["start_date"] = start
    if end:
        config_snapshot["end_date"] = end
    if cash is not None:
        config_snapshot["initial_cash"] = cash
    if commission is not None:
        config_snapshot["commission_rate"] = commission
    if slippage is not None:
        config_snapshot["slippage_rate"] = slippage

    updates = {"config_snapshot": json.dumps(config_snapshot)}
    if name:
        updates["name"] = name

    update_result = service.update(task.uuid, **updates)

    if not update_result.is_success():
        console.print(f":x: {update_result.message}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task.uuid[:12]}[/bold] updated.")
```

- [ ] **Step 2: 添加 delete 命令**

追加到 backtest_cli.py：

```python
@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(help="Task UUID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """:wastebasket: Delete a backtest task (soft delete)."""
    from ginkgo.data.containers import container

    service = container.services.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.message}")
        raise typer.Exit(1)

    task = result.data
    task_name = task.name if hasattr(task, "name") else task_id
    task_uuid = task.uuid if hasattr(task, "uuid") else task_id

    if not confirm:
        confirmed = typer.confirm(f"Delete task '{task_name}' ({task_uuid[:12]})?")
        if not confirmed:
            console.print("Cancelled.")
            return

    delete_result = service.update(task_uuid, is_del=True)

    if not delete_result.is_success():
        console.print(f":x: {delete_result.message}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task_uuid[:12]}[/bold] deleted.")
```

- [ ] **Step 3: 验证 edit 和 delete**

Run: `ginkgo backtest edit <task_id> --cash 200000`
Expected: `ginkgo backtest cat <task_id>` 显示更新后的 initial_cash

Run: `ginkgo backtest delete <task_id> --yes`
Expected: 任务从 list 中消失

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/client/backtest_cli.py
git commit -m "feat: add ginkgo backtest edit/delete commands"
```

---

### Task 6: engine run 添加 deprecated 警告

**Files:**
- Modify: `src/ginkgo/client/engine_cli.py`

- [ ] **Step 1: 在 engine run 命令入口添加 deprecated 警告**

在 `engine_cli.py` 的 `run` 函数体开头（约 L371，`if engine_id:` 之前）插入：

```python
    # Deprecated warning
    console.print(":warning: [bold yellow]Deprecated:[/bold yellow] 'ginkgo engine run' will be removed in a future version.")
    console.print("   Use [cyan]'ginkgo backtest run <task_id>'[/cyan] instead.")
    console.print()
```

- [ ] **Step 2: 验证 deprecated 警告**

Run: `ginkgo engine run <engine_id>`
Expected: 命令开头显示黄色 deprecated 警告，随后正常执行

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/client/engine_cli.py
git commit -m "feat: add deprecated warning to ginkgo engine run"
```

---

### Task 7: 端到端验证

**Files:** 无代码修改，仅验证。

- [ ] **Step 1: 验证 create → run → cat 完整流程**

```bash
# 开启 debug 模式
ginkgo debug on

# 创建回测任务
ginkgo backtest create --portfolio bb739b51f0634fb0b4403298443b516d --start 2024-01-01 --end 2024-03-31 --name "CLI e2e test"

# 记录输出的 task_id，执行回测
ginkgo backtest run <task_id>

# 查看结果
ginkgo backtest cat <task_id>
```

Expected: 回测正常运行，cat 显示 completed 状态和结果指标。

- [ ] **Step 2: 验证 CLI 创建的任务在 WebUI 可见**

在浏览器打开 WebUI → Portfolio bb739b51 → Backtest Tab。
Expected: 列表中出现 "CLI e2e test" 任务，状态与 CLI 一致。

- [ ] **Step 3: 验证 WebUI 创建的任务可通过 CLI 操作**

在 WebUI 创建一个回测任务，然后用 CLI：
```bash
ginkgo backtest list
ginkgo backtest cat <webui_task_id>
ginkgo backtest run <webui_task_id>
```

Expected: CLI 可正常列出、查看、执行 WebUI 创建的任务。

- [ ] **Step 4: 验证 engine run deprecated 警告**

```bash
ginkgo engine run <engine_id>
```

Expected: 显示 deprecated 警告后正常执行。
