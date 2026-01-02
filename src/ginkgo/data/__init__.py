# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: 数据模块公共接口提供依赖注入容器管理CRUD操作和数据源访问支持交易系统功能和组件集成


"""
Ginkgo Data Module

Data layer module with dependency injection container for managing services.

Usage:
    from ginkgo.data import container
    result = container.bar_service().get(code="000001.SZ")

Available services:
- container.bar_service() - K线数据服务
- container.tick_service() - Tick数据服务
- container.stockinfo_service() - 股票信息服务
- container.adjustfactor_service() - 复权因子服务
- container.file_service() - 文件管理服务
- container.engine_service() - 回测引擎服务
- container.portfolio_service() - 投资组合服务
- container.component_service() - 组件实例化服务
"""

# Import the dependency injection container
from ginkgo.data.containers import container

# Import seeding module for data initialization
from ginkgo.data import seeding

# Import CRUD utility for direct CRUD access
from ginkgo.data.utils import get_crud

__all__ = ["container", "seeding", "get_crud"]
