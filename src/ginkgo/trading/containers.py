# Upstream: client/deploy_cli, api/deployment, api/saga_transaction, tests
# Downstream: DeploymentService (trading/services), data/containers (依赖获取)
# Role: trading 层依赖注入容器，管理交易相关服务的实例化

from dependency_injector import containers, providers


class TradingContainer(containers.DeclarativeContainer):
    deployment_service = providers.Singleton(object)


trading_container = TradingContainer()

_deployment_service_instance = None


def _get_deployment_service():
    """Lazy factory for DeploymentService."""
    global _deployment_service_instance
    if _deployment_service_instance is None:
        from ginkgo.data.containers import container
        from ginkgo.trading.services.deployment_service import DeploymentService

        _deployment_service_instance = DeploymentService(
            portfolio_service=container.portfolio_service(),
            mapping_service=container.portfolio_mapping_service(),
            file_service=container.file_service(),
            deployment_crud=container.deployment_crud(),
            broker_instance_crud=container.broker_instance_crud(),
            live_account_service=container.live_account_service(),
            mongo_driver=container.mongo_driver(),
            param_crud=container.cruds.param(),
        )
    return _deployment_service_instance


trading_container.deployment_service.override(
    providers.Singleton(_get_deployment_service)
)
