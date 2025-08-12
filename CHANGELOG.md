# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Vectorized backtesting engine with NumPy/Pandas optimizations
- Batch processing support for multiple strategies
- Advanced portfolio optimization algorithms
- Real-time performance dashboard
- International market data support (US, HK)
- Cryptocurrency data sources integration
- Advanced factor mining tools with ML integration

### Changed
- Enhanced backtest performance for large datasets
- Improved memory efficiency for big data processing
- Extended API documentation with more examples

### Planned
- NSQ message queue integration for real-time data streaming
- WebSocket API for live trading interfaces
- Advanced risk analytics with Monte Carlo simulations
- Multi-timeframe strategy support
- Enhanced visualization tools with interactive charts

## [0.8.2] - 2025-01-12

### Added
- Complete risk management system with PositionRatioRisk, LossLimitRisk, and ProfitLimitRisk
- Dual risk control mechanism: passive order interception and active signal generation
- Event-driven risk monitoring responding to price updates in real-time
- Smart order volume adjustment instead of simple order rejection

### Changed
- Unified worker status display format between `ginkgo status` and `ginkgo worker status`
- Enhanced CLI interface with rich table format for worker information
- Improved system status overview with detailed worker monitoring

### Removed
- Redundant `manual_worker.py` script (functionality replaced by `ginkgo worker run`)

## [0.8.1] - 2024-12-15

### Added
- Reorganized backtest module structure into functional modules (analysis/, computation/, core/, entities/, execution/, services/, strategy/, trading/)
- Unified service architecture with dependency injection containers
- Container management commands (`ginkgo container`)
- Data source management commands (`ginkgo datasource`)
- New technical analysis indicators (RSI, Bollinger Bands, etc.)
- Alpha158 factor factory implementation
- Advanced performance analyzers (Calmar ratio, Sortino ratio, VaR/CVaR)

### Changed
- Enhanced development tools (`ginkgo dev`)
- Expanded system management capabilities
- Restructured data layer with improved CRUD operations
- Optimized test architecture and organization

### Fixed
- Unit test framework issues
- Updated requirements and dependencies
- Code structure cleanup and optimization
- Performance improvements and stability enhancements

## [0.7.1] - 2024-10-20

### Added
- Data cache system with Redis support
- Notification system (Telegram, Beep, Mail, WeChat)
- Basic live trading engine demo

## [0.6.2] - 2024-08-15

### Added
- CLI interface
- Trading records system
- Flexible data interval support
- Configuration file setup

### Fixed
- Precision lost problem

## [0.6.0] - 2024-06-10

### Added
- Plot module for data visualization

## [0.5.2] - 2024-04-20

### Added
- Basic backtest demonstration
- TDX data source integration

## [0.5.1] - 2024-03-15

### Changed
- Optimized backtest engine performance
- Enhanced backtest engine with comprehensive unit tests

## [0.5.0] - 2024-02-10

### Added
- Tushare data source integration
- AKShare data source integration
- Baostock data source integration

## [0.4.0] - 2024-01-05

### Added
- Standard data interface
- Optimized DataEngine
- Enhanced MysqlBase functionality

## [0.3.0] - 2023-11-20

### Added
- Multi-database support with ClickHouse integration
- MySQL database integration

## [0.2.0] - 2023-10-15

### Changed
- Updated to Python 3.11 support

## [0.1.5] - 2023-09-10

### Changed
- Architecture optimization

## [0.1.4] - 2023-08-25

### Added
- ClickHouse database driver

## [0.1.30] - 2023-08-01

### Added
- Complete engine testing framework

### Fixed
- GinkgoEngine critical issues

## [0.1.25] - 2023-07-15

### Fixed
- DataUpdate module bugs

## [0.1.24] - 2023-07-01

### Added
- Auto compile and install script (setup_auto.py)

### Changed
- Refactored install.py deployment process

## [0.1.23] - 2023-06-15

### Changed
- Refactored GinkgoMongo async methods

## [0.1.22] - 2023-06-01

### Fixed
- GinkgoMongo DataFrame copy() bug

## [0.1.21] - 2023-05-20

### Added
- SimMatcher unit tests
- T1Broker unit tests

### Changed
- DataEngine refactoring

## [0.1.20] - 2023-05-05

### Added
- Sizer component unit tests
- Matcher component unit tests
- Selector component unit tests
- Events system unit tests
- Analyzer component unit tests
- BaseBroker unit tests

## [0.1.19] - 2023-04-20

### Added
- Position management unit tests
- Broker component unit tests

## [0.1.18] - 2023-04-05

### Fixed
- macOS compatibility issues