# coding:utf-8
import typer
import sys
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
    help=":white_check_mark: Module for [bold medium_spring_green]UNITTEST[/]. [grey62]Confirm functional integrity with layered test architecture.[/grey62]",
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
    
    console.print(":test_tube: [bold green]Ginkgo Test Suite - Layered Architecture[/bold green]")
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
:file_folder: Legacy structure (being migrated):
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
    console.print(":information: Use [bold cyan]ginkgo unittest run --help[/bold cyan] to see all testing options")


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
    
    # Additional validations can be added here
    # - Check test data isolation
    # - Verify mock configurations
    # - Validate CI/CD setup
    # etc.


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
):
    """
    :test_tube: Execute tests with layered architecture support.
    
    COMMON USAGE:
      ginkgo unittest run                    # Unit tests (default)
      ginkgo unittest run --integration     # Integration tests
      ginkgo unittest run --database        # Database tests (needs confirmation)
      ginkgo unittest run --all             # All tests except database
    
    For detailed layer info: ginkgo unittest layers
    """
    import unittest
    from ginkgo.libs.core.config import GCONF
    from ginkgo.libs import GLOG

    if debug:
        GLOG.set_level("debug")
    
    test_root = Path(GCONF.WORKING_PATH) / "test"
    suite = unittest.TestSuite()
    test_paths = []
    
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
            console.print(":x: [red]Container tests not found. Run: ginkgo unittest run --unit to create them.[/red]")
    
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
    
    # Discover and add tests
    console.print(f":mag: [cyan]Discovering tests in {len(test_paths)} path(s)...[/cyan]")
    
    total_tests = 0
    for path in test_paths:
        if Path(path).exists():
            tests = unittest.TestLoader().discover(path, pattern="test_*.py")
            suite.addTest(tests)
            # Count tests for reporting
            test_count = _count_tests_in_suite(tests)
            total_tests += test_count
            console.print(f"  :file_folder: {path}: {test_count} tests")
        else:
            console.print(f":warning: [yellow]Path not found: {path}[/yellow]")
    
    if total_tests == 0:
        console.print(":x: [red]No tests found in selected paths[/red]")
        return
    
    console.print(f":test_tube: [green]Running {total_tests} tests...[/green]")
    
    # Setup logging
    if GCONF.LOGGING_FILE_ON:
        log_path = Path(GCONF.LOGGING_PATH) / "unittest.log"
        GLOG.reset_logfile("unittest.log")
        try:
            with open(log_path, "w") as f:
                f.truncate()
        except Exception as e:
            console.print(f":warning: [yellow]Failed to setup log file: {e}[/yellow]")
    
    # Run tests
    verbosity_level = 2 if verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity_level, stream=sys.stdout)
    
    if coverage:
        try:
            import coverage
            cov = coverage.Coverage()
            cov.start()
            result = runner.run(suite)
            cov.stop()
            cov.save()
            
            console.print("\n:bar_chart: [cyan]Generating coverage report...[/cyan]")
            cov.report()
            cov.html_report(directory="htmlcov")
            console.print(":page_facing_up: [green]Coverage report saved to htmlcov/index.html[/green]")
        except ImportError:
            console.print(":warning: [yellow]Coverage package not installed. Install with: pip install coverage[/yellow]")
            result = runner.run(suite)
    else:
        result = runner.run(suite)
    
    # Report results
    if result.wasSuccessful():
        console.print(f":white_check_mark: [bold green]All {total_tests} tests passed![/bold green]")
    else:
        failed = len(result.failures) + len(result.errors)
        console.print(f":x: [bold red]{failed} test(s) failed out of {total_tests}[/bold red]")
        if result.failures:
            console.print(f":boom: [red]Failures: {len(result.failures)}[/red]")
        if result.errors:
            console.print(f":rotating_light: [red]Errors: {len(result.errors)}[/red]")


def _add_legacy_paths(test_paths: list, test_root: Path, directories: list):
    """Add legacy test paths to the test paths list."""
    for directory in directories:
        legacy_path = test_root / directory
        if legacy_path.exists():
            test_paths.append(str(legacy_path))


def _count_tests_in_suite(suite) -> int:
    """Count the number of tests in a test suite."""
    count = 0
    for test in suite:
        if hasattr(test, '_tests'):
            count += _count_tests_in_suite(test)
        else:
            count += 1
    return count
