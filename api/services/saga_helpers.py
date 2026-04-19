"""
Saga 辅助工具模块

提供 Saga 事务管理器的辅助工具函数，解决闭包问题。
"""
from typing import Callable, Dict, Any, Optional
from functools import partial


class SagaStepBuilder:
    """Saga 步骤构建器

    解决在循环中创建 Saga 步骤时的闭包变量绑定问题。
    使用工厂模式延迟绑定变量值，确保每个步骤使用正确的变量。

    Example:
        builder = SagaStepBuilder(mapping_service, portfolio_uuid_getter)

        # 为每个组件创建步骤
        for component in components:
            step = builder.create_component_step(
                component_type="selector",
                file_type=FILE_TYPES.SELECTOR,
                component_uuid=component['uuid'],
                config=component.get('config', {})
            )
            saga.add_step(**step)
    """

    def __init__(
        self,
        mapping_service: Any,
        portfolio_uuid_getter: Callable[[], str]
    ):
        """初始化构建器

        Args:
            mapping_service: PortfolioMappingService 实例
            portfolio_uuid_getter: 获取 portfolio_uuid 的函数
        """
        self.mapping_service = mapping_service
        self.portfolio_uuid_getter = portfolio_uuid_getter

    def create_component_step(
        self,
        component_type: str,
        file_type: Any,
        component_uuid: str,
        config: Dict[str, Any]
    ) -> Dict[str, Callable]:
        """创建组件步骤

        Args:
            component_type: 组件类型名称（用于日志）
            file_type: FILE_TYPES 枚举值
            component_uuid: 组件 UUID
            config: 组件配置参数

        Returns:
            包含 execute 和 compensate 函数的字典
        """

        def execute():
            portfolio_uuid = self.portfolio_uuid_getter()
            if not portfolio_uuid:
                raise Exception("Portfolio UUID not available")

            self.mapping_service.add_file(
                portfolio_uuid=portfolio_uuid,
                file_id=component_uuid,
                file_type=file_type,
                params=config
            )
            return {'portfolio_uuid': portfolio_uuid, 'file_id': component_uuid}

        def compensate(result):
            try:
                portfolio_uuid = self.portfolio_uuid_getter()
                if portfolio_uuid:
                    self.mapping_service.remove_file(
                        portfolio_uuid=portfolio_uuid,
                        file_id=component_uuid
                    )
            except Exception as e:
                # 记录错误但不抛出异常，允许其他补偿继续
                from core.logging import logger
                logger.error(f"Failed to compensate {component_type} {component_uuid}: {e}")

        return {
            'name': f"add_{component_type}_{component_uuid[:8]}",
            'execute': execute,
            'compensate': compensate
        }


def create_portfolio_uuid_getter(saga_transaction, step_index: int) -> Callable[[], str]:
    """创建获取 portfolio_uuid 的函数

    从已执行的步骤中提取 portfolio_uuid。

    Args:
        saga_transaction: SagaTransaction 实例
        step_index: 包含 portfolio_uuid 的步骤索引

    Returns:
        返回 portfolio_uuid 的函数
    """

    def getter() -> Optional[str]:
        if step_index < len(saga_transaction.completed_steps):
            result = saga_transaction.completed_steps[step_index].result
            if hasattr(result, 'uuid'):
                return result.uuid
            elif isinstance(result, dict):
                return result.get('uuid')
        return None

    return getter


def create_context_getter(context_dict: Dict[str, Any], key: str) -> Callable[[], Any]:
    """创建从上下文字典获取值的函数

    Args:
        context_dict: 上下文字典
        key: 要获取的键

    Returns:
        返回上下文值的函数
    """

    def getter() -> Any:
        return context_dict.get(key)

    return getter


def create_context_setter(context_dict: Dict[str, Any], key: str) -> Callable[[Any], None]:
    """创建设置上下文字典值的函数

    Args:
        context_dict: 上下文字典
        key: 要设置的键

    Returns:
        设置上下文值的函数
    """

    def setter(value: Any) -> None:
        context_dict[key] = value

    return setter
