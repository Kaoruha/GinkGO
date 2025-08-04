import typer
from enum import Enum
from typing import List as typing_list, Optional, TYPE_CHECKING
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.console import Console

# Type-only imports for faster CLI startup
if TYPE_CHECKING:
    import pandas as pd

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":roll_of_paper: Manage [bold medium_spring_green]RESULT[/]. [grey62][/]",
    no_args_is_help=True,
)
console = Console()


class DisplayMode(str, Enum):
    table = "table"
    terminal = "terminal" 
    plot = "plot"


@app.command(name="list")
def list():
    print("list results")


@app.command(name="show")
def show(
    engine: Annotated[str, typer.Option(..., "--engine", "-e", "--e", case_sensitive=True, help="Engine ID.")] = None,
    portfolio: Annotated[
        str, typer.Option(..., "--portfolio", "-p", "--p", case_sensitive=True, help="Portfolio ID.")
    ] = None,
    analyzer: Annotated[
        str, typer.Option(..., "--analyzer", "-a", "--a", case_sensitive=True, help="Analyzer ID.")
    ] = None,
    mode: Annotated[DisplayMode, typer.Option("--mode", "-m", help="Display mode: table/terminal/plot")] = DisplayMode.table,
    page_size: Annotated[int, typer.Option("--page", "-p", help="Items per page")] = 20,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Enable interactive pagination")] = False,
    max_points: Annotated[int, typer.Option("--max-points", "-M", help="Max data points per page for terminal mode")] = 50,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output file path (only for plot mode)")] = None,
):
    """
    :open_file_folder: Analyze [bold medium_spring_green]BACKTEST[/] with plot.
    """
    from ginkgo.data.operations import (
        get_engines_page_filtered,
        get_portfolio_file_mappings_page_filtered,
        get_analyzer_records_page_filtered,
    )
    from ginkgo.data import get_engine_portfolio_mappings
    from ginkgo.enums import FILE_TYPES

    if engine is None:
        engines_df = get_engines_page_filtered()
        msg = "You could choose engine below with param --engine"
        console.print(msg)
        # 配置列显示
        engines_columns_config = {
            "uuid": {"display_name": "Engine ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "desc": {"display_name": "Description", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=engines_df,
            columns_config=engines_columns_config,
            title=":wrench: [bold]Available Engines:[/bold]",
            console=console
        )
        return
    if portfolio is None:
        mappings_df = get_engine_portfolio_mappings(engine)
        msg = "You could choose portfolio below with param --portfolio"
        console.print(msg)
        
        columns = {
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "portfolio_name": {"display_name": "Name", "style": "cyan"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        if mappings_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No portfolios found for this engine.[/yellow]")
        else:
            display_dataframe(
                data=mappings_df,
                columns_config=columns,
                title=":briefcase: [bold]Portfolios for Engine:[/bold]",
                console=console
            )
        return

    if analyzer is None:
        analyzers_df = get_portfolio_file_mappings_page_filtered(portfolio_id=portfolio, type=FILE_TYPES.ANALYZER)
        msg = "You could choose analyzer below with param --analyzer"
        console.print(msg)
        
        columns = {
            "file_id": {"display_name": "Analyzer ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        if analyzers_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No analyzers found for this portfolio.[/yellow]")
        else:
            display_dataframe(
                data=analyzers_df,
                columns_config=columns,
                title=":bar_chart: [bold]Analyzers for Portfolio:[/bold]",
                console=console
            )
        return

    result = get_analyzer_records_page_filtered(portfolio_id=portfolio, engine_id=engine, analyzer_id=analyzer)

    if result.shape[0] == 0:
        console.print("There is no data. Please run backtest first.")
        return

    # 根据模式显示结果
    if mode == DisplayMode.table:
        # 配置列显示 - 只显示日期和值
        analyzer_columns_config = {
            "timestamp": {"display_name": "Date", "style": "cyan"},
            "value": {"display_name": "Value", "style": "yellow"}
        }
        title = ":bar_chart: [bold]Analyzer Records[/bold]"
        
        if interactive:
            from ginkgo.libs.utils.display import display_dataframe_interactive
            display_dataframe_interactive(
                data=result,
                columns_config=analyzer_columns_config,
                title=title,
                page_size=page_size,
                enable_interactive=True,
                console=console
            )
        else:
            display_dataframe(
                data=result,
                columns_config=analyzer_columns_config,
                title=title,
                console=console
            )
            
    elif mode == DisplayMode.terminal:
        # 调试信息：显示数据结构
        console.print(f"[dim]数据概览: {result.shape[0]} 条记录，列: {result.columns.tolist()}[/dim]")
        
        # 创建标题
        title = result.iloc[0]["name"] if result.shape[0] > 0 and "name" in result.columns else "Analyzer Result"
        
        if interactive:
            from ginkgo.libs.utils.display import display_terminal_chart_interactive
            display_terminal_chart_interactive(
                data=result,
                title=title,
                max_points_per_page=max_points,
                enable_interactive=True,
                console=console
            )
        else:
            from ginkgo.libs.utils.display import display_terminal_chart
            display_terminal_chart(
                data=result,
                title=title,
                max_points=max_points,
                console=console
            )
        
    elif mode == DisplayMode.plot:
        _display_plot_mode(result, output)




def _display_plot_mode(result: "pd.DataFrame", output_path: Optional[str]):
    """matplotlib图表模式显示"""
    try:
        from ginkgo.backtest.plots.result_plot import ResultPlot
        
        # 准备数据格式 (ResultPlot需要特定格式)
        analyzer_name = result.iloc[0]["name"] if result.shape[0] > 0 else "Analyzer"
        data = [{analyzer_name: result}]
        labels = ["Backtest Result"]
        
        # 创建并显示图表
        plot = ResultPlot(f"Analyzer: {analyzer_name}")
        plot.update_data("", data, labels)
        
        # 根据是否有输出路径决定显示或保存
        if output_path:
            try:
                # 确保导出目录存在
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                
                plot.save_plot(output_path)
                console.print(f":white_check_mark: [green]Plot saved to:[/green] {output_path}")
            except Exception as e:
                console.print(f":x: [red]Failed to save plot:[/red] {e}")
        else:
            # 只有没有输出路径时才显示窗口
            plot.show()
        
    except ImportError as e:
        console.print(f":warning: [yellow]matplotlib not available: {e}[/yellow]")
        console.print("Falling back to table mode.")
        console.print("")
        _display_table_mode(result, 50)
    except Exception as e:
        console.print(f":x: [red]Failed to create plot:[/red] {e}")
        console.print("Falling back to table mode.")
        console.print("")
        _display_table_mode(result, 50)


@app.command(name="export")
def export():
    print("export results")


@app.command(name="remove")
def remove():
    print("remove results")
