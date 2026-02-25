# 优化版main.py - 单一入口，延迟加载所有重型依赖
def _get_imports():
    """获取需要的重型导入"""
    global typer, subprocess, time, math, datetime, click, os, Enum, typing_list, Annotated, Console, Table, print
    if 'typer' not in globals():
        import typer
        import subprocess
        import time
        import math
        import datetime
        import click
        import os
        from enum import Enum
        from typing import List as typing_list
        from typing_extensions import Annotated
        from rich.console import Console
        from rich.table import Table
        from rich import print
    return typer, Console

# 懒加载CLI模块
def _lazy_import_cli(module_name):
    """延迟导入CLI模块"""
    if module_name == 'components_cli':
        from ginkgo.client import components_cli
        return components_cli
    elif module_name == 'analysis_cli':
        from ginkgo.client import analysis_cli
        return analysis_cli
    # infrastructure_cli has been removed, functionality moved to config_cli
    elif module_name == 'dev_cli':
        from ginkgo.client import dev_cli
        return dev_cli
    elif module_name == 'test_cli':
        from ginkgo.client import test_cli
        return test_cli
    # Additional modules that may have unique functionality
    elif module_name == 'config_cli':
        from ginkgo.client import config_cli
        return config_cli
    # param_cli has been replaced by flat_cli.param_app
    elif module_name == 'kafka_cli':
        from ginkgo.client import kafka_cli
        return kafka_cli
    elif module_name == 'datasource_cli':
        from ginkgo.client import datasource_cli
        return datasource_cli
    elif module_name == 'container_cli':
        from ginkgo.client import container_cli
        return container_cli
    elif module_name == 'cache_cli':
        from ginkgo.client import cache_cli
        return cache_cli
    elif module_name == 'record_cli':
        from ginkgo.client import record_cli
        return record_cli
    elif module_name == 'interactive_cli':
        from ginkgo.client import interactive_cli
        return interactive_cli
    elif module_name == 'enhanced_cli':
        from ginkgo.client import enhanced_cli
        return enhanced_cli
    else:
        raise ImportError(f"Unknown CLI module: {module_name}")

# 延迟创建main app
def _create_main_app():
    """延迟创建main app，避免启动时导入typer"""
    typer, Console = _get_imports()
    
    return typer.Typer(
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,  # 禁用自动补全
    help="""
:rocket: [bold green]Ginkgo[/bold green] - Modern Quantitative Trading Platform

[bold blue]Quick Examples:[/bold blue]
  [cyan]ginkgo init[/cyan]                           Initialize Ginkgo
  [cyan]ginkgo data get stockinfo[/cyan]              Get stock data
  [cyan]ginkgo data get stockinfo --page-size 20[/cyan]  List stocks with pagination
  [cyan]ginkgo engine list[/cyan]                     List engines
  [cyan]ginkgo portfolio list[/cyan]                  List portfolios
  [cyan]ginkgo status[/cyan]                          Check status
"""
)

# 全局变量
_main_app = None
console = None

def get_main_app():
    """延迟创建main app实例"""
    global _main_app, console
    if _main_app is None:
        _main_app = _create_main_app()
        typer, Console = _get_imports()
        console = Console()
        _register_all_commands()
    return _main_app

def _register_all_commands():
    """注册所有命令到main_app - 优化版本"""

    # 获取typer依赖
    typer, Console = _get_imports()

    # Direct import of core commands to preserve typer signatures
    from ginkgo.client import core_cli

    # 延迟加载typer应用
    def _create_lazy_typer(module_name, app_name="app"):
        class LazyTyper:
            def __init__(self, module_name, app_name):
                self.module_name = module_name
                self.app_name = app_name
                self._app = None

            @property
            def app(self):
                if self._app is None:
                    module = _lazy_import_cli(self.module_name)
                    self._app = getattr(module, self.app_name)
                return self._app

            def __call__(self, *args, **kwargs):
                return self.app(*args, **kwargs)

        return LazyTyper(module_name, app_name).app

    # 新的模块化命令架构 - 使用独立的CLI文件
    from ginkgo.client import data_cli, engine_cli, portfolio_cli, param_cli, kafka_cli, worker_cli, mongo_cli, user_cli, group_cli, templates_cli, notify_cli, livecore_cli, execution_cli, scheduler_cli, tasktimer_cli, config_cli, serve_cli

    _main_app.add_typer(data_cli.app, name="data", help=":page_facing_up: Data management")
    _main_app.add_typer(engine_cli.app, name="engine", help=":fire: Engine management")
    _main_app.add_typer(portfolio_cli.app, name="portfolio", help=":bank: Portfolio management")
    _main_app.add_typer(param_cli.app, name="param", help=":wrench: Parameter management")
    _main_app.add_typer(kafka_cli.app, name="kafka", help=":satellite: Kafka queue management")
    _main_app.add_typer(worker_cli.app, name="worker", help=":gear: Worker management")
    _main_app.add_typer(mongo_cli.app, name="mongo", help=":leaf: MongoDB management")
    _main_app.add_typer(user_cli.app, name="user", help=":bust_in_silhouette: User management")
    _main_app.add_typer(group_cli.app, name="group", help=":people_hugging: User group management")
    _main_app.add_typer(templates_cli.app, name="templates", help=":memo: Notification template management")
    _main_app.add_typer(notify_cli.app, name="notify", help=":bell: Notification sending")
    _main_app.add_typer(livecore_cli.app, name="livecore", help=":rocket: LiveCore - Live Trading Container")
    _main_app.add_typer(execution_cli.app, name="execution", help=":execution: ExecutionNode - Portfolio Execution Engine")
    _main_app.add_typer(scheduler_cli.app, name="scheduler", help=":calendar: Scheduler - Portfolio Dynamic Scheduler")
    _main_app.add_typer(tasktimer_cli.app, name="tasktimer", help=":alarm_clock: TaskTimer - Scheduled Task Manager")
    _main_app.add_typer(config_cli.app, name="config", help=":gear: Configuration management")

    # Serve commands (api, webui, worker-data, worker-backtest, etc.)
    _main_app.add_typer(serve_cli.app, name="serve", help=":rocket: Start services in foreground")

    # Validation command (component code validation before backtesting)
    from ginkgo.client.validation_cli import validate, console
    _main_app.command(name="validate", help=":white_check_mark: Component validation (code check)")(validate)

    # Note: validation_cli.app is NOT added as a typer to avoid double 'validate' command
    # from ginkgo.client import validation_cli
    # _main_app.add_typer(validation_cli.app, name="validate", help=":white_check_mark: Strategy validation (code check)")

    # Evaluation command (backtest result analysis and monitoring)
    from ginkgo.client import evaluation_cli
    _main_app.add_typer(evaluation_cli.app, name="eval", help=":chart_with_upwards_trend: Backtest evaluation & monitoring")

    # 暂时保留flat_cli中的其他功能
    from ginkgo.client import flat_cli
    _main_app.add_typer(flat_cli.component_app, name="component", help=":wrench: Component management")
    _main_app.add_typer(flat_cli.mapping_app, name="mapping", help=":link: Mapping relationship management")
    _main_app.add_typer(flat_cli.result_app, name="result", help=":bar_chart: Result management")

    # 组件管理已整合到统一命令架构中 (get/list/create/delete/update components)

    # 最后注册核心命令，确保顺序一致并简化help文本
    _main_app.command(name="init", help=":rocket: Initialize system")(core_cli.init if hasattr(core_cli, 'init') else lambda: None)
    _main_app.command(name="status", help=":bar_chart: System status")(core_cli.status)
    _main_app.command(name="version", help=":rabbit: Version info")(core_cli.version if hasattr(core_cli, 'version') else lambda: None)
    _main_app.command(name="debug", help=":bug: Toggle debug mode")(core_cli.debug if hasattr(core_cli, 'debug') else lambda: None)
    # serve 命令已移到 serve_cli.app (包含 api, webui, worker-data, worker-backtest 等子命令)
    # Configuration 已整合到 get/set config 命令中

    # Add standalone version command (if not available in core_cli)
    if not hasattr(core_cli, 'version') or core_cli.version is None:
        @_main_app.command()
        def version():
            """
            :rabbit: Display version info
            """
            import sys
            from pathlib import Path

            config_path = Path(__file__).parent / "src" / "ginkgo" / "config"
            sys.path.insert(0, str(config_path))

            try:
                import package
                print(f"✨ {package.PACKAGENAME} {package.VERSION}")
            except ImportError:
                try:
                    from ginkgo.config.package import PACKAGENAME, VERSION
                    print(f"✨ {PACKAGENAME} {VERSION}")
                except ImportError:
                    print("✨ ginkgo 0.8.1")
            finally:
                if str(config_path) in sys.path:
                    sys.path.remove(str(config_path))

if __name__ == "__main__":
    import sys
    
    # 快速路径：version命令优化
    if len(sys.argv) == 2 and sys.argv[1] in ["version", "--version"]:
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / "src" / "ginkgo" / "config"
            sys.path.insert(0, str(config_path))
            import package
            print(f"✨ {package.PACKAGENAME} {package.VERSION}")
            sys.path.remove(str(config_path))
        except:
            print("✨ ginkgo 0.8.1")
        sys.exit(0)
    
    # 正常路径：加载完整的CLI
    main_app = get_main_app()
    main_app()