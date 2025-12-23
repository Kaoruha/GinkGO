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
    run_id: Annotated[
        Optional[str], typer.Option("--run-id", "-r", case_sensitive=True, help="Run session ID.")
    ] = None,
    engine: Annotated[
        Optional[str], typer.Option("--engine", "-e", case_sensitive=True, help="Engine ID.")
    ] = None,
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", case_sensitive=True, help="Portfolio ID.")
    ] = None,
    analyzer: Annotated[
        Optional[str], typer.Option("--analyzer", "-a", case_sensitive=True, help="Analyzer name.")
    ] = None,
    mode: Annotated[DisplayMode, typer.Option("--mode", "-m", help="Display mode: table/terminal/plot")] = DisplayMode.table,
    page_size: Annotated[int, typer.Option("--page", help="Items per page")] = 20,
    interactive: Annotated[bool, typer.Option("--interactive", "-i", help="Enable interactive pagination")] = False,
    max_points: Annotated[int, typer.Option("--max-points", "-M", help="Max data points per page for terminal mode")] = 50,
    output: Annotated[Optional[str], typer.Option("--output", "-o", help="Output file path (only for plot mode)")] = None,
):
    """
    :open_file_folder: Analyze [bold medium_spring_green]BACKTEST[/] with plot.

    Examples:
        # 按运行会话查询（新方式）
        ginkgo result show --run-id eng_abc_r_251223_1200_001

        # 按引擎/投资组合/分析器查询（旧方式）
        ginkgo result show --engine present_engine --portfolio present_portfolio --analyzer net_value

        # 使用终端绘图显示
        ginkgo result show --run-id xxx --mode terminal
    """
    from ginkgo.data.containers import container
    from ginkgo.enums import FILE_TYPES

    # 新方式：按 run_id 查询
    if run_id is not None:
        _show_by_run_id(run_id, portfolio, analyzer, mode, page_size, interactive, max_points, output)
        return

    # 旧方式：按 engine/portfolio/analyzer 查询
    from ginkgo.data.operations import (
        get_engines_page_filtered,
        get_portfolio_file_mappings_page_filtered,
        get_analyzer_records_page_filtered,
    )

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
        # 使用新的Service API获取引擎-投资组合映射
        engine_service = container.engine_service()
        mappings_result = engine_service.get_engine_portfolio_mappings(engine)

        if mappings_result.success:
            mappings_df = mappings_result.data
            if hasattr(mappings_df, 'to_dataframe'):
                mappings_df = mappings_df.to_dataframe()
        else:
            console.print(f":x: Failed to get engine-portfolio mappings: {mappings_result.error}")
            mappings_df = pd.DataFrame()  # 空DataFrame作为fallback
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
        from ginkgo.trading.plots.result_plot import ResultPlot
        
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


def _show_by_run_id(
    run_id: str,
    portfolio_id: Optional[str],
    analyzer_name: Optional[str],
    mode: DisplayMode,
    page_size: int,
    interactive: bool,
    max_points: int,
    output_path: Optional[str]
):
    """
    按 run_id 查询并显示结果（新方式）

    Args:
        run_id: 运行会话ID
        portfolio_id: 投资组合ID（可选）
        analyzer_name: 分析器名称（可选）
        mode: 显示模式
        page_size: 每页条数
        interactive: 是否交互式
        max_points: 终端模式最大点数
        output_path: 输出文件路径
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import (
        display_dataframe,
        display_dataframe_interactive,
        display_terminal_chart,
        display_terminal_chart_interactive
    )

    result_service = container.result_service()

    # 如果没有指定 portfolio，先列出可用的 portfolio
    if portfolio_id is None:
        summary_result = result_service.get_run_summary(run_id)
        if not summary_result.success:
            console.print(f":x: [red]未找到 run_id={run_id} 的记录[/red]")
            console.print(f"[yellow]{summary_result.error}[/yellow]")
            return

        summary = summary_result.data
        console.print(f":information_source: [bold]运行会话摘要:[/bold]")
        console.print(f"  Run ID: {summary['run_id']}")
        console.print(f"  Engine ID: {summary['engine_id']}")
        console.print(f"  总记录数: {summary['total_records']}")
        console.print(f"  时间范围: {summary['time_range']['start']} ~ {summary['time_range']['end']}")
        console.print("")

        # 显示可用的 portfolio
        if summary['portfolio_count'] > 1:
            console.print(f":briefcase: [bold]可用的投资组合 ({summary['portfolio_count']}个):[/bold]")
            for pid in summary['portfolios']:
                console.print(f"  - {pid}")
            console.print("")
            console.print("[yellow]请使用 --portfolio 参数指定投资组合[/yellow]")
            return
        else:
            portfolio_id = summary['portfolios'][0]
            console.print(f":briefcase: [cyan]使用投资组合: {portfolio_id}[/cyan]")
            console.print("")

    # 如果没有指定 analyzer，先列出可用的 analyzer
    if analyzer_name is None:
        analyzers_result = result_service.get_portfolio_analyzers(run_id, portfolio_id)
        if not analyzers_result.success:
            console.print(f":x: [red]获取 analyzer 列表失败[/red]")
            return

        analyzers = analyzers_result.data
        if len(analyzers) > 1:
            console.print(f":bar_chart: [bold]可用的分析器 ({len(analyzers)}个):[/bold]")
            for name in analyzers:
                console.print(f"  - {name}")
            console.print("")
            console.print("[yellow]请使用 --analyzer 参数指定分析器[/yellow]")
            return
        else:
            analyzer_name = analyzers[0]
            console.print(f":bar_chart: [cyan]使用分析器: {analyzer_name}[/cyan]")
            console.print("")

    # 获取数据
    data_result = result_service.get_analyzer_values(
        run_id=run_id,
        portfolio_id=portfolio_id,
        analyzer_name=analyzer_name,
        as_dataframe=True
    )

    if not data_result.success:
        console.print(f":x: [red]获取数据失败[/red]")
        console.print(f"[yellow]{data_result.error}[/yellow]")
        return

    result_df = data_result.data

    if result_df is None or result_df.shape[0] == 0:
        console.print(":exclamation: [yellow]没有数据可显示[/yellow]")
        return

    # 根据模式显示结果
    if mode == DisplayMode.table:
        analyzer_columns_config = {
            "timestamp": {"display_name": "Date", "style": "cyan"},
            "business_timestamp": {"display_name": "Business Time", "style": "dim"},
            "value": {"display_name": "Value", "style": "yellow"}
        }
        title = f":bar_chart: [bold]{analyzer_name}[/bold] [dim]({run_id})[/dim]"

        if interactive:
            display_dataframe_interactive(
                data=result_df,
                columns_config=analyzer_columns_config,
                title=title,
                page_size=page_size,
                enable_interactive=True,
                console=console
            )
        else:
            display_dataframe(
                data=result_df,
                columns_config=analyzer_columns_config,
                title=title,
                console=console
            )

    elif mode == DisplayMode.terminal:
        console.print(f"[dim]数据概览: {result_df.shape[0]} 条记录[/dim]")

        title = f"{analyzer_name} [{run_id}]"

        if interactive:
            display_terminal_chart_interactive(
                data=result_df,
                title=title,
                max_points_per_page=max_points,
                enable_interactive=True,
                console=console
            )
        else:
            display_terminal_chart(
                data=result_df,
                title=title,
                max_points=max_points,
                console=console
            )

    elif mode == DisplayMode.plot:
        _display_plot_mode(result_df, output_path)


@app.command(name="export")
def export():
    print("export results")


@app.command(name="remove")
def remove():
    print("remove results")
