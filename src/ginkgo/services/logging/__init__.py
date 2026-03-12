"""
Logging Service Module

This module provides centralized logging services for the Ginkgo trading system.
It includes:
- LogService: Unified log query service using ClickHouse backend
- LevelService: Dynamic log level management service
- Legacy Loki client (deprecated, kept for backward compatibility)

The logging system supports three log tables:
- ginkgo_logs_backtest: Backtest business logs
- ginkgo_logs_component: Component runtime logs
- ginkgo_logs_performance: Performance monitoring logs

Example:
    from ginkgo.services.logging import LogService, LevelService

    # Query backtest logs
    service = LogService()
    logs = service.query_backtest_logs(
        portfolio_id="portfolio-001",
        level="ERROR",
        limit=50
    )

    # Dynamic log level management
    level_service = LevelService()
    level_service.set_level("backtest", "DEBUG")
"""

from ginkgo.services.logging.log_service import LogService
from ginkgo.services.logging.level_service import LevelService

# Legacy Loki support (deprecated - will be removed in future version)
try:
    from ginkgo.services.logging.clients.loki_client import LokiClient
    _legacy_loki_available = True
except ImportError:
    _legacy_loki_available = False

__all__ = ["LogService", "LevelService"]

# Provide Loki client for backward compatibility
if _legacy_loki_available:
    __all__.append("LokiClient")
