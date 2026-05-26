# Ginkgo

Modern Python Quantitative Trading Library

Ginkgo is a quantitative trading framework featuring event-driven backtesting, multi-database support, complete risk management, and a Web UI for strategy management.

## Features

- **Event-Driven Backtesting**: `PriceUpdate -> Strategy -> Signal -> Portfolio -> Order -> Fill`
- **Multi-Database Support**: ClickHouse (time-series), MySQL (relational), MongoDB (documents), Redis (cache)
- **Multiple Data Sources**: Tushare, Yahoo Finance, AKShare, BaoStock, TDX
- **Complete Risk Control**: Position management, stop-loss/profit, real-time monitoring
- **Web UI**: Vue 3 + Ant Design Vue dashboard for backtest/portfolio/component management
- **Live Trading**: OKX broker integration with heartbeat monitoring and crash recovery
- **CLI Interface**: Typer-based CLI with Rich formatting

## Architecture

### Four-Component Boundary

Trading logic is split into four components with unidirectional data flow:

```
Selector -> Strategy -> Sizer -> Risk
  |           |          |        |
  v           v          v        v
codes    signals     volume   adjusted order
```

| Component | Responsibility | Can |
|-----------|---------------|-----|
| **Selector** | Stock selection | Output `List[str]` of codes |
| **Strategy** | Generate trading signals | Output `List[Signal]` (direction + weight) |
| **Sizer** | Determine position size | Output integer volume |
| **Risk** | Risk control intercept | Only reduce or reject orders |

### Three-Layer Architecture

```
API / CLI Layer -> Service Layer -> CRUD Layer -> Database
```

- **CRUD Layer**: Pure data access, one class per table, inherits `BaseCRUD`
- **Service Layer**: Business logic orchestration, cross-CRUD operations, returns `ServiceResult`
- **API Layer**: Must call Service, never bypass to CRUD directly

### Service Access

```python
from ginkgo import services

bar_crud = services.data.cruds.bar()
stockinfo_service = services.data.services.stockinfo_service()
engine = services.trading.engines.historic()
```

## Quick Start

### Installation

```bash
# uv (recommended)
uv sync
```

> **Note:** You need [uv](https://docs.astral.sh/uv/) installed. If you don't have it, run `curl -LsSf https://astral.sh/uv/install.sh | sh`.

Docker containers (Kafka, Redis, MySQL, ClickHouse, MongoDB) start automatically.

### Global CLI

After installation, `ginkgo` is globally available:

```bash
ginkgo version
ginkgo status
ginkgo debug on          # Required for database operations
```

### Configuration

```bash
vi ~/.ginkgo/config.yaml   # Main config
vi ~/.ginkgo/secure.yml    # Credentials (base64 encoded)
```

## CLI Reference

### Data Management

```bash
ginkgo data init                           # Initialize database tables
ginkgo data update --stockinfo             # Update stock information
ginkgo data update day --code 000001.SZ    # Update daily bar data
ginkgo data list stockinfo --page 50       # List stock info
```

### Portfolio & Components

```bash
ginkgo portfolio create --name "my_portfolio" --capital 1000000
ginkgo portfolio list
ginkgo portfolio get <uuid> --details

ginkgo component list
ginkgo component create --type strategy --name "my_strategy"
ginkgo component show <uuid>

# Bind component with parameters
ginkgo portfolio bind-component <portfolio_id> <file_id> --type strategy \
  --param '0:"MyStrategy"' --param '1:0.3'
```

### Backtesting

```bash
ginkgo backtest create --portfolio <id> --start 2025-01-01 --end 2026-01-01 --name "test"
ginkgo backtest run <backtest_id>
ginkgo backtest cat <backtest_id>
ginkgo backtest list
```

### Worker Management

```bash
ginkgo worker status
ginkgo worker start --count 4
ginkgo worker run --debug
```

### Development Servers

```bash
ginkgo serve api      # FastAPI server on :8000
ginkgo serve webui    # Vue dev server on :5173
```

## Strategy Development

```python
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES

class MyStrategy(BaseStrategy):
    def cal(self, portfolio_info, event):
        bars = self.data_feeder.get_bars(code, start, end)
        if self.should_buy(bars):
            return [Signal(code=code, direction=DIRECTION_TYPES.LONG)]
        return []
```

### Risk Management

```python
from ginkgo.trading.risk_management.position_ratio_risk import PositionRatioRisk
from ginkgo.trading.risk_management.loss_limit_risk import LossLimitRisk
from ginkgo.trading.risk_management.profit_target_risk import ProfitTargetRisk

portfolio.add_risk_manager(PositionRatioRisk(max_position_ratio=0.2))
portfolio.add_risk_manager(LossLimitRisk(loss_limit=10.0))
portfolio.add_risk_manager(ProfitTargetRisk(profit_limit=20.0))
```

## Web UI

Vue 3 + Ant Design Vue + Lightweight Charts + ECharts dashboard:

```bash
ginkgo serve webui    # http://localhost:5173
```

Features: portfolio management, backtest creation/monitoring, component editor, real-time charts.

## Live Trading

OKX exchange integration with:

- **LiveEngine**: Unified lifecycle management
- **OKXBroker**: Exchange adapter implementing IBroker interface
- **BrokerManager**: Instance lifecycle (start/pause/resume/stop)
- **HeartbeatMonitor**: Timeout detection and recovery

```bash
python -m ginkgo.livecore.main live-start   # Start live engine
python -m ginkgo.livecore.main live-status  # Check status
```

## System Requirements

- **Python**: 3.12.8+
- **Databases**: ClickHouse, MySQL, MongoDB, Redis
- **OS**: Linux, macOS, Windows
- **Memory**: 4GB+ recommended for backtesting

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b {seq}-{type}/{description}`
   - Branch format: `{incrementing-number}-{type}/{description}`
   - Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
   - Example: `4128-feat/webui-navigation`
3. Commit and push to branch
4. Open Pull Request

## License

MIT License - see the LICENSE file for details.
