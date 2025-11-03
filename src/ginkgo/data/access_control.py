"""
CRUD访问控制模块

这个模块提供装饰器和验证机制，确保CRUD方法只能在Service层调用。
通过调用栈分析和类型检查来实现访问控制。
"""

import inspect
import functools
from typing import Union, List, Any, Type
from ginkgo.libs import GLOG


class CRUDAccessViolationError(Exception):
    """CRUD非法访问异常"""

    pass


def _is_service_layer_call() -> bool:
    """
    检查当前调用是否来自Service层

    通过分析调用栈，检查是否有Service层的调用者
    """
    frame = inspect.currentframe()
    try:
        # 向上遍历调用栈
        while frame is not None:
            frame = frame.f_back
            if frame is None:
                break

            # 获取调用者的文件路径和类名
            filepath = frame.f_code.co_filename

            # 检查是否在services目录中
            if "/data/services/" in filepath:
                return True

            # 检查调用者是否是Service类的子类
            frame_locals = frame.f_locals
            if "self" in frame_locals:
                caller_class = frame_locals["self"].__class__
                # 检查类名是否以Service结尾
                if caller_class.__name__.endswith("Service"):
                    return True

                # 检查是否继承自BaseService
                try:
                    from ginkgo.data.services.base_service import BaseService

                    if isinstance(caller_class, type) and issubclass(caller_class, BaseService):
                        return True
                except ImportError:
                    pass

    finally:
        del frame

    return False


def _get_caller_info() -> str:
    """获取调用者信息用于日志"""
    frame = inspect.currentframe()
    try:
        return _find_actual_caller(frame)
    finally:
        del frame


def _find_actual_caller(frame) -> str:
    """
    动态遍历调用栈找到实际调用者位置
    
    跳过内部的访问控制、装饰器和包装器帧，找到真正的业务逻辑调用者
    """
    if frame is None:
        return "Unknown caller"
    
    try:
        current_frame = frame.f_back  # 跳过 _get_caller_info 本身
        
        while current_frame is not None:
            code = current_frame.f_code
            filename = code.co_filename
            function_name = code.co_name
            line_number = current_frame.f_lineno
            
            # 跳过访问控制模块内部的帧
            if not _is_internal_frame(filename, function_name):
                return f"{filename}:{line_number} in {function_name}"
            
            current_frame = current_frame.f_back
            
    except Exception as e:
        # 如果帧遍历失败，提供调试信息
        return f"Frame traversal error: {str(e)}"
    
    return "Unknown caller"


def _is_internal_frame(filename: str, function_name: str) -> bool:
    """
    判断是否为内部帧（需要跳过的帧）
    
    Args:
        filename: 文件路径
        function_name: 函数名
        
    Returns:
        True 如果是内部帧需要跳过，False 如果是实际调用者
    """
    # 跳过访问控制模块本身
    if "access_control.py" in filename:
        return True
    
    # 跳过装饰器包装器函数
    if function_name in ["wrapper", "_wrapped", "__wrapper__"]:
        return True
    
    # 跳过 functools 模块的内部函数
    if "functools" in filename:
        return True
        
    # 跳过其他装饰器相关的内部函数
    if function_name.startswith("_") and function_name.endswith("_wrapper"):
        return True
    
    return False


def service_only(method):
    """
    装饰器：限制方法只能在Service层调用

    用法:
        class SomeCRUD(BaseCRUD):
            @service_only
            def add(self, data):
                return super().add(data)
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not _is_service_layer_call():
            caller_info = _get_caller_info()
            error_msg = (
                f"CRUD method '{method.__name__}' called from non-Service layer: {caller_info}. "
                f"Consider using the appropriate Service method instead."
            )

            if STRICT_MODE:
                GLOG.ERROR(error_msg)
                raise CRUDAccessViolationError(error_msg)
            else:
                GLOG.DEBUG(f"[ACCESS_CONTROL] {error_msg}")

        return method(self, *args, **kwargs)

    return wrapper


def restrict_crud_access(crud_class: Type) -> Type:
    """
    类装饰器：为CRUD类的所有公共方法添加访问控制

    用法:
        @restrict_crud_access
        class BarCRUD(BaseCRUD):
            def add(self, data):
                return super().add(data)
    """
    # 需要保护的方法列表（CRUD核心操作）
    protected_methods = [
        "add",
        "add_batch",
        "add_all",
        "update",
        "update_batch",
        "update_by_id",
        "remove",
        "remove_batch",
        "remove_by_id",
        "delete",
        "find",
        "find_by_id",
        "get_page_filtered",
        "count",
        "exists",
    ]

    for method_name in protected_methods:
        if hasattr(crud_class, method_name):
            original_method = getattr(crud_class, method_name)
            if callable(original_method) and not method_name.startswith("_"):
                setattr(crud_class, method_name, service_only(original_method))

    return crud_class


class ServiceLayerProxy:
    """
    Service层代理类，用于安全地访问CRUD方法

    这个代理确保只有Service层可以调用CRUD方法
    """

    def __init__(self, crud_instance):
        self._crud = crud_instance
        self._service_verified = _is_service_layer_call()

    def __getattr__(self, name):
        if not self._service_verified:
            raise CRUDAccessViolationError(
                f"CRUD proxy can only be used from Service layer. "
                f"Attempted to access '{name}' from non-service context."
            )
        return getattr(self._crud, name)


def create_protected_crud_factory():
    """
    创建受保护的CRUD工厂函数

    这个工厂确保CRUD实例只能在适当的上下文中创建
    """

    def protected_get_crud(model_name: str):
        from ginkgo.data.utils import get_crud

        if not _is_service_layer_call():
            caller_info = _get_caller_info()
            GLOG.WARN(
                f"Direct CRUD access detected from non-service layer: {caller_info}. "
                f"Consider using Service layer instead."
            )
            # 在开发环境下可以抛出异常，生产环境下可以只记录警告
            # raise CRUDAccessViolationError(f"CRUD '{model_name}' should be accessed via Service layer")

        crud_instance = get_crud(model_name)
        return ServiceLayerProxy(crud_instance)

    return protected_get_crud


# 开发时的严格模式开关
STRICT_MODE = False  # 设为True时会抛出异常，False时只记录警告


def set_strict_mode(enabled: bool):
    """设置严格模式"""
    global STRICT_MODE
    STRICT_MODE = enabled


def validate_service_context(operation_name: str = "CRUD operation"):
    """
    验证当前是否在Service上下文中

    Args:
        operation_name: 操作名称，用于错误消息
    """
    if not _is_service_layer_call():
        caller_info = _get_caller_info()
        message = f"{operation_name} should be called from Service layer. Called from: {caller_info}"

        if STRICT_MODE:
            raise CRUDAccessViolationError(message)
        else:
            GLOG.WARN(message)
