# Upstream: CLI主入口(ginkgo engine命令调用)
# Downstream: EngineService/PortfolioService/MappingService/EngineAssemblyService(引擎/组合/映射/装配服务)、FileCRUD/EnginePortfolioMappingCRUD/PortfolioFileMappingCRUD/ParamCRUD(CRUD操作)、Rich库(表格/进度/面板显示)、psutil(进程监控)
# Role: 引擎管理CLI提供列表/创建/查看/状态/运行/删除/绑定/解绑等生命周期管理






"""
Ginkgo Engine CLI - 引擎管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns
from decimal import Decimal

# 导入辅助函数（从 engine_cli_helpers.py 提取）
from ginkgo.client.engine_cli_helpers import (
    resolve_engine_id,
    generate_backtest_analysis,
    collect_component_info,
    display_component_tree,
    _get_component_file_content,
    _is_param_for_component,
)

app = typer.Typer(help=":fire: Engine management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command("list")
def list_engines(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio ID"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter engines (search in id, name, type, status)"),
    limit: int = typer.Option(20, "--limit", "-l", help="Page size"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :clipboard: List all engines.
    """
    from ginkgo.data.containers import container

    console.print(":clipboard: Listing engines...")

    try:
        engine_service = container.engine_service()

        # Use fuzzy_search if filter is provided (database-level OR search)
        if filter:
            # Convert filter to string if needed
            filter_str = str(filter) if not isinstance(filter, str) else filter
            # Use database-level fuzzy search
            result = engine_service.fuzzy_search(filter_str, fields=['uuid', 'name', 'is_live', 'status'])
        elif status:
            # If only status filter, use database-level filtering
            from ginkgo.enums import ENGINESTATUS_TYPES
            try:
                # Try to convert status string to enum
                status_enum = ENGINESTATUS_TYPES.validate_input(status.upper())
                result = engine_service.get(status=status_enum)
            except Exception as e:
                from ginkgo.libs import GLOG
                GLOG.ERROR(f"Failed to convert status filter '{status}' to enum, falling back to application-level filtering: {e}")
                # If conversion fails, fall back to application-level filtering
                result = engine_service.get()
        else:
            # Get all engines
            result = engine_service.get()

        if result.success:
            engines_data = result.data

            # Raw output mode
            if raw:
                import json
                if hasattr(engines_data, 'to_dataframe'):
                    # Convert ModelList to dict
                    engines_df = engines_data.to_dataframe()
                    raw_data = engines_df.to_dict('records')
                elif isinstance(engines_data, list):
                    # Convert list to dict
                    raw_data = [item.__dict__ if hasattr(item, '__dict__') else item for item in engines_data]
                else:
                    raw_data = engines_data

                console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
                return

            # Handle both ModelList and list return types
            import pandas as pd

            if hasattr(engines_data, 'to_dataframe'):
                # ModelList with to_dataframe method
                engines_df = engines_data.to_dataframe()
            else:
                engines_df = pd.DataFrame()

            if engines_df.empty:
                console.print(":memo: No engines found.")
                return

            # Display results summary if filter was used
            if filter:
                console.print(f":mag: Found {len(engines_df)} engines matching filter: '{filter}'")

            # Display engines
            table = Table(title=":fire: Engines")
            table.add_column("UUID", style="dim", width=32)
            table.add_column("Name", style="cyan", width=18)
            table.add_column("Type", style="green", width=8)
            table.add_column("Status", style="yellow", width=12)
            table.add_column("Updated At", style="blue", width=20)

            for _, engine in engines_df.iterrows():
                # Format the update_at timestamp (simplified)
                update_at = engine.get('update_at')
                try:
                    if update_at is None or (hasattr(update_at, '__len__') and len(str(update_at)) == 0):
                        update_at_str = 'N/A'
                    else:
                        update_at_str = str(update_at)[:20]  # Simple string conversion
                except Exception as e:
                    from ginkgo.libs import GLOG
                    GLOG.ERROR(f"Failed to format update_at timestamp: {e}")
                    update_at_str = 'N/A'

                # Extract clean status name (simplified)
                status_raw = str(engine.get('status', 'Unknown'))
                if 'ENGINESTATUS_TYPES.' in status_raw:
                    status_clean = status_raw.split('ENGINESTATUS_TYPES.')[-1]
                elif '.' in status_raw:
                    status_clean = status_raw.split('.')[-1]
                else:
                    status_clean = status_raw

                # Format the Type column properly
                is_live_value = engine.get('is_live', False)
                if isinstance(is_live_value, bool):
                    engine_type = "Live" if is_live_value else "History"
                else:
                    # Handle string representation
                    engine_type = "Live" if str(is_live_value).lower() in ['true', '1', 'live'] else "History"

                table.add_row(
                    str(engine.get('uuid', ''))[:36],
                    str(engine.get('name', ''))[:18],
                    engine_type,
                    status_clean,
                    update_at_str
                )

            console.print(table)
        else:
            console.print(f":x: Failed to get engines: {result.error}")

    except Exception as e:
        console.print(f":x: Error: {e}")


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="Engine name"),
    engine_type: str = typer.Option("backtest", "--type", "-t", help="Engine type (backtest/live)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Engine description"),
):
    """
    :building_construction: Create a new engine.
    """
    from ginkgo.data.containers import container

    console.print(f":building_construction: Creating engine: {name}")

    try:
        engine_service = container.engine_service()
        is_live = engine_type == "live"
        result = engine_service.add(name=name, is_live=is_live, description=description or "")

        if result.success:
            engine_uuid = result.data.uuid if hasattr(result.data, 'uuid') else result.data
            console.print(f":white_check_mark: Engine '{name}' created successfully")
            console.print(f"  • Engine ID: {engine_uuid}")
            console.print(f"  • Type: {engine_type}")
            console.print(f"  • Description: {description or 'No description'}")
        else:
            console.print(f":x: Engine creation failed: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def cat(
    engine_id: Optional[str] = typer.Argument(None, help="Engine UUID or name (if not provided, will list available engines)"),
):
    """
    :cat: Show detailed engine information.
    """
    # 如果提供了engine_id，尝试解析为UUID
    if engine_id:
        original_identifier = engine_id
        resolved_uuid = resolve_engine_id(engine_id)

        if resolved_uuid is None:
            console.print(f":x: Engine not found: '{original_identifier}'")
            console.print(":information: Use 'ginkgo engine list' to see available engines")
            raise typer.Exit(1)

        # 如果解析成功，使用解析后的UUID
        engine_id = resolved_uuid
        if original_identifier != resolved_uuid:
            console.print(f":information: Resolved engine name '{original_identifier}' to UUID: {resolved_uuid}")

    # 如果没有提供engine_id，显示可用的引擎
    if not engine_id:
        console.print(":information: [bold]No engine ID provided.[/bold]")
        console.print(":clipboard: Listing available engines:")
        console.print()

        # 调用list_engines函数显示可用引擎，传递所有默认参数
        list_engines(status=None, portfolio_id=None, filter=None, limit=20, raw=False)
        console.print()
        console.print(":information: Use 'ginkgo engine cat <engine_uuid_or_name>' to see detailed information")
        raise typer.Exit(0)

    from ginkgo.data.containers import container

    console.print(f":cat: Showing engine {engine_id} details...")

    try:
        engine_service = container.engine_service()
        result = engine_service.get(engine_id=engine_id)

        if result.success:
            engines = result.data

            # Handle both ModelList and single object
            if hasattr(engines, '__len__') and len(engines) > 0:
                # ModelList - get the first engine
                engine = engines[0]
            elif hasattr(engines, 'uuid'):
                # Single engine object
                engine = engines
            else:
                console.print(":x: No engine found")
                raise typer.Exit(1)

            # 1. 显示Engine基本信息
            info_table = Table(title=f":fire: Engine Details: {engine.name}")
            info_table.add_column("Property", style="cyan", width=15)
            info_table.add_column("Value", style="white", width=50)

            info_table.add_row("ID", str(engine.uuid))
            info_table.add_row("Name", str(engine.name))
            info_table.add_row("Type", "Live" if engine.is_live else "History")
            info_table.add_row("Status", str(engine.status))
            info_table.add_row("Run Count", str(getattr(engine, 'run_count', 0)))

            # 显示时间范围
            start_date = getattr(engine, 'backtest_start_date', None)
            end_date = getattr(engine, 'backtest_end_date', None)
            if start_date and end_date:
                time_range = f"{start_date.strftime('%Y-%m-%d %H:%M:%S')} to {end_date.strftime('%Y-%m-%d %H:%M:%S')}"
                info_table.add_row("Time Range", time_range)
            elif start_date:
                time_range = f"{start_date.strftime('%Y-%m-%d %H:%M:%S')} (no end date)"
                info_table.add_row("Time Range", time_range)
            elif end_date:
                time_range = f"(no start date) to {end_date.strftime('%Y-%m-%d %H:%M:%S')}"
                info_table.add_row("Time Range", time_range)
            else:
                info_table.add_row("Time Range", "Not configured")

            info_table.add_row("Config Hash", str(getattr(engine, 'config_hash', 'N/A')))
            info_table.add_row("Description", str(getattr(engine, 'desc', '') or getattr(engine, 'description', 'No description')))

            console.print(info_table)

            # 2. 收集所有组件信息，然后组装显示
            component_data = collect_component_info(engine.uuid, container)

            # 3. 显示组件绑定关系树
            console.print(f"\n📁 Component Bindings:")
            display_component_tree(console, component_data)

            # 3. 显示配置快照（如果有）
            config_snapshot = getattr(engine, 'config_snapshot', '{}')
            if config_snapshot and config_snapshot != '{}':
                console.print(f"\n📋 Configuration Snapshot:")
                console.print(f"```json")
                import json
                try:
                    snapshot_obj = json.loads(config_snapshot)
                    console.print(json.dumps(snapshot_obj, indent=2, ensure_ascii=False))
                except Exception as e:
                    from ginkgo.libs import GLOG
                    GLOG.ERROR(f"Failed to parse configuration snapshot as JSON: {e}")
                    console.print(config_snapshot)
                console.print(f"```")
        else:
            console.print(f":x: Failed to get engine: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def status(
    engine_id: str = typer.Argument(..., help="Engine UUID or name"),
):
    """
    :gear: Get engine status.
    """
    from ginkgo.data.containers import container

    console.print(f":gear: Getting engine {engine_id} status...")

    try:
        # 解析 engine_id（支持名称和UUID）
        resolved_uuid = resolve_engine_id(engine_id)
        if resolved_uuid is None:
            console.print(f":x: Engine not found: '{engine_id}'")
            console.print(":information: Use 'ginkgo engine list' to see available engines")
            raise typer.Exit(1)

        engine_service = container.engine_service()
        result = engine_service.get(engine_id=resolved_uuid)

        if result.success:
            engines = result.data

            # Handle both ModelList and single object
            if hasattr(engines, '__len__') and len(engines) > 0:
                # ModelList - get the first engine
                engine = engines[0]
            elif hasattr(engines, 'uuid'):
                # Single engine object
                engine = engines
            else:
                console.print(":x: No engine found")
                raise typer.Exit(1)

            console.print(f":gear: Engine Status: {engine.status}")
            # TODO: Add more detailed status information
        else:
            console.print(f":x: Failed to get engine status: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def run(
    engine_id: Optional[str] = typer.Argument(None, help="Engine UUID or name (if not provided, will list available engines)"),
    background: bool = typer.Option(False, "--bg", help="Run in background"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only, don't run"),
):
    """
    :rocket: Run engine with assembled components.
    """
    # 如果提供了engine_id，尝试解析为UUID
    if engine_id:
        original_identifier = engine_id
        resolved_uuid = resolve_engine_id(engine_id)

        if resolved_uuid is None:
            console.print(f":x: Engine not found: '{original_identifier}'")
            console.print(":information: Use 'ginkgo engine list' to see available engines")
            raise typer.Exit(1)

        # 如果解析成功，使用解析后的UUID
        engine_id = resolved_uuid
        if original_identifier != resolved_uuid:
            console.print(f":information: Resolved engine name '{original_identifier}' to UUID: {resolved_uuid}")

    # 如果没有提供engine_id，显示可用的引擎
    if not engine_id:
        console.print(":information: [bold]No engine ID provided.[/bold]")
        console.print(":clipboard: Listing available engines:")
        console.print()

        # 调用list_engines函数显示可用引擎
        try:
            from ginkgo.data.containers import container

            engine_service = container.engine_service()
            result = engine_service.get()

            if result.success:
                engines_data = result.data

                # 处理数据格式
                import pandas as pd

                if hasattr(engines_data, 'to_dataframe'):
                    engines_df = engines_data.to_dataframe()
                else:
                    engines_df = pd.DataFrame()

                if engines_df.empty:
                    console.print(":memo: No engines found. Please create an engine first.")
                    console.print(":information: Use 'ginkgo engine create' to create a new engine.")
                    return

                # 显示可用引擎的表格
                table = Table(title=":fire: Available Engines")
                table.add_column("UUID", style="dim", width=36)
                table.add_column("Name", style="cyan", width=20)
                table.add_column("Type", style="green", width=8)
                table.add_column("Status", style="yellow", width=12)
                table.add_column("Updated At", style="blue", width=20)

                for _, engine in engines_df.iterrows():
                    # Format the update_at timestamp
                    update_at = engine.get('update_at')
                    try:
                        if update_at is None or (hasattr(update_at, '__len__') and len(str(update_at)) == 0):
                            update_at_str = 'N/A'
                        else:
                            update_at_str = str(update_at)[:20]
                    except Exception as e:
                        from ginkgo.libs import GLOG
                        GLOG.ERROR(f"Failed to format update_at timestamp: {e}")
                        update_at_str = 'N/A'

                    # Extract clean status name
                    status_raw = str(engine.get('status', 'Unknown'))
                    if 'ENGINESTATUS_TYPES.' in status_raw:
                        status_clean = status_raw.split('ENGINESTATUS_TYPES.')[-1]
                    elif '.' in status_raw:
                        status_clean = status_raw.split('.')[-1]
                    else:
                        status_clean = status_raw

                    # Format the Type column properly
                    is_live = engine.get('is_live', False)
                    engine_type = "Live" if is_live else "Backtest"

                    table.add_row(
                        str(engine.get('uuid', 'N/A')),
                        str(engine.get('name', 'N/A')),
                        engine_type,
                        status_clean,
                        update_at_str
                    )

                console.print(table)
                console.print()
                console.print(f":information: Found {len(engines_df)} available engines.")
                console.print(":information: To run an engine, use: [bold]ginkgo engine run <engine_uuid>[/bold]")

            else:
                console.print(":x: Failed to fetch engines from database")
                console.print(":information: Please check your database connection")

        except Exception as e:
            console.print(f":x: Error fetching engines: {e}")
            console.print(":information: Please check your configuration and try again")

        return

    if dry_run:
        console.print(f":mag: [bold]Dry run[/bold]: Validating engine assembly for {engine_id}...")
        try:
            from ginkgo.trading.core.containers import container
            assembly_service = container.services.engine_assembly_service()
            result = assembly_service.assemble_backtest_engine(engine_id=engine_id)
            if not result.success:
                console.print(f":x: Validation error: {result.message}")
                return

            engine = result.data

            console.print("Engine assembly validation passed")
            console.print(f"Engine ID: {engine}")
            console.print("Ready to run with assembled components")
        except Exception as e:
            console.print(f":x: Validation error: {e}")
            raise typer.Exit(1)
        return

    console.print(f":rocket: [bold]Starting engine {engine_id}[/bold]...")

    try:
        # 使用DI服务调用引擎装配服务
        from ginkgo.trading.core.containers import container
        from ginkgo.libs import GCONF
        import time

        # 确保调试模式启用
        original_debug = GCONF.DEBUGMODE
        GCONF.set_debug(True)
        console.print("Debug mode enabled for engine run")

        # 装配引擎
        console.print("Assembling engine components...")
        assembly_service = container.services.engine_assembly_service()
        result = assembly_service.assemble_backtest_engine(engine_id=engine_id)
        if not result.success:
            console.print(f":x: Engine assembly failed:")
            console.print(f"   Error: {result.error}")
            console.print(f"   Message: {result.message}")
            return

        engine = result.data
        # Note: portfolio_details需要从result.data中获取，但需要确认完整EngineAssemblyService的返回结构
        portfolio_details = {}  # 临时设置，需要根据实际情况调整

        console.print(f"Engine assembled successfully: {engine.name}")
        console.print(f"Engine ID: {engine.engine_id}")
        try:
            mode_str = str(engine.mode)
            engine_mode = 'BACKTEST' if 'BACKTEST' in mode_str else mode_str
        except Exception as e:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Failed to determine engine mode: {e}")
            engine_mode = 'UNKNOWN'
        console.print(f"Engine mode: {engine_mode}")

        # 🔧 在start前返回检查拼装逻辑
        console.print("检查拼装逻辑完成，在engine start前返回")
        portfolio_count = 0
        try:
            portfolio_count = len(engine.portfolios)
        except Exception as e:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Failed to count engine portfolios: {e}")
            portfolio_count = 0
        console.print(f"Portfolio数量: {portfolio_count}")

        # 显示Portfolio组件绑定情况
        if portfolio_count > 0:
            for portfolio in engine.portfolios:
                console.print(f"Portfolio {portfolio.portfolio_id}:")

                # 显示基本信息
                console.print(f"  📊 Portfolio {portfolio.portfolio_id} 绑定成功")

                # RiskManagers信息显示已简化

        console.print("拼装逻辑检查完成，开始执行引擎")

        if background:
            console.print(":repeat: Starting engine in background mode...")
            # 后台运行逻辑
            import threading
            import signal
            import sys

            def signal_handler(sig, frame):
                console.print("\n:stop_sign: Stopping background engine...")
                engine.stop()
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            def run_engine_background():
                success = engine.start()
                if success:
                    console.print(f":white_check_mark: Background engine {engine_id} completed successfully")
                else:
                    console.print(f":x: Background engine {engine_id} failed to start")

            # 启动后台线程
            engine_thread = threading.Thread(target=run_engine_background, daemon=True)
            engine_thread.start()

            console.print(f":white_check_mark: Engine started in background (Thread ID: {engine_thread.native_id})")
            console.print(":information_source: Use Ctrl+C to stop the engine")

            # 等待线程完成或被中断
            engine_thread.join()

        else:
            console.print(":repeat: Starting engine in foreground mode...")

            # 运行前综合检查
            console.print(":mag_right: Checking engine components binding...")
            engine.check_components_binding()

            # 启动引擎
            console.print(":timer: Engine auto-running...")
            success = engine.start()

            if not success:
                console.print(":x: Engine startup failed")
                raise typer.Exit(1)

            # 等待引擎自动完成
            console.print(":hourglass: Waiting for backtest completion...")

            start_check = time.time()
            timeout = 1800  # 30分钟超时保护

            while engine.is_active and (time.time() - start_check) < timeout:
                time.sleep(0.5)  # 0.5秒检查间隔

                # 可选：显示进度信息
                elapsed = time.time() - start_check
                if int(elapsed) % 30 == 0 and elapsed > 0:  # 每30秒显示一次进度
                    console.print(f":hourglass_flowing_sand: Running... Current time: {engine.now}")

            if engine.is_active:
                console.print(":warning: Backtest timeout, stopping engine...")
                engine.stop()
                raise typer.Exit(1)
            else:
                console.print(f":white_check_mark: Backtest completed successfully!")
                console.print(f":calendar: Final engine time: {engine.now}")
                console.print(f":chart_increasing: View detailed results with: ginkgo results --engine {engine_id}")

                # 生成回测统计分析报告
                console.print("\n" + "=" * 60)
                console.print("📊 Ginkgo回测统计分析报告")
                console.print("=" * 60)

                try:
                    # 获取Portfolio进行统计分析
                    if hasattr(engine, 'portfolios') and engine.portfolios:
                        try:
                            # engine.portfolios可能是list或dict，统一处理
                            portfolio = None

                            
                            if isinstance(engine.portfolios, dict):
                                # 如果是字典，取第一个值
                                if engine.portfolios:
                                    first_key = next(iter(engine.portfolios))
                                    portfolio = engine.portfolios[first_key]
                                else:
                                    console.print("⚠️ Portfolio字典为空，无法生成分析")
                                    return
                            elif isinstance(engine.portfolios, list):
                                # 如果是列表，取第一个元素
                                if len(engine.portfolios) > 0:
                                    portfolio = engine.portfolios[0]
                                else:
                                    console.print("⚠️ Portfolio列表为空，无法生成分析")
                                    return
                            else:
                                # 尝试直接使用
                                portfolio = engine.portfolios

                            if portfolio is None:
                                console.print("⚠️ 无法获取有效的Portfolio对象，无法生成分析")
                                return

                            # 基本统计分析
                            generate_backtest_analysis(console, portfolio, engine)

                        except Exception as portfolio_error:
                            console.print(f"⚠️ Portfolio数据处理失败: {portfolio_error}")
                    else:
                        console.print("⚠️ 未找到Portfolio数据，无法生成详细分析")

                except Exception as analysis_error:
                    console.print(f"⚠️ 分析生成失败: {analysis_error}")

                console.print("=" * 60)
                console.print("🎉 回测完成！统计分析已生成")

        # 恢复原始debug设置
        if not original_debug:
            GCONF.set_debug(False)

    except Exception as e:
        console.print(f":x: Engine run error: {e}")
        # 恢复debug设置
        try:
            if not original_debug:
                GCONF.set_debug(False)
        except Exception as e:
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Failed to restore debug config after engine run error: {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    engine_id: str = typer.Argument(..., help="Engine UUID"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm deletion"),
):
    """
    :wastebasket: Delete engine.
    """
    if not confirm:
        console.print(":x: Please use --confirm to delete engine")
        raise typer.Exit(1)

    console.print(f":wastebasket: Deleting engine: {engine_id}")

    try:
        from ginkgo.data.containers import container
        engine_service = container.engine_service()
        result = engine_service.delete(engine_id)

        if result.success:
            console.print(":white_check_mark: Engine deleted successfully")
        else:
            console.print(f":x: Failed to delete engine: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command("bind-portfolio")
def bind_portfolio(
    engine_id: Optional[str] = typer.Argument(None, help="Engine UUID or name (if not provided, will list available engines)"),
    portfolio_id: Optional[str] = typer.Argument(None, help="Portfolio UUID or name (if not provided, will list available portfolios)"),
):
    """
    :link: Bind an engine to a portfolio.
    """
    from ginkgo.data.containers import container

    # 如果没有提供 engine_id，显示可用的引擎
    if engine_id is None:
        console.print(":information: [bold]No engine ID provided.[/bold]")
        console.print(":clipboard: Listing available engines:")
        console.print()
        list_engines(status=None, portfolio_id=None, filter=None, limit=20, raw=False)
        console.print()
        console.print(":information: Use 'ginkgo engine bind-portfolio <engine_uuid_or_name> <portfolio_uuid_or_name>' to create binding")
        raise typer.Exit(0)

    # 如果没有提供 portfolio_id，显示可用的投资组合
    if portfolio_id is None:
        console.print(":information: [bold]No portfolio ID provided.[/bold]")
        console.print(":clipboard: Listing available portfolios:")
        console.print()

        portfolio_service = container.portfolio_service()
        result = portfolio_service.get()

        if result.success and result.data:
            if hasattr(result.data, 'to_dataframe'):
                import pandas as pd
                portfolios_df = result.data.to_dataframe()
            elif isinstance(result.data, list):
                portfolios_df = pd.DataFrame(result.data)
            else:
                portfolios_df = pd.DataFrame()

            if portfolios_df.empty:
                console.print(":memo: No portfolios found.")
            else:
                # 显示 portfolios 表格
                table = Table(title="Portfolios")
                table.add_column("UUID", style="cyan", width=40)
                table.add_column("Name", style="white")
                table.add_column("Initial Capital", style="green")
                table.add_column("Type", style="yellow")
                table.add_column("Status", style="blue")

                for _, row in portfolios_df.iterrows():
                    uuid_str = str(row.get('uuid', ''))[:40]
                    name = str(row.get('name', ''))
                    capital = f"¥{float(row.get('initial_capital', 0)):,.2f}"
                    ptype = "Live" if row.get('is_live', False) else "Backtest"
                    status = "Active" if not row.get('is_del', True) else "Deleted"

                    table.add_row(uuid_str, name, capital, ptype, status)

                console.print(table)
        else:
            console.print(":memo: No portfolios found.")

        console.print()
        console.print(":information: Use 'ginkgo engine bind-portfolio <engine_uuid_or_name> <portfolio_uuid_or_name>' to create binding")
        raise typer.Exit(0)

    console.print(f":link: Binding engine {engine_id} to portfolio {portfolio_id}...")

    try:
        # 解析 engine_id
        resolved_engine_uuid = resolve_engine_id(engine_id)
        if resolved_engine_uuid is None:
            console.print(f":x: Engine not found: '{engine_id}'")
            raise typer.Exit(1)

        # 解析 portfolio_id
        portfolio_service = container.portfolio_service()

        # 先尝试按UUID精确查找
        portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)
        if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
            resolved_portfolio_uuid = portfolio_result.data[0].uuid
            portfolio_name = portfolio_result.data[0].name
        else:
            # 尝试按name查找
            portfolio_result = portfolio_service.get(name=portfolio_id)
            if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
                resolved_portfolio_uuid = portfolio_result.data[0].uuid
                portfolio_name = portfolio_result.data[0].name
            else:
                console.print(f":x: Portfolio not found: '{portfolio_id}'")
                raise typer.Exit(1)

        # 获取engine name
        engine_service = container.engine_service()
        engine_result = engine_service.get(engine_id=resolved_engine_uuid)
        engine_name = engine_result.data[0].name if engine_result.success and engine_result.data else "unknown"

        # 先检查绑定是否已存在
        mapping_service = container.mapping_service()
        existing_result = mapping_service.get_engine_portfolio_mapping(
            engine_uuid=resolved_engine_uuid,
            portfolio_uuid=resolved_portfolio_uuid
        )

        if existing_result.success and existing_result.data and len(existing_result.data) > 0:
            # 绑定已存在
            console.print(f":information: Engine-Portfolio binding already exists")
            console.print(f"  • Engine: {engine_name} ({resolved_engine_uuid[:8]}...)")
            console.print(f"  • Portfolio: {portfolio_name} ({resolved_portfolio_uuid[:8]}...)")
            console.print(":information: Use 'ginkgo engine unbind-portfolio' to remove the binding")
            return

        # 使用 MappingService 创建新绑定
        result = mapping_service.create_engine_portfolio_mapping(
            engine_uuid=resolved_engine_uuid,
            portfolio_uuid=resolved_portfolio_uuid,
            engine_name=engine_name,
            portfolio_name=portfolio_name
        )

        if result.success:
            console.print(f":white_check_mark: Engine-Portfolio binding created successfully")
            console.print(f"  • Engine: {engine_name} ({resolved_engine_uuid[:8]}...)")
            console.print(f"  • Portfolio: {portfolio_name} ({resolved_portfolio_uuid[:8]}...)")
        else:
            console.print(f":white_check_mark: {result.message}")

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command("unbind-portfolio")
def unbind_portfolio(
    engine_id: str = typer.Argument(..., help="Engine UUID or name"),
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm unbinding"),
):
    """
    :broken_link: Unbind an engine from a portfolio.
    """
    if not confirm:
        console.print(":x: Please use --confirm to unbind portfolio")
        raise typer.Exit(1)

    from ginkgo.data.containers import container

    console.print(f":broken_link: Unbinding engine {engine_id} from portfolio {portfolio_id}...")

    try:
        # 解析 engine_id
        resolved_engine_uuid = resolve_engine_id(engine_id)
        if resolved_engine_uuid is None:
            console.print(f":x: Engine not found: '{engine_id}'")
            raise typer.Exit(1)

        # 解析 portfolio_id
        portfolio_service = container.portfolio_service()

        # 先尝试按UUID精确查找
        portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)
        if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
            resolved_portfolio_uuid = portfolio_result.data[0].uuid
            portfolio_name = portfolio_result.data[0].name
        else:
            # 尝试按name查找
            portfolio_result = portfolio_service.get(name=portfolio_id)
            if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
                resolved_portfolio_uuid = portfolio_result.data[0].uuid
                portfolio_name = portfolio_result.data[0].name
            else:
                console.print(f":x: Portfolio not found: '{portfolio_id}'")
                raise typer.Exit(1)

        # 使用 MappingService 删除绑定
        mapping_service = container.mapping_service()
        result = mapping_service.delete_engine_portfolio_mapping(
            engine_uuid=resolved_engine_uuid,
            portfolio_uuid=resolved_portfolio_uuid
        )

        if result.success:
            console.print(f":white_check_mark: Engine-Portfolio binding deleted successfully")
        else:
            console.print(f":x: Failed to delete binding: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)



