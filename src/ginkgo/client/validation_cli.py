# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 验证CLI实现数据馈送/时间提供者等核心类提供验证/检查/规则管理等命令支持交易系统功能和组件集成提供完整业务支持






"""Validation CLI module."""
"""
Validation CLI

This module provides command-line interface for strategy validation.
Separated from evaluation_cli.py to avoid confusion with backtest evaluation.
"""

from pathlib import Path

import typer
from typing import Any, Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

from ginkgo.trading.evaluation.core.enums import ComponentType

app = typer.Typer(
    help=":white_check_mark: Module for [bold medium_spring_green]VALIDATION[/]. [grey62]Component code validation before backtesting.[/grey62]",
    no_args_is_help=True,
)

console = Console()


@app.command("")
def validate(
    component_file: Annotated[str, typer.Argument(help=":page_facing_up: Path to the component file to validate")] = None,
    type: Annotated[str, typer.Option("--type", "-t", help=":label: Component type (strategy/selector/sizer/risk_manager) - default: strategy")] = "strategy",
    format: Annotated[str, typer.Option("--format", "-f", help=":page_facing_up: Report format (text/json/markdown) - default: text")] = "text",
    output: Annotated[str, typer.Option("--output", "-o", help=":file_folder: Save report to file (format determined by extension or --format)")] = None,
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help=":speech_balloon: Show detailed output")] = False,
    show_trace: Annotated[bool, typer.Option("--show-trace", "-T", help=":mag: Enable runtime signal tracing with database data")] = False,
    code: Annotated[str, typer.Option("--code", "-c", help=":1234: Stock code for tracing (default: 000001.SZ)")] = "000001.SZ",
    events: Annotated[int, typer.Option("--events", "-e", help=":1234: Number of events to process (default: all)")] = 0,
    visualize: Annotated[bool, typer.Option("--visualize", "-V", help=":art: Generate HTML chart visualization")] = False,
    # Database options (T102-T108)
    file_id: Annotated[str, typer.Option("--file-id", help=":database: Load component from database by file_id")] = None,
    list_strategies: Annotated[bool, typer.Option("--list", help=":list: List all components in database")] = False,
    all_db: Annotated[bool, typer.Option("--all", help=":globe_with_meridians: Validate all database strategies")] = False,
    name_filter: Annotated[str, typer.Option("--filter", help=":filter: Filter strategies by name (for --list or --all)")] = None,
):
    """
    :mag: Validate a trading component file.

    This command validates component structure, logic, and best practices.
    Use --type to specify component type (strategy/selector/sizer/risk_manager).
    Use --show-trace to trace runtime signal generation with database data.
    Use --visualize to generate interactive HTML chart visualization.
    Use --format to specify output format (text/json/markdown).
    Use --output to save report to a file.
    Use --file-id to validate components stored in database.

    Examples:
      ginkgo validate my_strategy.py
      ginkgo validate my_strategy.py --type strategy
      ginkgo validate my_selector.py --type selector
      ginkgo validate my_sizer.py --type sizer
      ginkgo validate my_risk_manager.py --type risk_manager
      ginkgo validate my_strategy.py --format json --output report.json
      ginkgo validate my_strategy.py --show-trace
      ginkgo validate --file-id <uuid> --type sizer

    Database validation (US5):
      ginkgo validate --file-id <uuid> --type strategy
      ginkgo validate --list
      ginkgo validate --all --filter Test
      ginkgo validate --all
      ginkgo validate --all --filter Test --format json --output reports/
    """
    from pathlib import Path
    from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
    from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
    from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
    from ginkgo.trading.evaluation.rules.structural_rules import (
        BaseStrategyInheritanceRule,
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
    from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader

    # Validate type parameter
    type_map = {
        "strategy": ComponentType.STRATEGY,
        "selector": ComponentType.SELECTOR,
        "sizer": ComponentType.SIZER,
        "risk_manager": ComponentType.RISK_MANAGER,
    }
    if type not in type_map:
        console.print(f":x: [red]Invalid type '{type}'. Must be one of: strategy, selector, sizer, risk_manager[/red]")
        raise typer.Exit(1)
    component_type = type_map[type]

    # Check if component type is supported
    if not component_type.is_supported():
        console.print(f":warning: [yellow]Component type '{type}' is not yet supported for validation[/yellow]")
        console.print("  Supported types: strategy")
        console.print("  Falling back to strategy validation...")
        component_type = ComponentType.STRATEGY

    # Handle --list option (T104)
    if list_strategies:
        _list_database_strategies(name_filter, console)
        return

    # Validate mutual exclusivity of input sources (T102, T103)
    sources_provided = sum([
        component_file is not None,
        file_id is not None,
        all_db,
    ])
    if sources_provided == 0:
        console.print("[error]Error: No component source specified[/error]")
        console.print("\nUsage: ginkgo validate <COMPONENT_FILE> [OPTIONS]")
        console.print("       ginkgo validate --file-id <uuid> [OPTIONS]")
        console.print("       ginkgo validate --all [OPTIONS]")
        raise typer.Exit(1)
    if sources_provided > 1:
        console.print("[error]Error: Cannot specify multiple component sources[/error]")
        console.print("  Use only one of: component_file, --file-id, --all")
        raise typer.Exit(1)

    # Handle --all batch validation (T105)
    if all_db:
        _batch_validate_database_strategies(
            name_filter=name_filter,
            report_format=format,
            output_dir=output,
            verbose=verbose,
            show_trace=show_trace,
            code=code,
            events=events,
            visualize=visualize,
            console=console,
        )
        return

    # Validate format parameter (T048)
    format_map = {
        "text": "text",
        "json": "json",
        "markdown": "markdown",
        "md": "markdown",  # Shortcut for markdown
    }
    if format not in format_map:
        console.print(f":x: [red]Invalid format '{format}'. Must be one of: text, json, markdown, md[/red]")
        raise typer.Exit(1)
    report_format = format_map[format]

    # Determine strategy source and file path (T107)
    source_info = None  # Track source for report output (T111)
    temp_file_path = None  # Track for cleanup (T108, T112)

    if file_id:
        loader = DatabaseStrategyLoader()
        try:
            with loader.load_by_file_id(file_id) as temp_path:
                temp_file_path = temp_path
                source_info = f"Database (file_id: {file_id[:8]}...)"
                if verbose:
                    console.print(f":database: Loading from database: {file_id[:8]}...")
                    console.print(f":file_folder: Temp file: {temp_path} (auto-cleaned)")
                _validate_single_strategy(
                    temp_path, component_type, report_format, output, verbose,
                    show_trace, code, events, visualize, source_info, console
                )
                return
        except FileNotFoundError as e:
            console.print(f":x: [red]{e}[/red]")
            raise typer.Exit(2)
        except Exception as e:
            console.print(f":x: [red]Error loading from database: {e}[/red]")
            if verbose:
                import traceback
                console.print(traceback.format_exc())
            raise typer.Exit(5)

    else:  # component_file
        file_path = Path(component_file)
        if not file_path.exists():
            console.print(f":x: [red]File not found: {component_file}[/red]")
            raise typer.Exit(2)
        source_info = f"Local file: {file_path.name}"
        _validate_single_strategy(
            file_path, component_type, report_format, output, verbose,
            show_trace, code, events, visualize, source_info, console
        )

def _validate_single_strategy(
    file_path: Path,
    component_type: ComponentType,
    report_format: str,
    output: Optional[str],
    verbose: bool,
    show_trace: bool,
    code: str,
    events: int,
    visualize: bool,
    source_info: str,
    console: Console,
):
    """
    Validate a single component file.

    Args:
        file_path: Path to component file (can be temp file)
        component_type: Type of component to validate
        report_format: Report format (text/json/markdown)
        output: Output file path
        verbose: Show detailed output
        show_trace: Enable signal tracing
        code: Stock code for tracing
        events: Number of events to process
        visualize: Generate HTML visualization
        source_info: Source description for report (T111)
        console: Rich console instance
    """
    from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
    from ginkgo.libs import GLOG
    from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
    from ginkgo.trading.evaluation.rules.rule_registry import get_global_registry
    from ginkgo.trading.evaluation.rules.structural_rules import (
        BaseStrategyInheritanceRule,
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

    # Register default rules (all 14 rules enabled)
    registry = get_global_registry()

    # Register all validation rules
    registry.register_rule_class(BaseStrategyInheritanceRule, ComponentType.STRATEGY)
    registry.register_rule_class(CalMethodRequiredRule, ComponentType.STRATEGY)
    registry.register_rule_class(SuperInitCallRule, ComponentType.STRATEGY)
    registry.register_rule_class(CalSignatureValidationRule, ComponentType.STRATEGY)
    registry.register_rule_class(ReturnStatementRule, ComponentType.STRATEGY)
    registry.register_rule_class(SignalFieldRule, ComponentType.STRATEGY)
    registry.register_rule_class(DirectionValidationRule, ComponentType.STRATEGY)
    registry.register_rule_class(TimeProviderUsageRule, ComponentType.STRATEGY)
    registry.register_rule_class(ForbiddenOperationsRule, ComponentType.STRATEGY)
    registry.register_rule_class(DecoratorUsageRule, ComponentType.STRATEGY)
    registry.register_rule_class(ExceptionHandlingRule, ComponentType.STRATEGY)
    registry.register_rule_class(LoggingRule, ComponentType.STRATEGY)
    registry.register_rule_class(ResetStateRule, ComponentType.STRATEGY)
    registry.register_rule_class(ParameterValidationRule, ComponentType.STRATEGY)

    # Create evaluator with specified type
    evaluator = SimpleEvaluator(component_type)

    console.print(f":mag: Validating {component_type.value}: {file_path.name}")
    if source_info:
        console.print(f":information: Source: {source_info}")

    try:
        result = evaluator.evaluate(file_path)

        # Generate report using selected format (T048)
        report_content = _generate_report(result, report_format)

        # Determine output file
        output_file = None
        if output:
            output_path = Path(output)
            if output_path.is_dir() or output.endswith('/'):
                filename = f"{file_path.stem}_report.{_get_format_extension(report_format)}"
                output_file = output_path / filename if output.endswith('/') else output_path / filename
            else:
                output_file = output_path
                if report_format == "text" and output_file.suffix in [".json", ".md", ".markdown"]:
                    ext_map = {".json": "json", ".md": "markdown", ".markdown": "markdown"}
                    report_format = ext_map.get(output_file.suffix, "text")

        # Save to file if output specified (T049)
        if output_file:
            _save_report_to_file(report_content, output_file, console)
            if not visualize and not show_trace:
                console.print(f"\n:white_check_mark: [green]Report saved to: {output_file}[/green]")
        else:
            # Display results to console (only for text format or when no output file)
            if report_format == "text":
                # Use print() for pre-formatted Rich content with ANSI codes
                console.print()
                print(report_content, end="")

        # Runtime signal tracing (T109)
        if show_trace:
            if result.passed:
                tracer_report = _run_signal_tracing(file_path, code, events, verbose)

                # Generate visualization if requested (T110)
                if visualize:
                    viz_output = output if output else "./signal_chart.html"
                    _generate_visualization(file_path, tracer_report, viz_output, verbose)
            else:
                console.print(":warning: [yellow]Skipping signal tracing - validation failed[/yellow]")
        elif visualize:
            # Visualization without tracing
            if result.passed:
                tracer_report = _run_signal_tracing(file_path, code, events, verbose, silent=True)
                viz_output = output if output else "./signal_chart.html"
                _generate_visualization(file_path, tracer_report, viz_output, verbose)
            else:
                console.print(":warning: [yellow]Skipping visualization - validation failed[/yellow]")

        # Exit with appropriate code
        if result.passed:
            console.print("\n:white_check_mark: [green]Validation PASSED[/green]")
        else:
            console.print(f"\n:x: [red]Validation FAILED: {result.error_count} error(s), {result.warning_count} warning(s)[/red]")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[error]Error during validation: {e}[/error]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(5)


def _list_database_strategies(name_filter: Optional[str], console: Console) -> None:
    """
    List all strategies in the database (T104).

    Args:
        name_filter: Optional name filter
        console: Rich console instance
    """
    from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader

    loader = DatabaseStrategyLoader()

    try:
        strategies = loader.list_strategies(name_filter=name_filter)

        if not strategies:
            console.print(":information: No strategies found in database")
            return

        # Create Rich table
        table = Table(title=":database: Database Strategies")
        table.add_column("File ID", style="cyan", no_wrap=False)
        table.add_column("Name", style="green")
        table.add_column("Portfolios", style="yellow", justify="right")

        for strategy in strategies:
            file_id_short = strategy["file_id"][:8] + "..."
            table.add_row(
                file_id_short,
                strategy["name"],
                str(strategy["portfolio_count"]),
            )

        console.print(table)
        console.print(f"\n:page_facing_up: Total: {len(strategies)} strategies")

    except Exception as e:
        console.print(f":x: [red]Error listing strategies: {e}[/red]")
        raise typer.Exit(5)


def _batch_validate_database_strategies(
    name_filter: Optional[str],
    report_format: str,
    output_dir: Optional[str],
    verbose: bool,
    show_trace: bool,
    code: str,
    events: int,
    visualize: bool,
    console: Console,
) -> None:
    """
    Validate all database strategies (T105).

    Args:
        name_filter: Optional name filter
        report_format: Report format
        output_dir: Output directory for reports
        verbose: Show detailed output
        show_trace: Enable signal tracing
        code: Stock code for tracing
        events: Number of events to process
        visualize: Generate HTML visualization
        console: Rich console instance
    """
    from pathlib import Path
    from ginkgo.trading.evaluation.utils.database_loader import DatabaseStrategyLoader

    loader = DatabaseStrategyLoader()

    try:
        strategies = loader.list_strategies(name_filter=name_filter)

        if not strategies:
            console.print(":information: No strategies found in database")
            return

        console.print(f":globe_with_meridians: Validating {len(strategies)} strategies...")
        console.print()

        # Determine output directory
        output_path = Path(output_dir) if output_dir else None
        if output_path:
            output_path.mkdir(parents=True, exist_ok=True)

        passed_count = 0
        failed_count = 0

        for i, strategy_info in enumerate(strategies, 1):
            file_id = strategy_info["file_id"]
            strategy_name = strategy_info["name"]

            console.print(f"[{i}/{len(strategies)}] {strategy_name} ({file_id[:8]}...)")

            try:
                with loader.load_by_file_id(file_id) as temp_path:
                    # Determine output file for this strategy
                    strategy_output = None
                    if output_path:
                        strategy_output = output_path / f"{strategy_name}_report.{_get_format_extension(report_format)}"

                    # Validate (reuse existing validation logic but without exit on failure)
                    _validate_single_strategy(
                        temp_path, ComponentType.STRATEGY, report_format,
                        strategy_output, verbose, code, events, False,
                        f"Database (file_id: {file_id[:8]}...)", console
                    )
                    passed_count += 1
                    console.print()

            except SystemExit as e:
                # Validation failed, continue with next strategy
                failed_count += 1
                console.print(f":x: Failed (exit code {e.code})")
                console.print()
                continue
            except Exception as e:
                failed_count += 1
                console.print(f":x: Error: {e}")
                console.print()
                continue

        # Summary
        console.print(f"\n:chart_with_upwards_trend: Batch validation complete")
        console.print(f"  Total: {len(strategies)}")
        console.print(f"  :white_check_mark: Passed: {passed_count}")
        console.print(f"  :x: Failed: {failed_count}")

        if failed_count > 0:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: [red]Error during batch validation: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        raise typer.Exit(5)


def _run_signal_tracing(strategy_file, stock_code: str, max_events: int, verbose: bool, silent: bool = False):
    """
    Run runtime signal tracing on a strategy with database data.

    Args:
        strategy_file: Path to the strategy file
        stock_code: Stock code to get data from database (default: 000001.SZ)
        max_events: Maximum number of events to process (0 = all)
        verbose: Show detailed output
        silent: If True, don't print trace report (for visualization-only mode)

    Returns:
        SignalTraceReport object
    """
    from pathlib import Path
    from ginkgo.trading.evaluation.analyzers.runtime_analyzer import SignalTracer
    from ginkgo.trading.events import EventPriceUpdate
    from ginkgo.data.containers import container
    from datetime import datetime, timedelta
    import importlib.util
    import sys

    console.print("\n:telescope: [bold cyan]Runtime Signal Tracing[/bold cyan]")
    console.print(f"Stock Code: {stock_code}")

    try:
        # Load strategy class from file
        spec = importlib.util.spec_from_file_location("strategy_module", strategy_file)
        if spec is None or spec.loader is None:
            console.print(f":x: [red]Failed to load strategy file: {strategy_file}[/red]")
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules["strategy_module"] = module
        spec.loader.exec_module(module)

        # Find strategy class (class that inherits from BaseStrategy)
        from ginkgo.trading.strategies.base_strategy import BaseStrategy
        strategy_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, BaseStrategy) and attr != BaseStrategy:
                strategy_class = attr
                break

        if strategy_class is None:
            console.print(f":x: [red]No strategy class found in file[/red]")
            return

        console.print(f":page_facing_up: Found strategy class: {strategy_class.__name__}")

        # Get all bar data from database for data_feeder
        bar_service = container.bar_service()
        result = bar_service.get(code=stock_code)

        if not result.success:
            console.print(f":x: [red]Failed to get data for {stock_code}: {result.message}[/red]")
            return

        all_bars = result.data
        if not all_bars:
            console.print(f":x: [red]No bar data found for {stock_code}[/red]")
            return

        console.print(f":page_facing_up: Loaded {len(all_bars)} bar records from database")

        # Create a simple data_feeder for the strategy
        class SimpleDataFeeder:
            def __init__(self, bars):
                self.bars = bars
                self.bars_by_code = {}
                for bar in bars:
                    if bar.code not in self.bars_by_code:
                        self.bars_by_code[bar.code] = []
                    self.bars_by_code[bar.code].append(bar)

            def get_bars(self, code, start_date=None, end_date=None):
                """Get bars for a code within date range."""
                bars = self.bars_by_code.get(code, [])
                if start_date:
                    bars = [b for b in bars if b.timestamp >= start_date]
                if end_date:
                    bars = [b for b in bars if b.timestamp <= end_date]
                return bars

        # Create a simple time_provider for the strategy
        class SimpleTimeProvider:
            def __init__(self, initial_time):
                self.current_time = initial_time

            def now(self):
                return self.current_time

            def set_current_time(self, new_time):
                self.current_time = new_time
                return True

        # Create and initialize strategy with data_feeder and time_provider
        strategy = strategy_class(name=f"trace_{strategy_class.__name__}")
        strategy.bind_data_feeder(SimpleDataFeeder(all_bars))

        # Create and set time_provider (reused across all events)
        if all_bars:
            time_provider = SimpleTimeProvider(all_bars[0].timestamp)
            strategy.set_time_provider(time_provider)

        # Limit events if requested (use last N bars for events)
        event_bars = all_bars
        if max_events > 0:
            event_bars = all_bars[-max_events:]

        console.print(f":telescope: Processing {len(event_bars)} events for tracing")

        # Create tracer
        with SignalTracer(strategy, str(strategy_file)) as tracer:
            # Debug: check if cal() was wrapped
            if verbose:
                console.print(f"  [DEBUG] cal method after wrapping: {strategy.cal}")
                console.print(f"  [DEBUG] Original cal saved: {tracer._original_cal is not None}")

            # Simulate strategy execution with database data
            # Initialize portfolio_info with required fields for strategy compatibility
            portfolio_info = {
                "uuid": "validation_test_portfolio",
                "portfolio_id": "validation_test_portfolio",
                "engine_id": "validation_test_engine",
                "run_id": "validation_test_run",
                "now": datetime.now(),
            }

            for bar in event_bars:
                try:
                    # Update time_provider current time (reuse same instance)
                    time_provider.current_time = bar.timestamp
                    # Update portfolio_info now timestamp
                    portfolio_info["now"] = bar.timestamp

                    # Create event from bar data
                    # Need to convert MBar to Bar entity first for EventPriceUpdate.set() to work
                    from ginkgo.trading.entities.bar import Bar as BarEntity
                    bar_entity = BarEntity.from_model(bar)
                    event = EventPriceUpdate(payload=bar_entity, name="PriceUpdate")

                    # Call strategy cal()
                    try:
                        signals = strategy.cal(portfolio_info, event)
                    except Exception as cal_error:
                        if verbose:
                            console.print(f"  [CAL ERROR] {cal_error}")
                        signals = []

                    # Debug: check if signals were generated
                    if verbose:
                        console.print(f"  [{bar.timestamp}] Generated {len(signals) if signals else 0} signals")

                    if verbose and signals:
                        for signal in signals:
                            console.print(
                                f"  :bell: Signal #{len(tracer.get_report().traces)}: "
                                f"{getattr(signal, 'code', 'N/A')} - "
                                f"{getattr(signal, 'direction', 'N/A')}"
                            )

                except Exception as e:
                    if verbose:
                        console.print(f":warning: Error processing bar {bar.timestamp}: {e}")
                    continue

        # Get and display trace report
        report = tracer.get_report()
        if not silent:
            console.print("\n:chart_with_upwards_trend: [bold]Signal Trace Report[/bold]")
            # Use str() to get formatted string representation
            console.print(str(report))

        # Store event_bars in report for visualization
        report.metadata["event_bars"] = event_bars

        return report

    except Exception as e:
        console.print(f":x: [red]Error during signal tracing: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())
        return None


def _generate_visualization(strategy_file: str, report: Any, output_path: str, verbose: bool = False) -> None:
    """
    Generate HTML visualization for signal tracing report.

    Includes K-line chart with signal markers showing price context
    for each signal generation event.

    Args:
        strategy_file: Path to the strategy file
        report: SignalTraceReport object
        output_path: Path to output HTML file
        verbose: Show detailed output
    """
    from pathlib import Path
    from ginkgo.trading.evaluation.reporters.html_visualizer import HTMLSignalVisualizer

    try:
        console.print(f"\n:art: [bold cyan]Generating HTML visualization[/bold cyan]")

        # Get event_bars from report metadata (K-line data)
        event_bars = report.metadata.get("event_bars", [])

        # Use traces directly (contains event timestamp, not signal timestamp)
        traces = report.traces

        console.print(f"  K-line bars: {len(event_bars)}")
        console.print(f"  Signals: {len(traces)}")

        # Create visualizer
        visualizer = HTMLSignalVisualizer()

        # Generate chart with K-line and signal markers from traces
        visualizer.generate_signal_chart_from_traces(
            bars=event_bars,
            traces=traces,
            output_path=output_path,
            title=f"Strategy Signal Chart - {Path(strategy_file).stem}",
            width=1200,
            height=600,
        )

        console.print(f":white_check_mark: [green]HTML chart saved to: {output_path}[/green]")
        console.print(f"  Total signals: {report.signal_count}")
        console.print(f"  Buy signals: {report.buy_count}")
        console.print(f"  Sell signals: {report.sell_count}")

        if verbose:
            console.print(f"\n  Open in browser: file://{Path(output_path).absolute()}")

    except Exception as e:
        console.print(f":x: [red]Error generating visualization: {e}[/red]")
        if verbose:
            import traceback
            console.print(traceback.format_exc())


def _get_format_extension(format_name: str) -> str:
    """Get file extension for a report format."""
    extensions = {
        "text": "txt",
        "json": "json",
        "markdown": "md",
    }
    return extensions.get(format_name, "txt")


def _generate_report(result, report_format: str) -> str:
    """
    Generate evaluation report in the specified format.

    Args:
        result: EvaluationResult object
        report_format: Format (text/json/markdown)

    Returns:
        Formatted report as string
    """
    from ginkgo.trading.evaluation.reporters.text_reporter import TextReporter
    from ginkgo.trading.evaluation.reporters.json_reporter import JsonReporter
    from ginkgo.trading.evaluation.reporters.markdown_reporter import MarkdownReporter

    # Select reporter based on format
    if report_format == "json":
        reporter = JsonReporter()
    elif report_format == "markdown":
        reporter = MarkdownReporter()
    else:  # text
        reporter = TextReporter()

    # Generate report
    return reporter.generate(result)


def _save_report_to_file(content: str, output_path, console) -> None:
    """
    Save report content to file.

    Args:
        content: Report content
        output_path: Path to output file
        console: Rich console for messages
    """
    from pathlib import Path

    output_path = Path(output_path)

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write content to file
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        console.print(f":x: [red]Failed to save report to {output_path}: {e}[/red]")
        raise
