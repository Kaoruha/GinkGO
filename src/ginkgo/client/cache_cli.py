import typer
from enum import Enum
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

class CacheType(str, Enum):
    ALL = "all"
    FUNCTION = "function" 
    SYNC = "sync"
    TICK = "tick"

app = typer.Typer(
    help=":wastebasket: Module for [bold medium_spring_green]CACHE[/]. [grey62]Redis cache management and cleanup.[/grey62]",
    no_args_is_help=True,
)

@app.command()
def clear(
    cache_type: Annotated[
        CacheType, 
        typer.Option("--type", "-t", help=":label: Cache type to clear")
    ] = CacheType.ALL,
    code: Annotated[
        Optional[str],
        typer.Option("--code", "-c", help=":chart_with_upwards_trend: Stock code (required for sync/tick types)")
    ] = None,
    name: Annotated[
        Optional[str],
        typer.Option("--name", "-n", help=":gear: Function name (optional for function type)")
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help=":warning: Skip confirmation prompt")
    ] = False,
):
    """
    :broom: Clear Redis cache entries.
    
    Examples:
      ginkgo cache clear                           # Clear all caches
      ginkgo cache clear --type function           # Clear all function caches
      ginkgo cache clear --type function --name get_bars  # Clear specific function cache
      ginkgo cache clear --type sync --code 000001.SZ     # Clear sync cache for stock
      ginkgo cache clear --type tick --code 000001.SZ     # Clear tick cache for stock
    """
    # Import heavy dependencies at function level for faster startup
    from ginkgo.data.containers import container
    
    # Validate parameters
    if cache_type in [CacheType.SYNC, CacheType.TICK] and not code:
        console.print(":x: [red]Error: --code parameter is required for sync/tick cache types[/red]")
        raise typer.Exit(1)
    
    # Show what will be cleared
    if cache_type == CacheType.ALL:
        operation_desc = "all caches"
    elif cache_type == CacheType.FUNCTION:
        if name:
            operation_desc = f"function cache for '{name}'"
        else:
            operation_desc = "all function caches"
    elif cache_type == CacheType.SYNC:
        operation_desc = f"sync cache for code '{code}'"
    elif cache_type == CacheType.TICK:
        operation_desc = f"tick cache for code '{code}'"
    
    # Confirmation prompt
    if not force:
        console.print(f":warning: [yellow]About to clear {operation_desc}[/yellow]")
        if not Confirm.ask("Are you sure you want to proceed?"):
            console.print(":x: [cyan]Operation cancelled[/cyan]")
            raise typer.Exit(0)
    
    # Perform cache clearing operations
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            
            if cache_type == CacheType.ALL:
                _clear_all_caches(progress)
            elif cache_type == CacheType.FUNCTION:
                _clear_function_cache(progress, name)
            elif cache_type == CacheType.SYNC:
                _clear_sync_cache(progress, code)
            elif cache_type == CacheType.TICK:
                _clear_tick_cache(progress, code)
                
        console.print(f":white_check_mark: [green]Successfully cleared {operation_desc}[/green]")
        
    except Exception as e:
        console.print(f":x: [red]Error clearing cache: {str(e)}[/red]")
        raise typer.Exit(1)

def _clear_all_caches(progress: Progress):
    """Clear all cache types"""
    from ginkgo.data.containers import container
    
    task = progress.add_task("Clearing all caches...", total=100)
    
    try:
        # Clear function caches
        progress.update(task, description="Clearing function caches...", advance=0)
        redis_service = container.redis_service()
        function_cleared = redis_service.clear_function_cache()
        progress.update(task, advance=40)
        
        # Clear sync progress caches
        progress.update(task, description="Clearing sync progress caches...", advance=0)
        sync_cleared = redis_service.clear_all_sync_progress()
        progress.update(task, advance=40)
        
        # Clear container caches  
        progress.update(task, description="Clearing container caches...", advance=0)
        # Note: This is a more destructive operation, be careful
        # We'll skip this for now in "all" mode to be safe
        progress.update(task, advance=20)
        
        progress.update(task, description=f"Cleared {function_cleared} function cache entries, {sync_cleared} sync progress entries", completed=100)
        
    except Exception as e:
        progress.update(task, description=f"Error: {str(e)}", completed=100)
        raise

def _clear_function_cache(progress: Progress, func_name: Optional[str] = None):
    """Clear function caches"""
    from ginkgo.data.containers import container
    
    desc = f"Clearing function cache for '{func_name}'" if func_name else "Clearing all function caches"
    task = progress.add_task(desc, total=100)
    
    try:
        redis_service = container.redis_service()
        cleared_count = redis_service.clear_function_cache(func_name)
        progress.update(task, description=f"Cleared {cleared_count} function cache entries", completed=100)
        
    except Exception as e:
        progress.update(task, description=f"Error: {str(e)}", completed=100)
        raise

def _clear_sync_cache(progress: Progress, code: str):
    """Clear sync cache for specific stock code"""
    from ginkgo.data.containers import container
    
    task = progress.add_task(f"Clearing sync cache for {code}", total=100)
    
    try:
        redis_service = container.redis_service()
        # Clear both tick and bar sync progress
        tick_cleared = redis_service.clear_sync_progress(code, "tick")
        bar_cleared = redis_service.clear_sync_progress(code, "bar")
        progress.update(task, description=f"Cleared sync cache for {code} (tick: {tick_cleared}, bar: {bar_cleared})", completed=100)
        
    except Exception as e:
        progress.update(task, description=f"Error: {str(e)}", completed=100)
        raise

def _clear_tick_cache(progress: Progress, code: str):
    """Clear tick cache for specific stock code"""
    from ginkgo.data.containers import container
    
    task = progress.add_task(f"Clearing tick cache for {code}", total=100)
    
    try:
        tick_service = container.tick_service()
        cleared = tick_service.clear_sync_cache(code)
        progress.update(task, description=f"Cleared tick cache for {code}: {cleared}", completed=100)
        
    except Exception as e:
        progress.update(task, description=f"Error: {str(e)}", completed=100)
        raise

@app.command()
def status():
    """
    :bar_chart: Display cache status and statistics.
    """
    from ginkgo.data.containers import container
    
    console.print(":chart_with_upwards_trend: [bold blue]Cache Status Report[/bold blue]")
    console.print()
    
    # Create status table
    table = Table(title="Redis Cache Statistics", show_header=True, header_style="bold magenta")
    table.add_column("Cache Type", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Details", style="yellow")
    
    try:
        redis_service = container.redis_service()
        
        # Check Redis connection
        try:
            redis_info = redis_service.get_redis_info()
            if redis_info.get("connected", False):
                redis_status = ":white_check_mark: Connected"
                redis_details = f"Version: {redis_info.get('version', 'Unknown')}"
            else:
                redis_status = ":x: Disconnected"
                redis_details = redis_info.get("error", "Unknown error")
        except Exception as e:
            redis_status = ":x: Error"
            redis_details = str(e)
            
        table.add_row("Redis Connection", redis_status, redis_details)
        
        # Function cache statistics
        try:
            # Get function cache keys count
            func_cache_keys = redis_service.crud_repo.keys("ginkgo_func_cache_*")
            func_cache_count = len(func_cache_keys) if func_cache_keys else 0
            table.add_row(
                "Function Cache", 
                ":white_check_mark: Active" if func_cache_count > 0 else ":information_source: Empty",
                f"{func_cache_count} entries"
            )
        except Exception as e:
            table.add_row("Function Cache", ":x: Error", str(e))
        
        # Sync progress cache
        try:
            sync_keys = redis_service.crud_repo.keys("ginkgo_sync_progress_*")
            sync_count = len(sync_keys) if sync_keys else 0
            table.add_row(
                "Sync Progress", 
                ":white_check_mark: Active" if sync_count > 0 else ":information_source: Empty",
                f"{sync_count} entries"
            )
        except Exception as e:
            table.add_row("Sync Progress", ":x: Error", str(e))
            
    except Exception as e:
        table.add_row("Redis Service", ":x: Error", f"Failed to get service: {str(e)}")
    
    console.print(table)
    console.print()
    console.print(":bulb: [dim]Tip: Use 'ginkgo cache clear --help' for cache cleanup options[/dim]")

@app.command()
def list(
    cache_type: Annotated[
        Optional[CacheType],
        typer.Option("--type", "-t", help=":label: Filter by cache type")
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help=":1234: Maximum number of entries to show")
    ] = 50,
):
    """
    :clipboard: List cache entries.
    """
    from ginkgo.data.containers import container
    
    console.print(":clipboard: [bold blue]Cache Entries[/bold blue]")
    console.print()
    
    try:
        redis_service = container.redis_service()
        
        # Determine which patterns to search for
        patterns = []
        if cache_type is None or cache_type == CacheType.ALL:
            patterns = ["ginkgo_func_cache_*", "ginkgo_sync_progress_*"]
        elif cache_type == CacheType.FUNCTION:
            patterns = ["ginkgo_func_cache_*"]
        elif cache_type in [CacheType.SYNC, CacheType.TICK]:
            patterns = ["ginkgo_sync_progress_*"]
            
        # Create results table
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Type", style="cyan", no_wrap=True)
        table.add_column("Key", style="green")
        table.add_column("Details", style="yellow")
        
        total_shown = 0
        for pattern in patterns:
            keys = redis_service.crud_repo.keys(pattern)
            if keys:
                for key in keys[:limit - total_shown]:
                    # Determine cache type from key
                    if "func_cache" in key:
                        cache_type_display = "Function"
                        # Extract function name from key
                        parts = key.split("_")
                        func_name = parts[3] if len(parts) > 3 else "Unknown"
                        details = f"Function: {func_name}"
                    elif "sync_progress" in key:
                        cache_type_display = "Sync Progress"
                        # Extract code and type from key
                        parts = key.split("_")
                        code = parts[3] if len(parts) > 3 else "Unknown"
                        data_type = parts[4] if len(parts) > 4 else "Unknown"
                        details = f"Code: {code}, Type: {data_type}"
                    else:
                        cache_type_display = "Other"
                        details = "Unknown format"
                        
                    table.add_row(cache_type_display, key, details)
                    total_shown += 1
                    
                    if total_shown >= limit:
                        break
            
            if total_shown >= limit:
                break
                
        if total_shown == 0:
            console.print(":information_source: [yellow]No cache entries found[/yellow]")
        else:
            console.print(table)
            if total_shown >= limit:
                console.print(f":information_source: [dim]Showing first {limit} entries. Use --limit to see more.[/dim]")
                
    except Exception as e:
        console.print(f":x: [red]Error listing cache entries: {str(e)}[/red]")
        raise typer.Exit(1)