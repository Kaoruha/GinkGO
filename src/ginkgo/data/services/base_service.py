"""
Base Service Classes

This module provides abstract base classes for all data services,
establishing common patterns for initialization, error handling, caching, and logging.

Architecture:
    BaseService (Abstract base class)
    ├── DataService (Data synchronization services)
    ├── ManagementService (Entity management services)
    └── BusinessService (Business logic services)
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from datetime import datetime
import inspect

from ginkgo.libs import GLOG, cache_with_expiration, retry


class ServiceResult:
    """Standardized service operation result structure."""

    def __init__(self, success: bool = False, error: str = None, data: Any = None, message: str = None):
        self.success = success
        self.error = error
        self.message = message
        self.warnings = []
        self.data = data if data is not None else {}
        self.metadata = {}

    def add_warning(self, message: str):
        """Add a warning message."""
        self.warnings.append(message)

    def set_data(self, key: str, value: Any):
        """Set result data."""
        self.data[key] = value

    def set_metadata(self, key: str, value: Any):
        """Set result metadata."""
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result = {
            "success": self.success,
            "error": self.error,
        }

        # Only include non-empty collections
        if self.warnings:
            result["warnings"] = self.warnings
        if self.data:
            result.update(self.data)
        if self.metadata:
            result["metadata"] = self.metadata

        return result
    
    @classmethod
    def success(cls, data: Any = None, message: str = None) -> 'ServiceResult':
        """
        创建成功的服务结果
        
        Args:
            data: 返回的数据
            message: 成功消息
            
        Returns:
            ServiceResult: 成功的结果对象
        """
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error(cls, error: str, data: Any = None) -> 'ServiceResult':
        """
        创建失败的服务结果
        
        Args:
            error: 错误消息
            data: 可选的错误相关数据
            
        Returns:
            ServiceResult: 失败的结果对象
        """
        return cls(success=False, error=error, data=data)
    
    @classmethod
    def failure(cls, message: str, data: Any = None) -> 'ServiceResult':
        """
        创建失败的服务结果（别名方法）
        
        Args:
            message: 失败消息
            data: 可选的失败相关数据
            
        Returns:
            ServiceResult: 失败的结果对象
        """
        return cls(success=False, error=message, data=data)
    
    def is_success(self) -> bool:
        """
        检查操作是否成功
        
        Returns:
            bool: 是否成功
        """
        return self.success
    
    def is_failure(self) -> bool:
        """
        检查操作是否失败
        
        Returns:
            bool: 是否失败
        """
        return not self.success
    
    def __str__(self) -> str:
        """
        字符串表示
        
        Returns:
            str: 结果的字符串表示
        """
        if self.success:
            data_str = f", data={self.data}" if self.data else ""
            return f"ServiceResult(success=True{data_str})"
        else:
            error_str = f", error={self.error}" if self.error else ""
            return f"ServiceResult(success=False{error_str})"


class BaseService(ABC):
    """
    Abstract base class for all data services.

    Provides common functionality:
    - Standardized initialization and logging
    - Error handling and result formatting
    - Health check capabilities
    - Performance monitoring hooks
    """

    def __init__(self, **dependencies):
        """
        Initialize service with dependency injection.

        Args:
            **dependencies: Injected dependencies (crud_repo, data_source, etc.)
        """
        # Store dependencies
        self._dependencies = dependencies

        # Set up logging
        self._service_name = self.__class__.__name__
        self._logger = GLOG

        # Initialize service-specific attributes
        self._initialize_dependencies()

        # Log successful initialization
        self._logger.DEBUG(f"{self._service_name} Initialized.")

        # Track initialization time for health checks
        self._initialized_at = datetime.now()

    def _initialize_dependencies(self):
        """
        Initialize dependencies as instance attributes.
        Override in subclasses for custom dependency handling.
        """
        for name, dependency in self._dependencies.items():
            setattr(self, name, dependency)

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

    @property
    def initialized_at(self) -> datetime:
        """Get initialization timestamp."""
        return self._initialized_at

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get service health status.

        Returns:
            Dictionary containing health information
        """
        return {
            "service_name": self._service_name,
            "status": "healthy",
            "initialized_at": self._initialized_at.isoformat(),
            "uptime_seconds": (datetime.now() - self._initialized_at).total_seconds(),
            "dependencies": list(self._dependencies.keys()),
        }

    def create_result(self, success: bool = False, error: str = None) -> ServiceResult:
        """
        Create a standardized service result.

        Args:
            success: Operation success status
            error: Error message if any

        Returns:
            ServiceResult instance
        """
        return ServiceResult(success=success, error=error)

    def _log_operation_start(self, operation: str, **params):
        """Log the start of an operation."""
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v is not None)
        self._logger.DEBUG(f"{self._service_name}.{operation} started with params: {param_str}")

    def _log_operation_end(self, operation: str, success: bool, duration: float = None):
        """Log the end of an operation."""
        status = "completed" if success else "failed"
        duration_str = f" in {duration:.3f}s" if duration else ""
        self._logger.DEBUG(f"{self._service_name}.{operation} {status}{duration_str}")

    def _validate_required_params(self, **params) -> Optional[str]:
        """
        Validate required parameters.

        Returns:
            Error message if validation fails, None otherwise
        """
        for name, value in params.items():
            if value is None or (isinstance(value, str) and not value.strip()):
                return f"Parameter '{name}' is required and cannot be empty"
        return None


class DataService(BaseService):
    """
    Base class for data synchronization services.

    Common pattern for services that sync data from external sources
    (BarService, TickService, AdjustfactorService, StockinfoService).
    """

    def __init__(self, crud_repo, data_source, **additional_deps):
        """
        Initialize data service.

        Args:
            crud_repo: CRUD repository for database operations
            data_source: External data source for fetching data
            **additional_deps: Additional service dependencies
        """
        super().__init__(crud_repo=crud_repo, data_source=data_source, **additional_deps)

    @retry(max_try=3)
    def _fetch_from_source(self, fetch_method: str, **params) -> Any:
        """
        Generic method to fetch data from external source with retry.

        Args:
            fetch_method: Method name to call on data_source
            **params: Parameters to pass to the fetch method

        Returns:
            Fetched data
        """
        try:
            method = getattr(self.data_source, fetch_method)
            return method(**params)
        except AttributeError:
            raise ValueError(f"Data source does not support method: {fetch_method}")

    def _save_to_database(self, data: Union[Any, List[Any]], batch: bool = True) -> ServiceResult:
        """
        Generic method to save data to database.

        Args:
            data: Data to save (single item or list)
            batch: Whether to use batch insert

        Returns:
            ServiceResult with operation status
        """
        result = self.create_result()

        try:
            if batch and isinstance(data, list):
                self.crud_repo.add_batch(data)
                result.set_data("records_added", len(data))
            else:
                saved_data = self.crud_repo.add(data)
                result.set_data("records_added", 1)
                result.set_data("saved_record", saved_data)

            result.success = True

        except Exception as e:
            result.error = f"Database operation failed: {str(e)}"
            self._logger.ERROR(f"Failed to save data: {e}")

        return result


class ManagementService(BaseService):
    """
    Base class for entity management services.

    Common pattern for services that manage entities
    (EngineService, PortfolioService, FileService).
    """

    def __init__(self, crud_repo, **additional_deps):
        """
        Initialize management service.

        Args:
            crud_repo: Primary CRUD repository
            **additional_deps: Additional CRUD repositories or services
        """
        super().__init__(crud_repo=crud_repo, **additional_deps)

    def _check_entity_exists(self, identifier: str, field: str = "uuid") -> bool:
        """
        Check if entity exists in database.

        Args:
            identifier: Entity identifier value
            field: Field name to search by

        Returns:
            True if entity exists, False otherwise
        """
        try:
            filters = {field: identifier}
            results = self.crud_repo.find(filters=filters, page_size=1)
            return len(results) > 0
        except Exception as e:
            self._logger.WARN(f"Error checking entity existence: {e}")
            return False

    @cache_with_expiration(expiration_seconds=120)
    def _get_entity_by_id(self, entity_id: str, as_dict: bool = False) -> Optional[Any]:
        """
        Generic method to get entity by ID with caching.

        Args:
            entity_id: Entity identifier
            as_dict: Whether to return as dictionary

        Returns:
            Entity if found, None otherwise
        """
        try:
            filters = {"uuid": entity_id}
            results = self.crud_repo.find(filters=filters, page_size=1)

            if results:
                entity = results[0]
                return entity.to_dict() if as_dict and hasattr(entity, "to_dict") else entity
            return None

        except Exception as e:
            self._logger.ERROR(f"Error retrieving entity {entity_id}: {e}")
            return None


class BusinessService(BaseService):
    """
    Base class for business logic services.

    Common pattern for services that implement complex business logic
    (ComponentService, and future analytical services).
    """

    def __init__(self, **service_deps):
        """
        Initialize business service.

        Args:
            **service_deps: Other service dependencies
        """
        super().__init__(**service_deps)

    def _validate_business_rules(self, **context) -> List[str]:
        """
        Validate business rules. Override in subclasses.

        Args:
            **context: Business context for validation

        Returns:
            List of validation error messages
        """
        return []

    def _process_business_logic(self, operation: str, **context) -> ServiceResult:
        """
        Template method for business logic processing.

        Args:
            operation: Operation name for logging
            **context: Operation context

        Returns:
            ServiceResult with operation outcome
        """
        start_time = time.time()
        self._log_operation_start(operation, **context)

        result = self.create_result()

        try:
            # Validate business rules
            validation_errors = self._validate_business_rules(**context)
            if validation_errors:
                result.error = "; ".join(validation_errors)
                return result

            # Perform actual business logic (to be implemented in subclasses)
            business_result = self._execute_business_operation(operation, **context)
            result.success = business_result.get("success", False)
            if not result.success:
                result.error = business_result.get("error", "Unknown business logic error")
            else:
                result.data.update(business_result.get("data", {}))

        except Exception as e:
            result.error = f"Business logic error: {str(e)}"
            self._logger.ERROR(f"Business logic error in {operation}: {e}")

        finally:
            duration = time.time() - start_time
            self._log_operation_end(operation, result.success, duration)

        return result

    def _execute_business_operation(self, operation: str, **context) -> Dict[str, Any]:
        """
        Execute specific business operation. Override in subclasses.

        Args:
            operation: Operation name
            **context: Operation context

        Returns:
            Dictionary with operation result
        """
        return {"success": True, "data": {}}
