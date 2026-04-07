# Upstream: services/logging (模块初始化)
# Downstream: LogService, LevelService, AlertService
# Role: 日志服务依赖注入容器，提供日志查询/级别管理/告警服务

"""
Logging Service Container

Dependency injection container for logging services.
Provides LogService instances with ClickHouse backend, LevelService for dynamic log level management,
and AlertService for log monitoring and alerting.
"""

from dependency_injector import containers, providers
from ginkgo.services.logging.log_service import LogService
from ginkgo.services.logging.level_service import LevelService
from ginkgo.services.logging.alert_service import AlertService
from ginkgo.data.drivers import get_db_connection
from ginkgo.data.models.model_logs import MBacktestLog
from ginkgo.data.services.redis_service import RedisService
from ginkgo.libs import GLOG


def _get_redis_client():
    """获取 Redis 客户端（用于 AlertService）"""
    try:
        rs = RedisService()
        return rs.get_client()
    except Exception:
        return None


class LoggingContainer(containers.DeclarativeContainer):
    """
    Logging 服务依赖注入容器

    提供 LogService、LevelService 和 AlertService 实例的依赖注入支持。
    """

    # ClickHouse 引擎（共享实例）
    clickhouse_engine = providers.Singleton(
        lambda: get_db_connection(MBacktestLog)
    )

    # 日志查询服务
    log_service = providers.Factory(
        LogService,
        engine=clickhouse_engine
    )

    # 动态日志级别管理服务
    level_service = providers.Singleton(
        LevelService,
        glog=providers.Singleton(lambda: GLOG)
    )

    # 日志告警服务
    alert_service = providers.Singleton(
        AlertService,
        redis_client=providers.Singleton(lambda: _get_redis_client()),
        db_engine=clickhouse_engine
    )


# 创建全局容器实例
container = LoggingContainer()
