"""
Execution Module Dependency Injection Container

This module provides dependency injection for execution-related services,
including signal confirmation handlers and portfolio management services.
"""

from dependency_injector import containers, providers

from .confirmation.confirmation_handler import ConfirmationHandler
from ..services.portfolio_management_service import PortfolioManagementService


class ExecutionContainer(containers.DeclarativeContainer):
    """
    执行模块的依赖注入容器
    
    管理执行相关的服务实例，包括确认处理器和组合管理服务
    """
    
    # 确认处理器 - 无需依赖
    confirmation_handler = providers.Singleton(ConfirmationHandler)
    
    # 组合管理服务 - 无需依赖（通过延迟加载获取依赖）
    portfolio_management_service = providers.Singleton(PortfolioManagementService)


# 单例容器实例
execution_container = ExecutionContainer()


def get_execution_service_info():
    """获取执行模块服务信息"""
    
    # 获取可用服务
    services_list = []
    for attr_name in dir(execution_container):
        if (attr_name.endswith("_service") or attr_name.endswith("_handler")) and not attr_name.startswith("_"):
            services_list.append(attr_name)
    
    return {
        "services": services_list,
        "module": "execution",
        "description": "Signal execution and portfolio management services"
    }


# 绑定服务信息方法到容器实例
execution_container.get_service_info = get_execution_service_info