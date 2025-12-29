# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 增强回测系统命令，提供config配置管理、strategy策略管理、engine引擎管理和system系统监控功能






"""
Enhanced Backtest CLI Commands

增强回测系统的CLI命令
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import Optional, List
import json
import datetime

from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig, EngineMode, DataFrequency, ConfigTemplates
from ginkgo.backtest.core.containers import container
from ginkgo.client.cli_utils import format_table, format_json

# 创建CLI应用
enhanced_app = typer.Typer(help="增强回测系统命令", name="enhanced")
console = Console()


@enhanced_app.command("config")
def config_commands(
    action: str = typer.Argument(..., help="操作: create, show, templates, optimize"),
    config_file: Optional[str] = typer.Option(None, "--file", "-f", help="配置文件路径"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="配置名称"),
    template: Optional[str] = typer.Option(None, "--template", "-t", help="配置模板"),
    optimize_for: Optional[str] = typer.Option(None, "--optimize", "-o", help="优化目标: large_dataset, realtime")
):
    """配置管理命令"""
    
    if action == "create":
        create_config(config_file, name, template)
    elif action == "show":
        show_config(config_file)
    elif action == "templates":
        show_templates()
    elif action == "optimize":
        optimize_config(config_file, optimize_for)
    else:
        console.print(f"[red]未知操作: {action}[/red]")
        console.print("可用操作: create, show, templates, optimize")


def create_config(config_file: Optional[str], name: Optional[str], template: Optional[str]):
    """创建配置文件"""
    
    if template:
        # 使用模板创建配置
        template_map = {
            "day_trading": ConfigTemplates.day_trading_config,
            "swing_trading": ConfigTemplates.swing_trading_config,
            "long_term": ConfigTemplates.long_term_config,
            "ml_research": ConfigTemplates.ml_research_config
        }
        
        if template not in template_map:
            console.print(f"[red]未知模板: {template}[/red]")
            console.print(f"可用模板: {', '.join(template_map.keys())}")
            return
        
        config = template_map[template]()
        console.print(f"✓ 使用模板 '{template}' 创建配置")
    else:
        # 创建默认配置
        config = BacktestConfig(name=name or "DefaultConfig")
        console.print("✓ 创建默认配置")
    
    # 显示配置信息
    display_config_summary(config)
    
    # 保存到文件
    if config_file:
        config.save_to_file(config_file)
        console.print(f"✓ 配置已保存到: {config_file}")
    else:
        # 显示完整配置
        config_dict = config.to_dict()
        console.print(Panel(format_json(config_dict), title="完整配置"))


def show_config(config_file: Optional[str]):
    """显示配置信息"""
    
    if config_file:
        try:
            config = BacktestConfig.load_from_file(config_file)
        except Exception as e:
            console.print(f"[red]加载配置文件失败: {e}[/red]")
            return
    else:
        # 显示默认配置
        config = BacktestConfig()
        console.print("显示默认配置")
    
    display_config_summary(config)


def display_config_summary(config: BacktestConfig):
    """显示配置摘要"""
    
    table = Table(title="配置摘要")
    table.add_column("参数", style="cyan")
    table.add_column("值", style="green")
    
    table.add_row("名称", config.name)
    table.add_row("描述", config.description)
    table.add_row("时间范围", f"{config.start_date} ~ {config.end_date}")
    table.add_row("引擎模式", config.engine_mode.value)
    table.add_row("数据频率", config.data_frequency.value)
    table.add_row("初始资金", f"¥{config.initial_capital:,.2f}")
    table.add_row("交易成本", f"{config.transaction_cost*100:.3f}%")
    table.add_row("滑点", f"{config.slippage*100:.2f}%")
    table.add_row("止损设置", f"{'启用' if config.enable_stop_loss else '禁用'}")
    table.add_row("止盈设置", f"{'启用' if config.enable_stop_profit else '禁用'}")
    table.add_row("估算内存", f"{config.estimate_memory_usage():.1f}MB")
    
    console.print(table)


def show_templates():
    """显示可用配置模板"""
    
    console.print(Panel("可用配置模板", style="blue"))
    
    templates = [
        ("day_trading", "日内交易", ConfigTemplates.day_trading_config),
        ("swing_trading", "波段交易", ConfigTemplates.swing_trading_config),
        ("long_term", "长期投资", ConfigTemplates.long_term_config),
        ("ml_research", "机器学习研究", ConfigTemplates.ml_research_config)
    ]
    
    table = Table()
    table.add_column("模板名称", style="cyan")
    table.add_column("描述", style="green")
    table.add_column("引擎模式", style="yellow")
    table.add_column("数据频率", style="magenta")
    
    for name, desc, func in templates:
        config = func()
        table.add_row(name, desc, config.engine_mode.value, config.data_frequency.value)
    
    console.print(table)


def optimize_config(config_file: Optional[str], optimize_for: Optional[str]):
    """优化配置"""
    
    if not config_file:
        console.print("[red]请指定配置文件路径[/red]")
        return
    
    try:
        config = BacktestConfig.load_from_file(config_file)
    except Exception as e:
        console.print(f"[red]加载配置文件失败: {e}[/red]")
        return
    
    original_mode = config.engine_mode
    original_memory = config.estimate_memory_usage()
    
    if optimize_for == "large_dataset":
        config.optimize_for_large_dataset()
        console.print("✓ 已优化为大数据集模式")
    elif optimize_for == "realtime":
        config.optimize_for_realtime()
        console.print("✓ 已优化为实时处理模式")
    else:
        console.print(f"[red]未知优化目标: {optimize_for}[/red]")
        console.print("可用优化目标: large_dataset, realtime")
        return
    
    # 显示优化结果
    new_memory = config.estimate_memory_usage()
    
    console.print(f"\n优化结果:")
    console.print(f"  引擎模式: {original_mode.value} → {config.engine_mode.value}")
    console.print(f"  估算内存: {original_memory:.1f}MB → {new_memory:.1f}MB")
    
    # 保存优化后的配置
    config.save_to_file(config_file)
    console.print(f"✓ 优化后的配置已保存到: {config_file}")


@enhanced_app.command("strategy")
def strategy_commands(
    action: str = typer.Argument(..., help="操作: list, create, test"),
    strategy_type: Optional[str] = typer.Option(None, "--type", "-t", help="策略类型"),
    params: Optional[str] = typer.Option(None, "--params", "-p", help="策略参数(JSON格式)")
):
    """策略管理命令"""
    
    if action == "list":
        list_strategies()
    elif action == "create":
        create_strategy(strategy_type, params)
    elif action == "test":
        test_strategy(strategy_type)
    else:
        console.print(f"[red]未知操作: {action}[/red]")
        console.print("可用操作: list, create, test")


def list_strategies():
    """列出可用策略"""
    
    service_info = container.get_service_info()
    strategies = service_info['strategies']
    
    table = Table(title="可用策略")
    table.add_column("策略名称", style="cyan")
    table.add_column("状态", style="green")
    
    for strategy in strategies:
        try:
            # 测试策略是否可以创建
            instance = container.strategies[strategy]()
            status = "✓ 可用"
        except Exception as e:
            status = f"✗ 错误: {str(e)[:30]}"
        
        table.add_row(strategy, status)
    
    console.print(table)


def create_strategy(strategy_type: Optional[str], params: Optional[str]):
    """创建策略实例"""
    
    if not strategy_type:
        console.print("[red]请指定策略类型[/red]")
        list_strategies()
        return
    
    try:
        # 解析参数
        strategy_params = {}
        if params:
            try:
                strategy_params = json.loads(params)
            except json.JSONDecodeError:
                console.print("[red]参数格式错误，请使用有效的JSON格式[/red]")
                return
        
        # 创建策略实例
        strategy = container.strategies[strategy_type](**strategy_params)
        
        console.print(f"✓ 成功创建策略: {strategy_type}")
        console.print(f"  策略名称: {strategy.name}")
        console.print(f"  策略类型: {type(strategy).__name__}")
        
        if strategy_params:
            console.print(f"  策略参数: {strategy_params}")
            
    except Exception as e:
        console.print(f"[red]创建策略失败: {e}[/red]")


def test_strategy(strategy_type: Optional[str]):
    """测试策略"""
    
    if not strategy_type:
        console.print("[red]请指定策略类型[/red]")
        list_strategies()
        return
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(f"测试策略: {strategy_type}", total=None)
            
            # 创建策略实例
            strategy = container.strategies[strategy_type]()
            
            # 基本测试
            assert hasattr(strategy, 'cal'), "策略必须实现cal方法"
            assert hasattr(strategy, 'name'), "策略必须有名称属性"
            
            console.print(f"✓ 策略 {strategy_type} 测试通过")
            console.print(f"  策略名称: {strategy.name}")
            console.print(f"  策略类: {type(strategy).__name__}")
            
    except Exception as e:
        console.print(f"[red]策略测试失败: {e}[/red]")


@enhanced_app.command("engine")
def engine_commands(
    action: str = typer.Argument(..., help="操作: list, create, benchmark"),
    engine_type: Optional[str] = typer.Option(None, "--type", "-t", help="引擎类型"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="配置文件")
):
    """引擎管理命令"""
    
    if action == "list":
        list_engines()
    elif action == "create":
        create_engine(engine_type, config_file)
    elif action == "benchmark":
        benchmark_engines()
    else:
        console.print(f"[red]未知操作: {action}[/red]")
        console.print("可用操作: list, create, benchmark")


def list_engines():
    """列出可用引擎"""
    
    service_info = container.get_service_info()
    engines = service_info['engines']
    
    table = Table(title="可用引擎")
    table.add_column("引擎名称", style="cyan")
    table.add_column("状态", style="green")
    table.add_column("描述", style="yellow")
    
    engine_descriptions = {
        "historic": "基础历史回测引擎",
        "enhanced_historic": "增强历史回测引擎（性能优化）",
        "matrix": "矩阵回测引擎（向量化处理）",
        "live": "实时交易引擎",
        "unified": "统一回测引擎（智能模式选择）"
    }
    
    for engine in engines:
        try:
            # 测试引擎是否可以创建
            instance = container.engines[engine]()
            status = "✓ 可用"
        except Exception as e:
            status = f"✗ 错误: {str(e)[:30]}"
        
        description = engine_descriptions.get(engine, "未知引擎")
        table.add_row(engine, status, description)
    
    console.print(table)


def create_engine(engine_type: Optional[str], config_file: Optional[str]):
    """创建引擎实例"""
    
    if not engine_type:
        console.print("[red]请指定引擎类型[/red]")
        list_engines()
        return
    
    try:
        # 加载配置
        config = BacktestConfig()
        if config_file:
            config = BacktestConfig.load_from_file(config_file)
        
        # 创建引擎实例
        engine = container.engines[engine_type]()
        
        # 设置配置
        if hasattr(engine, 'set_config'):
            engine.set_config(config)
        
        console.print(f"✓ 成功创建引擎: {engine_type}")
        console.print(f"  引擎名称: {engine.name}")
        console.print(f"  引擎类型: {type(engine).__name__}")
        
        if config_file:
            console.print(f"  配置文件: {config_file}")
            
    except Exception as e:
        console.print(f"[red]创建引擎失败: {e}[/red]")


def benchmark_engines():
    """引擎性能基准测试"""
    
    console.print("开始引擎性能基准测试...")
    
    try:
        from test.performance.test_enhanced_backtest_benchmark import PerformanceBenchmark
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("运行性能基准测试", total=None)
            
            benchmark = PerformanceBenchmark()
            results = benchmark.run_full_benchmark()
        
        console.print("✓ 性能基准测试完成")
        
        # 显示结果摘要
        console.print("\n[bold blue]性能测试结果摘要[/bold blue]")
        
        # 引擎创建性能
        if 'engine_creation' in results:
            console.print("\n[cyan]引擎创建性能:[/cyan]")
            for engine_type, result in results['engine_creation'].items():
                console.print(f"  {engine_type:15} | {result['avg_time']*1000:6.2f}ms | {result['memory_per_engine']:6.2f}MB")
        
    except ImportError:
        console.print("[yellow]性能测试模块未找到，跳过基准测试[/yellow]")
    except Exception as e:
        console.print(f"[red]性能基准测试失败: {e}[/red]")


@enhanced_app.command("system")
def system_commands(
    action: str = typer.Argument(..., help="操作: status, info, health"),
):
    """系统状态命令"""
    
    if action == "status":
        show_system_status()
    elif action == "info":
        show_system_info()
    elif action == "health":
        check_system_health()
    else:
        console.print(f"[red]未知操作: {action}[/red]")
        console.print("可用操作: status, info, health")


def show_system_status():
    """显示系统状态"""
    
    console.print(Panel("增强回测系统状态", style="blue"))
    
    # 容器状态
    service_info = container.get_service_info()
    
    table = Table(title="组件状态")
    table.add_column("组件类型", style="cyan")
    table.add_column("可用数量", style="green")
    table.add_column("组件列表", style="yellow")
    
    components = [
        ("引擎", len(service_info['engines']), ", ".join(service_info['engines'])),
        ("策略", len(service_info['strategies']), ", ".join(service_info['strategies'])),
        ("分析器", len(service_info['analyzers']), ", ".join(service_info['analyzers'])),
        ("投资组合", len(service_info['portfolios']), ", ".join(service_info['portfolios']))
    ]
    
    for comp_type, count, items in components:
        table.add_row(comp_type, str(count), items[:50] + "..." if len(items) > 50 else items)
    
    console.print(table)


def show_system_info():
    """显示系统信息"""
    
    console.print(Panel("增强回测系统信息", style="blue"))
    
    info_table = Table()
    info_table.add_column("项目", style="cyan")
    info_table.add_column("值", style="green")
    
    # 系统信息
    import psutil
    import platform
    
    info_table.add_row("Python版本", platform.python_version())
    info_table.add_row("操作系统", platform.system() + " " + platform.release())
    info_table.add_row("CPU核心数", str(psutil.cpu_count()))
    info_table.add_row("内存总量", f"{psutil.virtual_memory().total / (1024**3):.1f}GB")
    
    console.print(info_table)
    
    # 容器信息
    service_info = container.get_service_info()
    console.print(f"\n[cyan]容器服务信息:[/cyan]")
    console.print(f"  引擎类型: {len(service_info['engines'])} 种")
    console.print(f"  策略类型: {len(service_info['strategies'])} 种")
    console.print(f"  分析器类型: {len(service_info['analyzers'])} 种")
    console.print(f"  投资组合类型: {len(service_info['portfolios'])} 种")


def check_system_health():
    """检查系统健康状态"""
    
    console.print(Panel("系统健康检查", style="blue"))
    
    health_status = []
    
    # 检查容器组件
    try:
        service_info = container.get_service_info()
        
        # 测试引擎创建
        for engine_type in ['historic', 'enhanced_historic']:
            try:
                engine = container.engines[engine_type]()
                health_status.append(("引擎", engine_type, "✓ 正常"))
            except Exception as e:
                health_status.append(("引擎", engine_type, f"✗ 错误: {str(e)[:30]}"))
        
        # 测试策略创建
        for strategy_type in ['trend_follow', 'dual_thrust']:
            try:
                strategy = container.strategies[strategy_type]()
                health_status.append(("策略", strategy_type, "✓ 正常"))
            except Exception as e:
                health_status.append(("策略", strategy_type, f"✗ 错误: {str(e)[:30]}"))
        
    except Exception as e:
        health_status.append(("容器", "整体", f"✗ 错误: {str(e)}"))
    
    # 显示健康状态
    table = Table()
    table.add_column("组件类型", style="cyan")
    table.add_column("组件名称", style="yellow")
    table.add_column("状态", style="green")
    
    for comp_type, comp_name, status in health_status:
        color = "red" if "✗" in status else "green"
        table.add_row(comp_type, comp_name, f"[{color}]{status}[/{color}]")
    
    console.print(table)
    
    # 总结
    healthy = all("✓" in status for _, _, status in health_status)
    if healthy:
        console.print("\n[green]✓ 系统健康状态良好[/green]")
    else:
        console.print("\n[red]✗ 系统存在健康问题，请检查上述错误[/red]")


if __name__ == "__main__":
    enhanced_app()