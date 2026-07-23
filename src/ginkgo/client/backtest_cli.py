# Upstream: CLI入口 (ginkgo backtest命令)
# Downstream: BacktestTaskService, container.backtest_task_service()
# Role: 回测任务CLI命令 — list/cat

"""
Backtest CLI Commands - 统一回测命令入口
"""

import json
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.client.cli_utils import build_list_result, format_result

console = Console(emoji=True, legacy_windows=False)
app = typer.Typer(
    help=":chart_with_upwards_trend: Backtest task management",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


def _display_progress(status_val, raw_progress):
    """completed 状态语义上进度必为 100%。

    #5996: 旧任务 DB progress 字段可能为 0（完成回调未覆盖历史数据），
    但 status==completed 时进度语义上必然完成，CLI 输出层兜底显示 100%，
    而非原样输出 DB 里的陈旧 0%。
    """
    if str(status_val).lower() == "completed":
        return 100
    return raw_progress


def _emit_backtest_failure(result):
    """#6449 re-review #2: 回测失败时若 result.data['preflight_warning'] 有全文，印全文。

    UseCase 层(BacktestOrchestrator)把 preflight warning 全文放 data['preflight_warning']，
    error 留固定短语；翻译层(CLI)负责全文展示（master console.print(warning) 行为）。
    多标的(≥4 symbol)时含 #6282 symbol 级 `ginkgo data sync` 指引，曾因 error[:200]
    截断丢失。bg/非 bg 两失败分支共用此 helper 保对称（ADR-022 §3 不静默）。
    """
    console.print(f":x: Backtest failed: {result.error}")
    preflight_warning = (
        result.data.get("preflight_warning")
        if isinstance(result.data, dict) else None
    )
    if preflight_warning:
        console.print(preflight_warning)


def _task_record(task) -> dict:
    """序列化 backtest task 为 JSON record。

    覆盖 text 路径（cat_task）渲染的全部字段：元数据 + 回测结果 metrics +
    statistics + 执行信息。ADR-021：--format json 让机读消费者在 JSON 路径拿到
    与 text 等量的结构化回测结果，避免 text/json 信息量不对称（#6580 review）。
    _task_record 被 list/cat 共用，list 每个 record 同步带上 metrics。
    """

    def _get(name, default=None):
        # 兼容 model 实例 / MagicMock / dict（fuzzy_search 返回）
        if hasattr(task, name):
            return getattr(task, name)
        return task.get(name, default)

    status_val = _get("status", "")
    start_time = _get("start_time")
    end_time = _get("end_time")
    return {
        # 元数据
        "uuid": str(_get("uuid", "")),
        "task_id": str(_get("task_id", "")),
        "name": _get("name", ""),
        "portfolio_id": _get("portfolio_id", ""),
        "engine_id": _get("engine_id", ""),
        "status": status_val,
        "progress": _display_progress(status_val, _get("progress", 0)),
        "created_at": str(_get("create_at", "")),
        # 回测结果 metrics（text 路径 Results panel）
        "final_portfolio_value": _get("final_portfolio_value", 0.0),
        "total_pnl": _get("total_pnl", 0.0),
        "max_drawdown": _get("max_drawdown", 0.0),
        "sharpe_ratio": _get("sharpe_ratio", 0.0),
        "annual_return": _get("annual_return", 0.0),
        "win_rate": _get("win_rate", 0.0),
        # 回测统计（text 路径 Statistics panel）
        "total_signals": _get("total_signals", 0),
        "total_orders": _get("total_orders", 0),
        "total_positions": _get("total_positions", 0),
        "total_events": _get("total_events", 0),
        # 执行信息（None 原样保留，机读判 completed/failed 需要）
        "start_time": str(start_time) if start_time is not None else None,
        "end_time": str(end_time) if end_time is not None else None,
        "duration_seconds": _get("duration_seconds"),
        "error_message": _get("error_message"),
        # config_snapshot：回测配置快照（text 路径 Config panel；#6652 review E6 补齐 _task_record 覆盖声明）。
        "config_snapshot": _get("config_snapshot"),
    }


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
    from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components
    from datetime import datetime

    # 校验日期格式（#5994/#6083：仅接受 YYYY-MM-DD）
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")
    except ValueError:
        console.print(f":x: 日期格式无效，要求 YYYY-MM-DD；start={start} end={end}")
        raise typer.Exit(1)

    # 校验日期范围（#5993：end 早于 start 拒绝）
    if end_date < start_date:
        console.print(f":x: 结束日期 {end} 早于开始日期 {start}")
        raise typer.Exit(1)

    # 未来日期警告（#6009：未来日期无历史数据，警告但不阻断）
    today = datetime.now().date()
    if start_date.date() > today or end_date.date() > today:
        console.print(f":warning: 警告：start={start} 或 end={end} 为未来日期，该区间可能无历史数据")

    # 校验 cash 为正（#5983/#6004：拒绝非正现金，避免回测以零/负资金运行）
    if cash <= 0:
        console.print(f":x: cash 必须为正数，当前：{cash}")
        raise typer.Exit(1)

    # 范围外警告（#6004：极端 cash 警告但不阻断，建议合理范围 1,000~10,000,000,000）
    if cash < 1000 or cash > 10_000_000_000:
        console.print(f":warning: 警告：cash={cash} 超出建议范围（1,000~10,000,000,000），结果可能无意义")

    # 校验 portfolio 存在
    portfolio_service = container.portfolio_service()
    portfolio_result = portfolio_service.get(portfolio_id=portfolio)
    if not portfolio_result.is_success():
        console.print(f":x: Portfolio not found: {portfolio}")
        raise typer.Exit(1)

    # 校验 portfolio 有组件绑定
    try:
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

    service = container.backtest_task_service()
    result = service.create(
        name=task_name,
        portfolio_id=portfolio,
        config_snapshot=config_snapshot,
    )

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data
    task_uuid = task.uuid if hasattr(task, "uuid") else str(task)
    console.print(f":white_check_mark: Backtest task created: [bold green]{task_uuid}[/bold green]")
    console.print(f"   Run with: [cyan]ginkgo backtest run {task_uuid}[/cyan]")


def _print_remote_summary(detail) -> None:
    """从远端 task detail dict 打印关键指标（字段缺失/为空则跳过，ADR-024）。

    detail 来自 ``GET /backtest/{uuid}``（``BacktestTaskDetail.dict()``），completed 时已含
    annual_return/sharpe/max_drawdown/win_rate/total_pnl/final_portfolio_value/total_orders
    等，无需另拉 /results。
    """
    if not isinstance(detail, dict):
        return
    rows = [
        ("Annual Return", detail.get("annual_return")),
        ("Sharpe", detail.get("sharpe_ratio")),
        ("Max Drawdown", detail.get("max_drawdown")),
        ("Win Rate", detail.get("win_rate")),
        ("Total PnL", detail.get("total_pnl")),
        ("Final Value", detail.get("final_portfolio_value")),
        ("Orders", detail.get("total_orders")),
        ("Signals", detail.get("total_signals")),
    ]
    table = Table(show_header=False, box=None)
    for label, val in rows:
        if val is None or val == "":
            continue
        if isinstance(val, float):
            val = f"{val:.4f}"
        table.add_row(f"[dim]{label}[/dim]", str(val))
    if table.row_count:
        console.print(table)


def _run_remote_backtest(task_id: str, bg: bool = False, timeout: Optional[int] = None) -> None:
    """client 模式 backtest run：提交到远端 + 轮询 + 打印（ADR-024 命令级分支）。

    与本地 ``BacktestOrchestrator`` 路径对偶：零本地计算，全部交远端 BacktestWorker。
    ``--bg`` 语义对齐本地（提交后即返回，不阻塞 CLI），非 bg 则同步轮询到终态。

    ``timeout``（秒）：非 bg 时轮询上限，到点未终态则返回当前 status + 提示稍后 ``backtest cat``
    查询，避免 CLI 无限阻塞（ADR-024 Consequences：远端 worker 跑长回测，CLI 不应挂死）。
    ``None`` / ``<=0`` 表示不限（旧行为，仅显式 ``--timeout 0`` 触发）。
    """
    from ginkgo.client.remote.services import RemoteBacktestRunner

    runner = RemoteBacktestRunner()
    poll_timeout = timeout if (timeout is not None and timeout > 0) else None
    try:
        console.print(f":rocket: Submitting backtest [bold]{task_id}[/bold] to remote server...")
        # best-effort banner：先取详情印 name（取不到不阻塞提交）
        try:
            head = runner.get_status(task_id)
            if isinstance(head, dict) and head.get("name"):
                console.print(f"   Name: {head['name']}")
        except Exception:
            pass

        if bg:
            runner.submit(task_id)
            console.print(
                f":hourglass: Submitted to remote. Poll status: "
                f"[cyan]ginkgo backtest cat {task_id}[/cyan]"
            )
            return

        def _on_progress(status, detail):
            progress = detail.get("progress") if isinstance(detail, dict) else None
            tag = str(status) + (
                f" ({progress:.0f}%)" if isinstance(progress, (int, float)) else ""
            )
            console.print(f"   status: [cyan]{tag}[/cyan]")

        state, detail, _results = runner.run(
            task_id, on_progress=_on_progress, timeout=poll_timeout
        )
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f":x: Remote backtest failed: {e}")
        raise typer.Exit(1)

    if state == "completed":
        console.print(f":white_check_mark: Backtest completed: [bold green]{task_id[:12]}[/bold green]")
        _print_remote_summary(detail)
    elif state == "failed":
        msg = detail.get("error_message") if isinstance(detail, dict) else None
        console.print(f":x: Backtest failed: {msg or 'see server logs'}")
        raise typer.Exit(1)
    elif state == "stopped":
        console.print(":stop_sign: Backtest stopped")
        raise typer.Exit(1)
    else:
        console.print(
            f":hourglass: Backtest still {state} (poll timed out). "
            f"Check later: [cyan]ginkgo backtest cat {task_id}[/cyan]"
        )
        raise typer.Exit(1)


@app.command("run")
def run_task(
    task_id: str = typer.Argument(help="Task UUID to run"),
    bg: bool = typer.Option(False, "--bg", help="Run in background thread"),
    remote: bool = typer.Option(
        False, "--remote",
        help="Submit to the server worker + poll (control plane API). Default runs the engine locally.",
    ),
    timeout: int = typer.Option(
        3600, "--timeout",
        help="Remote poll timeout in seconds (--remote only). Default 3600 (1h); 0 = no limit. "
             "On timeout the CLI returns non-terminal status — poll later with `backtest cat`.",
    ),
):
    """:rocket: Run a backtest task. Default runs the engine locally — in client mode the engine
    reads/writes the server DB directly via the data plane (ADR-024 hybrid). Pass --remote to submit
    to the server worker instead."""
    import json as _json
    import threading
    from ginkgo import services
    from ginkgo.data.containers import container

    # ADR-024 混合架构：默认本地跑引擎（数据面直连配置的 DB；client 模式 GCONF 指向 A 的 DB，
    # 引擎经 datafeeder 读 A、经 result_service 写 A，零代码改）。--remote 走控制面 API，
    # 提交到 A 的 worker + 轮询。run 是 UseCase 编排（orchestrator+progress+aggregator），
    # 非单一 service 方法，无法代理 → 命令级分支（ADR-022 §3 不静默）。
    if remote:
        _run_remote_backtest(task_id, bg=bg, timeout=timeout)
        return

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        # 精确匹配失败，尝试模糊匹配
        fuzzy_result = service.fuzzy_search(task_id)
        if fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) == 1:
            result = ServiceResult.success(fuzzy_result.data[0])
        elif fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) > 1:
            console.print(f"[yellow]Found {len(fuzzy_result.data)} matching tasks:[/yellow]\n")
            table = Table(show_header=True, header_style="bold")
            table.add_column("UUID", style="cyan")
            table.add_column("Name")
            table.add_column("Status")
            for t in fuzzy_result.data:
                table.add_row(
                    t.uuid[:12] + "...",
                    t.name or "-",
                    t.status or "-",
                )
            console.print(table)
            console.print(f"\n[yellow]Please use a more specific UUID.[/yellow]")
            raise typer.Exit(1)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data

    # #6449: 委派 UseCase 层（BacktestOrchestrator.run_from_task）。
    # config 解析 / preflight 数据预检 / 标 running 全部由 UseCase 层统一处理，
    # CLI 仅做 task 解析 + UI 输出 + 框架异常翻译。业务层报"事实"
    # （OrchestratorResult.success=False + 原因），CLI 翻译为 typer.Exit。
    try:
        from ginkgo.trading.services.backtest_orchestrator import BacktestOrchestrator
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

        orchestrator = BacktestOrchestrator(
            assembly_service=(
                container.engine_assembly_service()
                if hasattr(container, "engine_assembly_service")
                else services.trading.services.engine_assembly_service()
            ),
            portfolio_service=container.portfolio_service(),
            task_service=service,
            result_aggregator=BacktestResultAggregator(
                analyzer_service=container.analyzer_service(),
                backtest_task_service=service,
            ),
        )

        def _progress_callback(progress: float, current_date: str):
            service.update_progress(
                task.uuid,
                progress=progress,
                current_stage="RUNNING",
                current_date=current_date,
            )

        # #6449 review fix: 补回 master 启动 banner（Period/Capital/Portfolio）。
        # config 已下沉到 run_from_task，banner 仅需 UI 字段，从 task.config_snapshot
        # 轻量取值；完整 BacktestConfig 解析仍由 UseCase 层负责，避免重复构造。
        # 解析损坏时退化 '?'；run_from_task 会抛 JSONDecodeError 进下方 except 兜底。
        try:
            _snap = _json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else (task.config_snapshot or {})
        except Exception:
            _snap = {}
        console.print(f":rocket: Starting backtest: [bold]{task.name}[/bold]")
        console.print(f"   Period: {_snap.get('start_date', '?')} ~ {_snap.get('end_date', '?')}")
        console.print(f"   Capital: {_snap.get('initial_cash', '?')}")
        console.print(f"   Portfolio: {(task.portfolio_id or '?')[:12]}")
        console.print()

        if bg:

            def _run_in_thread():
                # #6449 re-review 守卫：bg 线程内 run_from_task 在到达自带 try/except 的
                # self.run() 之前有未包裹抛异常路径（_json.loads / preflight_data_coverage
                # DB 不可达 / BacktestConfig 构造）。master 把这些放主线程同步执行从不触发；
                # 本 PR 下沉进 bg 线程，须镜像非 bg 路径（L255 except Exception）标 failed +
                # 印原因，否则线程静默死亡、CLI exit 0、task 卡 pending（ADR-022 §3 不静默）。
                try:
                    result = orchestrator.run_from_task(
                        task, progress_callback=_progress_callback,
                    )
                except Exception as e:
                    service.update_status(task.uuid, "failed", error_message=str(e))
                    console.print(f":x: Backtest failed: {e}")
                    return
                if result.is_success():
                    service.update_progress(
                        task.uuid,
                        progress=100,
                        current_stage="FINALIZING",
                        current_date=str(result.data.get("backtest_end_date", "")) if isinstance(result.data, dict) else "",
                    )
                    console.print(f":white_check_mark: Backtest completed: {task.uuid[:12]}")

                    # 灌入日志到 ClickHouse（静默降级）—— 镜像非 bg 路径 (L279-288)，
                    # 否则 --bg 回测日志不灌入、logging logs --task 恒空
                    # （#5293 在 --bg 场景仍复现，#6564 review 曾标范围外）。
                    try:
                        from ginkgo.services.logging.log_ingester import LogIngester
                        ingester = LogIngester()
                        ingest_result = ingester.ingest_task_logs(task.uuid)
                        if ingest_result.inserted > 0:
                            console.print(f"   Logs ingested: {ingest_result.inserted} records")
                    except Exception as e:
                        GLOG.WARNING(f"{e}")
                else:
                    _emit_backtest_failure(result)

            thread = threading.Thread(target=_run_in_thread, daemon=True)
            thread.start()
            console.print(f":hourglass: Backtest running in background (thread)")
        else:
            result = orchestrator.run_from_task(
                task, progress_callback=_progress_callback,
            )

            if not result.is_success():
                _emit_backtest_failure(result)
                raise typer.Exit(1)

            service.update_progress(
                task.uuid,
                progress=100,
                current_stage="FINALIZING",
                current_date=str(result.data.get("backtest_end_date", "")) if isinstance(result.data, dict) else "",
            )

            # 灌入日志到 ClickHouse（静默降级）
            try:
                from ginkgo.services.logging.log_ingester import LogIngester

                ingester = LogIngester()
                ingest_result = ingester.ingest_task_logs(task.uuid)
                if ingest_result.inserted > 0:
                    console.print(f"   Logs ingested: {ingest_result.inserted} records")
            except Exception as e:
                GLOG.WARNING(f"{e}")
                pass

            console.print(f":white_check_mark: Backtest completed: [bold green]{task.uuid[:12]}[/bold green]")

    except typer.Exit:
        # #6590/#6449 守卫：typer.Exit MRO 含 Exception，须在 except Exception 前透传，
        # 否则 L229 的 raise typer.Exit(1) 被吞，error_message 被写成 str(e)=='1' 覆盖真因。
        raise
    except Exception as e:
        service.update_status(task.uuid, "failed", error_message=str(e))
        console.print(f":x: Backtest failed: {e}")
        raise typer.Exit(1)


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
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data
    status_val = task.status if hasattr(task, "status") else ""
    if status_val == "completed":
        console.print(":x: Cannot edit a completed task.")
        raise typer.Exit(1)

    config_snapshot = (
        json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot
    )

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
        console.print(f":x: {update_result.error}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task.uuid[:12]}[/bold] updated.")


@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(help="Task UUID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", "--confirm", help="Skip confirmation"),
):
    """:wastebasket: Delete a backtest task (soft delete)."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.error}")
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
        console.print(f":x: {delete_result.error}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task_uuid[:12]}[/bold] deleted.")


@app.command("list")
def list_tasks(
    portfolio: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio UUID"),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status (pending/running/completed/failed)"
    ),
    page_size: int = typer.Option(20, "--page-size", help="Items per page (0 = all)"),
    page: int = typer.Option(0, "--page", help="Page number"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit results"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text/json"),
):
    """:clipboard: List backtest tasks."""
    from ginkgo.data.containers import container

    # #5009 契约：--page（0-based）+ --page-size（0=全量）。
    # ADR-021：参数校验失败 exit 2（BAD_PARAMS）；JSON 模式发错误 envelope（#6652 review R3-issue1）。
    if page < 0:
        if format == "json":
            format_result(ServiceResult.failure(message="--page must be >= 0", code="BAD_PARAMS"), format="json", command="list")
            raise typer.Exit(2)
        console.print("[red]:x: --page must be >= 0[/red]")
        raise typer.Exit(2)
    if page_size < 0:
        if format == "json":
            format_result(ServiceResult.failure(message="--page-size must be >= 0 (0 = all)", code="BAD_PARAMS"), format="json", command="list")
            raise typer.Exit(2)
        console.print("[red]:x: --page-size must be >= 0 (0 = all)[/red]")
        raise typer.Exit(2)

    service = container.backtest_task_service()
    effective_page_size = limit or page_size
    # ADR-021 第 1/5 维：整段包 try，JSON 模式 stdout 永远合法 JSON。
    # _task_record 逐条 DB enrichment（config_snapshot 查询）异常也走 INTERNAL envelope，非裸 traceback（#6652 review R3-issue2）。
    try:
        result = service.list(page=page, page_size=effective_page_size, portfolio_id=portfolio, status=status)

        if not result.is_success():
            # ADR-021 第 5/6 维：JSON 模式发错误 envelope + exit 1；text 模式诊断 + exit 1。
            if format == "json":
                format_result(result, format="json", command="list")
            else:
                console.print(f":x: {result.error}")
                raise typer.Exit(1)

        data = result.data
        tasks = data.get("data", [])
        total = data.get("total", 0)

        if format == "json":
            records = [_task_record(task) for task in tasks]
            json_result = build_list_result(
                records, total=total, limit=effective_page_size, offset=page * effective_page_size
            )
            format_result(json_result, format="json", command="list")
            return

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
            portfolio_id = (
                task.portfolio_id[:12] if hasattr(task, "portfolio_id") else str(task.get("portfolio_id", ""))[:12]
            )
            status_val = task.status if hasattr(task, "status") else task.get("status", "")
            raw_progress = task.progress if hasattr(task, "progress") else task.get("progress", 0)
            progress = _display_progress(status_val, raw_progress)
            created = str(task.create_at)[:19] if hasattr(task, "create_at") else ""

            status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(status_val, "white")

            table.add_row(
                uuid_str,
                name[:20],
                portfolio_id,
                f"[{status_style}]{status_val}[/{status_style}]",
                f"{int(progress)}%" if isinstance(progress, (int, float)) else str(progress),
                created,
            )

        console.print(table)
        console.print(f"\n  Total: {total} tasks (Page {page}, size {effective_page_size})")
    except typer.Exit:
        raise
    except Exception as e:
        # ADR-021 第 1/5 维：JSON 模式 stdout 永远合法 JSON（异常=INTERNAL 错误对象）+ exit 1。
        if format == "json":
            format_result(
                ServiceResult.failure(message=f"Error: {e}", code="INTERNAL"),
                format="json",
                command="list",
            )
        else:
            console.print(f":x: Error: {e}")
            raise typer.Exit(1)


@app.command("cat")
def cat_task(
    task_id: str = typer.Argument(help="Task UUID or task_id"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text/json"),
):
    """:mag: Show backtest task details."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        # 精确匹配失败，尝试模糊匹配
        fuzzy_result = service.fuzzy_search(task_id)
        if fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) == 1:
            result = ServiceResult.success(fuzzy_result.data[0])
        elif fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) > 1:
            if format == "json":
                # ADR-021 第 1/5 维：JSON 模式不发 rich table（非 JSON），改发错误 envelope + exit 1。
                candidates = ", ".join(
                    (t.uuid[:12] if hasattr(t, "uuid") else str(t.get("uuid", ""))[:12])
                    for t in fuzzy_result.data
                )
                format_result(
                    ServiceResult.failure(
                        message=f"Multiple tasks match '{task_id}': {candidates}",
                        code="VALIDATION_ERROR",
                    ),
                    format="json",
                    command="get",
                )
            else:
                console.print(f"[yellow]Fuzzy match found {len(fuzzy_result.data)} tasks:[/yellow]\n")
                table = Table(show_header=True, header_style="bold")
                table.add_column("UUID", style="cyan")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Created")
                for t in fuzzy_result.data:
                    table.add_row(
                        t.uuid[:12] + "...",
                        t.name or "-",
                        t.status or "-",
                        str(t.create_at)[:-7] if t.create_at else "-",
                    )
                console.print(table)
                console.print(f"\n[yellow]Please use a more specific identifier.[/yellow]")
                raise typer.Exit(1)

    if not result.is_success():
        if format == "json":
            format_result(
                ServiceResult.failure(message=f"Backtest task not found: {task_id}", code="NOT_FOUND"),
                format="json",
                command="get",
            )
            return
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data

    if format == "json":
        format_result(ServiceResult.success(data=_task_record(task)), format="json", command="get")
        return

    # -- Basic info --
    info_lines = []
    info_lines.append(f"[bold]UUID:[/bold]         {task.uuid}")
    info_lines.append(f"[bold]Task ID:[/bold]      {task.task_id}")
    info_lines.append(f"[dim]  \U0001f4a1 查看分析结果: ginkgo result show --run-id {task.task_id}[/dim]")
    info_lines.append(f"[bold]Name:[/bold]         {task.name}")
    info_lines.append(f"[bold]Portfolio:[/bold]    {task.portfolio_id}")
    info_lines.append(f"[bold]Engine:[/bold]       {task.engine_id}")
    status_val = task.status
    status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(status_val, "white")
    info_lines.append(f"[bold]Status:[/bold]       [{status_style}]{status_val}[/{status_style}]")
    display_progress = _display_progress(status_val, task.progress)
    info_lines.append(f"[bold]Progress:[/bold]     {display_progress}%")
    info_lines.append(f"[bold]Created:[/bold]      {task.create_at}")

    if task.start_time:
        info_lines.append(f"[bold]Started:[/bold]      {task.start_time}")
    if task.end_time:
        info_lines.append(f"[bold]Completed:[/bold]    {task.end_time}")
    if task.duration_seconds:
        info_lines.append(f"[bold]Duration:[/bold]     {task.duration_seconds}s")

    if task.error_message:
        info_lines.append(f"[bold red]Error:[/bold red]        {task.error_message[:200]}")

    console.print(Panel("\n".join(info_lines), title=f":mag: Task {task.uuid[:12]}"))

    # -- Configuration --
    if task.config_snapshot:
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

    # -- Results (direct columns, not a JSON blob) --
    result_lines = []
    metrics = [
        ("Final Value", task.final_portfolio_value),
        ("Total PnL", task.total_pnl),
        ("Max Drawdown", task.max_drawdown),
        ("Sharpe Ratio", task.sharpe_ratio),
        ("Annual Return", task.annual_return),
        ("Win Rate", task.win_rate),
    ]
    has_metrics = any(v and v != 0.0 for _, v in metrics)
    if has_metrics:
        for label, value in metrics:
            if value and value != 0.0:
                result_lines.append(f"[bold]{label}:[/bold] {value:.4f}")
        console.print(Panel("\n".join(result_lines), title=":bar_chart: Results"))

    # -- Statistics --
    stats_lines = []
    stats = [
        ("Signals", task.total_signals),
        ("Orders", task.total_orders),
        ("Positions", task.total_positions),
        ("Events", task.total_events),
    ]
    has_stats = any(v and v != 0 for _, v in stats)
    if has_stats:
        for label, value in stats:
            if value and value != 0:
                stats_lines.append(f"[bold]{label}:[/bold] {value}")
        console.print(Panel("\n".join(stats_lines), title=":1234: Statistics"))
    elif status_val == "completed":
        console.print(
            Panel(
                "[yellow]⚠️ No trades generated — selector may have returned empty symbols.[/yellow]",
                title=":warning: Warning",
            )
        )


def _save_results(service, task_uuid: str, engine, portfolio_id: str):
    """保存回测结果到 backtest_task 表（复用 BacktestResultAggregator）。"""
    try:
        from ginkgo.data.containers import container as data_container
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

        analyzer_service = data_container.analyzer_service()
        aggregator = BacktestResultAggregator(
            analyzer_service=analyzer_service,
            backtest_task_service=service,
        )
        result = aggregator.aggregate_and_save(
            task_id=task_uuid,
            portfolio_id=portfolio_id,
            engine_id=task_uuid,
            status="completed",
        )
        if not result.is_success():
            from ginkgo.libs import GLOG

            GLOG.ERROR(f"Failed to aggregate results for {task_uuid[:8]}: {result.error}")

    except Exception as e:
        from ginkgo.libs import GLOG

        GLOG.ERROR(f"Failed to save results for {task_uuid[:8]}: {e}")
