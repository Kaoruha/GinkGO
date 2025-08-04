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
    from ginkgo.backtest.evaluation import BacktestEvaluator
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
    from ginkgo.backtest.evaluation import BacktestEvaluator
    
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
    from ginkgo.backtest.evaluation import BacktestEvaluator
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