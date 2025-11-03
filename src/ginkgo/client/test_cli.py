# coding:utf-8
import typer
import sys
import subprocess
from enum import Enum
from pathlib import Path
from typing_extensions import Annotated
from rich.prompt import Prompt, Confirm
from rich import print
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":test_tube: Module for [bold medium_spring_green]PYTEST[/]. [grey62]Modern testing framework with enhanced capabilities.[/grey62]",
    no_args_is_help=True,
)

console = Console()


class LogLevelType(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class TestLayer(str, Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    DATABASE = "database"
    PERFORMANCE = "performance"


@app.command(name="list")
def list_tests():
    """
    :test_tube: Display available test modules and summary by layer.
    """
    import os
    from pathlib import Path

    # Get project root
    from ginkgo.libs.core.config import GCONF
    
    test_root = Path(GCONF.WORKING_PATH) / "test"
    
    console.print(":test_tube: [bold green]Ginkgo Test Suite - Modern Testing Framework[/bold green]")
    console.print()
    
    # Test layer information
    layers_info = {
        "unit": {
            "description": "Pure unit tests (no external dependencies)",
            "path": "test/unit/",
            "safety": ":green_circle: Safe - No database/network access",
            "speed": ":zap: Fast execution"
        },
        "integration": {
            "description": "Integration tests with mocked dependencies", 
            "path": "test/integration/",
            "safety": ":yellow_circle: Safe - Uses mocked dependencies",
            "speed": ":snail: Moderate execution"
        },
        "database": {
            "description": "Database interaction tests",
            "path": "test/database/",
            "safety": ":red_circle: REQUIRES CONFIRMATION - Modifies databases",
            "speed": ":snail: Slow execution"
        },
        "performance": {
            "description": "Performance and benchmark tests",
            "path": "test/performance/",
            "safety": ":yellow_circle: Safe - May consume resources",
            "speed": ":snail: Very slow execution"
        }
    }
    
    for layer_name, info in layers_info.items():
        layer_path = test_root / layer_name
        
        # Count test files
        test_count = 0
        if layer_path.exists():
            test_count = len(list(layer_path.rglob("test_*.py")))
        
        # Create panel for each layer
        panel_content = f"""
{info['description']}

:file_folder: Path: {info['path']}
:test_tube: Test files: {test_count}
{info['safety']}
{info['speed']}
        """.strip()
        
        console.print(Panel(
            panel_content,
            title=f":clipboard: {layer_name.upper()} Tests",
            border_style="green" if layer_name == "unit" else "yellow" if layer_name in ["integration", "performance"] else "red"
        ))
        console.print()
    
    # Legacy test structure info
    legacy_panel = """
:file_folder: Legacy structure (migrated to modern testing):
├── test/backtest/     → unit/backtest/
├── test/crud/         → database/crud/
├── test/data/         → integration/data/
├── test/db/           → database/drivers/
├── test/libs/         → unit/libs/
├── test/services/     → integration/services/
└── test/notifiers/    → unit/notifiers/
    """.strip()
    
    console.print(Panel(
        legacy_panel,
        title=":arrows_counterclockwise: Migration Status",
        border_style="dim"
    ))
    
    console.print()
    console.print(":information: Use [bold cyan]ginkgo test run --help[/bold cyan] to see all testing options")


@app.command()
def layers():
    """
    :bar_chart: Show detailed information about test layers and their purposes.
    """
    console.print(":books: [bold blue]Test Layer Architecture Guide[/bold blue]")
    console.print()
    
    # Create comprehensive table
    table = Table(title=":test_tube: Test Layers Overview", show_header=True, header_style="bold magenta")
    table.add_column("Layer", style="cyan", width=12)
    table.add_column("Purpose", style="green", width=30)
    table.add_column("Dependencies", style="yellow", width=20)
    table.add_column("Safety Level", justify="center", width=15)
    table.add_column("Execution Speed", justify="center", width=15)
    
    table.add_row(
        "UNIT",
        "Pure logic testing with no external deps",
        "None (mocked)",
        ":green_circle: Completely Safe",
        ":zap: Very Fast"
    )
    
    table.add_row(
        "INTEGRATION", 
        "Component interaction with mocks",
        "Mocked externals",
        ":yellow_circle: Safe with Mocks",
        ":walking: Moderate"
    )
    
    table.add_row(
        "DATABASE",
        "Real database operations testing", 
        "Live databases",
        ":red_circle: Requires Caution",
        ":snail: Slow"
    )
    
    table.add_row(
        "PERFORMANCE",
        "Benchmarks and load testing",
        "System resources", 
        ":yellow_circle: Resource Intensive",
        ":snail: Very Slow"
    )
    
    console.print(table)
    console.print()
    
    # Safety guidelines
    safety_guide = """
:shield:  SAFETY GUIDELINES:

:green_circle: UNIT Tests:
   • Run anywhere, anytime
   • No database connections
   • Fast feedback loop
   • Default choice for development

:yellow_circle: INTEGRATION Tests:
   • Use mocked dependencies
   • Safe for CI/CD pipelines
   • Verify component interactions
   • Good for regression testing

:red_circle: DATABASE Tests:
   • :warning:  ONLY in TEST environment
   • Require explicit confirmation
   • Use *_test database names
   • Auto-cleanup after execution
   • NEVER run against production

:yellow_circle: PERFORMANCE Tests:
   • May consume significant resources
   • Best run on dedicated test hardware
   • Generate detailed reports
   • Useful for optimization work
    """.strip()
    
    console.print(Panel(
        safety_guide,
        title=":shield: Safety Guidelines",
        border_style="blue"
    ))


@app.command() 
def validate():
    """
    :mag: Validate test environment configuration and safety settings.
    """
    from test.database.test_isolation import validate_test_database_config
    
    console.print(":mag: [bold blue]Test Environment Validation[/bold blue]")
    console.print()
    
    # Validate database test configuration
    is_safe, issues = validate_test_database_config()
    
    if is_safe:
        console.print(":white_check_mark: [bold green]Database test environment is SAFE[/bold green]")
    else:
        console.print(":x: [bold red]Database test environment has ISSUES:[/bold red]")
        for issue in issues:
            console.print(f"   • {issue}")
        console.print()
        console.print(":wrench: [yellow]Fix these issues before running database tests[/yellow]")
    
    console.print()
    
    # Check pytest installation
    try:
        import pytest
        console.print(f":white_check_mark: [green]Pytest version {pytest.__version__} is available[/green]")
    except ImportError:
        console.print(":x: [red]Pytest is not installed. Run: pip install pytest[/red]")


@app.command()
def run(
    # New layered testing options
    unit: Annotated[bool, typer.Option(case_sensitive=False, help=":test_tube: Unit tests")] = False,
    integration: Annotated[bool, typer.Option(case_sensitive=False, help=":link: Integration tests")] = False,
    database: Annotated[bool, typer.Option(case_sensitive=False, help=":floppy_disk: Database tests")] = False,
    performance: Annotated[bool, typer.Option(case_sensitive=False, help=":chart_with_upwards_trend: Performance tests")] = False,
    containers: Annotated[bool, typer.Option(case_sensitive=False, help=":package: Container tests")] = False,
    
    # Module-specific options
    module: Annotated[str, typer.Option("--module", "-m", help=":dart: Specific module")] = None,
    test_pattern: Annotated[str, typer.Option("--pattern", "-k", help=":mag: Test pattern to match")] = None,
    
    # Legacy compatibility options (deprecated) - hidden for cleaner help
    all: Annotated[bool, typer.Option(case_sensitive=False, help=":arrows_counterclockwise: All tests (no database)")] = False,
    
    # Legacy module options (will be migrated) - hidden for cleaner help
    base: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Base module tests", hidden=True)] = False,
    db: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Use --database instead", hidden=True)] = False,
    serv: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Services tests", hidden=True)] = False,
    libs: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Library tests", hidden=True)] = False,
    datasource: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Data source tests", hidden=True)] = False,
    backtest: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Backtest tests", hidden=True)] = False,
    lab: Annotated[bool, typer.Option(case_sensitive=False, help=":warning: [legacy] Experimental tests", hidden=True)] = False,
    
    # Control options
    y: Annotated[bool, typer.Option(case_sensitive=False, help=":white_check_mark: Auto-confirm")] = False,
    force: Annotated[bool, typer.Option(case_sensitive=False, help=":zap: Skip safety checks", hidden=True)] = False,
    debug: Annotated[bool, typer.Option(case_sensitive=False, help=":bug: Debug logging")] = False,
    verbose: Annotated[bool, typer.Option(case_sensitive=False, help=":memo: Verbose output")] = False,
    coverage: Annotated[bool, typer.Option(case_sensitive=False, help=":bar_chart: Coverage report")] = False,
    fail_fast: Annotated[bool, typer.Option("--fail-fast", "-x", help=":stop_sign: Stop on first failure")] = False,
    parallel: Annotated[int, typer.Option("--parallel", "-n", help=":rocket: Number of parallel workers")] = None,
):
    """
    :test_tube: Execute tests with modern testing framework and layered architecture support.
    
    COMMON USAGE:
      ginkgo test run                      # Unit tests (default)
      ginkgo test run --integration        # Integration tests
      ginkgo test run --database           # Database tests (needs confirmation)
      ginkgo test run --all                # All tests except database
      ginkgo test run -k "test_pattern"    # Run tests matching pattern
    
    For detailed layer info: ginkgo test layers
    """
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs import GLOG

    if debug:
        GLOG.set_level("debug")
    
    test_root = Path(GCONF.WORKING_PATH) / "test"
    test_paths = []
    pytest_args = []
    
    # Handle legacy options first (with deprecation warnings)
    if db:
        console.print(":warning: [yellow]--db is deprecated. Use --database instead[/yellow]")
        database = True
    
    # Default behavior: run unit tests if no specific layer is specified
    if not any([unit, integration, database, performance, containers, all]):
        unit = True
        console.print("ℹ️ [cyan]No test layer specified. Running unit tests by default.[/cyan]")
    
    # Handle --all option
    if all:
        unit = True
        integration = True
        performance = True
        containers = True
        # Note: database tests are NOT included in --all for safety
    
    # Build test paths based on selected layers
    if unit:
        unit_path = test_root / "unit"
        if unit_path.exists():
            if module:
                module_path = unit_path / module
                if module_path.exists():
                    test_paths.append(str(module_path))
                else:
                    console.print(f":x: [red]Unit tests for module '{module}' not found at {module_path}[/red]")
            else:
                test_paths.append(str(unit_path))
        else:
            console.print(":warning: [yellow]Unit test directory not found, using legacy structure[/yellow]")
            _add_legacy_paths(test_paths, test_root, ['libs', 'backtest'])
    
    if integration:
        integration_path = test_root / "integration"
        if integration_path.exists():
            if module:
                module_path = integration_path / module
                if module_path.exists():
                    test_paths.append(str(module_path))
            else:
                test_paths.append(str(integration_path))
        else:
            console.print(":warning: [yellow]Integration test directory not found, using legacy structure[/yellow]")
            _add_legacy_paths(test_paths, test_root, ['data', 'services'])
    
    if containers:
        containers_path = test_root / "unit" / "containers"
        if containers_path.exists():
            test_paths.append(str(containers_path))
        else:
            console.print(":x: [red]Container tests not found. Run: ginkgo test run --unit to create them.[/red]")
    
    if performance:
        performance_path = test_root / "performance"
        if performance_path.exists():
            test_paths.append(str(performance_path))
        else:
            console.print(":warning: [yellow]Performance test directory not found[/yellow]")
    
    if database:
        # Special handling for database tests with safety checks
        if not force:
            from test.database.test_isolation import validate_test_database_config, print_database_test_warning
            
            # Validate environment
            is_safe, issues = validate_test_database_config()
            if not is_safe:
                console.print(":x: [bold red]Database test environment is NOT SAFE:[/bold red]")
                for issue in issues:
                    console.print(f"   • {issue}")
                console.print("\n:wrench: [yellow]Fix these issues or use --force to skip validation[/yellow]")
                return
            
            # Show warning and get confirmation
            if not y:
                if not print_database_test_warning():
                    console.print("ℹ️ [cyan]Database tests cancelled by user[/cyan]")
                    return
        
        database_path = test_root / "database"
        if database_path.exists():
            test_paths.append(str(database_path))
        else:
            console.print(":warning: [yellow]Database test directory not found, using legacy structure[/yellow]")
            _add_legacy_paths(test_paths, test_root, ['db', 'crud'])
    
    # Handle legacy options
    if base:
        test_paths.append(str(test_root))
    if libs:
        test_paths.append(str(test_root / "libs"))
    if datasource:
        test_paths.append(str(test_root / "data"))
    if backtest:
        test_paths.append(str(test_root / "backtest"))
    if serv:
        test_paths.append(str(test_root / "services"))
    if lab:
        test_paths.append(str(test_root / "lab"))
    
    if not test_paths:
        console.print(":x: [red]No test paths selected. Use --help to see available options.[/red]")
        return
    
    # Build pytest arguments
    pytest_args.extend(test_paths)
    
    # Add pytest options
    if verbose:
        pytest_args.append("-v")
    elif not debug:
        pytest_args.append("-q")
    
    if fail_fast:
        pytest_args.append("-x")
    
    if test_pattern:
        pytest_args.extend(["-k", test_pattern])
    
    if coverage:
        pytest_args.extend(["--cov=src/ginkgo", "--cov-report=html", "--cov-report=term"])
    
    if parallel:
        pytest_args.extend(["-n", str(parallel)])
    
    if debug:
        pytest_args.append("--tb=long")
        pytest_args.append("--log-cli-level=DEBUG")
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        console.print(":x: [red]Pytest is not installed. Run: pip install pytest[/red]")
        return
    
    console.print(f":test_tube: [green]Running pytest with arguments: {' '.join(pytest_args)}[/green]")
    
    # Setup logging
    if GCONF.LOGGING_FILE_ON:
        from ginkgo.libs import GLOG
        log_path = Path(GCONF.LOGGING_PATH) / "pytest.log"
        GLOG.reset_logfile("pytest.log")
        try:
            with open(log_path, "w") as f:
                f.truncate()
        except Exception as e:
            console.print(f":warning: [yellow]Failed to setup log file: {e}[/yellow]")
    
    # Run pytest
    try:
        exit_code = pytest.main(pytest_args)
        
        # Report results based on exit code
        if exit_code == 0:
            console.print(":white_check_mark: [bold green]All tests passed![/bold green]")
        elif exit_code == 1:
            console.print(":x: [bold red]Some tests failed[/bold red]")
        elif exit_code == 2:
            console.print(":warning: [yellow]Test execution was interrupted[/yellow]")
        elif exit_code == 3:
            console.print(":x: [red]Internal error occurred[/red]")
        elif exit_code == 4:
            console.print(":x: [red]Pytest usage error[/red]")
        elif exit_code == 5:
            console.print(":information: [blue]No tests were collected[/blue]")
        
        return exit_code
        
    except Exception as e:
        console.print(f":x: [red]Error running pytest: {e}[/red]")
        return 1


def _add_legacy_paths(test_paths: list, test_root: Path, directories: list):
    """Add legacy test paths to the test paths list."""
    for directory in directories:
        legacy_path = test_root / directory
        if legacy_path.exists():
            test_paths.append(str(legacy_path))


@app.command()
def markers():
    """
    :label: List available pytest markers for test categorization.
    """
    console.print(":label: [bold blue]Available Pytest Markers[/bold blue]")
    console.print()
    
    # Create table for markers
    table = Table(title=":bookmark: Test Markers", show_header=True, header_style="bold magenta")
    table.add_column("Marker", style="cyan", width=15)
    table.add_column("Purpose", style="green", width=40)
    table.add_column("Usage Example", style="yellow", width=30)
    
    markers_info = [
        ("unit", "Pure unit tests", "pytest -m unit"),
        ("integration", "Integration tests", "pytest -m integration"),
        ("database", "Database tests", "pytest -m database"),
        ("slow", "Slow-running tests", "pytest -m 'not slow'"),
        ("network", "Tests requiring network", "pytest -m 'not network'"),
        ("performance", "Performance tests", "pytest -m performance"),
        ("smoke", "Quick smoke tests", "pytest -m smoke"),
    ]
    
    for marker, purpose, example in markers_info:
        table.add_row(marker, purpose, example)
    
    console.print(table)
    console.print()
    
    usage_info = """
:information: MARKER USAGE:

• Run specific markers:       pytest -m unit
• Exclude markers:           pytest -m 'not slow'
• Combine markers:           pytest -m 'unit and not slow'
• List all markers:          pytest --markers
    """.strip()
    
    console.print(Panel(
        usage_info,
        title=":bookmark: Usage Guide",
        border_style="blue"
    ))