# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 组件工厂服务提供创建/获取/列出等方法封装策略/风控/选股器/仓位管理等组件的创建逻辑和数据访问支持交易系统功能和组件集成提供完整业务支持






"""
Component Factory Service

This service handles the creation and management of trading system components
such as strategies, analyzers, selectors, sizers, and risk managers.
It provides a unified interface for component instantiation and lifecycle management.
"""

from typing import List, Any, Optional, Dict, Type
import inspect
from abc import ABC, abstractmethod

from ginkgo.libs import GLOG
from ginkgo.enums import FILE_TYPES
from ginkgo.data.containers import container


class ComponentFactoryService:
    """
    Service for creating and managing trading system components.

    This service provides methods to instantiate various types of trading
    components dynamically based on their configuration and file content.
    """

    def __init__(self):
        """Initialize the component factory service."""
        self._logger = GLOG
        self._component_service = None  # Will be lazily initialized
        self._base_class_mapping = {}

    def initialize(self) -> bool:
        """Initialize the component factory service."""
        try:
            # Get component service from data container
            self._component_service = container.component_service()

            # Initialize base class mapping
            self._initialize_base_class_mapping()

            self._logger.INFO("ComponentFactoryService initialized")
            return True

        except Exception as e:
            self._logger.ERROR(f"Failed to initialize ComponentFactoryService: {e}")
            return False

    def _initialize_base_class_mapping(self):
        """Initialize the mapping of file types to their base classes."""
        try:
            from ginkgo.trading.strategies import BaseStrategy as BaseStrategy
            from ginkgo.trading.analysis.analyzers import BaseAnalyzer
            from ginkgo.trading.selectors import BaseSelector
            from ginkgo.trading.sizers import BaseSizer
            from ginkgo.trading.risk_managementss import BaseRiskManagement as BaseRisk

            self._base_class_mapping = {
                FILE_TYPES.STRATEGY: BaseStrategy,
                FILE_TYPES.ANALYZER: BaseAnalyzer,
                FILE_TYPES.SELECTOR: BaseSelector,
                FILE_TYPES.SIZER: BaseSizer,
                FILE_TYPES.RISKMANAGER: BaseRisk,
            }

        except ImportError as e:
            self._logger.ERROR(f"Failed to import base classes: {e}")
            raise

    def create_component(self, file_id: str, mapping_id: str, file_type: FILE_TYPES) -> Optional[Any]:
        """
        Create a component instance from file configuration.

        Args:
            file_id: UUID of the file containing component code
            mapping_id: UUID of the portfolio-file mapping
            file_type: Type of component to create

        Returns:
            Instantiated component or None if creation failed
        """
        try:
            if self._component_service is None:
                self._logger.ERROR("ComponentFactoryService not initialized")
                return None

            # Delegate to the data container's component service
            component = self._component_service.get_instance_by_file(
                file_id=file_id, mapping_id=mapping_id, file_type=file_type
            )

            if component is None:
                self._logger.ERROR(f"Failed to create component {file_type.value} from file {file_id}")
                return None

            self._logger.DEBUG(f"Created {file_type.value} component: {component.__class__.__name__}")
            return component

        except Exception as e:
            self._logger.ERROR(f"Error creating component: {e}")
            return None

    def create_components_by_portfolio(self, portfolio_id: str, file_type: FILE_TYPES) -> List[Any]:
        """
        Create all components of a specific type for a portfolio.

        Args:
            portfolio_id: UUID of the portfolio
            file_type: Type of components to create

        Returns:
            List of instantiated components
        """
        try:
            if self._component_service is None:
                self._logger.ERROR("ComponentFactoryService not initialized")
                return []

            # Delegate to the data container's component service
            components = self._component_service.get_trading_system_components_by_portfolio(
                portfolio_id=portfolio_id, file_type=file_type
            )

            self._logger.DEBUG(f"Created {len(components)} {file_type.value} components for portfolio {portfolio_id}")
            return components

        except Exception as e:
            self._logger.ERROR(f"Error creating components by portfolio: {e}")
            return []

    def validate_component_code(self, code: str, file_type: FILE_TYPES) -> Dict[str, Any]:
        """
        Validate component code without instantiating it.

        Args:
            code: Component source code
            file_type: Expected component type

        Returns:
            Validation result with status and details
        """
        try:
            if self._component_service is None:
                self._logger.ERROR("ComponentFactoryService not initialized")
                return {"success": False, "error": "Service not initialized"}

            # Delegate to the data container's component service
            result = self._component_service.validate_component_code(code, file_type)
            return result

        except Exception as e:
            self._logger.ERROR(f"Error validating component code: {e}")
            return {"success": False, "error": str(e)}

    def get_component_requirements(self, file_type: FILE_TYPES) -> Dict[str, Any]:
        """
        Get requirements and constraints for a component type.

        Args:
            file_type: Type of component

        Returns:
            Dictionary with requirements information
        """
        try:
            base_class = self._base_class_mapping.get(file_type)
            if base_class is None:
                return {"error": f"Unsupported component type: {file_type}"}

            # Analyze base class to extract requirements
            signature = inspect.signature(base_class.__init__)
            methods = [method for method in dir(base_class) if not method.startswith("_")]
            abstract_methods = getattr(base_class, "__abstractmethods__", set())

            return {
                "base_class": base_class.__name__,
                "required_methods": list(abstract_methods),
                "available_methods": methods,
                "init_signature": str(signature),
                "module": base_class.__module__,
            }

        except Exception as e:
            self._logger.ERROR(f"Error getting component requirements: {e}")
            return {"error": str(e)}

    def create_strategies_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Create all strategy components for a portfolio."""
        return self.create_components_by_portfolio(portfolio_id, FILE_TYPES.STRATEGY)

    def create_analyzers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Create all analyzer components for a portfolio."""
        return self.create_components_by_portfolio(portfolio_id, FILE_TYPES.ANALYZER)

    def create_selectors_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Create all selector components for a portfolio."""
        return self.create_components_by_portfolio(portfolio_id, FILE_TYPES.SELECTOR)

    def create_sizers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Create all sizer components for a portfolio."""
        return self.create_components_by_portfolio(portfolio_id, FILE_TYPES.SIZER)

    def create_risk_managers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Create all risk manager components for a portfolio."""
        return self.create_components_by_portfolio(portfolio_id, FILE_TYPES.RISKMANAGER)

    def get_supported_component_types(self) -> List[str]:
        """Get list of supported component types."""
        return [file_type.value for file_type in self._base_class_mapping.keys()]
