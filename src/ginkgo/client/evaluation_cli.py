# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 评估CLI提供策略评估/分析/比较/报告等命令支持回测结果的多维度性能分析






"""
Evaluation CLI

This module provides command-line interface for backtest evaluation and live monitoring.
"""

import typer
import json
from typing import Optional, List
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":chart_with_upwards_trend: Module for [bold medium_spring_green]EVALUATION[/]. [grey62]Backtest stability analysis and live monitoring.[/grey62]",
    no_args_is_help=True,
)

console = Console()


@app.command("strategy")
def evaluate_strategy(
    strategy_file: Annotated[str, typer.Argument(help=":page_facing_up: Path to the strategy file to evaluate")] = None,
    level: Annotated[str, typer.Option("--level", "-l", help=":chart: Evaluation level (basic/standard/strict)")] = "standard",
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help=":speech_balloon: Show detailed output")] = False,
    show_context: Annotated[bool, typer.Option("--show-context", "-c", help=":books: Show signal generation context analysis")] = False,
):
    """
    :mag: Evaluate a trading strategy file.

    This command validates strategy structure and logic before backtesting.

    Examples:
      ginkgo eval strategy my_strategy.py
      ginkgo eval strategy my_strategy.py --level basic
      ginkgo eval strategy my_strategy.py --show-context
      ginkgo eval strategy my_strategy.py --level strict --verbose
    """
    from pathlib import Path
    from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
    from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
    from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
    from ginkgo.trading.evaluation.rules.structural_rules import (
        StrategyBaseInheritanceRule,
        CalMethodRequiredRule,
        CalSignatureValidationRule,
        SuperInitCallRule,
    )
    from ginkgo.trading.evaluation.rules.logical_rules import (
        ReturnStatementRule,
        SignalFieldRule,
        DirectionValidationRule,
        TimeProviderUsageRule,
        ForbiddenOperationsRule,
    )
    from ginkgo.trading.evaluation.rules.best_practice_rules import (
        DecoratorUsageRule,
        ExceptionHandlingRule,
        LoggingRule,
        ResetStateRule,
        ParameterValidationRule,
    )

    # Validate level parameter
    level_map = {
        "basic": EvaluationLevel.BASIC,
        "standard": EvaluationLevel.STANDARD,
        "strict": EvaluationLevel.STRICT,
    }
    if level not in level_map:
        console.print(f":x: [red]Invalid level '{level}'. Must be one of: basic, standard, strict[/red]")
        raise typer.Exit(1)
    eval_level = level_map[level]

    # Check if file is provided
    if strategy_file is None:
        console.print("[error]Error: No strategy file specified[/error]")
        console.print("\nUsage: ginkgo eval strategy <STRATEGY_FILE> [OPTIONS]")
        raise typer.Exit(1)

    file_path = Path(strategy_file)
    if not file_path.exists():
        console.print(f":x: [red]File not found: {strategy_file}[/red]")
        raise typer.Exit(2)

    # Register default rules
    registry = get_global_registry()

    # Basic level rules
    registry.register_rule_class(
        StrategyBaseInheritanceRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        CalMethodRequiredRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        SuperInitCallRule,
        ComponentType.STRATEGY,
    )

    # Standard level rules
    registry.register_rule_class(
        CalSignatureValidationRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        ReturnStatementRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        SignalFieldRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        DirectionValidationRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        TimeProviderUsageRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        ForbiddenOperationsRule,
        ComponentType.STRATEGY,
    )

    # Strict level rules (best-practice checks; only run at --level strict)
    registry.register_rule_class(
        DecoratorUsageRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        ExceptionHandlingRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        LoggingRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        ResetStateRule,
        ComponentType.STRATEGY,
    )
    registry.register_rule_class(
        ParameterValidationRule,
        ComponentType.STRATEGY,
    )

    # Create evaluator and run evaluation
    evaluator = SimpleEvaluator(ComponentType.STRATEGY)

    console.print(f":mag: Evaluating strategy: {file_path.name}")
    console.print(f"Level: {level.upper()}")

    try:
        result = evaluator.evaluate(file_path, level=eval_level)

        # Display results
        console.print()
        console.print(result)

        # Show signal context if requested
        if show_context:
            _display_signal_context(file_path)

        # Exit with appropriate code
        if result.passed:
            console.print("\n:white_check_mark: [green]Evaluation PASSED[/green]")
        else:
            console.print(f"\n:x: [red]Evaluation FAILED: {result.error_count} error(s), {result.warning_count} warning(s)[/red]")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[error]Error during evaluation: {e}[/error]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(5)


@app.command("stability")
def evaluate_stability(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Engine ID")],
    start_date: Annotated[Optional[str], typer.Option("--start", help=":calendar: Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[str], typer.Option("--end", help=":calendar: End date (YYYY-MM-DD)")] = None,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to file")] = None,
    min_signals: Annotated[int, typer.Option("--min-signals", help=":signal_strength: Minimum signals per slice")] = 10,
    min_orders: Annotated[int, typer.Option("--min-orders", help=":clipboard: Minimum orders per slice")] = 5,
):
    """
    :chart_with_upwards_trend: Evaluate backtest stability using slice analysis.
    """
    from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
    try:
        console.print(f":hourglass_flowing_sand: [yellow]Evaluating stability for portfolio {portfolio}, engine {engine}...[/yellow]")

        evaluator = BacktestEvaluator(
            min_signals_per_slice=min_signals,
            min_orders_per_slice=min_orders
        )
        
        result = evaluator.evaluate_backtest_stability(
            portfolio_id=portfolio,
            # ADR-016: 回测记录按 task_id 查。--engine 传入值在此回测评估场景即 task_id；
            # CLI flag 重命名待 #4639 实现本命令时一并处理。
            task_id=engine,
            start_date=start_date,
            end_date=end_date
        )
        
        if result['status'] != 'success':
            console.print(f":x: [bold red]Evaluation failed:[/bold red] {result.get('reason', result.get('error', 'Unknown error'))}")
            return
            
        # Step 3: Display results
        _display_stability_results(result)
        
        # Step 4: Export if requested
        if export:
            if evaluator.export_evaluation_report(result, export):
                console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
            else:
                console.print(f":x: [red]Failed to export report to: {export}[/red]")
                
    except Exception as e:
        console.print(f":x: [bold red]Error during evaluation:[/bold red] {e}")


@app.command("segment")
def evaluate_segment(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Backtest task ID")],
    freq: Annotated[str, typer.Option("--freq", help=":calendar: Segment frequency (M=month, Q=quarter, Y=year)")] = "M",
    analyzers: Annotated[Optional[str], typer.Option("--analyzers", help=":mag: Comma-separated analyzer names, empty = all")] = None,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to JSON file")] = None,
):
    """
    :bar_chart: Per-analyzer window statistics segmented by time period (monthly/quarterly/annually).
    """
    from ginkgo.trading.analysis.engine import AnalysisEngine
    try:
        from ginkgo import services
        e = AnalysisEngine(services.data.result_service(), services.data.analyzer_service())
        names = [a.strip() for a in analyzers.split(",")] if analyzers else None
        r = e.time_segments(task_id=engine, portfolio_id=portfolio, freq=freq, analyzers=names)

        console.print(r.to_rich())

        if export:
            with open(export, "w") as f:
                json.dump(r.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
    except Exception as exc:
        console.print(f":x: [bold red]Error during segment analysis:[/bold red] {exc}")


@app.command("rolling")
def evaluate_rolling(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Backtest task ID")],
    window: Annotated[int, typer.Option("--window", help=":arrows_clockwise: Rolling window size (trading days)")] = 20,
    step: Annotated[int, typer.Option("--step", help=":fast_forward: Slide step (days)")] = 5,
    analyzers: Annotated[Optional[str], typer.Option("--analyzers", help=":mag: Comma-separated analyzer names, empty = all")] = None,
    stability: Annotated[bool, typer.Option("--stability", help=":balance_scale: Show cross-window stability score per analyzer")] = False,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to JSON file")] = None,
):
    """
    :arrows_clockwise: Rolling window per-analyzer statistics (stability across windows).
    """
    from ginkgo.trading.analysis.engine import AnalysisEngine
    try:
        from ginkgo import services
        e = AnalysisEngine(services.data.result_service(), services.data.analyzer_service())
        names = [a.strip() for a in analyzers.split(",")] if analyzers else None
        r = e.rolling(task_id=engine, portfolio_id=portfolio, window=window, step=step, analyzers=names)

        console.print(r.to_rich())

        if stability:
            summary = r.stability_summary()
            stab_table = Table(title=f"[Rolling] Cross-Window Stability — {engine}")
            stab_table.add_column("Analyzer", style="cyan")
            stab_table.add_column("Score", justify="right")
            stab_table.add_column("CV", justify="right")
            stab_table.add_column("Consistency", justify="right")
            stab_table.add_column("Trend", justify="right")
            stab_table.add_column("Outlier", justify="right")
            for name, s in summary.items():
                ind = s["individual_scores"]
                # 均值≈0 的序列 CV 无意义(std/|mean| 除零 → inf)，展示为 "-"
                cv = ind["coefficient_of_variation"]
                cv_str = "-" if cv == float("inf") or cv != cv else f"{cv:.4f}"
                stab_table.add_row(
                    name,
                    f"{s['comprehensive_score']:.4f}",
                    cv_str,
                    f"{ind['consistency_ratio']:.4f}",
                    f"{ind['trend_stability']:.4f}",
                    f"{ind['outlier_ratio']:.4f}",
                )
            console.print(stab_table)

        if export:
            payload = {"windows": r.to_dict()}
            if stability:
                payload["stability"] = r.stability_summary()
            with open(export, "w") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
            console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
    except Exception as exc:
        console.print(f":x: [bold red]Error during rolling analysis:[/bold red] {exc}")


@app.command("funnel")
def evaluate_funnel(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Backtest task ID (G0/G1 数据源, G2 baseline)")],
    candidate: Annotated[Optional[str], typer.Option("--candidate", help=":vs: 模拟盘/对比 task ID (G2 candidate)")] = None,
    stability_window: Annotated[int, typer.Option("--stability-window", help=":arrows_clockwise: G1 平稳度滚动窗 (天)")] = 60,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to JSON file")] = None,
):
    """
    :filter: 四级漏斗总览 (G0 回测可信 → G1 回测有效 → G2 模拟一致 → G3 实盘就绪)。

    逐 gate 报 PASS/FAIL/样本不足/BLOCKED，未过 blocker 附修复建议。
    """
    from ginkgo.trading.analysis.engine import AnalysisEngine
    from ginkgo.trading.analysis.evaluation.funnel_evaluator import FunnelEvaluator
    try:
        from ginkgo import services
        e = AnalysisEngine(services.data.result_service(), services.data.analyzer_service())
        fe = FunnelEvaluator(e)
        r = fe.evaluate(
            portfolio_id=portfolio, task_id=engine,
            candidate_task_id=candidate, stability_window=stability_window,
        )
        _print_funnel(r)
        if export:
            with open(export, "w") as f:
                json.dump(r.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
    except Exception as exc:
        console.print(f":x: [bold red]Error during funnel evaluation:[/bold red] {exc}")


@app.command("parity")
def evaluate_parity(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    baseline: Annotated[str, typer.Option("--baseline", "-b", help=":gear: 回测 task ID (基准)")],
    candidate: Annotated[str, typer.Option("--candidate", "-c", help=":vs: 模拟盘/对比 task ID")],
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to JSON file")] = None,
):
    """
    :vs: 回测 vs 模拟盘 (或另一次回测) 同窗一致性 5 项指标 (G2)。

    日收益相关性 / 累计收益差带宽 / 换手偏差 / 回撤形态同构 / 重叠天数。
    """
    from ginkgo.trading.analysis.engine import AnalysisEngine
    from ginkgo.trading.analysis.evaluation.parity_calculator import ParityCalculator
    try:
        from ginkgo import services
        e = AnalysisEngine(services.data.result_service(), services.data.analyzer_service())
        base_dp = e._load_data(baseline, portfolio)
        cand_dp = e._load_data(candidate, portfolio)
        base_nav, cand_nav = base_dp.get("net_value"), cand_dp.get("net_value")
        if base_nav is None or cand_nav is None:
            console.print(":x: [red]net_value 链缺失, 无法对比[/red]")
            raise typer.Exit(1)
        r = ParityCalculator().compare(
            baseline=base_nav, candidate=cand_nav,
            baseline_label=f"backtest:{baseline[:8]}",
            candidate_label=f"candidate:{candidate[:8]}",
            baseline_turnover=base_dp.get("order_count"),
            candidate_turnover=cand_dp.get("order_count"),
        )
        _print_parity(r)
        if export:
            with open(export, "w") as f:
                json.dump(r.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
    except Exception as exc:
        console.print(f":x: [bold red]Error during parity analysis:[/bold red] {exc}")


@app.command("preflight")
def evaluate_preflight(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    start: Annotated[str, typer.Option("--start", "-s", help=":calendar: 窗口起始日 (YYYY-MM-DD)")],
    end: Annotated[str, typer.Option("--end", "-e", help=":calendar: 窗口结束日 (YYYY-MM-DD)")],
    min_bars: Annotated[int, typer.Option("--min-bars", help=":gear: 覆盖充足的最小 bar 条数")] = 10,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to JSON file")] = None,
):
    """
    :mag: 回测前数据质量预检 (G0): bar 缺口/日历对齐 + 复权一致 + 覆盖 (#6282 口径)。

    codes 取 portfolio 的 FixedSelector 参数; 动态 selector 放行并说明。
    """
    from ginkgo.data.containers import container
    from ginkgo.workers.backtest_worker.task_helpers import resolve_selector_codes
    from ginkgo.trading.analysis.evaluation.preflight_checker import PreflightChecker
    try:
        codes = resolve_selector_codes(portfolio)
        if not codes:
            console.print(":information: [yellow]动态 selector 无显式 codes，无需按 code 预检[/yellow]")
            raise typer.Exit(0)

        af_service = container.adjustfactor_service()

        def _factor_loader(code, s, e):
            res = af_service.get(code=code, start_date=s, end_date=e)
            items = res.data if getattr(res, "success", False) else []
            if isinstance(items, dict):
                items = items.get("data", [])
            out = []
            for r in items or []:
                ts = getattr(r, "timestamp", None)
                fac = getattr(r, "fore_adjustfactor", None)
                if ts is None or fac is None:
                    continue
                out.append((ts.date() if hasattr(ts, "date") else ts, float(fac)))
            return out

        checker = PreflightChecker(
            bar_crud=container.cruds.bar(), factor_loader=_factor_loader,
        )
        r = checker.check(portfolio, codes, start, end, min_bars=min_bars)
        _print_preflight(r)
        if export:
            with open(export, "w") as f:
                json.dump(r.to_dict(), f, ensure_ascii=False, indent=2, default=str)
            console.print(f":floppy_disk: [green]Report exported to: {export}[/green]")
        if not r.ok:
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f":x: [bold red]Error during preflight:[/bold red] {exc}")
        raise typer.Exit(1)


def _print_preflight(r) -> None:
    console.print(f"\n[bold]:mag: Data Preflight — portfolio {r.portfolio_id[:8]}[/bold]")
    console.print(f"  窗口 {r.start} ~ {r.end}  ·  codes: {len(r.codes)}")
    for note in r.notes:
        console.print(f"  [dim]:memo: {note}[/dim]")

    table = Table(title="数据质量总览")
    table.add_column("Code", style="cyan")
    table.add_column("Bar 数", justify="right")
    table.add_column("缺口率", justify="right")
    table.add_column("缺失日", justify="right")
    table.add_column("因子回跳", justify="right")
    table.add_column("状态")
    from ginkgo.trading.analysis.evaluation.preflight_checker import GAP_WARNING_PCT, GAP_BLOCKER_PCT
    for code in r.codes:
        q = r.quality.get(code, {})
        cov = r.coverage.get(code, 0)
        gap = q.get("gap_pct")
        rev = q.get("factor_reversals")
        sev = q.get("severity", "-")
        if sev == "blocker":
            status = "[red]✗ blocker[/red]"
        elif sev == "warning" or (rev is None and cov >= 10):
            status = "[yellow]⚠ warning[/yellow]"
        else:
            status = "[green]✓ ok[/green]"
        gap_str = f"{gap:.1f}%" if isinstance(gap, (int, float)) else "-"
        table.add_row(
            code, str(cov), gap_str, str(q.get("missing_days", "-")),
            "-" if rev is None else str(rev), status,
        )
    console.print(table)

    if r.issues:
        it = Table(title="问题清单 (按严重度)")
        it.add_column("严重度")
        it.add_column("类型", style="cyan")
        it.add_column("Code")
        it.add_column("详情")
        it.add_column("建议", style="dim")
        for i in sorted(r.issues, key=lambda x: 0 if x.severity == "blocker" else 1):
            sev = "[red]blocker[/red]" if i.severity == "blocker" else "[yellow]warning[/yellow]"
            it.add_row(sev, i.kind, i.code, i.detail, i.remediation)
        console.print(it)
    verdict = "[green]✓ 数据就绪，可跑回测[/green]" if r.ok else \
        "[red]✗ 存在 blocker，先修数据再回测[/red]"
    console.print(Panel(verdict, title="结论"))


def _fmt_val(v, unit: str = "") -> str:
    if v is None or v != v:
        return "-"
    if unit == "年":
        return f"{v:.2f} 年"
    if unit == "%":
        return f"{v:.1f}%"
    return f"{v:.4f}"


_STATUS_STYLE = {
    "PASS": "[green]✓ PASS[/green]",
    "FAIL": "[red]✗ FAIL[/red]",
    "INSUFFICIENT_DATA": "[yellow]? 样本不足[/yellow]",
    "BLOCKED": "[dim]⊘ BLOCKED[/dim]",
}


def _print_funnel(r) -> None:
    console.print(f"\n[bold]:filter: Evaluation Funnel — portfolio {r.portfolio_id[:8]}[/bold]")
    console.print(f"  task={r.task_id}" + (f"  candidate={r.candidate_task_id}" if r.candidate_task_id else ""))
    for note in r.notes:
        console.print(f"  [dim]:memo: {note}[/dim]")
    table = Table(title=f"漏斗位置: [bold cyan]{r.level_reached}[/bold cyan]")
    table.add_column("Gate", style="cyan")
    table.add_column("指标", style="white")
    table.add_column("值", justify="right")
    table.add_column("阈值", justify="right")
    table.add_column("状态")
    table.add_column("说明 / 建议", overflow="fold")
    for g in r.gates:
        thr = f"{g.gate.threshold:g}{' ' + g.gate.unit if g.gate.unit else ''}"
        advice = g.detail if g.status in ("PASS", "INSUFFICIENT_DATA", "BLOCKED") else g.gate.remediation
        table.add_row(
            f"{g.gate.level}.{g.gate.id.split('_', 1)[1]}",
            g.gate.name,
            _fmt_val(g.value, g.gate.unit),
            thr,
            _STATUS_STYLE.get(g.status, g.status),
            advice,
        )
    console.print(table)


def _print_parity(r) -> None:
    console.print(f"\n[bold]:vs: Parity — {r.baseline_label} vs {r.candidate_label}[/bold]")
    table = Table(title=f"同窗一致性 (重叠 {r.overlap_days} 天: {r.overlap_start} ~ {r.overlap_end})")
    table.add_column("指标", style="cyan")
    table.add_column("值", justify="right")
    table.add_column("阈值", justify="right")
    table.add_column("判定")
    from ginkgo.trading.analysis.evaluation.parity_calculator import ParityCalculator
    from ginkgo.trading.analysis.evaluation.gate_definitions import gates_by_level
    calc = ParityCalculator()
    for gate in gates_by_level("G2"):
        if gate.id == "g2_overlap_days":
            v = r.overlap_days
        else:
            v = {"g2_daily_return_corr": r.daily_return_corr,
                 "g2_cum_return_band": r.band_ratio,
                 "g2_turnover_deviation": r.turnover_deviation_pct,
                 "g2_drawdown_shape": r.drawdown_shape_corr}.get(gate.id)
        passed = calc.evaluate_gate(r, gate)
        verdict = "-" if passed is None else _STATUS_STYLE["PASS" if passed else "FAIL"]
        unit = "%" if gate.id == "g2_turnover_deviation" else ("倍带宽" if gate.id == "g2_cum_return_band" else ("天" if gate.id == "g2_overlap_days" else ""))
        table.add_row(gate.name, _fmt_val(v, unit), f"{gate.threshold:g}", verdict)
    console.print(table)
    for note in r.notes:
        console.print(f"  [dim]:memo: {note}[/dim]")


@app.command("monitor-create")
def create_monitor(
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Engine ID")],
    output: Annotated[str, typer.Option("--output", "-o", help=":floppy_disk: Output baseline file")],
    start_date: Annotated[Optional[str], typer.Option("--start", help=":calendar: Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[str], typer.Option("--end", help=":calendar: End date (YYYY-MM-DD)")] = None,
):
    """
    :telescope: Create monitoring baseline from backtest data.
    """
    from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
    try:
        console.print(f":hourglass_flowing_sand: [yellow]Creating monitoring baseline from portfolio {portfolio}, engine {engine}...[/yellow]")

        evaluator = BacktestEvaluator()
        
        # Run evaluation to get baseline
        result = evaluator.evaluate_backtest_stability(
            portfolio_id=portfolio,
            # ADR-016: 回测记录按 task_id 查。--engine 传入值在此回测评估场景即 task_id；
            # CLI flag 重命名待 #4639 实现本命令时一并处理。
            task_id=engine,
            start_date=start_date,
            end_date=end_date
        )
        
        if result['status'] != 'success':
            console.print(f":x: [bold red]Failed to create baseline:[/bold red] {result.get('reason', result.get('error'))}")
            return
            
        # Extract monitoring baseline
        baseline = result['monitoring_baseline']
        
        # Save to file
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(baseline, f, indent=2, ensure_ascii=False, default=str)
            
        console.print(f":telescope: [green]Monitoring baseline created: {output}[/green]")
        
        # Display baseline summary
        _display_baseline_summary(baseline)
        
    except Exception as e:
        console.print(f":x: [bold red]Error creating baseline:[/bold red] {e}")


@app.command("monitor-live")  
def monitor_live(
    baseline: Annotated[str, typer.Option("--baseline", "-b", help=":telescope: Baseline file path")],
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")],
    interval: Annotated[int, typer.Option("--interval", help=":clock: Check interval in seconds")] = 300,
):
    """
    :eyes: Start live monitoring using baseline (demo mode).
    """
    import time
    from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
    try:
        # Load baseline
        with open(baseline, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)

        console.print(f":telescope: [green]Loaded baseline from: {baseline}[/green]")

        # Create live monitor
        evaluator = BacktestEvaluator()
        monitor = evaluator.create_live_monitor(baseline_data)
        
        console.print(f":eyes: [yellow]Starting live monitoring for portfolio {portfolio}...[/yellow]")
        console.print(f":clock: Check interval: {interval} seconds")
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        
        # Demo monitoring loop
        iteration = 0
        while True:
            iteration += 1
            console.print(f"\n:mag_right: [cyan]Monitoring check #{iteration}[/cyan]")
            
            # In real implementation, this would fetch live analyzer data
            # For demo, we simulate some checks
            console.print("  • Fetching live analyzer data... :hourglass_flowing_sand:")
            time.sleep(1)
            console.print("  • Checking for slice completion... :clock:")
            time.sleep(1)
            console.print("  • No deviations detected :white_check_mark:")
            
            # Wait for next check
            for remaining in range(interval, 0, -1):
                console.print(f"  Next check in {remaining}s...", end="\r")
                time.sleep(1)
                
    except KeyboardInterrupt:
        console.print("\n:stop_sign: [yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f":x: [bold red]Error during monitoring:[/bold red] {e}")


def _display_stability_results(result: dict):
    """Display formatted stability evaluation results"""
    
    # Overview panel
    overview_text = f"""
[bold]Portfolio:[/bold] {result['portfolio_id']}
[bold]Engine:[/bold] {result.get('engine_id') or result.get('task_id', 'N/A')}
[bold]Evaluation Time:[/bold] {result['evaluation_time']}
[bold]Status:[/bold] :white_check_mark: Success
    """
    console.print(Panel(overview_text, title=":chart_with_upwards_trend: Evaluation Overview", border_style="green"))
    
    # Data summary
    data_summary = result['data_summary']
    summary_table = Table(title=":bar_chart: Data Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="yellow")
    
    summary_table.add_row("Analyzer Records", str(data_summary['analyzer_records']))
    summary_table.add_row("Signal Records", str(data_summary['signal_records']))
    summary_table.add_row("Order Records", str(data_summary['order_records']))
    summary_table.add_row("Time Span (days)", str(data_summary['time_span']['days']))
    
    console.print(summary_table)
    
    # Optimal slice configuration
    slice_config = result['optimal_slice_config']
    config_text = f"""
[bold]Optimal Period:[/bold] {slice_config['period_days']} days
[bold]Stability Score:[/bold] {slice_config['stability_score']:.4f}
[bold]Slice Count:[/bold] {slice_config['slice_count']}
    """
    console.print(Panel(config_text, title=":scissors: Optimal Slice Configuration", border_style="blue"))
    
    # Stability analysis
    stability = result['stability_analysis']
    comparison = stability['cross_metric_comparison']
    
    stability_table = Table(title=":balance_scale: Stability Analysis")
    stability_table.add_column("Metric", style="cyan")
    stability_table.add_column("Stability Score", style="yellow")
    stability_table.add_column("Status", style="green")
    
    for metric_name, score in comparison['ranking'][:10]:  # Show top 10
        status = ":white_check_mark:" if score > 0.7 else ":warning:" if score > 0.5 else ":x:"
        stability_table.add_row(metric_name, f"{score:.4f}", status)
        
    console.print(stability_table)
    
    # Recommendations
    recommendations = result['recommendations']
    if recommendations:
        rec_text = "\n".join([f"• {rec}" for rec in recommendations])
        console.print(Panel(rec_text, title=":bulb: Recommendations", border_style="yellow"))


def _display_baseline_summary(baseline: dict):
    """Display baseline summary"""
    
    summary_text = f"""
[bold]Slice Period:[/bold] {baseline['slice_period_days']} days
[bold]Total Slices:[/bold] {baseline['total_slices']}
[bold]Creation Time:[/bold] {baseline['creation_time']}
[bold]Metrics Count:[/bold] {len(baseline['baseline_stats'])}
    """
    console.print(Panel(summary_text, title=":telescope: Baseline Summary", border_style="green"))
    
    # Top metrics by stability
    metrics_table = Table(title=":bar_chart: Baseline Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Mean", style="yellow")
    metrics_table.add_column("Std Dev", style="yellow")
    metrics_table.add_column("Range", style="blue")
    
    for metric_name, stats in list(baseline['baseline_stats'].items())[:10]:
        mean_val = f"{stats['mean']:.4f}"
        std_val = f"{stats['std']:.4f}"
        range_val = f"{stats['min']:.2f} ~ {stats['max']:.2f}"
        metrics_table.add_row(metric_name, mean_val, std_val, range_val)

    console.print(metrics_table)


def _display_signal_context(file_path):
    """
    Display signal generation context analysis for a strategy.

    Analyzes the cal() method to show:
    - Data sources used
    - Signal generation conditions
    - Possible signal directions
    - Key logic patterns
    """
    import ast
    import re
    from pathlib import Path

    console.print("\n")
    console.print(Panel(":books: [bold cyan]Signal Generation Context Analysis[/bold cyan]", border_style="cyan"))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        tree = ast.parse(source_code, filename=str(file_path))

        # Analyze strategy
        context = {
            'data_sources': [],
            'signal_conditions': [],
            'directions': [],
            'key_logic': [],
            'imports': []
        }

        # Extract imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    context['imports'].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    context['imports'].append(node.module)

        # Find and analyze cal() method
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "cal":
                        # Analyze cal() method
                        _analyze_cal_method(item, source_code, context)
                        break

        # Display analysis results
        _display_context_analysis(context, source_code, file_path)

    except Exception as e:
        console.print(f":warning: [yellow]Could not analyze signal context: {e}[/yellow]")


def _analyze_cal_method(func_node, source_code, context):
    """Analyze cal() method for signal generation patterns."""
    import ast

    # Get the source code of cal() method
    if hasattr(func_node, 'lineno') and hasattr(func_node, 'end_lineno'):
        lines = source_code.split('\n')
        method_source = '\n'.join(lines[func_node.lineno-1:func_node.end_lineno])
        context['method_source'] = method_source

    # Walk through the method
    for node in ast.walk(func_node):
        # Find data source usage
        if isinstance(node, ast.Attribute):
            if node.attr in ['get_bars', 'get_ticks', 'data_feeder', 'get_time_provider']:
                context['data_sources'].append(node.attr)

        # Find DIRECTION_TYPES usage
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                if node.value.id == 'DIRECTION_TYPES':
                    context['directions'].append(node.attr)

        # Find conditional statements (if conditions)
        if isinstance(node, ast.If):
            condition = ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test.lineno)
            context['signal_conditions'].append({
                'line': node.lineno,
                'condition': condition[:100] if len(condition) > 100 else condition
            })

        # Find Signal() calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "Signal":
                # Extract key arguments
                args_info = {}
                for kw in node.keywords:
                    if kw.arg in ['direction', 'reason', 'code']:
                        args_info[kw.arg] = ast.unparse(kw.value) if hasattr(ast, 'unparse') else kw.arg

                context['key_logic'].append({
                    'line': node.lineno,
                    'type': 'Signal creation',
                    'details': args_info
                })


def _display_context_analysis(context, source_code, file_path):
    """Display the analyzed context in a formatted way."""
    from pathlib import Path
    from rich.table import Table
    from rich.syntax import Syntax

    # Strategy overview
    console.print(f"[bold]Strategy File:[/bold] {Path(file_path).name}")

    # Data sources table
    if context['data_sources']:
        data_table = Table(title=":floppy_disk: Data Sources Used")
        data_table.add_column("Source", style="cyan")
        data_table.add_column("Purpose", style="yellow")

        source_purposes = {
            'get_bars': 'K-line data retrieval',
            'get_ticks': 'Tick data retrieval',
            'data_feeder': 'Unified data access',
            'get_time_provider': 'Time access'
        }

        for source in set(context['data_sources']):
            purpose = source_purposes.get(source, 'Data access')
            data_table.add_row(source, purpose)

        console.print(data_table)

    # Signal directions
    if context['directions']:
        directions_str = ", ".join(set(context['directions']))
        console.print(f":arrow_up_down: [bold]Possible Directions:[/bold] {directions_str}")

    # Signal conditions
    if context['signal_conditions']:
        condition_table = Table(title=":mag: Signal Generation Conditions")
        condition_table.add_column("Line", style="cyan", width=6)
        condition_table.add_column("Condition", style="yellow")

        for cond in context['signal_conditions'][:10]:  # Show first 10
            condition_table.add_row(str(cond['line']), cond['condition'][:80])

        console.print(condition_table)

    # Signal creation points
    if context['key_logic']:
        logic_table = Table(title=":light_bulb: Signal Creation Logic")
        logic_table.add_column("Line", style="cyan", width=6)
        logic_table.add_column("Type", style="green")
        logic_table.add_column("Details", style="yellow")

        for logic in context['key_logic'][:10]:
            details_str = ", ".join([f"{k}={v}" for k, v in logic['details'].items()])
            logic_table.add_row(str(logic['line']), logic['type'], details_str[:60])

        console.print(logic_table)

    # Show cal() method source if available
    if 'method_source' in context and len(context['method_source']) < 1000:
        console.print("\n:page_facing_up: [bold]cal() Method Source:[/bold]")
        syntax = Syntax(context['method_source'], "python", theme="monokai", line_numbers=True)
        console.print(syntax)

