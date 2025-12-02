"""
Base Service Module

扁平化架构设计：BaseService + 具体Service
移除中间层的DataService、ManagementService、BusinessService分类
"""

from abc import ABC
from typing import Any, Dict

from ginkgo.libs import GLOG


class ServiceResult:
    """Standardized service operation result structure."""

    def __init__(self, success: bool = False, error: str = "", data: Any = None, message: str = ""):
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
    def success(cls, data: Any = None, message: str = "") -> 'ServiceResult':
        """
        创建成功的服务结果

        Args:
            data: 返回的数据
            message: 成功消息

        Returns:
            ServiceResult: 成功的结果对象
        """
        return cls(success=True, error="", data=data, message=message)

    @classmethod
    def error(cls, error: str = "", data: Any = None, message: str = "") -> 'ServiceResult':
        """
        创建失败的服务结果

        Args:
            error: 错误消息
            data: 可选的错误相关数据
            message: 可选的消息（如果未提供则使用error）

        Returns:
            ServiceResult: 失败的结果对象
        """
        if not message:
            message = error
        return cls(success=False, error=error, message=message, data=data)

    @classmethod
    def failure(cls, message: str = "", data: Any = None) -> 'ServiceResult':
        """
        创建失败的服务结果（别名方法）

        Args:
            message: 失败消息
            data: 可选的失败相关数据

        Returns:
            ServiceResult: 失败的结果对象
        """
        return cls(success=False, error=message, message=message, data=data)

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
        self._logger.DEBUG(f"{self._service_name} initialized with dependencies: {list(dependencies.keys())}")

    def _initialize_dependencies(self):
        """
        Initialize dependencies as private attributes for better encapsulation.
        Override in subclasses for custom dependency handling.
        """
        for name, dependency in self._dependencies.items():
            # Make all dependencies private with _ prefix
            setattr(self, f'_{name}', dependency)

    @property
    def service_name(self) -> str:
        """Get service name."""
        return self._service_name

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

    def __str__(self) -> str:
        return f"<{self._service_name}>"

    def __repr__(self) -> str:
        return f"<{self._service_name} at {hex(id(self))}>"

# 向后兼容性 - 保留空类作为别名
DataService = BaseService
ManagementService = BaseService
BusinessService = BaseService