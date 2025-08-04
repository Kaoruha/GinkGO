"""
Component Service (Class-based)

This service handles the business logic for dynamically instantiating
trading system components (strategies, analyzers, selectors, sizers, risk managers)
from file content and parameters.
"""

from typing import List, Any, Optional, Type
import inspect

from ...enums import FILE_TYPES
from .base_service import BusinessService


class ComponentService(BusinessService):
    def __init__(self, file_service, portfolio_service):
        """Initializes the service with its dependencies."""
        super().__init__(file_service=file_service, portfolio_service=portfolio_service)

    def get_instance_by_file(self, file_id: str, mapping_id: str, file_type: FILE_TYPES) -> Any:
        """
        Creates an instance of a trading component from file content and parameters.

        Args:
            file_id: UUID of the file containing the component code
            mapping_id: UUID of the portfolio-file mapping
            file_type: Type of component to instantiate

        Returns:
            Instantiated component object or None if failed
        """
        try:
            # Get the component class mapping
            cls_base_mapping = self._get_component_base_classes()

            if file_type not in cls_base_mapping:
                self._logger.ERROR(f"Unsupported file type: {file_type}")
                return None

            base_class = cls_base_mapping[file_type]

            # Get file content
            content = self.file_service.get_file_content(file_id)
            if not content:
                self._logger.ERROR(f"Empty or missing file content for file {file_id}")
                return None

            # Execute code in isolated namespace
            namespace = {}
            try:
                exec(content.decode("utf-8"), namespace)
            except Exception as e:
                self._logger.ERROR(f"Failed to execute code from file {file_id}: {e}")
                return None

            # Find the component class
            component_class = self._find_component_class(namespace, base_class)
            if component_class is None:
                self._logger.ERROR(f"No valid {base_class.__name__} subclass found in file {file_id}")
                return None

            # Get parameters for instantiation
            parameters = self._get_instantiation_parameters(mapping_id)

            # Instantiate the component
            try:
                instance = component_class(*parameters)

                # Special handling for analyzers
                if file_type == FILE_TYPES.ANALYZER:
                    if hasattr(instance, "set_analyzer_id"):
                        instance.set_analyzer_id(file_id)

                self._logger.DEBUG(f"Successfully instantiated {component_class.__name__} from file {file_id}")
                return instance

            except Exception as e:
                self._logger.ERROR(f"Failed to instantiate {component_class.__name__} from file {file_id}: {e}")
                return None

        except Exception as e:
            self._logger.ERROR(f"Unexpected error creating instance from file {file_id}: {e}")
            return None

    def get_trading_system_components_by_portfolio(self, portfolio_id: str, file_type: FILE_TYPES) -> List[Any]:
        """
        Gets all instantiated components of a specific type for a portfolio.

        Args:
            portfolio_id: UUID of the portfolio
            file_type: Type of components to retrieve

        Returns:
            List of instantiated component objects
        """
        if not isinstance(file_type, FILE_TYPES):
            self._logger.ERROR(f"Invalid file type: {file_type}")
            return []

        # Get all file mappings for the portfolio and type
        mappings = self.portfolio_service.get_portfolio_file_mappings(
            portfolio_id=portfolio_id, file_type=file_type, as_dataframe=True
        )

        components = []
        for _, mapping in mappings.iterrows():
            file_id = mapping["file_id"]
            mapping_id = mapping["uuid"]

            instance = self.get_instance_by_file(file_id, mapping_id, file_type)
            if instance is not None:
                components.append(instance)
            else:
                self._logger.WARN(f"Failed to instantiate component from mapping {mapping_id}")

        self._logger.INFO(f"Retrieved {len(components)} {file_type.value} components for portfolio {portfolio_id}")
        return components

    def get_strategies_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Gets all strategy instances for a portfolio."""
        return self.get_trading_system_components_by_portfolio(portfolio_id, FILE_TYPES.STRATEGY)

    def get_analyzers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Gets all analyzer instances for a portfolio."""
        return self.get_trading_system_components_by_portfolio(portfolio_id, FILE_TYPES.ANALYZER)

    def get_selectors_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Gets all selector instances for a portfolio."""
        return self.get_trading_system_components_by_portfolio(portfolio_id, FILE_TYPES.SELECTOR)

    def get_sizers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Gets all sizer instances for a portfolio."""
        return self.get_trading_system_components_by_portfolio(portfolio_id, FILE_TYPES.SIZER)

    def get_risk_managers_by_portfolio(self, portfolio_id: str) -> List[Any]:
        """Gets all risk manager instances for a portfolio."""
        return self.get_trading_system_components_by_portfolio(portfolio_id, FILE_TYPES.RISKMANAGER)

    def validate_component_code(self, code: str, file_type: FILE_TYPES) -> dict:
        """
        Validates component code without instantiating it.

        Args:
            code: Python code as string
            file_type: Expected component type

        Returns:
            Dictionary with validation results
        """
        result = {"valid": False, "error": None, "class_name": None, "base_class": None}

        try:
            # Get expected base class
            cls_base_mapping = self._get_component_base_classes()
            if file_type not in cls_base_mapping:
                result["error"] = f"Unsupported file type: {file_type}"
                return result

            base_class = cls_base_mapping[file_type]
            result["base_class"] = base_class.__name__

            # Try to execute the code
            namespace = {}
            try:
                exec(code, namespace)
            except Exception as e:
                result["error"] = f"Code execution failed: {e}"
                return result

            # Find component class
            component_class = self._find_component_class(namespace, base_class)
            if component_class is None:
                result["error"] = f"No valid {base_class.__name__} subclass found"
                return result

            result["valid"] = True
            result["class_name"] = component_class.__name__

        except Exception as e:
            result["error"] = f"Validation error: {e}"

        return result

    def _get_component_base_classes(self) -> dict:
        """
        Gets the mapping of file types to their base classes.

        Returns:
            Dictionary mapping FILE_TYPES to base classes
        """
        try:
            from ...backtest.strategy.strategies.base_strategy import StrategyBase
            from ...backtest.analysis.analyzers.base_analyzer import BaseAnalyzer
            from ...backtest.strategy.sizers.base_sizer import BaseSizer
            from ...backtest.strategy.selectors.base_selector import BaseSelector
            from ...backtest.strategy.risk_managements.base_risk import BaseRiskManagement

            return {
                FILE_TYPES.STRATEGY: StrategyBase,
                FILE_TYPES.ANALYZER: BaseAnalyzer,
                FILE_TYPES.SIZER: BaseSizer,
                FILE_TYPES.SELECTOR: BaseSelector,
                FILE_TYPES.RISKMANAGER: BaseRiskManagement,
            }
        except ImportError as e:
            self._logger.ERROR(f"Failed to import component base classes: {e}")
            return {}

    def _find_component_class(self, namespace: dict, base_class: Type) -> Optional[Type]:
        """
        Finds a component class in the namespace that inherits from base_class.

        Args:
            namespace: Execution namespace containing classes
            base_class: Expected base class

        Returns:
            Component class or None if not found
        """
        for name, obj in namespace.items():
            if (
                isinstance(obj, type) and issubclass(obj, base_class) and obj != base_class
            ):  # Don't return the base class itself
                return obj
        return None

    def _get_instantiation_parameters(self, mapping_id: str) -> List[str]:
        """
        Gets parameters for component instantiation from the database.

        Args:
            mapping_id: UUID of the portfolio-file mapping

        Returns:
            List of parameter values in order
        """
        try:
            params_df = self.portfolio_service.get_parameters_for_mapping(mapping_id, as_dataframe=True)

            if params_df.empty:
                return []

            # Sort by order and return values
            params_df = params_df.sort_values("index")
            return params_df["value"].tolist()

        except Exception as e:
            self._logger.ERROR(f"Failed to get parameters for mapping {mapping_id}: {e}")
            return []

    def get_component_info(self, file_id: str, file_type: FILE_TYPES) -> dict:
        """
        Gets information about a component without instantiating it.

        Args:
            file_id: UUID of the file
            file_type: Type of component

        Returns:
            Dictionary with component information
        """
        result = {
            "success": False,
            "file_id": file_id,
            "file_type": file_type.name if hasattr(file_type, "name") else str(file_type),
            "error": None,
            "warnings": [],
            "class_name": None,
            "methods": [],
            "init_params": [],
            "init_signature": None,
            "valid": False,
            "file_size_bytes": 0,
            "code_lines": 0,
            "base_class": None,
            "docstring": None,
        }

        # Input validation
        if not file_id or not file_id.strip():
            result["error"] = "File ID cannot be empty"
            return result

        try:
            content = self.file_service.get_file_content(file_id)
            if not content:
                result["error"] = "No file content found"
                return result

            result["file_size_bytes"] = len(content)

        except Exception as e:
            result["error"] = f"Failed to retrieve file content: {str(e)}"
            return result

        try:
            code_str = content.decode("utf-8")
            result["code_lines"] = len(code_str.splitlines())
        except UnicodeDecodeError as e:
            result["error"] = f"Failed to decode file content: {str(e)}"
            return result

        try:

            # Validate the code
            validation = self.validate_component_code(code_str, file_type)
            result["valid"] = validation["valid"]
            result["error"] = validation["error"]
            result["class_name"] = validation["class_name"]
            result["base_class"] = validation["base_class"]

            # Propagate validation warnings
            if validation["warnings"]:
                result["warnings"].extend(validation["warnings"])

            if validation["valid"]:
                # Get more detailed information
                try:
                    namespace = {}
                    exec(code_str, namespace)

                    cls_base_mapping = self._get_component_base_classes()
                    base_class = cls_base_mapping[file_type]
                    component_class = self._find_component_class(namespace, base_class)

                    if component_class:
                        # Get method names
                        try:
                            methods = [
                                name
                                for name, method in inspect.getmembers(component_class, predicate=inspect.isfunction)
                            ]
                            result["methods"] = [m for m in methods if not m.startswith("_")]
                        except Exception as e:
                            result["warnings"].append(f"Failed to analyze methods: {str(e)}")

                        # Get init parameters
                        try:
                            init_signature = inspect.signature(component_class.__init__)
                            result["init_params"] = [
                                param.name for param in init_signature.parameters.values() if param.name != "self"
                            ]
                            result["init_signature"] = str(init_signature)
                        except Exception as e:
                            result["warnings"].append(f"Failed to analyze init signature: {str(e)}")

                        # Get class docstring
                        try:
                            if component_class.__doc__:
                                result["docstring"] = component_class.__doc__.strip()
                        except Exception as e:
                            result["warnings"].append(f"Failed to get docstring: {str(e)}")

                        result["success"] = True

                    else:
                        result["error"] = "Component class not found after validation passed"

                except Exception as e:
                    result["error"] = f"Failed to analyze component details: {str(e)}"

        except Exception as e:
            result["error"] = f"Analysis error: {str(e)}"
            self._logger.ERROR(f"Component info analysis error for file {file_id}: {e}")

        return result
