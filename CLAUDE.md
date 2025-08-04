# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ginkgo is a Python quantitative trading library featuring:
- Event-driven backtesting engine with multi-database support (ClickHouse, MySQL, MongoDB, Redis)
- Multiple data sources (Tushare, Yahoo, AKShare, BaoStock, TDX)
- Trading strategies, portfolio management, and risk control
- CLI interface using Typer with rich formatting
- Unified services architecture with dependency injection containers

## Memories

- Emoji使用Rich的:sun:模板

## Key Commands

### Environment Setup
```bash
# Create virtual environment and install
python3 -m virtualenv venv && source venv/bin/activate
python ./install.py

# Or with conda
conda create -n ginkgo python=3.12.8
conda activate ginkgo
python ./install.py
```

### Core CLI Commands
```bash
# Version and system status
ginkgo version
ginkgo system status
ginkgo system config show

# Data management
ginkgo data init                           # Initialize database tables
ginkgo data update --stockinfo             # Update stock information
ginkgo data update --calendar              # Update trading calendar
ginkgo data update day --code 000001.SZ    # Update daily bar data
ginkgo data update tick --code 000001.SZ   # Update tick data
ginkgo data list stockinfo --page 50       # List stock info
ginkgo data plot day --code 000001.SZ --start 20200101 --end 20210101
ginkgo data show day --code 000001.SZ --adjusted --adj-type fore

# Backtesting
ginkgo backtest run {engine_id}            # Run specific backtest
ginkgo backtest component list strategy    # List strategies
ginkgo backtest result show {id}           # View backtest results

# Development and testing
ginkgo system config set --debug on       # Enable debug mode (REQUIRED for tests)
ginkgo unittest run --a                   # Run all unit tests
ginkgo system config set --debug off      # Disable debug mode after testing

# Development services
ginkgo dev server                          # Start FastAPI server
ginkgo dev jupyter                         # Start Jupyter Lab
ginkgo worker status                       # Show worker processes
```

### Testing Requirements
**CRITICAL**: Always enable debug mode before running tests:
```bash
ginkgo system config set --debug on    # Required for tests
ginkgo unittest run --a                # Run all tests
python -m pytest test/ -v              # Alternative
ginkgo system config set --debug off   # Disable after testing
```

## Architecture Overview

### Directory Structure
- `src/ginkgo/backtest/`: Event-driven backtesting engine
  - `core/`, `entities/`, `execution/`, `strategy/`, `analysis/`
- `src/ginkgo/data/`: Data layer with drivers, models, CRUD operations, sources
- `src/ginkgo/client/`: CLI interface using Typer
- `src/ginkgo/libs/`: Core utilities, configuration, threading
- `src/ginkgo/core/`: Core services and dependency injection containers

### Key Design Patterns

**Event-Driven Architecture**: 
MarketEvent → Strategy → SignalEvent → Portfolio → OrderEvent → Engine → FillEvent

**Template Method Pattern**: Base classes with override points
- `BaseStrategy.cal()` - Strategy implementation
- `BaseAnalyzer._do_activate()` - Performance analysis

**Factory Pattern**: `EngineAssemblerFactory().create_engine(engine_type="historic")`

**Dependency Injection**: Unified services via containers
```python
from ginkgo import services
bar_crud = services.data.cruds.bar()
engine = services.backtest.engines.historic()
```

**Lazy Loading**: Dynamic imports in `src/ginkgo/data/operations/__init__.py`

### Core Base Classes

**`Base`** (`src/ginkgo/backtest/core/base.py`): Foundation with UUID and source tracking
```python
class Base:
    def __init__(self, uuid: str = ""):
        self._uuid = uuid
        self._source = SOURCE_TYPES.VOID
    def to_dataframe(self) -> pd.DataFrame: ...
```

**Database Models**: `MClickBase` (ClickHouse), `MMysqlBase` (MySQL)
- Naming convention: `MBar`, `MTick`, `MStockInfo`, etc.

### Event System

**Event Types** (`src/ginkgo/enums.py`):
- `EVENT_TYPES`: PRICEUPDATE, SIGNALGENERATION, ORDERSUBMITTED, ORDERFILLED
- `DIRECTION_TYPES`: LONG, SHORT
- `ORDER_TYPES`: MARKETORDER, LIMITORDER
- `ORDERSTATUS_TYPES`: NEW, SUBMITTED, FILLED, CANCELED

**Event Flow**: Engine processes events through handlers, triggering strategy calculations and portfolio management

### Data Operations

**Consistent CRUD Pattern** (`src/ginkgo/data/operations/`):
All operations use lazy-loading and follow naming conventions:
```python
# Create operations
add_bar(data) / add_bars([data1, data2])

# Read operations  
get_bars_page_filtered(code="000001.SZ", start="20230101", end="20231231")

# Update operations
update_bar(uuid, new_data)

# Delete operations
delete_bars_filtered(code="000001.SZ", start="20230101")
```

### Global Utilities

**Performance Decorators** (`src/ginkgo/libs/utils/common.py`):
```python
@time_logger                     # Execution timing
@retry(max_try=5)               # Exponential backoff
@skip_if_ran                    # Redis caching
@cache_with_expiration(60)      # Memory caching
```

**Global Instances** (`src/ginkgo/libs/__init__.py`):
```python
from ginkgo.libs import GLOG, GCONF, GTM
GLOG.info("message")           # Rich logger
GCONF.get("database.host")     # Configuration
GTM.submit_task(func, args)     # Thread manager
```

## Configuration

**Config Files:**
- `~/.ginkgo/config.yaml` - Main configuration
- `~/.ginkgo/secure.yml` - Credentials
- `src/ginkgo/config/` - Package settings

**Multi-Database Support** (`src/ginkgo/data/drivers/`):
```python
from ginkgo.data.drivers import (
    create_mysql_connection,
    create_clickhouse_connection,
    create_redis_connection
)
```

## Development Guidelines

**Strategy Development**: 
```python
class MyStrategy(BaseStrategy):
    def cal(self) -> List[Signal]:
        # Implement trading logic
        return signals
```

**Testing Patterns**:
- Enable debug mode before testing
- Focus on core logic verification
- Test abstract method enforcement
- Verify error handling and edge cases

**Database Operations Requirements**:
**CRITICAL**: Always enable debug mode before any database operations (create, read, update, delete):
```bash
ginkgo system config set --debug on    # Required for database operations
# Perform database operations...
ginkgo system config set --debug off   # Disable after operations
```
This applies to:
- All CRUD operations
- Data initialization (`ginkgo data init`)
- Data updates (`ginkgo data update`)
- Backtest execution
- Any operations that modify database state

**Data Source Integration**: Implement `SourceBase` interface

**Component Creation**: Follow existing patterns in respective modules

## Key Entry Points

- `main.py`: CLI entry point with Typer
- `install.py`: Installation and setup script
- `src/ginkgo/__init__.py`: Unified services access
- `src/ginkgo/client/`: CLI command modules

## Important Notes

- The project uses Python 3.12.8
- Rich library for CLI formatting and console output
- Event-driven architecture for backtesting
- Lazy-loading for performance optimization
- Multi-database support with unified CRUD operations
- Debug mode is required for running tests