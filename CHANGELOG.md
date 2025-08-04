##### 0.8.1
  - [x] **Architecture Refactoring** - 架构重构
  - - [x] Reorganize backtest module structure into functional modules
  - - [x] Split backtest into: analysis/, computation/, core/, entities/, execution/, services/, strategy/, trading/
  - - [x] Implement unified service architecture with dependency injection containers
  - - [x] Restructure data layer with improved CRUD operations
  - - [x] Optimize test architecture and organization
  - [x] **CLI Enhancements** - CLI功能增强
  - - [x] Add container management commands (`ginkgo container`)
  - - [x] Add data source management commands (`ginkgo datasource`)
  - - [x] Enhance development tools (`ginkgo dev`)
  - - [x] Expand system management capabilities
  - [x] **Technical Indicators & Analysis** - 技术指标和分析
  - - [x] Add new technical analysis indicators (RSI, Bollinger Bands, etc.)
  - - [x] Implement Alpha158 factor factory
  - - [x] Add advanced performance analyzers (Calmar ratio, Sortino ratio, VaR/CVaR)
  - - [x] Enhance evaluation and metric stability tools
  - [x] **Bug Fixes & Optimizations** - 修复和优化
  - - [x] Update unit test framework and fix test issues
  - - [x] Update requirements and dependencies
  - - [x] Code structure cleanup and optimization
  - - [x] Performance improvements and stability enhancements

##### 1.0(FUTURE)
  - [x] Update Python > 3.11.
  - [x] Update Sqlalchemy > 2.0.
  - [x] Upgrade Backtest Framework.

  ~~- [DEV] Support MongoDB and Clickhouse.~~

  - [x] Support MysqlDB and Clickhouse.
  - [x] Add 2 or 3 DataSource.
  - [x] Add ML Engine.
  - [x] ML Integration Module
  - - [x] Scikit-learn, PyTorch, TensorFlow integration
  - - [x] Alpha factor mining and feature engineering
  - - [x] Model training and validation pipeline
  - - [x] Real-time ML inference in backtesting
  - [TODO] Vectorized Backtesting Engine
  - - [TODO] NumPy/Pandas vectorized operations
  - - [TODO] Batch processing for multiple strategies
  - - [TODO] Performance optimization for big datasets
  - - [TODO] Memory-efficient data handling
  - [x] Enhanced TUI (Terminal User Interface)
  - - [x] Rich terminal UI with real-time updates
  - - [x] Interactive strategy monitoring
  - - [x] Advanced data visualization in terminal
  - - [x] Intuitive navigation and controls
  - [x] Advanced Risk Management System
  - - [x] Real-time position and exposure monitoring
  - - [x] VaR (Value at Risk) calculation
  - - [x] Drawdown control mechanisms
  - - [x] Portfolio-level risk metrics
  - - [x] Customizable risk alerts and limits
  - [TODO] Support other markets.

##### 0.9.0
  - [TODO]  Support More DataSource
  - - [TODO]  Support NSQ
  - - [TODO]  Support Cryptocurrency exchanges
  - - [TODO]  Support International markets

##### 0.7.1(DEV)
  - [x] Support Data Cache with Redis.
  - [x] Add Notification
  - - [x] Add Telegram Notification
  - - [x] Add Beep Notification
  - - [x] Add Mail Notification
  - - [x] Add Wechat Notification
  - [x] Basic Live engine demo

##### 0.6.2
  - [x] Fix precision lost problem.
  - [x] Add CLI
  - [x] Add Trading Records.
  - [x] Support More Flexible Data Interval
  - [x] Config file setup

##### 0.6
  - - [x] Plot Moduel

##### 0.5.2
  - [x] Basic Backtest demo
  - [x] TDX

##### 0.5.1
  - [x] Backtest Engine Upgrade
  - - [x] Optimize Backtest Engine
  - - [x] Backtest Engine Unittest

##### 0.5
  - [x] Tushare
  - [x] AK Share
  - [x] Baostock


##### 0.4
  - [x] Create Standard Data Interface.
  - [x] Optimize DataEngine.
  - [x] Optimize MysqlBase.

##### 0.3
  - [x] Support Multi Databases.
  - - [x] Support Clickhouse
  - - [x] Support Mysql

##### 0.2
  - [x] Update to Python3.11

##### 0.1.5
  - [x] Optimize Architecture.

##### 0.1.4
  - [x] Add Clickhouse Driver.

##### 0.1.30
  - [x] Complete Engine Test
  - [x] Fix GinkgoEngine

##### 0.1.25
  - [x] DataUpdate bug fix.

##### 0.1.24
  - [x] Upgrade AutoDeployment Script.
  - - [x] Add Auto Compile and install script  setup_auto.py
  - - [x] Refactoring of install.py

##### 0.1.23
  - [x] Upgrade GinkgoMongo
  - - [x] Refactoring of Async Methods

##### 0.1.22
  - [x] Fix GinkgoMongo DF Copy() Bug.

##### 0.1.21
  - [x] SimMatcher UnitTest.
  - [x] T1Broker UnitTest.
  - [x] Refactoring of DataEngine.

##### 0.1.20
  - [x] Sizer UnitTest.
  - [x] Matcher UnitTest.
  - [x] Selector UnitTest.
  - [x] Events UnitTest.
  - [x] Analyzer Unittest.
  - [x] BaseBroker UnitTest.

##### 0.1.19
  - [x] Position UnitTest.
  - [x] Add Broker UnitTest.

##### 0.1.18
  - [x] Fix bugs on MacOS.
