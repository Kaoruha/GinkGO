import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":clipboard: Module for [bold medium_spring_green]RECORD[/] management. [grey62]View trading signals, orders, and positions.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def signal(
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Items per page (0=no pagination)")] = 50,
):
    """
    :satellite_antenna: List trading signals.
    """
    from ginkgo.data.operations import get_signals_page_filtered, get_engines_page_filtered, get_engine_portfolio_mappings_page_filtered
    from ginkgo.libs.utils.display import display_dataframe
    
    try:
        # 第一层：如果没有传入 engine，显示所有可用的 engines
        if engine is None:
            engines_df = get_engines_page_filtered()
            console.print("Please specify an engine ID. Available engines:")
            
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
            console.print("\n[dim]Use: ginkgo backtest record signal --engine <engine_id>[/dim]")
            return
        
        # 第二层：如果有 engine 但没有 portfolio，显示该 engine 下绑定的所有 portfolios
        if portfolio is None:
            portfolios_df = get_engine_portfolio_mappings_page_filtered(engine_id=engine)
            
            if portfolios_df.shape[0] == 0:
                console.print(f":exclamation: [yellow]No portfolios found for engine {engine}.[/yellow]")
                return
                
            console.print(f"Please specify a portfolio ID. Available portfolios for engine {engine}:")
            
            # 配置列显示
            portfolios_columns_config = {
                "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
                "portfolio_name": {"display_name": "Name", "style": "cyan"},
                "update_at": {"display_name": "Update At", "style": "dim"}
            }
            
            display_dataframe(
                data=portfolios_df,
                columns_config=portfolios_columns_config,
                title=f":briefcase: [bold]Portfolios for Engine {engine}:[/bold]",
                console=console
            )
            console.print(f"\n[dim]Use: ginkgo backtest record signal --engine {engine} --portfolio <portfolio_id>[/dim]")
            return
        
        # 第三层：有 engine 和 portfolio，显示具体的 signals
        signals_df = get_signals_page_filtered(
            engine_id=engine, 
            portfolio_id=portfolio, 
            page_size=page if page > 0 else None, 
            as_dataframe=True
        )
        
        if signals_df.shape[0] == 0:
            console.print(f":exclamation: [yellow]No signals found for engine {engine} and portfolio {portfolio}.[/yellow]")
            return
        
        # 配置列显示
        signal_columns_config = {
            "uuid": {"display_name": "Signal ID", "style": "dim"},
            "engine_id": {"display_name": "Engine ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "direction": {"display_name": "Direction", "style": "green"},
            "code": {"display_name": "Code", "style": "cyan"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"},
            "reason": {"display_name": "Reason", "style": "yellow"}
        }
        
        title = f":satellite_antenna: [bold]Signals for Engine {engine} / Portfolio {portfolio}:[/bold]"
        display_dataframe(
            data=signals_df,
            columns_config=signal_columns_config,
            title=title,
            console=console
        )
        
        if signals_df.shape[0] == page and page > 0:
            console.print(f"[dim]Showing first {page} records. Use --page 0 to see all records.[/dim]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch signals:[/bold red] {e}")


@app.command()
def order(
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Items per page (0=no pagination)")] = 50,
):
    """
    :clipboard: List order records.
    """
    from ginkgo.data.operations import get_order_records_page_filtered
    
    try:
        if portfolio:
            orders_df = get_order_records_page_filtered(portfolio_id=portfolio, page_size=page if page > 0 else None)
        else:
            orders_df = get_order_records_page_filtered(page_size=page if page > 0 else None)
        
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
            "status": {"display_name": "Status", "style": "green"}
        }
        
        title = f":clipboard: [bold]Orders for portfolio {portfolio}:[/bold]" if portfolio else ":clipboard: [bold]Orders:[/bold]"
        display_dataframe(
            data=orders_df,
            columns_config=order_columns_config,
            title=title,
            console=console
        )
        
        if orders_df.shape[0] == page and page > 0:
            console.print(f"[dim]Showing first {page} records. Use --page 0 to see all records.[/dim]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch orders:[/bold red] {e}")


@app.command()
def position(
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Items per page (0=no pagination)")] = 50,
):
    """
    :bar_chart: List position records.
    """
    from ginkgo.data.operations import get_position_records_page_filtered
    
    try:
        if portfolio:
            positions_df = get_position_records_page_filtered(portfolio_id=portfolio, page_size=page if page > 0 else None)
        else:
            positions_df = get_position_records_page_filtered(page_size=page if page > 0 else None)
        
        # 配置列显示
        position_columns_config = {
            "uuid": {"display_name": "Position ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "code": {"display_name": "Code", "style": "cyan"},
            "quantity": {"display_name": "Quantity", "style": "yellow"},
            "average_price": {"display_name": "Avg Price", "style": "yellow"},
            "market_value": {"display_name": "Market Value", "style": "green"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"}
        }
        
        title = f":bar_chart: [bold]Positions for portfolio {portfolio}:[/bold]" if portfolio else ":bar_chart: [bold]Positions:[/bold]"
        display_dataframe(
            data=positions_df,
            columns_config=position_columns_config,
            title=title,
            console=console
        )
        
        if positions_df.shape[0] == page and page > 0:
            console.print(f"[dim]Showing first {page} records. Use --page 0 to see all records.[/dim]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch positions:[/bold red] {e}")


@app.command()
def analyzer(
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Items per page (0=no pagination)")] = 50,
):
    """
    :bar_chart: List analyzer records.
    """
    from ginkgo.data.operations import get_analyzer_records_page_filtered
    
    try:
        kwargs = {}
        if portfolio:
            kwargs['portfolio_id'] = portfolio
        if engine:
            kwargs['engine_id'] = engine
        if page > 0:
            kwargs['page_size'] = page
            
        analyzer_df = get_analyzer_records_page_filtered(**kwargs)
        
        title_parts = []
        if portfolio:
            title_parts.append(f"portfolio {portfolio}")
        if engine:
            title_parts.append(f"engine {engine}")
        
        # 配置列显示
        analyzer_columns_config = {
            "uuid": {"display_name": "Record ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "engine_id": {"display_name": "Engine ID", "style": "dim"},
            "analyzer_id": {"display_name": "Analyzer ID", "style": "cyan"},
            "name": {"display_name": "Name", "style": "cyan"},
            "value": {"display_name": "Value", "style": "yellow"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"}
        }
        
        title = f":bar_chart: [bold]Analyzer records for {' and '.join(title_parts)}:[/bold]" if title_parts else ":bar_chart: [bold]Analyzer records:[/bold]"
        display_dataframe(
            data=analyzer_df,
            columns_config=analyzer_columns_config,
            title=title,
            console=console
        )
        
        if analyzer_df.shape[0] == page and page > 0:
            console.print(f"[dim]Showing first {page} records. Use --page 0 to see all records.[/dim]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch analyzer records:[/bold red] {e}")