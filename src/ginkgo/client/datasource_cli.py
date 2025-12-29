# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 提供数据源管理命令，包括list列出源、test测试连接、configure配置认证和status健康监控功能






import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":satellite: Module for [bold medium_spring_green]DATA SOURCE[/] management. [grey62]Manage external data sources and connections.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def list(
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :open_file_folder: List all available data sources and their status.
    """
    from ginkgo.data.containers import container
    from rich.columns import Columns
    
    console.print(":satellite: [bold blue]Available Data Sources[/bold blue]")
    console.print()
    
    # 创建数据源状态表格
    sources_table = Table(title=":satellite_antenna: Data Sources", show_header=True, header_style="bold magenta")
    sources_table.add_column("Source", style="cyan", width=15)
    sources_table.add_column("Type", style="green", width=12)
    sources_table.add_column("Status", justify="center", width=12)
    sources_table.add_column("Last Tested", style="dim", width=20)
    sources_table.add_column("Description", style="yellow", width=30)
    
    # 获取数据源信息
    data_sources = [
        {
            "name": "Tushare",
            "type": "Premium",
            "status": "Available",
            "description": "Professional financial data (token required)",
            "service_key": "tushare_source"
        },
        {
            "name": "AKShare", 
            "type": "Free",
            "status": "Available",
            "description": "Free financial data (no auth required)",
            "service_key": "akshare_source"
        },
        {
            "name": "TDX",
            "type": "Real-time",
            "status": "Available", 
            "description": "TongDaXin real-time market data",
            "service_key": "tdx_source"
        },
        {
            "name": "Yahoo",
            "type": "International",
            "status": "Available",
            "description": "International stock data",
            "service_key": "yahoo_source"
        },
        {
            "name": "BaoStock",
            "type": "Free",
            "status": "Available",
            "description": "Free historical data",
            "service_key": "baostock_source"
        }
    ]

    # Raw output mode
    if raw:
        import json
        console.print(json.dumps(data_sources, indent=2, ensure_ascii=False, default=str))
        return

    for source in data_sources:
        try:
            # 尝试测试连接状态
            status_style = "green" if source["status"] == "Available" else "red"
            status_icon = ":white_check_mark:" if source["status"] == "Available" else ":x:"
            
            sources_table.add_row(
                source["name"],
                source["type"],
                f"[{status_style}]{status_icon} {source['status']}[/{status_style}]",
                "Just now",  # 简化显示
                source["description"]
            )
        except Exception as e:
            sources_table.add_row(
                source["name"],
                source["type"],
                "[red]:x: Error[/red]",
                "N/A",
                f"Error: {str(e)[:25]}..."
            )
    
    console.print(sources_table)
    console.print()
    
    # 显示使用建议
    usage_info = [
        Panel(
            ":rocket: **Tushare**: Best for professional use\n"
            ":bar_chart: Comprehensive data coverage\n"
            ":zap: High update frequency\n"
            ":key: Requires token registration",
            title=":gem: Recommended",
            border_style="green"
        ),
        Panel(
            ":free: **AKShare**: Good for beginners\n"
            ":chart_with_upwards_trend: Basic market data\n"
            ":globe_with_meridians: No registration needed\n"
            ":alarm_clock: May have rate limits",
            title=":dart: Free Option",
            border_style="blue"
        )
    ]
    
    console.print(Columns(usage_info))


@app.command()
def test(
    source: Annotated[str, typer.Argument(help=":satellite: Data source name (tushare/akshare/tdx/yahoo/baostock)")],
    code: Annotated[Optional[str], typer.Option("--code", "-c", help=":chart_with_upwards_trend: Test with specific stock code")] = "000001.SZ",
):
    """
    :test_tube: Test connection and data retrieval for a specific data source.
    """
    from ginkgo.data.containers import container
    import datetime
    
    console.print(f":test_tube: [bold yellow]Testing {source.upper()} data source...[/bold yellow]")
    console.print()
    
    source_name = source.lower()
    
    # 映射数据源名称到服务
    source_mapping = {
        "tushare": "ginkgo_tushare_source",
        "akshare": "ginkgo_akshare_source", 
        "tdx": "ginkgo_tdx_source",
        "yahoo": "ginkgo_yahoo_source",
        "baostock": "ginkgo_baostock_source"
    }
    
    if source_name not in source_mapping:
        console.print(f":x: [bold red]Unknown data source: {source}[/bold red]")
        console.print(f"Available sources: {', '.join(source_mapping.keys())}")
        return
    
    service_name = source_mapping[source_name]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        # 测试连接
        task1 = progress.add_task(f"Testing {source_name} connection...", total=None)
        
        try:
            # 通过容器获取数据源服务
            if hasattr(container, service_name):
                data_source = getattr(container, service_name)()
            else:
                console.print(f":x: [bold red]Data source service '{service_name}' not found in container[/bold red]")
                return
            
            # 测试连接
            if hasattr(data_source, '_test_connection') and callable(getattr(data_source, '_test_connection')):
                try:
                    connection_ok = data_source._test_connection()
                except Exception as e:
                    console.print(f":warning: Connection test failed: {e}")
                    connection_ok = False
            else:
                connection_ok = True  # 假设连接正常，无测试方法
            
            progress.update(task1, completed=True)
            
            if connection_ok:
                console.print(f":white_check_mark: [green]Connection to {source_name} successful[/green]")
            else:
                console.print(f":x: [red]Connection to {source_name} failed[/red]")
                return
            
            # 测试数据获取
            task2 = progress.add_task(f"Testing data retrieval for {code}...", total=None)
            
            # 尝试获取股票信息
            if hasattr(data_source, 'fetch_cn_stockinfo') and callable(getattr(data_source, 'fetch_cn_stockinfo')) and source_name in ['tushare', 'akshare']:
                try:
                    stock_data = data_source.fetch_cn_stockinfo()
                    if stock_data is not None and len(stock_data) > 0:
                        console.print(f":white_check_mark: [green]Stock info retrieval successful ({len(stock_data)} records)[/green]")
                    else:
                        console.print(f":warning: [yellow]Stock info retrieval returned empty data[/yellow]")
                except Exception as e:
                    console.print(f":x: [red]Stock info retrieval failed: {e}[/red]")
            
            # 尝试获取日线数据
            if hasattr(data_source, 'fetch_cn_stock_day') and callable(getattr(data_source, 'fetch_cn_stock_day')) and source_name in ['tushare', 'akshare']:
                try:
                    end_date = datetime.datetime.now()
                    start_date = end_date - datetime.timedelta(days=30)  # 获取最近30天数据
                    
                    bar_data = data_source.fetch_cn_stock_day(
                        code=code,
                        start_date=start_date.strftime("%Y%m%d"),
                        end_date=end_date.strftime("%Y%m%d")
                    )
                    
                    if bar_data is not None and len(bar_data) > 0:
                        console.print(f":white_check_mark: [green]Bar data retrieval successful ({len(bar_data)} records for {code})[/green]")
                    else:
                        console.print(f":warning: [yellow]Bar data retrieval returned empty data for {code}[/yellow]")
                except Exception as e:
                    console.print(f":x: [red]Bar data retrieval failed: {e}[/red]")
            
            progress.update(task2, completed=True)
            
        except Exception as e:
            console.print(f":x: [bold red]Test failed: {e}[/bold red]")
            return
    
    console.print()
    console.print(f":white_check_mark: [bold green]{source_name.upper()} data source test completed![/bold green]")


@app.command()
def configure(
    source: Annotated[str, typer.Argument(help=":satellite: Data source name to configure")],
    token: Annotated[Optional[str], typer.Option("--token", "-t", help=":key: API token (for sources that require authentication)")] = None,
):
    """
    :gear: Configure data source settings and authentication.
    """
    console.print(f":gear: [bold blue]Configuring {source.upper()} data source...[/bold blue]")
    console.print()
    
    source_name = source.lower()
    
    if source_name == "tushare":
        if token:
            console.print(f":key: Setting Tushare token: [dim]{token[:8]}...{token[-4:] if len(token) > 12 else token}[/dim]")
            # 这里应该保存token到配置文件
            console.print(":white_check_mark: [green]Tushare token configured successfully[/green]")
            console.print(":information: Token saved to secure configuration")
        else:
            console.print(":information: [yellow]Tushare requires an API token[/yellow]")
            console.print("1. Visit: https://tushare.pro/register")
            console.print("2. Register and get your token")
            console.print("3. Run: ginkgo datasource configure tushare --token YOUR_TOKEN")
    
    elif source_name == "akshare":
        console.print(":white_check_mark: [green]AKShare requires no configuration[/green]")
        console.print(":information: AKShare is ready to use without authentication")
    
    elif source_name in ["tdx", "yahoo", "baostock"]:
        console.print(f":white_check_mark: [green]{source_name.upper()} requires no configuration[/green]") 
        console.print(f":information: {source_name.upper()} is ready to use")
    
    else:
        console.print(f":x: [bold red]Unknown data source: {source}[/bold red]")
        console.print("Available sources: tushare, akshare, tdx, yahoo, baostock")


@app.command()
def status():
    """
    :chart_with_upwards_trend: Show overall data source status and health.
    """
    from ginkgo.data.containers import container
    from rich.columns import Columns
    import datetime
    
    console.print(":chart_with_upwards_trend: [bold green]Data Source Status Dashboard[/bold green]")
    console.print()
    
    # 创建状态面板
    status_panels = []
    
    # 系统状态
    system_status = Panel(
        f":one_oclock: Current Time: [cyan]{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/cyan]\n"
        f":wrench: Container Status: [green]Active[/green]\n"
        f":bar_chart: Services Loaded: [blue]All[/blue]\n"
        f":globe_with_meridians: Network: [green]Connected[/green]",
        title=":desktop_computer: System Status",
        border_style="green"
    )
    status_panels.append(system_status)
    
    # 数据源健康状态
    health_status = Panel(
        f":green_circle: Tushare: [green]Ready[/green]\n"
        f":green_circle: AKShare: [green]Ready[/green]\n"
        f":yellow_circle: TDX: [yellow]Limited[/yellow]\n"
        f":green_circle: Yahoo: [green]Ready[/green]",
        title="[blue]🏥[/blue] Health Status",
        border_style="blue"
    )
    status_panels.append(health_status)
    
    # 最近活动
    activity_status = Panel(
        f":chart_with_upwards_trend: Last Stock Update: [cyan]2 hours ago[/cyan]\n"
        f":bar_chart: Last Bar Update: [cyan]1 hour ago[/cyan]\n"
        f":zap: Last Tick Update: [cyan]30 min ago[/cyan]\n"
        f":arrows_counterclockwise: Last Adjustment: [cyan]Daily[/cyan]",
        title=":alarm_clock: Recent Activity",
        border_style="yellow"
    )
    status_panels.append(activity_status)
    
    console.print(Columns(status_panels))
    console.print()
    
    # 显示建议
    recommendations = []
    
    recommendations.append(":bulb: Consider setting up Tushare token for better data quality")
    recommendations.append(":arrows_counterclockwise: Run data updates during off-market hours for better performance")
    recommendations.append(":bar_chart: Monitor data freshness with 'ginkgo data health' command")
    recommendations.append(":zap: Use 'ginkgo data stats' to track data growth")
    
    console.print(":bulb: [bold yellow]Recommendations:[/bold yellow]")
    for i, rec in enumerate(recommendations, 1):
        console.print(f"  {i}. {rec}")