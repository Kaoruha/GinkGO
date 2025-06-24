# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ginkgo is a Python backtesting library for trading research that supports both vectorized and event-driven backtesting. The project includes:

- Core backtesting engine with event-driven architecture
- Data management with multiple database backends (ClickHouse, MySQL, MongoDB, Redis)
- Multiple data sources (Tushare, Yahoo Finance, AKShare, BaoStock, TDX)
- Trading strategies, portfolio management, and risk management
- Machine learning integration for quantitative trading
- Web UI built with Vue.js and TypeScript
- Command-line interface using Typer

## Architecture

### Core Components

- **Backtest Engine** (`src/ginkgo/backtest/`): Event-driven backtesting framework
  - `engines/`: Different execution engines (historic, live, kafka, etc.)
  - `events/`: Event system for price updates, orders, signals
  - `strategies/`: Trading strategy implementations
  - `portfolios/`: Portfolio management and position tracking
  - `analyzers/`: Performance analysis and metrics

- **Data Layer** (`src/ginkgo/data/`): 
  - `drivers/`: Database drivers for different backends
  - `models/`: SQLAlchemy models for data persistence
  - `operations/`: CRUD operations for all data models
  - `sources/`: Data source adapters

- **Client Interface** (`src/ginkgo/client/`): CLI commands and TUI interface

- **Web Frontend** (`web/`): Vue.js application for visualization and control

### Key Patterns

- Event-driven architecture: All backtesting operations flow through events
- Strategy pattern: Trading strategies inherit from base classes
- Factory pattern: Engine assembler creates appropriate engine configurations
- Plugin architecture: Modular components for strategies, analyzers, data sources

## Commands

### Python Environment Setup
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
# Show version and status
ginkgo version
ginkgo status

# Data management
ginkgo data init                           # Initialize database tables
ginkgo data update stockinfo               # Update stock information
ginkgo data update calendar                # Update trading calendar
ginkgo data update day --code 000001.SZ    # Update daily bar data
ginkgo data update tick --code 000001.SZ   # Update tick data
ginkgo data list stockinfo --page 50       # List stock info
ginkgo data plot day --code 000001.SZ --start 20200101 --end 20210101

# Backtesting
ginkgo backtest ls                         # List available backtests
ginkgo backtest run {id}                   # Run specific backtest

# Development and testing
ginkgo config --debug on/off              # Enable/disable debug mode
ginkgo unittest run --a                   # Run all unit tests

# Services
ginkgo server                              # Start API server
ginkgo jupyter                             # Start Jupyter Lab
ginkgo chat                               # Interactive CLI mode
```

### Web Development Commands
```bash
cd web/
npm run dev                    # Start development server
npm run build                  # Build for production
npm run type-check            # TypeScript type checking
npm run lint                  # ESLint with auto-fix
npm run format               # Prettier formatting
```

### Testing

**IMPORTANT**: Before running unit tests, ensure debug mode is enabled:

```bash
# Check current debug mode status
ginkgo status

# Enable debug mode for testing (required for unit tests)
ginkgo config --debug on

# Disable debug mode after testing
ginkgo config --debug off

# Python tests - run from root directory
python -m pytest test/ -v

# Ginkgo unit tests
ginkgo unittest run --a                   # Run all unit tests

# Web tests
cd web/
npm run type-check
npm run lint
```

## Configuration

- Main config: `~/.ginkgo/config.yaml`
- Secure credentials: `~/.ginkgo/secure.yml`
- Package config: `src/ginkgo/config/package.py`

## Development Notes

- The project uses SQLAlchemy for ORM with multiple database backends
- Event system is central to backtesting - all components communicate via events
- Web UI communicates with Python backend via FastAPI
- Strategies should inherit from `BaseStrategy` class
- New data sources should implement the `SourceBase` interface
- All database models use the base classes in `model_clickbase.py` and `model_mysqlbase.py`