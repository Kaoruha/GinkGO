import typer
from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column
from rich.console import Console
from rich.tree import Tree

# All heavy imports moved to function level for faster CLI startup

console = Console()

app = typer.Typer(
    help=":shark: Module for [bold medium_spring_green]BACKTEST[/]. [grey62]Build your own strategy and do backtest.[/grey62]",
    no_args_is_help=True,
)


# Lazy load and add sub-modules to app
def _setup_subcommands():
    """Lazy load sub-command modules"""
    from ginkgo.client import (
        backtest_component_cli,
        backtest_result_cli,
        engine_cli,
        portfolio_cli,
        param_cli,
        record_cli,
    )

    app.add_typer(engine_cli.app, name="engine")
    app.add_typer(portfolio_cli.app, name="portfolio")
    app.add_typer(backtest_component_cli.app, name="component")
    app.add_typer(param_cli.app, name="param")
    app.add_typer(record_cli.app, name="record")
    app.add_typer(backtest_result_cli.app, name="result")


# Setup subcommands when module is imported
_setup_subcommands()


class ResultType(str, Enum):
    analyzer = "analyzer"
    order = "order"


def print_order_paganation(df, page: int):
    """
    Echo dataframe in TTY page by page.
    """
    from ginkgo.libs.utils.display import display_dataframe

    # 配置列显示
    order_columns_config = {
        "uuid": {"display_name": "Order ID", "style": "dim"},
        "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
        "code": {"display_name": "Code", "style": "cyan"},
        "direction": {"display_name": "Direction", "style": "green"},
        "order_type": {"display_name": "Order Type", "style": "blue"},
        "quantity": {"display_name": "Quantity", "style": "yellow"},
        "limit_price": {"display_name": "Limit Price", "style": "yellow"},
        "timestamp": {"display_name": "Timestamp", "style": "dim"},
        "status": {"display_name": "Status", "style": "green"},
    }

    if page > 0:
        data_length = df.shape[0]
        page_count = int(data_length / page) + 1
        for i in range(page_count):
            page_data = df[i * page : (i + 1) * page]
            display_dataframe(
                data=page_data,
                columns_config=order_columns_config,
                title=f":clipboard: [bold]Orders (Page {i+1}/{page_count}):[/bold]",
                console=console,
            )

            go_next_page = Prompt.ask(f"Current: {(i+1)*page}/{data_length}, Continue? [y/N]")
            if go_next_page.upper() in ["N", "NO", "Q", "QUIT"]:
                console.print("See you soon. :sunglasses:")
                raise typer.Abort()
    else:
        display_dataframe(
            data=df, columns_config=order_columns_config, title=":clipboard: [bold]Orders:[/bold]", console=console
        )


@app.command()
def run(
    engine: Annotated[
        str, typer.Option(..., "--engine", "-e", "--e", case_sensitive=True, help=":id: Backtest engine ID")
    ] = None,
    debug: Annotated[
        bool, typer.Option("--debug", "-d", case_sensitive=False, help=":bug: Enable debug logging")
    ] = False,
):
    """
    :rocket: Run backtest with specified engine configuration.
    """
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.data.containers import container
    from ginkgo.trading.core.containers import container as backtest_container

    engine_service = container.engine_service()
    engine_df = engine_service.get_engine(engine, as_dataframe=True) if engine else None
    if (engine_df is None or engine_df.shape[0] == 0) or engine is None:
        engines_df = engine_service.get_engines(as_dataframe=True)
        msg = f"There is no engine [light_coral]{engine}[/light_coral] in your database. " if engine is not None else ""
        msg += "You could choose another engine below."
        console.print(msg)
        # 配置列显示
        engines_columns_config = {
            "uuid": {"display_name": "Engine ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "desc": {"display_name": "Description", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"},
        }

        display_dataframe(
            data=engines_df,
            columns_config=engines_columns_config,
            title=":wrench: [bold]Available Engines:[/bold]",
            console=console,
        )
        return
    else:
        # Use the DI service instead of direct factory call  
        assembly_service = backtest_container.services.engine_assembly_service()
        result = assembly_service.assemble_backtest_engine(engine)
        
        if result.success:
            console.print(f"[green]:white_check_mark: Backtest {engine} completed successfully[/green]")
        else:
            console.print(f"[red]:x: Failed to run backtest {engine}: {result.error}[/red]")


@app.command()
def tree(
    target: Annotated[
        Optional[str], typer.Option("--target", "-t", "--t", help=":id: Engine ID or Portfolio ID to display as tree")
    ] = None,
    detail: Annotated[bool, typer.Option("--detail", help=":mag: Show component parameters")] = False,
    type: Annotated[
        Optional[str],
        typer.Option(
            "--type",
            help=":filter: Filter by component type (analyzer, index, riskmanager, selector, sizer, strategy, engine, handler)",
        ),
    ] = None,
):
    """
    :deciduous_tree: Display engine or portfolio components in tree structure.
    """
    from ginkgo.enums import FILE_TYPES
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.client.cli_utils import _show_engine_tree, _show_portfolio_tree
    from ginkgo.data.containers import container

    # Convert string type to FILE_TYPES enum if provided
    if type is not None:
        try:
            type = FILE_TYPES.enum_convert(type)
            if type is None:
                valid_types = [item.name.lower() for item in FILE_TYPES if item.name != "OTHER"]
                console.print(f":x: [bold red]Invalid component type.[/bold red] Valid types: {', '.join(valid_types)}")
                return
        except Exception as e:
            valid_types = [item.name.lower() for item in FILE_TYPES if item.name != "OTHER"]
            console.print(f":x: [bold red]Invalid component type.[/bold red] Valid types: {', '.join(valid_types)}")
            return

    # 如果没有传入target，显示所有可用的engines和portfolios
    if target is None:
        console.print("Available engines and portfolios:")
        # 显示可用的engines和portfolios
        engine_service = container.engine_service()
        portfolio_service = container.portfolio_service()

        engines_df = engine_service.get_engines(as_dataframe=True)
        portfolios_df = portfolio_service.get_portfolios(as_dataframe=True)

        # 配置列显示 - engines
        engines_columns_config = {
            "uuid": {"display_name": "Engine ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "desc": {"display_name": "Description", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"},
        }

        # 配置列显示 - portfolios
        portfolios_columns_config = {
            "uuid": {"display_name": "Portfolio ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
            "backtest_end_date": {"display_name": "End Date", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"},
        }

        display_dataframe(
            data=engines_df,
            columns_config=engines_columns_config,
            title=":wrench: [bold]Available Engines:[/bold]",
            console=console,
        )

        display_dataframe(
            data=portfolios_df,
            columns_config=portfolios_columns_config,
            title=":briefcase: [bold]Available Portfolios:[/bold]",
            console=console,
        )
        return

    # 尝试查找engine
    engine_service = container.engine_service()
    portfolio_service = container.portfolio_service()

    engine_df = engine_service.get_engine(target, as_dataframe=True)
    portfolio_df = None

    if engine_df.shape[0] == 0:
        # 如果不是engine，尝试查找portfolio
        portfolio_df = portfolio_service.get_portfolio(target, as_dataframe=True)

        if portfolio_df.shape[0] == 0:
            # 两者都没找到，显示可用的列表
            console.print(f":exclamation: ID [light_coral]{target}[/light_coral] not found in engines or portfolios.")
            console.print("Available engines and portfolios:")
            # 显示可用的engines和portfolios
            engines_df = engine_service.get_engines(as_dataframe=True)
            portfolios_df = portfolio_service.get_portfolios(as_dataframe=True)

            # 配置列显示 - engines
            engines_columns_config = {
                "uuid": {"display_name": "Engine ID", "style": "dim"},
                "name": {"display_name": "Name", "style": "cyan"},
                "desc": {"display_name": "Description", "style": "dim"},
                "update_at": {"display_name": "Update At", "style": "dim"},
            }

            # 配置列显示 - portfolios
            portfolios_columns_config = {
                "uuid": {"display_name": "Portfolio ID", "style": "dim"},
                "name": {"display_name": "Name", "style": "cyan"},
                "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
                "backtest_end_date": {"display_name": "End Date", "style": "dim"},
                "update_at": {"display_name": "Update At", "style": "dim"},
            }

            display_dataframe(
                data=engines_df,
                columns_config=engines_columns_config,
                title=":wrench: [bold]Available Engines:[/bold]",
                console=console,
            )

            display_dataframe(
                data=portfolios_df,
                columns_config=portfolios_columns_config,
                title=":briefcase: [bold]Available Portfolios:[/bold]",
                console=console,
            )
            return
        else:
            # 找到portfolio，显示portfolio树
            _show_portfolio_tree(portfolio_df.iloc[0], detail, type)
    else:
        # 找到engine，显示engine树
        _show_engine_tree(engine_df.iloc[0], detail, type)


def showorder(
    id: Annotated[str, typer.Argument(case_sensitive=True, help=":id: Backtest ID")] = "",
    page: Annotated[
        int,
        typer.Option("--page", "-p", case_sensitive=False, help=":page_facing_up: Items per page (0=no pagination)"),
    ] = 0,
):
    """
    :clipboard: Display order records from backtest results.
    """
    import pandas as pd
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.data.containers import container
    from ginkgo.enums import ORDERSTATUS_TYPES

    if id == "":
        # Get backtest results via service layer
        try:
            result_service = container.result_service()
            raw = result_service.get_backtest_results(as_dataframe=True)
        except AttributeError:
            # Fallback if service doesn't exist
            from ginkgo.data.operations import get_backtest_list_df

            raw = get_backtest_list_df()

        # Use subset of columns for showorder display
        if raw.shape[0] > 0:
            rs = raw[["backtest_id", "profit", "start_at", "finish_at"]].copy()
            rs["uuid"] = raw["backtest_id"]  # Use backtest_id as display ID
        else:
            rs = raw

        # T6: 配置列显示，更新术语为run_id
        backtest_results_columns_config = {
            "uuid": {"display_name": "UUID", "style": "dim"},
            "backtest_id": {"display_name": "Run ID", "style": "cyan"},  # T6: 显示名称改为Run ID
            "profit": {"display_name": "Profit", "style": "green"},
            "start_at": {"display_name": "Start At", "style": "dim"},
            "finish_at": {"display_name": "Finish At", "style": "dim"},
        }

        display_dataframe(
            data=rs,
            columns_config=backtest_results_columns_config,
            title=":clipboard: [bold]Available Backtest Records:[/bold]",
            console=console,
        )
        return
    # Got backtest id
    try:
        order_service = container.order_service()
        orders = order_service.get_orders_by_portfolio(id, as_dataframe=True)
    except AttributeError:
        # Fallback if service doesn't exist
        from ginkgo.data.operations import get_order_df_by_portfolioid

        orders = get_order_df_by_portfolioid(id)

    if orders.shape[0] == 0:
        console.print(f"There is no orders about Backtest: {id}")
        return

    orders = orders[orders["status"] == ORDERSTATUS_TYPES.FILLED]
    print_order_paganation(orders, page)


def showparams():
    pass


def showresult(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    index: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="Type the analyzer_id to plot.",
        ),
    ] = None,
    compare: Annotated[
        str,
        typer.Option(case_sensitive=False, help="Do Compare with other backtest."),
    ] = "",
):
    """
    :one-piece_swimsuit: Show the backtest result.
    """
    import pandas as pd
    from pathlib import Path
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.data.containers import container

    if id == "":
        try:
            result_service = container.result_service()
            raw = result_service.get_backtest_results(as_dataframe=True)
        except AttributeError:
            # Fallback if service doesn't exist
            from ginkgo.data.operations import get_backtest_list_df

            raw = get_backtest_list_df()
        rs = raw[["uuid", "backtest_id", "profit", "start_at", "finish_at"]] if raw.shape[0] > 0 else raw

        # 配置列显示
        backtest_results_columns_config = {
            "uuid": {"display_name": "UUID", "style": "dim"},
            "backtest_id": {"display_name": "Run ID", "style": "cyan"},  # T6: 显示名称改为Run ID
            "profit": {"display_name": "Profit", "style": "green"},
            "start_at": {"display_name": "Start At", "style": "dim"},
            "finish_at": {"display_name": "Finish At", "style": "dim"},
        }

        display_dataframe(
            data=rs,
            columns_config=backtest_results_columns_config,
            title=":bar_chart: [bold]Backtest Results:[/bold]",
            console=console,
        )
        return
    # Got backtest id
    try:
        result_service = container.result_service()
        record = result_service.get_backtest_record(id)
    except AttributeError:
        # Fallback if service doesn't exist
        from ginkgo.data.operations import get_backtest_record_by_backtest, get_backtest_list_df

        record = get_backtest_record_by_backtest(id)

    print(record)
    if record is None:
        console.print(f":sad_but_relieved_face: Record {id} not exist. Please select one of follow.")
        try:
            result_service = container.result_service()
            print(result_service.get_backtest_results(as_dataframe=True))
        except AttributeError:
            from ginkgo.data.operations import get_backtest_list_df

            print(get_backtest_list_df())
        return
    console.print(f":sunflower: Backtest [light_coral]{id}[/light_coral]  Worth: {record.profit}")
    console.print(f"You could use [green]ginkgo backtest res {id} analyzer_id1 analyzer_id2 ...[/green] to see detail.")

    import yaml

    if len(index) == 0:
        # get all the analyzer
        content = record.content
        analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
        if len(analyzers) == 0:
            console.print("No Analyzer.")
            return

        # Create analyzer list DataFrame for display
        analyzer_data = []
        for i in analyzers:
            analyzer_data.append({"ID": i["id"], "Name": i["parameters"][0]})

        analyzer_df = pd.DataFrame(analyzer_data)
        columns = {"ID": {"display_name": "ID", "style": "dim"}, "Name": {"display_name": "Name", "style": "dim"}}

        display_dataframe(
            data=analyzer_df,
            columns_config=columns,
            title=":bar_chart: [bold]Available Analyzers:[/bold]",
            console=console,
        )
        return

    from ginkgo.trading.plots.result_plot import ResultPlot

    # Got analyzer id
    analyzer_ids = index
    content = record.content
    analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
    fig_data = []
    ids = [id]
    temp_data = {}
    for i in analyzer_ids:
        try:
            analyzer_service = container.analyzer_service()
            df = analyzer_service.get_analyzer_data_by_backtest(id, i, as_dataframe=True)
        except AttributeError:
            # Fallback if service doesn't exist
            from ginkgo.data.operations import get_analyzer_df_by_backtest

            df = get_analyzer_df_by_backtest(id, i)

        if df.shape[0] == 0:
            continue
        analyzer_name = "TestName"
        for j in analyzers:
            if j["id"] == i:
                analyzer_name = j["parameters"][0]
                break
        temp_data[analyzer_name] = df
    fig_data.append(temp_data)
    if compare != "":
        temp_data = {}
        print("add compare")
        for i in analyzer_ids:
            try:
                analyzer_service = container.analyzer_service()
                df = analyzer_service.get_analyzer_data_by_backtest(compare, i, as_dataframe=True)
            except AttributeError:
                # Fallback if service doesn't exist
                from ginkgo.data.operations import get_analyzer_df_by_backtest

                df = get_analyzer_df_by_backtest(compare, i)

            if df.shape[0] == 0:
                continue
            analyzer_name = "TestName"
            for j in analyzers:
                if j["id"] == i:
                    analyzer_name = j["parameters"][0]
                    break
            temp_data[analyzer_name] = df
        ids.append(compare)
        fig_data.append(temp_data)
    plot = ResultPlot("Backtest")
    plot.update_data(id, fig_data, ids)
    plot.show()


@app.command()
def clean(
    force: Annotated[bool, typer.Option("--force", "-f", help=":exclamation: Skip confirmation prompt")] = False,
):
    """
    :broom: Clean orphaned mappings and records where source entities don't exist.

    This command removes:
    - Mappings where source portfolios, engines, or files don't exist
    - Records where portfolios or engines don't exist

    Use with caution as this operation cannot be undone.
    """
    from rich.prompt import Confirm

    if not force:
        if not Confirm.ask(":question: Clean orphaned data?", default=True):
            console.print(":relieved_face: Operation cancelled.")
            return

    console.print(":broom: Starting orphaned data cleanup...")

    # Clean orphaned mappings and records
    _clean_orphaned_data(console)

    console.print(":white_check_mark: [bold green]Orphaned data cleanup completed[/bold green]")


def _clean_orphaned_data(console):
    """Helper function to clean orphaned mappings and records"""
    from ginkgo.data.containers import container
    from ginkgo.data.operations.engine_portfolio_mapping_crud import delete_engine_portfolio_mapping
    from ginkgo.data.operations.portfolio_file_mapping_crud import delete_portfolio_file_mapping
    from ginkgo.data.operations.analyzer_record_crud import delete_analyzer_records_filtered
    from ginkgo.data.operations import delete_signal_filtered
    from ginkgo.data.operations.order_record_crud import delete_order_records_filtered
    from ginkgo.data.operations.position_record_crud import delete_position_records_filtered

    # Get all existing entities using service layer
    portfolio_service = container.portfolio_service()
    engine_service = container.engine_service()
    file_service = container.file_service()

    portfolios = portfolio_service.get_portfolios(as_dataframe=True)
    engines = engine_service.get_engines(as_dataframe=True)
    files = file_service.get(as_dataframe=True)

    portfolio_ids = set(portfolios["uuid"].tolist()) if portfolios.shape[0] > 0 else set()
    engine_ids = set(engines["uuid"].tolist()) if engines.shape[0] > 0 else set()
    file_ids = set(files["uuid"].tolist()) if files.shape[0] > 0 else set()

    console.print(f":mag: Found {len(portfolio_ids)} portfolios, {len(engine_ids)} engines, {len(file_ids)} files")

    # Clean orphaned engine-portfolio mappings
    engine_portfolio_mappings = engine_service.get_engine_portfolio_mappings(as_dataframe=True)
    if engine_portfolio_mappings.shape[0] > 0:
        orphaned_count = 0
        for _, mapping in engine_portfolio_mappings.iterrows():
            if mapping["engine_id"] not in engine_ids or mapping["portfolio_id"] not in portfolio_ids:
                delete_engine_portfolio_mapping(mapping["uuid"])
                orphaned_count += 1

        if orphaned_count > 0:
            console.print(f":link: Cleaned {orphaned_count} orphaned engine-portfolio mappings")
        else:
            console.print(":link: No orphaned engine-portfolio mappings found")

    # Clean orphaned portfolio-file mappings
    portfolio_file_mappings = portfolio_service.get_portfolio_file_mappings(as_dataframe=True)
    if portfolio_file_mappings.shape[0] > 0:
        orphaned_count = 0
        for _, mapping in portfolio_file_mappings.iterrows():
            if mapping["portfolio_id"] not in portfolio_ids or mapping["file_id"] not in file_ids:
                delete_portfolio_file_mapping(mapping["uuid"])
                orphaned_count += 1

        if orphaned_count > 0:
            console.print(f":file_folder: Cleaned {orphaned_count} orphaned portfolio-file mappings")
        else:
            console.print(":file_folder: No orphaned portfolio-file mappings found")

    # Clean orphaned records where portfolio or engine doesn't exist
    try:
        from ginkgo.data.operations.analyzer_record_crud import (
            get_portfolio_ids_from_analyzer_records,
            get_engine_ids_from_analyzer_records,
        )
        from ginkgo.data.operations import get_portfolio_ids_from_signals
        from ginkgo.data.operations.order_record_crud import (
            get_portfolio_ids_from_order_records,
            get_engine_ids_from_order_records,
        )
        from ginkgo.data.operations.position_record_crud import (
            get_portfolio_ids_from_position_records,
            get_engine_ids_from_position_records,
        )

        console.print(":clipboard: Cleaning orphaned analyzer records...")
        _clean_orphaned_records_by_crud("analyzer", portfolio_ids, engine_ids, console)

        console.print(":satellite_antenna: Cleaning orphaned signal records...")
        _clean_orphaned_records_by_crud("signal", portfolio_ids, engine_ids, console)

        console.print(":clipboard: Cleaning orphaned order records...")
        _clean_orphaned_records_by_crud("order", portfolio_ids, engine_ids, console)

        console.print(":bar_chart: Cleaning orphaned position records...")
        _clean_orphaned_records_by_crud("position", portfolio_ids, engine_ids, console)

    except Exception as e:
        console.print(f":warning: Error cleaning orphaned records: {e}")


def _clean_orphaned_records_by_crud(record_type: str, valid_portfolio_ids: set, valid_engine_ids: set, console):
    """Helper function to clean orphaned records using CRUD methods"""
    try:
        orphaned_count = 0

        if record_type == "analyzer":
            from ginkgo.data.operations.analyzer_record_crud import (
                get_portfolio_ids_from_analyzer_records,
                get_engine_ids_from_analyzer_records,
                delete_analyzer_records_filtered,
            )

            # Check portfolio_ids
            analyzer_portfolio_ids = get_portfolio_ids_from_analyzer_records()
            for portfolio_id in analyzer_portfolio_ids:
                if portfolio_id not in valid_portfolio_ids:
                    delete_analyzer_records_filtered(portfolio_id)
                    orphaned_count += 1

            # Check engine_ids
            analyzer_engine_ids = get_engine_ids_from_analyzer_records()
            for engine_id in analyzer_engine_ids:
                if engine_id not in valid_engine_ids:
                    delete_analyzer_records_filtered(portfolio_id="", engine_id=engine_id)
                    orphaned_count += 1

        elif record_type == "signal":
            from ginkgo.data.operations import get_portfolio_ids_from_signals, delete_signal_filtered

            # Check portfolio_ids (signal table doesn't have engine_id)
            signal_portfolio_ids = get_portfolio_ids_from_signals()
            for portfolio_id in signal_portfolio_ids:
                if portfolio_id not in valid_portfolio_ids:
                    delete_signal_filtered(portfolio_id=portfolio_id)
                    orphaned_count += 1

        elif record_type == "order":
            from ginkgo.data.operations.order_record_crud import (
                get_portfolio_ids_from_order_records,
                get_engine_ids_from_order_records,
                delete_order_records_filtered,
            )

            # Check portfolio_ids
            order_portfolio_ids = get_portfolio_ids_from_order_records()
            for portfolio_id in order_portfolio_ids:
                if portfolio_id not in valid_portfolio_ids:
                    delete_order_records_filtered(portfolio_id)
                    orphaned_count += 1

            # Note: order_record delete doesn't support engine_id filter currently
            # We skip engine_id cleanup for order records

        elif record_type == "position":
            from ginkgo.data.operations.position_record_crud import (
                get_portfolio_ids_from_position_records,
                get_engine_ids_from_position_records,
                delete_position_records_filtered,
            )

            # Check portfolio_ids
            position_portfolio_ids = get_portfolio_ids_from_position_records()
            for portfolio_id in position_portfolio_ids:
                if portfolio_id not in valid_portfolio_ids:
                    delete_position_records_filtered(portfolio_id)
                    orphaned_count += 1

            # Note: position_record delete doesn't support engine_id filter currently
            # We skip engine_id cleanup for position records

        if orphaned_count > 0:
            console.print(f":wastebasket: Cleaned {orphaned_count} orphaned {record_type} records")
        else:
            console.print(f":white_check_mark: No orphaned {record_type} records found")

    except Exception as e:
        console.print(f":warning: Error cleaning {record_type} records: {e}")
