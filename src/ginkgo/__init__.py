# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Ginkgo主模块公共接口，提供统一的services服务访问入口和service_hub服务枢纽，导出核心服务容器和依赖注入管理器






"""
Ginkgo ServiceHub - 统一服务访问协调器

ServiceHub作为服务访问器的协调中心，明确分离服务访问器与业务服务的边界。
提供懒加载、错误处理、诊断功能和向后兼容性。

Usage:
    from ginkgo import service_hub

    # Data services - 完善的数据访问层
    bar_crud = service_hub.data.cruds.bar()
    bar_service = service_hub.data.services.bar_service()
    stockinfo_service = service_hub.data.services.stockinfo_service()
    tick_service = service_hub.data.services.tick_service()

    # Trading services - 交易引擎和组件
    engine = service_hub.trading.engines.time_controlled()
    portfolio = service_hub.trading.base_portfolio()

    # Core services - 核心基础服务
    config_service = service_hub.core.services.config()
    logger_service = service_hub.core.services.logger()
    thread_service = service_hub.core.services.thread()

    # Features services - 因子工程服务
    feature_container = service_hub.features

    # ML services - 机器学习服务 (如可用)
    ml_container = service_hub.ml

Backward Compatibility:
    为了向后兼容，services仍然可用，但建议使用service_hub:
    from ginkgo import services  # 仍然支持，但建议迁移到service_hub
"""

# Import ServiceHub - 主要的统一访问协调器
from ginkgo.service_hub import service_hub, services

# Export main interfaces - 推荐使用service_hub，保留services为向后兼容
__all__ = ['service_hub', 'services']