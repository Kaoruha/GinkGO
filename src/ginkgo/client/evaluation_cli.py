# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 评估CLI提供策略评估/分析/比较/报告等命令支持回测结果的多维度性能分析支持交易系统功能和组件集成提供完整业务支持






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
        BaseStrategyInheritanceRule,
        ComponentType.STRATEGY,
        EvaluationLevel.BASIC,
    )
    registry.register_rule_class(
        CalMethodRequiredRule,
        ComponentType.STRATEGY,
        EvaluationLevel.BASIC,
    )
    registry.register_rule_class(
        SuperInitCallRule,
        ComponentType.STRATEGY,
        EvaluationLevel.BASIC,
    )

    # Standard level rules
    registry.register_rule_class(
        CalSignatureValidationRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
    )
    registry.register_rule_class(
        ReturnStatementRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
    )
    registry.register_rule_class(
        SignalFieldRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
    )
    registry.register_rule_class(
        DirectionValidationRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
    )
    registry.register_rule_class(
        TimeProviderUsageRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
    )
    registry.register_rule_class(
        ForbiddenOperationsRule,
        ComponentType.STRATEGY,
        EvaluationLevel.STANDARD,
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
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", help=":briefcase: Portfolio ID")] = None,
    engine: Annotated[str, typer.Option("--engine", "-e", help=":gear: Engine ID")] = None,
    start_date: Annotated[Optional[str], typer.Option("--start", help=":calendar: Start date (YYYY-MM-DD)")] = None,
    end_date: Annotated[Optional[str], typer.Option("--end", help=":calendar: End date (YYYY-MM-DD)")] = None,
    export: Annotated[Optional[str], typer.Option("--export", help=":floppy_disk: Export report to file")] = None,
    min_signals: Annotated[int, typer.Option("--min-signals", help=":signal_strength: Minimum signals per slice")] = 10,
    min_orders: Annotated[int, typer.Option("--min-orders", help=":clipboard: Minimum orders per slice")] = 5,
):
    """
    :chart_with_upwards_trend: Evaluate backtest stability using slice analysis.
    """
    from ginkgo.trading.evaluation import BacktestEvaluator
    from ginkgo.data.operations import get_portfolio_ids_from_analyzer_records, get_engine_ids_from_analyzer_records
    from ginkgo.libs.utils.display import display_dataframe
    
    try:
        # Step 1: Validate inputs or show available options
        if portfolio is None:
            portfolio_ids = get_portfolio_ids_from_analyzer_records()
            if not portfolio_ids:
                console.print(":exclamation: [yellow]No portfolios found in analyzer records.[/yellow]")
                return
                
            console.print("Please specify a portfolio ID. Available portfolios:")
            for pid in portfolio_ids[:10]:  # Show first 10
                console.print(f"  • {pid}")
            if len(portfolio_ids) > 10:
                console.print(f"  ... and {len(portfolio_ids) - 10} more")
            console.print(f"\n[dim]Use: ginkgo evaluation stability --portfolio <portfolio_id>[/dim]")
            return
            
        if engine is None:
            engine_ids = get_engine_ids_from_analyzer_records()
            if not engine_ids:
                console.print(":exclamation: [yellow]No engines found in analyzer records.[/yellow]")
                return
                
            console.print("Please specify an engine ID. Available engines:")
            for eid in engine_ids[:10]:  # Show first 10
                console.print(f"  • {eid}")
            if len(engine_ids) > 10:
                console.print(f"  ... and {len(engine_ids) - 10} more")
            console.print(f"\n[dim]Use: ginkgo evaluation stability --portfolio {portfolio} --engine <engine_id>[/dim]")
            return
            
        # Step 2: Run stability evaluation
        console.print(f":hourglass_flowing_sand: [yellow]Evaluating stability for portfolio {portfolio}, engine {engine}...[/yellow]")
        
        evaluator = BacktestEvaluator(
            min_signals_per_slice=min_signals,
            min_orders_per_slice=min_orders
        )
        
        result = evaluator.evaluate_backtest_stability(
            portfolio_id=portfolio,
            engine_id=engine,
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
    from ginkgo.trading.evaluation import BacktestEvaluator
    
    try:
        console.print(f":hourglass_flowing_sand: [yellow]Creating monitoring baseline from portfolio {portfolio}, engine {engine}...[/yellow]")
        
        evaluator = BacktestEvaluator()
        
        # Run evaluation to get baseline
        result = evaluator.evaluate_backtest_stability(
            portfolio_id=portfolio,
            engine_id=engine,
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
    from ginkgo.trading.evaluation import BacktestEvaluator
    import time
    
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
[bold]Engine:[/bold] {result['engine_id']}
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
