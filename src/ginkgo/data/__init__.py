# Upstream: Trading Strategies, Analysis Modules, Backtest Engines
# Downstream: ClickHouse, MySQL, MongoDB
# Role: 数据模块公共接口V6提供CRUD操作/数据源访问/流式数据处理和依赖注入容器管理支持交易系统功能和组件集成提供完整业务支持






"""
Ginkgo Data Module - Public API (V6)

This module is the main, simplified entry point to the data layer.
It leverages a Dependency Injection Container for managing services and their dependencies.

V6 updates: Added price adjustment support with new convenience APIs

⚠️ DEPRECATION NOTICE:
Most functions in this module are deprecated and will be removed in future versions.
Please use the service APIs directly via the container:

    # Old way (deprecated):
    from ginkgo.data import get_bars
    result = get_bars(code="000001.SZ", start_date="20230101", end_date="20231231")

    # New way (recommended):
    from ginkgo.data.containers import container
    result = container.bar_service().get(code="000001.SZ", start_date="20230101", end_date="20231231")

Available services:
- container.bar_service()
- container.tick_service()
- container.stockinfo_service()
- container.adjustfactor_service()
- container.file_service()
- container.engine_service()
- container.portfolio_service()
- container.component_service()
"""

import inspect

# Import the container to access services
from ginkgo.data.containers import container

# Import seeding module for direct access to seeding functions
from ginkgo.data import seeding

# Import utils for general utility functions that don't require service injection
from ginkgo.data.utils import get_crud  # get_crud is still needed for direct CRUD access in getters

from ginkgo.libs import time_logger, retry, skip_if_ran, GLOG
from ginkgo.enums import ADJUSTMENT_TYPES, FREQUENCY_TYPES
import pandas as pd
from datetime import datetime

# --- Public API Functions ---


@retry
@time_logger
def fetch_and_update_adjustfactor(code: str, fast_mode: bool = True, *args, **kwargs):
    """Public API: Synchronizes adjustment factors for a stock code."""
    container.adjustfactor_service().sync(code, fast_mode=fast_mode)


@retry
@time_logger
def calc_adjust_factors(code: str, *args, **kwargs):
    """
    Public API: Calculate fore/back adjustment factors for a stock code.

    This function corresponds to the CLI 'calc' command and triggers the calculation
    of fore and back adjustment factors based on existing raw adjustment factor data.

    Args:
        code: Stock code to calculate adjustment factors for
        *args, **kwargs: Additional arguments

    Returns:
        Dict containing calculation results with statistics and status
    """
    return container.adjustfactor_service().calculate(code, *args, **kwargs)


@retry
@time_logger
def recalculate_adjust_factors_for_code(code: str, *args, **kwargs):
    """
    Public API: Recalculate fore/back adjustment factors for a specific stock code.

    This function implements the separated architecture where raw adjustment factor
    data is pulled first, then fore/back adjust factors are calculated separately.

    Args:
        code: Stock code to recalculate adjustment factors for
        *args, **kwargs: Additional arguments

    Returns:
        Dict containing calculation results with success status and statistics
    """
    return container.adjustfactor_service().calculate(code, *args, **kwargs)


@retry
@skip_if_ran
@time_logger
def fetch_and_update_stockinfo(*args, **kwargs):
    """Public API: Synchronizes stock information for all stocks."""
    container.stockinfo_service().sync_all()


@retry
@time_logger
def fetch_and_update_tradeday(*args, **kwargs):
    """Public API: Synchronizes trading calendar data."""
    # This is a placeholder for trade day synchronization
    # The actual implementation would depend on the trade day service
    GLOG.DEBUG("Trade day synchronization - placeholder implementation")
    pass


@retry
@time_logger
def fetch_and_update_cn_daybar(code: str, fast_mode: bool = True, *args, **kwargs):
    """Public API: Synchronizes daily bar data for a stock code."""
    container.bar_service().sync_smart(code, fast_mode=fast_mode)


@retry
@time_logger
def fetch_and_update_cn_daybar_with_date_range(code: str, start_date=None, end_date=None, *args, **kwargs):
    """Public API: Synchronizes daily bar data for a stock code within specified date range."""
    from datetime import datetime

    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y%m%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y%m%d")

    return container.bar_service().sync_range(code, start_date, end_date, frequency=FREQUENCY_TYPES.DAY)


@retry
@time_logger
def fetch_and_update_cn_daybar_batch_with_date_range(codes: list, start_date=None, end_date=None, *args, **kwargs):
    """Public API: Synchronizes daily bar data for multiple stock codes within specified date range."""
    from datetime import datetime

    # Convert string dates to datetime if needed
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y%m%d")
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, "%Y%m%d")

    return container.bar_service().sync_range_batch(codes, start_date, end_date)


@retry
@time_logger
def fetch_and_update_tick(code: str, fast_mode: bool = False, *args, **kwargs):
    """Public API: Synchronizes tick data for a stock code."""
    container.tick_service().sync_smart(code)


@retry
@time_logger
def fetch_and_update_tick_incremental(code: str, *args, **kwargs):
    """增量同步：从数据库最新日期开始同步到当下"""
    return container.tick_service().sync_smart(code)


@retry
@time_logger
def fetch_and_update_tick_full(code: str, force_overwrite: bool = False, *args, **kwargs):
    """全量同步：从当前日期开始逐日回溯检查和同步

    已移动到TickService.sync_backfill_by_date()，这里保持向后兼容
    """
    return container.tick_service().sync_backfill_by_date(code=code, force_overwrite=force_overwrite)


@retry
@time_logger
def fetch_and_update_tick_all(*args, **kwargs):
    """全代码同步：同步所有股票的tick数据

    已迁移到KafkaService.send_tick_all_signal()，这里保持向后兼容
    建议使用container.kafka_service().send_tick_all_signal(full=False, force=False)
    """
    from ginkgo.data.containers import container

    stockinfo_service = container.stockinfo_service()
    stock_result = stockinfo_service.get()

    if not stock_result.success or not stock_result.data:
        raise Exception("Failed to get stock list")

    success_count = 0
    error_count = 0

    for stock in stock_result.data:
        try:
            result = fetch_and_update_tick_incremental(stock.code)
            if result:
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            error_count += 1
            print(f"Error syncing {stock.code}: {e}")

    return {
        "total": len(stock_result.data),
        "success": success_count,
        "error": error_count
    }


@time_logger
def init_example_data(*args, **kwargs):
    """Public API: Initializes a clean set of example data for backtesting."""
    seeding.run()


# --- Data Retrieval (Getters) ---
# Use services for data retrieval to leverage caching and business logic


def get_adjustfactors(*args, **kwargs):
    """Get adjustment factors using AdjustfactorService with caching.

    ⚠️ DEPRECATED: This function is deprecated. Use container.adjustfactor_service().get_adjustfactors() instead.
    """
    import warnings
    warnings.warn(
        "ginkgo.data.get_adjustfactors() is deprecated. Use container.adjustfactor_service().get_adjustfactors() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return container.adjustfactor_service().get_adjustfactors(*args, **kwargs)




def get_ticks(*args, **kwargs):
    """Get tick data using TickService with caching.

    ⚠️ DEPRECATED: This function is deprecated. Use container.tick_service().get(*args, **kwargs) instead.
    """
    import warnings
    warnings.warn(
        "ginkgo.data.get_ticks() is deprecated. Use container.tick_service().get(*args, **kwargs) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return container.tick_service().get(*args, **kwargs)


def get_bars_adjusted(code: str, adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE, *args, **kwargs):
    """
    Get price-adjusted bar data (convenience method).

    ⚠️ DEPRECATED: This function is deprecated. Use container.bar_service().get_bars_adjusted() instead.

    Args:
        code: Stock code (required for adjustment)
        adjustment_type: Price adjustment type (FORE/BACK)
        *args, **kwargs: Additional arguments passed to BarService

    Returns:
        Price-adjusted bar data as DataFrame or list of models
    """
    import warnings
    warnings.warn(
        "ginkgo.data.get_bars_adjusted() is deprecated. Use container.bar_service().get_bars_adjusted() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return container.bar_service().get_bars_adjusted(code, adjustment_type, *args, **kwargs)


def get_ticks_adjusted(code: str, adjustment_type: ADJUSTMENT_TYPES = ADJUSTMENT_TYPES.FORE, *args, **kwargs):
    """
    Get price-adjusted tick data (convenience method).

    ⚠️ DEPRECATED: This function is deprecated. Use container.tick_service().get_ticks_adjusted() instead.

    Args:
        code: Stock code (required for adjustment)
        adjustment_type: Price adjustment type (FORE/BACK)
        *args, **kwargs: Additional arguments passed to TickService

    Returns:
        Price-adjusted tick data as DataFrame or list of models
    """
    import warnings
    warnings.warn(
        "ginkgo.data.get_ticks_adjusted() is deprecated. Use container.tick_service().get_ticks_adjusted() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return container.tick_service().get_ticks_adjusted(code, adjustment_type, *args, **kwargs)


# --- Stock Info Query Functions (now part of StockinfoService) ---


def get_stockinfos(*args, **kwargs):
    """
    ⚠️ DEPRECATED: This function is deprecated. Use container.stockinfo_service().get(*args, **kwargs) instead.
    """
    import warnings
    warnings.warn(
        "ginkgo.data.get_stockinfos() is deprecated. Use container.stockinfo_service().get(*args, **kwargs) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return container.stockinfo_service().get(*args, **kwargs)


def get_stockinfo_codes_set():
    return container.stockinfo_service().get_stockinfo_codes_set()


def is_code_in_stocklist(code: str) -> bool:
    return container.stockinfo_service().is_code_in_stocklist(code)


# --- Additional Utility Functions ---


def is_tick_in_db(code: str, date, *args, **kwargs) -> bool:
    """Check if tick data exists in database for a specific code and date."""
    return container.tick_service().is_tick_data_available(code, date)


def count_bars(code: str = None, **kwargs) -> int:
    """Count bar records matching the filters."""
    return container.bar_service().count_bars(code, **kwargs)


def count_ticks(code: str = None, date=None, **kwargs) -> int:
    """Count tick records matching the filters."""
    return container.tick_service().count_ticks(code, date, **kwargs)


def count_adjustfactors(code: str = None, **kwargs) -> int:
    """Count adjustment factor records matching the filters."""
    return container.adjustfactor_service().count_adjustfactors(code, **kwargs)


def get_available_bar_codes(**kwargs) -> list:
    """Get list of stock codes that have bar data."""
    return container.bar_service().get_available_codes()


def get_available_tick_codes(**kwargs) -> list:
    """Get list of stock codes that have tick data."""
    return container.tick_service().get_available_codes()


def get_available_adjustfactor_codes(**kwargs) -> list:
    """Get list of stock codes that have adjustment factor data."""
    return container.adjustfactor_service().get_available_codes()


# --- File Management Functions ---


def add_file(name: str, file_type, data: bytes, description: str = None) -> dict:
    """Add a new file to the database."""
    return container.file_service().add_file(name, file_type, data, description)


def copy_file(clone_id: str, new_name: str, file_type=None) -> dict:
    """Create a copy of an existing file."""
    return container.file_service().copy_file(clone_id, new_name, file_type)


def update_file(file_id: str, name: str = None, data: bytes = None, description: str = None) -> bool:
    """Update an existing file."""
    return container.file_service().update_file(file_id, name, data, description)


def delete_file(file_id: str) -> bool:
    """Delete a file by ID."""
    return container.file_service().delete_file(file_id)




def get_file_content(file_id: str) -> bytes:
    """Get the content of a specific file."""
    return container.file_service().get_file_content(file_id)


# --- Engine Management Functions ---


def add_engine(name: str, is_live: bool = False, description: str = None) -> dict:
    """Create a new backtest engine."""
    return container.engine_service().create_engine(name, is_live, description)


def get_engine(engine_id: str, as_dataframe: bool = False):
    """Get a single engine by ID."""
    return container.engine_service().get_engine(engine_id, as_dataframe)


def get_engines(name: str = None, is_live: bool = None, as_dataframe: bool = True, **kwargs):
    """Get engines with optional filters."""
    return container.engine_service().get_engines(name, is_live, as_dataframe=as_dataframe, **kwargs)


def delete_engine(engine_id: str) -> bool:
    """Delete an engine by ID."""
    return container.engine_service().delete_engine(engine_id)


def delete_engines(engine_ids: list) -> int:
    """Delete multiple engines."""
    return container.engine_service().delete_engines(engine_ids)


def add_engine_portfolio_mapping(
    engine_id: str, portfolio_id: str, engine_name: str = None, portfolio_name: str = None
) -> dict:
    """Associate a portfolio with an engine."""
    return container.engine_service().add_portfolio_to_engine(engine_id, portfolio_id, engine_name, portfolio_name)


def get_engine_portfolio_mappings(engine_id: str = None, portfolio_id: str = None, as_dataframe: bool = True, **kwargs):
    """Get engine-portfolio mappings."""
    return container.engine_service().get_engine_portfolio_mappings(engine_id, portfolio_id, as_dataframe, **kwargs)


# --- Portfolio Management Functions ---


def add_portfolio(
    name: str, backtest_start_date: str, backtest_end_date: str, is_live: bool = False, description: str = None
) -> dict:
    """Create a new investment portfolio."""
    return container.portfolio_service().create_portfolio(
        name, backtest_start_date, backtest_end_date, is_live, description
    )


def get_portfolio(portfolio_id: str, as_dataframe: bool = False):
    """Get a single portfolio by ID."""
    return container.portfolio_service().get_portfolio(portfolio_id, as_dataframe)


def get_portfolios(name: str = None, is_live: bool = None, as_dataframe: bool = True, **kwargs):
    """Get portfolios with optional filters."""
    return container.portfolio_service().get_portfolios(name, is_live, as_dataframe, **kwargs)


def delete_portfolio(portfolio_id: str) -> bool:
    """Delete a portfolio by ID."""
    return container.portfolio_service().delete_portfolio(portfolio_id)


def delete_portfolios(portfolio_ids: list) -> int:
    """Delete multiple portfolios."""
    return container.portfolio_service().delete_portfolios(portfolio_ids)


def add_portfolio_file_mapping(portfolio_id: str, file_id: str, name: str, file_type) -> dict:
    """Associate a file with a portfolio."""
    return container.portfolio_service().add_file_to_portfolio(portfolio_id, file_id, name, file_type)


def delete_portfolio_file_mapping(mapping_id: str) -> bool:
    """Remove a file association from a portfolio."""
    return container.portfolio_service().remove_file_from_portfolio(mapping_id)


def get_portfolio_file_mappings(portfolio_id: str = None, file_type=None, as_dataframe: bool = True, **kwargs):
    """Get portfolio-file mappings."""
    return container.portfolio_service().get_portfolio_file_mappings(portfolio_id, file_type, as_dataframe, **kwargs)


def add_param(mapping_id: str, order: int, value: str) -> dict:
    """Add a parameter to a portfolio-file mapping."""
    return container.portfolio_service().add_parameter(mapping_id, order, value)


def get_params(mapping_id: str, as_dataframe: bool = True):
    """Get parameters for a portfolio-file mapping."""
    return container.portfolio_service().get_parameters_for_mapping(mapping_id, as_dataframe)


# --- Component Instantiation Functions ---


def get_instance_by_file(file_id: str, mapping_id: str, file_type):
    """Create an instance of a trading component from file content."""
    return container.component_service().get_instance_by_file(file_id, mapping_id, file_type)


def get_trading_system_components_by_portfolio(portfolio_id: str, file_type):
    """Get all instantiated components of a specific type for a portfolio."""
    return container.component_service().get_trading_system_components_by_portfolio(portfolio_id, file_type)


def get_analyzers_by_portfolio(portfolio_id: str):
    """Get all analyzer instances for a portfolio."""
    return container.component_service().get_analyzers_by_portfolio(portfolio_id)


# --- Dynamic Export of all functions ---
__all__ = [
    name for name, obj in globals().items()
    if callable(obj) and not name.startswith('_') and hasattr(obj, '__module__') and obj.__module__ == __name__
]
