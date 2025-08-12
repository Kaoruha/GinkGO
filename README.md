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

### Configuration

Configure databases and data sources:

```bash
# Edit main configuration
vi ~/.ginkgo/config.yaml

# Set secure credentials (base64 encoded)
vi ~/.ginkgo/secure.yml
```

**Secure Configuration Template:**
```yaml
database:
  clickhouse:
    database: ginkgo
    username: admin
    password: {base64_encoded_password}
    host: localhost
    port: 8123
  mysql:
    database: ginkgo
    username: ginkgoadmin
    password: {base64_encoded_password}
    host: localhost
    port: 3306
  mongodb:
    database: ginkgo
    username: ginkgoadm
    password: {base64_encoded_password}
tushare:
  token: {your_tushare_token}
```

### Verification

```bash
ginkgo version    # Check installation
ginkgo status     # System status overview
```

## 📊 Data Management

### Initialize Database

```bash
ginkgo system config set --debug on  # Required for database operations
ginkgo data init                      # Create tables and seed data
```

### Data Updates

```bash
# Stock information
ginkgo data update --stockinfo

# Trading calendar  
ginkgo data update --calendar

# Daily bars
ginkgo data update day --code 000001.SZ

# Tick data
ginkgo data update tick --code 000001.SZ

# Adjustment factors
ginkgo data update adjust --code 000001.SZ
```

### Data Exploration

```bash
# List stocks
ginkgo data list stockinfo --page 50

# Show specific stock data
ginkgo data show day --code 000001.SZ --adjusted --adj-type fore

# Plot candlestick charts
ginkgo data plot day --code 000001.SZ --start 20200101 --end 20210101
```

## 🔄 Backtesting

### Strategy Development

```python
from ginkgo.backtest.strategy.strategies.base_strategy import BaseStrategy
from ginkgo.backtest.entities import Signal
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

### Risk Management

```python
from ginkgo.backtest.strategy.risk_managements import (
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

### Running Backtests

```bash
# List available strategies
ginkgo backtest component list strategy

# Run backtest
ginkgo backtest run {engine_id}

# View results
ginkgo backtest result show {result_id}
```

## 👨‍💻 Development

### Worker Management

```bash
# View worker status
ginkgo worker status

# Start workers
ginkgo worker start --count 4

# Debug single worker
ginkgo worker run --debug
```

### Testing

```bash
ginkgo system config set --debug on  # Required for tests
ginkgo unittest run --a               # Run all tests
python -m pytest test/ -v             # Alternative
```

### Development Services

```bash
ginkgo dev server   # Start FastAPI server
ginkgo dev jupyter  # Launch Jupyter Lab
```

## 🛠️ API Usage

### Service Access Pattern

```python
from ginkgo import services

# Data services
bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()

# Backtest services  
engine = services.backtest.engines.historic()
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