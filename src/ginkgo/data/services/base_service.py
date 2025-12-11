"""
Base Service Module

Flat architecture design: BaseService + concrete Services
Remove intermediate DataService, ManagementService, BusinessService classifications
"""

from abc import ABC
from typing import Any, Dict

from ginkgo.libs import GLOG


class ServiceResult:
    """Standardized service operation result structure."""

    def __init__(self, success: bool = False, error: str = "", data: Any = None, message: str = ""):
        """
        Initialize service result with success status, error info, data and message

        Args:
            success: Whether the operation succeeded
            error: Error message when operation fails
            data: Result data payload
            message: Optional status message
        """
        self.success = success
        self.error = error
        self.message = message
        self.warnings = []
        self.data = data  # 允许None值，不自动转换为{}
        self.metadata = {}

    def add_warning(self, message: str):
        """
        Add warning information to result

        Args:
            message: Warning message text
        """
        self.warnings.append(message)

    def set_data(self, key: str, value: Any):
        """
        Set key-value pair in result data dictionary

        Args:
            key: Data field name
            value: Data value to store
        """
        self.data[key] = value

    def set_metadata(self, key: str, value: Any):
        """
        Set metadata information for operation result

        Args:
            key: Metadata field name
            value: Metadata value to store
        """
        self.metadata[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert service result to dictionary representation for serialization

        Returns:
            Dictionary containing all result attributes, only non-empty collections
        """
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
    def success(cls, data: Any = None, message: str = "") -> 'ServiceResult':
        """
        Create successful service result

        Args:
            data: Return data
            message: Success message

        Returns:
            ServiceResult: Successful result object
        """
        return cls(success=True, error="", data=data, message=message)

    @classmethod
    def error(cls, error: str = "", data: Any = None, message: str = "") -> 'ServiceResult':
        """
        Create failed service result

        Args:
            error: Error message
            data: Optional error-related data
            message: Optional message (uses error if not provided)

        Returns:
            ServiceResult: Failed result object
        """
        if not message:
            message = error
        return cls(success=False, error=error, message=message, data=data)

    @classmethod
    def failure(cls, message: str = "", data: Any = None) -> 'ServiceResult':
        """
        Create failed service result (alias method)

        Args:
            message: Failure message
            data: Optional failure-related data

        Returns:
            ServiceResult: Failed result object
        """
        return cls(success=False, error=message, message=message, data=data)

    def is_success(self) -> bool:
        """
        Check if operation succeeded

        Returns:
            bool: Whether succeeded
        """
        return self.success

    def is_failure(self) -> bool:
        """
        Check if operation failed

        Returns:
            bool: Whether failed
        """
        return not self.success

    def __str__(self) -> str:
        """
        String representation

        Returns:
            str: String representation of result
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
        Initialize service through dependency injection

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
        self._logger.DEBUG(f"{self._service_name} initialized with dependencies: {list(dependencies.keys())}")

    def _initialize_dependencies(self):
        """
        Set injected dependencies as private attributes for encapsulation

        Can be overridden in subclasses to implement custom dependency initialization logic
        """
        for name, dependency in self._dependencies.items():
            # Make all dependencies private with _ prefix
            setattr(self, f'_{name}', dependency)

    @property
    def service_name(self) -> str:
        """
        Get service instance name

        Returns:
            Service class name string
        """
        return self._service_name

    def create_result(self, success: bool = False, error: str = None) -> ServiceResult:
        """
        Create standardized ServiceResult instance for operation response

        Args:
            success: Whether operation succeeded
            error: Error message when operation fails

        Returns:
            ServiceResult instance with given success status
        """
        return ServiceResult(success=success, error=error)

    def _log_operation_start(self, operation: str, **params):
        """
        Log the start of a service operation with parameters for debugging.

        Args:
            operation: Name of the operation being started
            **params: Operation parameters to log
        """
        param_str = ", ".join(f"{k}={v}" for k, v in params.items() if v is not None)
        self._logger.DEBUG(f"{self._service_name}.{operation} started with params: {param_str}")

    def _log_operation_end(self, operation: str, success: bool, duration: float = None):
        """
        Log the completion status and duration of a service operation.

        Args:
            operation: Name of the completed operation
            success: Whether the operation succeeded
            duration: Optional execution duration in seconds
        """
        status = "completed" if success else "failed"
        duration_str = f" in {duration:.3f}s" if duration else ""
        self._logger.DEBUG(f"{self._service_name}.{operation} {status}{duration_str}")

    def __str__(self) -> str:
        """
        Return a user-friendly string representation of the service.

        Returns:
            Service name in angle brackets format
        """
        return f"<{self._service_name}>"

    def __repr__(self) -> str:
        """
        Return a developer-friendly string representation with memory address.

        Returns:
            Service name with memory location for debugging
        """
        return f"<{self._service_name} at {hex(id(self))}>"

# Backward compatibility - Keep empty classes as aliases
DataService = BaseService
ManagementService = BaseService
BusinessService = BaseService