# Ginkgo

Modern Python Quantitative Trading Library — event-driven backtesting, multi-database support, complete risk control, and a Web UI for strategy management.

## Features

- **Event-Driven Backtesting**: `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill`
- **Multi-Database**: ClickHouse (time-series), MySQL (relational), MongoDB (documents), Redis (cache)
- **Multiple Data Sources**: Tushare, AKShare, Yahoo Finance, BaoStock, TDX
- **Complete Risk Control**: position sizing, stop-loss / take-profit, real-time monitoring
- **Web UI**: Vue 3 + shadcn-vue dashboard for portfolio / backtest / component management
- **Live Trading**: OKX integration with heartbeat monitoring (⚠️ end-to-end pending — see [e2e audit](docs/e2e-cli-flow-audit.md))
- **CLI**: Typer + Rich

> Architecture diagrams, component inventory, design rules, dev reference → [docs/claude-dev-reference.md](docs/claude-dev-reference.md) · [ADRs](docs/adrs/README.md)

## Installation

```bash
# uv (recommended)
uv sync
```

Requires [uv](https://docs.astral.sh/uv/). Docker containers (Kafka, Redis, MySQL, ClickHouse, MongoDB) start automatically. After install, `ginkgo` is globally available:

```bash
ginkgo version
ginkgo status
ginkgo debug on          # Required for database operations
```

### Configuration

`~/.ginkgo/` is the single config home, initialized by `install.py` (`copy_config`) and materialized on demand by `GCONF` (`generate_config_file`). Both resolve templates from the package's bundled `config/` dir (via `__file__`), so host / container / wheel installs land on the same layout.

```bash
vi ~/.ginkgo/config.yml       # Main config
vi ~/.ginkgo/secure.yml       # Credentials (base64 encoded)
vi ~/.ginkgo/task_timer.yml   # tasktimer worker schedule
```

Force-overwrite stale config: `python install.py -updateconfig`. Docker workers mount the host `~/.ginkgo` read-only at `/root/.ginkgo` (`x-worker-common` volume).

## Usage

```bash
# Data
ginkgo data init
ginkgo data update --stockinfo
ginkgo data update day --code 000001.SZ

# Portfolio & components
ginkgo portfolio create --name "my" --capital 1000000
ginkgo component list
ginkgo portfolio bind-component <pid> <file_id> --type strategy \
  --param '0:MyStrategy' --param '1:14'        # index 0 = constructor name

# Backtest
ginkgo backtest create --portfolio <pid> --start 2025-01-01 --end 2026-01-01 --name "test"
ginkgo backtest run <id>
ginkgo backtest cat <id>

# Deploy (paper / live) — ⚠️ end-to-end pending, see e2e audit
ginkgo account create <user_id> --exchange okx --name "my_okx" --api-key <k> --api-secret <s>
ginkgo deploy deploy <pid> --mode paper
ginkgo deploy deploy <pid> --mode live --account <account_uuid>

# Servers
ginkgo serve api      # FastAPI on :8000
ginkgo serve webui    # Vue dev server on :5173
```

Full CLI walkthrough (build → backtest → paper → live) → [docs/e2e-cli-flow-audit.md](docs/e2e-cli-flow-audit.md)

### Write a Strategy

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

Risk managers, analyzers, selectors, sizers → [docs/claude-dev-reference.md](docs/claude-dev-reference.md)

## Requirements

- **Python**: 3.12.8+
- **Databases**: ClickHouse, MySQL, MongoDB, Redis
- **OS**: Linux, macOS, Windows
- **Memory**: 4GB+ recommended for backtesting

## Contributing

1. Branch: `{seq}-{type}/{description}` — types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`. Next seq: `git branch -r | grep -oP '\d+(?=-)' | sort -n | tail -1`
2. Tests in `tests/` (no in-module `tests/` subdirs)
3. Open a Pull Request

## License

MIT — see [LICENSE](LICENSE).
