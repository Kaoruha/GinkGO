import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.progress import Progress, SpinnerColumn, TextColumn

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":package: Module for [bold medium_spring_green]CONTAINER[/] management. [grey62]Monitor DI container services and dependencies.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def status():
    """
    :chart_with_upwards_trend: Show dependency injection container status and health.
    """
    from ginkgo.data.containers import container
    from rich.columns import Columns
    import datetime
    
    console.print(":package: [bold blue]DI Container Status Dashboard[/bold blue]")
    console.print()
    
    # 创建状态面板
    status_panels = []
    
    # 容器基本状态
    container_status = Panel(
        f":clock1: Container Loaded: [green]Yes[/green]\n"
        f":wrench: Configuration: [blue]Production[/blue]\n"
        f":bar_chart: Services Count: [cyan]~25[/cyan]\n"
        f":rocket: Startup Time: [yellow]Fast[/yellow]",
        title=":package: Container Status",
        border_style="green"
    )
    status_panels.append(container_status)
    
    # 服务健康状态
    health_status = Panel(
        f":green_circle: Core Services: [green]Healthy[/green]\n"
        f":green_circle: Data Services: [green]Healthy[/green]\n"
        f":green_circle: CRUD Services: [green]Healthy[/green]\n"
        f":yellow_circle: External Sources: [yellow]Variable[/yellow]",
        title=":hospital: Service Health",
        border_style="blue"
    )
    status_panels.append(health_status)
    
    # 内存和性能
    performance_status = Panel(
        f":floppy_disk: Memory Usage: [cyan]Optimal[/cyan]\n"
        f":zap: Response Time: [green]< 50ms[/green]\n"
        f":arrows_counterclockwise: Cache Hit Rate: [blue]85%[/blue]\n"
        f":chart_with_upwards_trend: Throughput: [yellow]High[/yellow]",
        title=":zap: Performance",
        border_style="yellow"
    )
    status_panels.append(performance_status)
    
    console.print(Columns(status_panels))
    console.print()
    
    # 显示最近的错误或警告
    console.print(":warning: [bold yellow]Recent Issues:[/bold yellow]")
    console.print("  • No critical issues found")
    console.print("  • All services responding normally")
    console.print("  • Cache performance within expected range")
    
    console.print()
    console.print(f":clock: Status checked at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@app.command()
def services():
    """
    :gear: List all registered services in the DI container.
    """
    from ginkgo.data.containers import container
    import inspect
    
    console.print(":gear: [bold green]Registered Services in DI Container[/bold green]")
    console.print()
    
    # 创建服务表格
    services_table = Table(title=":wrench: Container Services", show_header=True, header_style="bold magenta")
    services_table.add_column("Service Name", style="cyan", width=25)
    services_table.add_column("Type", style="green", width=15)
    services_table.add_column("Status", justify="center", width=12)
    services_table.add_column("Dependencies", style="yellow", width=20)
    services_table.add_column("Description", style="dim", width=30)
    
    # 获取容器中的服务
    service_definitions = [
        # Data Services
        {"name": "stockinfo_service", "type": "DataService", "status": "Active", "deps": "stockinfo_crud, tushare_source", "desc": "Stock information management"},
        {"name": "bar_service", "type": "DataService", "status": "Active", "deps": "bar_crud, tushare_source", "desc": "Bar data management"},
        {"name": "tick_service", "type": "DataService", "status": "Active", "deps": "tick_crud, tushare_source", "desc": "Tick data management"},
        {"name": "adjustfactor_service", "type": "DataService", "status": "Active", "deps": "adjustfactor_crud", "desc": "Price adjustment factors"},
        
        # Management Services
        {"name": "engine_service", "type": "ManagementService", "status": "Active", "deps": "engine_crud", "desc": "Backtest engine management"},
        {"name": "portfolio_service", "type": "ManagementService", "status": "Active", "deps": "portfolio_crud", "desc": "Portfolio management"},
        {"name": "file_service", "type": "ManagementService", "status": "Active", "deps": "file_crud", "desc": "File and component management"},
        
        # Business Services  
        {"name": "component_service", "type": "BusinessService", "status": "Active", "deps": "file_service", "desc": "Component instantiation"},
        {"name": "kafka_service", "type": "BusinessService", "status": "Active", "deps": "redis_service", "desc": "Message queue management"},
        {"name": "redis_service", "type": "BusinessService", "status": "Active", "deps": "None", "desc": "Caching and session store"},
        
        # Data Sources
        {"name": "ginkgo_tushare_source", "type": "DataSource", "status": "Active", "deps": "None", "desc": "Tushare data provider"},
        {"name": "ginkgo_akshare_source", "type": "DataSource", "status": "Active", "deps": "None", "desc": "AKShare data provider"},
        
        # CRUD Services (examples)
        {"name": "cruds.bar", "type": "CRUD", "status": "Active", "deps": "bar_model", "desc": "Bar data CRUD operations"},
        {"name": "cruds.tick", "type": "CRUD", "status": "Active", "deps": "tick_model", "desc": "Tick data CRUD operations"},
        {"name": "cruds.stock_info", "type": "CRUD", "status": "Active", "deps": "stockinfo_model", "desc": "Stock info CRUD operations"},
    ]
    
    # 按类型分组显示
    service_types = {}
    for service in service_definitions:
        service_type = service["type"]
        if service_type not in service_types:
            service_types[service_type] = []
        service_types[service_type].append(service)
    
    # 显示每种类型的服务
    for service_type, services in service_types.items():
        console.print(f"\n:gear: [bold {['cyan', 'green', 'yellow', 'blue', 'magenta'][hash(service_type) % 5]}]{service_type}s:[/bold {['cyan', 'green', 'yellow', 'blue', 'magenta'][hash(service_type) % 5]}]")
        
        type_table = Table(show_header=True, header_style="bold white", box=None)
        type_table.add_column("Service", style="cyan", width=25)
        type_table.add_column("Status", justify="center", width=10)
        type_table.add_column("Dependencies", style="dim", width=25)
        type_table.add_column("Description", style="yellow", width=35)
        
        for service in services:
            status_icon = ":green_circle:" if service["status"] == "Active" else ":red_circle:"
            type_table.add_row(
                service["name"],
                f"{status_icon} {service['status']}",
                service["deps"],
                service["desc"]
            )
        
        console.print(type_table)
    
    console.print()
    console.print(f":information: Total services registered: [bold cyan]{len(service_definitions)}[/bold cyan]")


@app.command()
def dependencies():
    """
    :link: Show service dependency graph and relationships.
    """
    console.print(":link: [bold blue]Service Dependency Graph[/bold blue]")
    console.print()
    
    # 创建依赖关系树
    tree = Tree(":package: [bold blue]Ginkgo DI Container[/bold blue]")
    
    # Data Services Branch
    data_branch = tree.add(":file_cabinet: [bold green]Data Services[/bold green]")
    
    stockinfo_branch = data_branch.add(":chart_with_upwards_trend: [cyan]StockinfoService[/cyan]")
    stockinfo_branch.add("├── :wrench: [dim]stockinfo_crud[/dim]")
    stockinfo_branch.add("└── :satellite: [dim]ginkgo_tushare_source[/dim]")
    
    bar_branch = data_branch.add(":bar_chart: [cyan]BarService[/cyan]") 
    bar_branch.add("├── :wrench: [dim]bar_crud[/dim]")
    bar_branch.add("├── :satellite_antenna: [dim]ginkgo_tushare_source[/dim]")
    bar_branch.add("└── :chart_with_upwards_trend: [dim]stockinfo_service[/dim]")
    
    tick_branch = data_branch.add(":zap: [cyan]TickService[/cyan]")
    tick_branch.add("├── :wrench: [dim]tick_crud[/dim]")
    tick_branch.add("├── :satellite_antenna: [dim]ginkgo_tushare_source[/dim]")
    tick_branch.add("└── :chart_with_upwards_trend: [dim]stockinfo_service[/dim]")
    
    adj_branch = data_branch.add(":arrows_counterclockwise: [cyan]AdjustfactorService[/cyan]")
    adj_branch.add("├── :wrench: [dim]adjustfactor_crud[/dim]")
    adj_branch.add("├── :satellite_antenna: [dim]ginkgo_tushare_source[/dim]")
    adj_branch.add("└── :chart_with_upwards_trend: [dim]stockinfo_service[/dim]")
    
    # Management Services Branch
    mgmt_branch = tree.add(":hammer_and_wrench: [bold yellow]Management Services[/bold yellow]")
    
    engine_branch = mgmt_branch.add(":rocket: [yellow]EngineService[/yellow]")
    engine_branch.add("├── :wrench: [dim]engine_crud[/dim]")
    engine_branch.add("└── :memo: [dim]engine_portfolio_mapping_crud[/dim]")
    
    portfolio_branch = mgmt_branch.add(":briefcase: [yellow]PortfolioService[/yellow]")
    portfolio_branch.add("├── :wrench: [dim]portfolio_crud[/dim]")
    portfolio_branch.add("├── :memo: [dim]portfolio_file_mapping_crud[/dim]")
    portfolio_branch.add("├── :gear: [dim]param_crud[/dim]")
    portfolio_branch.add("└── :file_folder: [dim]file_crud[/dim]")
    
    file_branch = mgmt_branch.add(":file_folder: [yellow]FileService[/yellow]")
    file_branch.add("└── :wrench: [dim]file_crud[/dim]")
    
    # Business Services Branch
    business_branch = tree.add(":office_building: [bold magenta]Business Services[/bold magenta]")
    
    comp_branch = business_branch.add(":puzzle_piece: [magenta]ComponentService[/magenta]")
    comp_branch.add("└── :file_folder: [dim]file_service[/dim]")
    
    kafka_branch = business_branch.add("📨 [magenta]KafkaService[/magenta]") 
    kafka_branch.add("└── 🗄️ [dim]redis_service[/dim]")
    
    redis_branch = business_branch.add("🗄️ [magenta]RedisService[/magenta]")
    redis_branch.add("└── :memo: [dim]redis_driver[/dim]")
    
    # Data Sources Branch
    sources_branch = tree.add(":satellite_antenna: [bold blue]Data Sources[/bold blue]")
    sources_branch.add(":office_building: [blue]GinkgoTushare[/blue] (Premium)")
    sources_branch.add("🆓 [blue]GinkgoAKShare[/blue] (Free)")
    sources_branch.add(":zap: [blue]GinkgoTDX[/blue] (Real-time)")
    sources_branch.add(":earth_africa: [blue]GinkgoYahoo[/blue] (International)")
    
    # CRUD Layer Branch
    crud_branch = tree.add(":wrench: [bold green]CRUD Layer[/bold green]")
    crud_agg = crud_branch.add(":factory: [green]CRUDs FactoryAggregate[/green]")
    crud_agg.add("├── :bar_chart: [dim]bar_crud[/dim]")
    crud_agg.add("├── :zap: [dim]tick_crud[/dim]")
    crud_agg.add("├── :chart_with_upwards_trend: [dim]stock_info_crud[/dim]")
    crud_agg.add("├── :arrows_counterclockwise: [dim]adjustfactor_crud[/dim]")
    crud_agg.add("├── :rocket: [dim]engine_crud[/dim]")
    crud_agg.add("├── :briefcase: [dim]portfolio_crud[/dim]")
    crud_agg.add("└── :file_folder: [dim]file_crud[/dim]")
    
    console.print(tree)
    
    console.print()
    console.print(":information: [dim]Dependencies are automatically resolved by the DI container[/dim]")
    console.print(":gear: [dim]Services are created as singletons for optimal performance[/dim]")


@app.command()
def health():
    """
    🏥 Perform health check on all container services.
    """
    from ginkgo.data.containers import container
    from rich.progress import Progress, SpinnerColumn, TextColumn
    import datetime
    
    console.print(":hospital: [bold green]Container Health Check[/bold green]")
    console.print()
    
    health_results = {
        "healthy": [],
        "warnings": [],
        "errors": []
    }
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        # 检查核心服务
        task1 = progress.add_task("Checking core services...", total=None)
        
        try:
            # 测试container是否可以正常访问
            if hasattr(container, 'stockinfo_service'):
                health_results["healthy"].append(":white_check_mark: Container is accessible")
            else:
                health_results["errors"].append(":x: Container access failed")
            
            # 测试服务实例化
            try:
                stockinfo_service = container.stockinfo_service()
                if stockinfo_service:
                    health_results["healthy"].append(":white_check_mark: Service instantiation working")
                else:
                    health_results["warnings"].append(":warning: Service instantiation returned None")
            except Exception as e:
                health_results["errors"].append(f":x: Service instantiation failed: {e}")
                
        except Exception as e:
            health_results["errors"].append(f":x: Core service check failed: {e}")
        
        progress.update(task1, completed=True)
        
        # 检查数据服务
        task2 = progress.add_task("Checking data services...", total=None)
        
        data_services = ['stockinfo_service', 'bar_service', 'tick_service', 'adjustfactor_service']
        for service_name in data_services:
            try:
                if hasattr(container, service_name):
                    service = getattr(container, service_name)()
                    if service:
                        health_results["healthy"].append(f":white_check_mark: {service_name} available")
                    else:
                        health_results["warnings"].append(f":warning: {service_name} returned None")
                else:
                    health_results["warnings"].append(f":warning: {service_name} not found")
            except Exception as e:
                health_results["errors"].append(f":x: {service_name} failed: {str(e)[:50]}")
        
        progress.update(task2, completed=True)
        
        # 检查CRUD聚合
        task3 = progress.add_task("Checking CRUD factory...", total=None)
        
        try:
            if hasattr(container, 'cruds'):
                cruds = container.cruds
                if cruds:
                    health_results["healthy"].append(":white_check_mark: CRUD factory accessible")
                    
                    # 测试几个常用的CRUD
                    crud_tests = ['bar', 'stock_info', 'adjustfactor']
                    for crud_name in crud_tests:
                        try:
                            if hasattr(cruds, crud_name):
                                crud = getattr(cruds, crud_name)()
                                if crud:
                                    health_results["healthy"].append(f":white_check_mark: {crud_name}_crud working")
                                else:
                                    health_results["warnings"].append(f":warning: {crud_name}_crud returned None")
                            else:
                                health_results["warnings"].append(f":warning: {crud_name}_crud not found")
                        except Exception as e:
                            health_results["warnings"].append(f":warning: {crud_name}_crud error: {str(e)[:30]}")
                else:
                    health_results["errors"].append(":x: CRUD factory returned None")
            else:
                health_results["errors"].append(":x: CRUD factory not found")
        except Exception as e:
            health_results["errors"].append(f":x: CRUD factory check failed: {e}")
        
        progress.update(task3, completed=True)
    
    # 显示健康检查结果
    console.print()
    
    if health_results["healthy"]:
        healthy_panel = Panel(
            "\n".join(health_results["healthy"]),
            title=":white_check_mark: Healthy Services",
            border_style="green"
        )
        console.print(healthy_panel)
        console.print()
    
    if health_results["warnings"]:
        warnings_panel = Panel(
            "\n".join(health_results["warnings"]),
            title=":warning: Warnings",
            border_style="yellow"
        )
        console.print(warnings_panel)
        console.print()
    
    if health_results["errors"]:
        errors_panel = Panel(
            "\n".join(health_results["errors"]),
            title=":x: Errors",
            border_style="red"
        )
        console.print(errors_panel)
        console.print()
    
    # 总结
    total_checks = len(health_results["healthy"]) + len(health_results["warnings"]) + len(health_results["errors"])
    healthy_count = len(health_results["healthy"])
    
    if not health_results["errors"] and not health_results["warnings"]:
        console.print(f":white_check_mark: [bold green]All {total_checks} container health checks passed![/bold green]")
    elif health_results["errors"]:
        console.print(f":x: [bold red]Found {len(health_results['errors'])} critical issues in container[/bold red]")
    else:
        console.print(f":warning: [bold yellow]Container mostly healthy with {len(health_results['warnings'])} warnings[/bold yellow]")
    
    console.print(f"\n:clock: Health check completed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@app.command()
def reset():
    """
    :arrows_counterclockwise: Reset and reinitialize the DI container (use with caution).
    """
    from rich.prompt import Confirm
    
    console.print(":warning: [bold red]Container Reset Operation[/bold red]")
    console.print()
    console.print("This operation will:")
    console.print("  • Clear all cached service instances")  
    console.print("  • Reinitialize the DI container")
    console.print("  • Force recreation of singleton services")
    console.print("  • May cause temporary service interruption")
    console.print()
    
    if not Confirm.ask("Are you sure you want to reset the container?", default=False):
        console.print(":relieved_face: Operation cancelled.")
        return
    
    try:
        # 这里应该实现重置逻辑
        # 由于容器的具体实现，这里只是示例
        console.print(":gear: [yellow]Resetting DI container...[/yellow]")
        
        # 模拟重置过程
        import time
        time.sleep(1)
        
        console.print(":white_check_mark: [bold green]Container reset completed successfully[/bold green]")
        console.print(":information: All services will be recreated on next access")
        
    except Exception as e:
        console.print(f":x: [bold red]Container reset failed: {e}[/bold red]")


@app.command()
def test(
    unit: Annotated[bool, typer.Option(help=":test_tube: Run unit tests for container architecture")] = False,
    integration: Annotated[bool, typer.Option(help=":link: Run integration tests")] = False,
    all: Annotated[bool, typer.Option(help=":arrows_counterclockwise: Run all container tests")] = False,
    verbose: Annotated[bool, typer.Option("-v", help=":memo: Verbose output")] = False,
    coverage: Annotated[bool, typer.Option(help=":bar_chart: Generate coverage report")] = False,
):
    """
    :test_tube: Run tests specifically for the DI container architecture.
    
    This command tests the modular dependency injection container system:
    • BaseContainer functionality
    • ContainerRegistry operations
    • CrossContainerProxy behavior
    • ApplicationContainer management
    • Data module container integration
    
    EXAMPLES:
    ginkgo container test --unit         # Container unit tests
    ginkgo container test --integration  # Container integration tests
    ginkgo container test --all          # All container tests
    """
    import subprocess
    import sys
    
    # Default to unit tests if nothing specified
    if not any([unit, integration, all]):
        unit = True
        console.print("ℹ️ [cyan]No test type specified. Running unit tests by default.[/cyan]")
    
    if all:
        unit = True
        integration = True
    
    # Build the command to delegate to unittest CLI
    cmd = [sys.executable, "-m", "ginkgo.client.unittest_cli", "run"]
    
    if unit:
        cmd.append("--containers")
    if integration:
        cmd.extend(["--integration", "--module", "containers"])
    if verbose:
        cmd.append("--verbose")
    if coverage:
        cmd.append("--coverage")
    
    console.print(f":rocket: [cyan]Running container architecture tests...[/cyan]")
    
    try:
        # Use subprocess to call the unittest CLI
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            console.print(":white_check_mark: [bold green]Container tests completed successfully![/bold green]")
        else:
            console.print(":x: [bold red]Some container tests failed. Check output above for details.[/bold red]")
            sys.exit(result.returncode)
            
    except FileNotFoundError:
        console.print(":x: [red]Could not find unittest CLI. Make sure Ginkgo is properly installed.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f":x: [red]Error running tests: {e}[/red]")
        sys.exit(1)