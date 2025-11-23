# Ginkgo


🚀 **Modern Python Quantitative Trading Library**

Ginkgo is a comprehensive quantitative trading framework featuring event-driven backtesting, multi-database support, and complete risk management systems.

## ✨ Features

- 🎯 **Event-Driven Backtesting Engine**: Complete event chain from price updates to order fills
- 💾 **Multi-Database Support**: ClickHouse, MySQL, MongoDB, Redis with unified interfaces
- 📊 **Multiple Data Sources**: Tushare, Yahoo Finance, AKShare, BaoStock, TDX integration
- ⚡ **High-Performance Architecture**: Dependency injection, lazy loading, caching optimization
- 🛡️ **Complete Risk Control**: Position management, stop-loss/profit, real-time monitoring
- 🔧 **Rich CLI Interface**: Beautiful terminal UI with comprehensive management commands
- 🧠 **ML Integration**: Machine learning strategies and factor engineering support

## 🏗️ Architecture

```
Event-Driven Flow: PriceUpdate → Strategy → Signal → Portfolio → Order → Fill

Core Components:
├── Data Layer        # Multi-database unified access
├── Strategy Layer    # Trading strategies with risk control
├── Execution Layer   # Order matching and portfolio management
├── Analysis Layer    # Performance analysis and visualization
└── Service Layer     # Dependency injection and global utilities
```

### ⏰ TimeRelated Architecture Design

**Design Principle**: TimeRelated mixin provides time advancement capabilities for components that need active time progression in backtesting scenarios.

**Entity Classification**:

📦 **Data Containers** (No TimeRelated inheritance needed):
- `Bar`, `Tick`, `Adjustfactor`: Pure data containers with timestamp attributes
- These entities store **data timestamps** but don't need **time progression**
- Their timestamp represents when the data occurred, not current processing time

🎯 **Business Logic Entities** (TimeRelated inheritance appropriate):
- `Order`, `Signal`: May need time progression for business logic (expiry, decay)
- `Position`: May track holding duration and time-based calculations
- `Transfer`: May need time progression for transaction processing

🏗️ **System Components** (TimeRelated inheritance essential):
- Backtesting engines: Drive time progression across the entire system
- Strategy components: Need current time awareness for decision making
- Portfolio managers: Require time progression for state updates

**Key Methods**:
- `advance_time(target_time)`: Move forward in time (no backward movement allowed)
- `now`: Current processing time (distinct from data timestamps)
- `is_before(other_time)` / `is_after(other_time)`: Time comparison utilities
- `time_elapsed_since(start_time)`: Calculate time differences
- `can_advance_to(target_time)`: Validate time advancement
- `reset_time()`: Reset time state for testing/restarting

This design ensures clean separation between **data time** (when something happened) and **processing time** (current system state), critical for accurate backtesting.

## 🚀 Quick Start

### Installation

Create virtual environment and install:

```bash
# Using virtualenv
python3 -m virtualenv venv && source venv/bin/activate
python ./install.py

# Using conda  
conda create -n ginkgo python=3.12.8
conda activate ginkgo
python ./install.py
```

### ⭐ Global Command Access

**After installation, Ginkgo becomes globally available - no environment activation needed!**

```bash
# Works from anywhere, any Python environment, any directory
ginkgo version                    # Check installation
ginkgo status                     # System status overview  
ginkgo data update --stockinfo    # Update stock data
ginkgo worker start --count 4     # Start data workers
ginkgo backtest run {engine_id}   # Run backtests

# 🎯 Key Advantage: No need to activate environments or be in project directory
```

This design makes Ginkgo perfect for:
- **System services** and **cron jobs** (no environment switching)
- **Production deployment** (consistent command interface)  
- **Multi-environment usage** (same command works everywhere)

### Configuration

Configure databases and data sources:

```bash
# Edit main configuration
vi ~/.ginkgo/config.yaml

# Set secure credentials (base64 encoded)
vi ~/.ginkgo/secure.yml
```

**Secure Configuration Template (~/.ginkgo/secure.yml):**
```yaml
database:
  clickhouse:
    database: ginkgo
    username: admin
    password: {password ==> base64encoder}
    host: localhost
    port: 8123
  mysql:
    database: ginkgo
    username: ginkgoadmin
    password: {password ==> base64encoder}
    host: localhost
    port: 3306
  mongodb:
    database: ginkgo
    username: ginkgoadm
    password: {password ==> base64encoder}
tushare:
  token: {tokenhere}
```

## 📊 Core Commands

### System Management
```bash
# System status and configuration
ginkgo version                        # Show version info
ginkgo status                         # System status overview
ginkgo debug on/off                   # Toggle debug mode
ginkgo config                         # Show configuration

# Quick setup
ginkgo init                           # Initialize system and database
```

### Data Operations
```bash
# Data fetching (simplified commands)
ginkgo get stockinfo                  # Fetch stock information
ginkgo get calendar                   # Fetch trading calendar
ginkgo get bars --code 000001.SZ     # Fetch daily bar data
ginkgo get ticks --code 000001.SZ    # Fetch tick data

# Data exploration
ginkgo show stocks                    # List available stocks
ginkgo show bars --code 000001.SZ    # Show bar data
ginkgo plot 000001.SZ --start 20230101 # Plot candlestick charts

# Advanced data management
ginkgo data init                      # Initialize database tables
ginkgo data update --stockinfo        # Update stock information
ginkgo data update day --code 000001.SZ  # Update daily data
ginkgo data list stockinfo --page 50 # List with pagination
```

### Backtesting
```bash
# Strategy and backtest management
ginkgo list strategies                # List available strategies
ginkgo list engines                   # List backtest engines
ginkgo run {engine_id}               # Run backtest (simplified)
ginkgo results {engine_id}           # Show backtest results

# Advanced backtesting
ginkgo backtest run {engine_id}      # Full backtest command
ginkgo backtest result show {id}     # Detailed results
ginkgo backtest component list strategy # List strategy components
```

### Worker Management
```bash
# Worker operations
ginkgo worker status                  # Show worker processes
ginkgo worker start --count 4         # Start data workers
ginkgo worker stop --all              # Stop all workers
ginkgo worker run --debug             # Debug single worker
ginkgo worker scale 6                 # Scale to 6 workers
```

### Development Tools
```bash
# Testing
ginkgo test --all                     # Run all tests (simplified)
ginkgo test run --all                 # Full test command

# Development services
ginkgo dev server                     # Start FastAPI server
ginkgo dev jupyter                    # Launch Jupyter Lab

# Advanced tools
ginkgo kafka status                   # Kafka cluster status
ginkgo cache clear                    # Clear cache
ginkgo datasource list                # List data sources
ginkgo container status               # Container management
ginkgo evaluation run                 # Performance evaluation
```

## 🔄 Strategy Development

### Basic Strategy Template

```python
from ginkgo.trading.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities import Signal
from ginkgo.enums import DIRECTION_TYPES

class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        # Your trading logic here
        if self.should_buy():
            return [Signal(
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                reason="Buy signal"
            )]
        return []
```

### Risk Management Integration

```python
from ginkgo.trading.strategy.risk_managements import (
    PositionRatioRisk, 
    LossLimitRisk, 
    ProfitLimitRisk
)

# Position control (max 20% per stock, 80% total)
portfolio.add_risk_manager(PositionRatioRisk(
    max_position_ratio=0.2,
    max_total_position_ratio=0.8
))

# Stop-loss at 10%
portfolio.add_risk_manager(LossLimitRisk(loss_limit=10.0))

# Take-profit at 20%  
portfolio.add_risk_manager(ProfitLimitRisk(profit_limit=20.0))
```

## 🛠️ API Usage

### Service Access Pattern

```python
from ginkgo import services

# Data services
bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()

# Trading services  
engine = services.trading.engines.historic()
```

### Common Operations

```python
from ginkgo.libs import GLOG, GCONF, GTM

# Configuration
debug_mode = GCONF.DEBUGMODE
db_host = GCONF.get("database.host")

# Logging
GLOG.info("Processing data...")
GLOG.ERROR("Connection failed")

# Worker management
GTM.start_multi_worker(count=4)
status = GTM.get_workers_status()
```

## 🎯 Performance Features

- **Lazy Loading**: Dynamic imports for faster startup
- **Multi-Level Caching**: Redis + Memory + Method-level caching  
- **Batch Processing**: Optimized data operations
- **Event-Driven**: Asynchronous processing pipeline
- **Decorator Optimization**: `@time_logger`, `@retry`, `@cache_with_expiration`

## 📋 System Requirements

- **Python**: 3.12.8+
- **Databases**: ClickHouse (time-series), MySQL (relational), Redis (cache), MongoDB (documents)
- **OS**: Linux, macOS, Windows
- **Memory**: 4GB+ recommended for backtesting

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Rich**: Beautiful terminal interfaces
- **Typer**: Modern CLI framework
- **Dependency-Injector**: Professional DI container
- **ClickHouse**: High-performance analytics database
- **Tushare**: Financial data provider

---

**Made with ❤️ for quantitative trading research**
