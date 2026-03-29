"""
容器框架异常类单元测试

覆盖范围：
- ContainerError 基类异常
- ServiceNotFoundError 服务未找到
- CircularDependencyError 循环依赖
- ContainerNotRegisteredError 容器未注册
- DuplicateServiceError 重复服务
- InvalidContainerConfigError 无效配置
- ContainerLifecycleError 生命周期错误
"""


import pytest

from ginkgo.libs.containers.exceptions import (
    ContainerError,
    ServiceNotFoundError,
    CircularDependencyError,
    ContainerNotRegisteredError,
    DuplicateServiceError,
    InvalidContainerConfigError,
    ContainerLifecycleError,
)


@pytest.mark.unit
class TestContainerError:
    """ContainerError 基类异常测试"""

    def test_inherits_from_exception(self):
        """验证基类继承自 Exception"""
        assert issubclass(ContainerError, Exception)

    def test_default_message(self):
        """默认只传 message"""
        exc = ContainerError("something went wrong")
        assert str(exc) == "something went wrong"
        assert exc.container_name is None

    def test_with_container_name(self):
        """同时传递 message 和 container_name"""
        exc = ContainerError("bad state", container_name="data")
        assert str(exc) == "bad state"
        assert exc.container_name == "data"

    def test_container_name_defaults_to_none(self):
        """container_name 默认为 None"""
        exc = ContainerError("error")
        assert exc.container_name is None


@pytest.mark.unit
class TestServiceNotFoundError:
    """ServiceNotFoundError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(ServiceNotFoundError, ContainerError)

    def test_service_name_attribute(self):
        """验证 service_name 属性"""
        exc = ServiceNotFoundError("bar_service")
        assert exc.service_name == "bar_service"

    def test_message_without_container(self):
        """不指定容器时的错误消息"""
        exc = ServiceNotFoundError("bar_service")
        assert str(exc) == "Service 'bar_service' not found"

    def test_message_with_container(self):
        """指定容器时的错误消息"""
        exc = ServiceNotFoundError("bar_service", container_name="data")
        assert str(exc) == "Service 'bar_service' not found in container 'data'"
        assert exc.container_name == "data"

    def test_container_name_defaults_to_none(self):
        """container_name 默认为 None"""
        exc = ServiceNotFoundError("foo")
        assert exc.container_name is None


@pytest.mark.unit
class TestCircularDependencyError:
    """CircularDependencyError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(CircularDependencyError, ContainerError)

    def test_dependency_chain_attribute(self):
        """验证 dependency_chain 属性"""
        chain = ["a", "b", "c", "a"]
        exc = CircularDependencyError(chain)
        assert exc.dependency_chain == chain

    def test_message_format(self):
        """验证错误消息格式"""
        exc = CircularDependencyError(["module_a", "module_b", "module_a"])
        assert "Circular dependency detected" in str(exc)
        assert "module_a -> module_b -> module_a" in str(exc)

    def test_empty_chain(self):
        """空链路也能正常创建"""
        exc = CircularDependencyError([])
        assert exc.dependency_chain == []
        assert "Circular dependency detected:" in str(exc)


@pytest.mark.unit
class TestContainerNotRegisteredError:
    """ContainerNotRegisteredError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(ContainerNotRegisteredError, ContainerError)

    def test_message_format(self):
        """验证错误消息包含容器名"""
        exc = ContainerNotRegisteredError("data")
        assert "data" in str(exc)
        assert "not registered" in str(exc)
        assert exc.container_name == "data"


@pytest.mark.unit
class TestDuplicateServiceError:
    """DuplicateServiceError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(DuplicateServiceError, ContainerError)

    def test_message_format(self):
        """验证错误消息包含服务名和容器名"""
        exc = DuplicateServiceError("bar_service", "data")
        assert "bar_service" in str(exc)
        assert "data" in str(exc)
        assert "already exists" in str(exc)
        assert exc.container_name == "data"


@pytest.mark.unit
class TestInvalidContainerConfigError:
    """InvalidContainerConfigError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(InvalidContainerConfigError, ContainerError)

    def test_message_format(self):
        """验证错误消息包含配置问题"""
        exc = InvalidContainerConfigError("data", "missing host")
        assert "data" in str(exc)
        assert "missing host" in str(exc)
        assert "Invalid configuration" in str(exc)
        assert exc.container_name == "data"


@pytest.mark.unit
class TestContainerLifecycleError:
    """ContainerLifecycleError 异常测试"""

    def test_inherits_from_container_error(self):
        """验证继承链"""
        assert issubclass(ContainerLifecycleError, ContainerError)

    def test_message_format(self):
        """验证错误消息包含操作和原因"""
        exc = ContainerLifecycleError("data", "initialize", "timeout exceeded")
        assert "data" in str(exc)
        assert "initialize" in str(exc)
        assert "timeout exceeded" in str(exc)
        assert "failed to" in str(exc)
        assert exc.container_name == "data"
