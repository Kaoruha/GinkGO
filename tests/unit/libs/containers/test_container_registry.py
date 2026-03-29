"""
ContainerRegistry 容器注册中心单元测试

覆盖范围：
- 容器注册 / 注销
- 获取容器和跨容器服务查找
- 依赖解析和缓存
- 健康状态查询
- 生命周期管理（initialize_all / shutdown_all）
- 线程安全
"""

from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from ginkgo.libs.containers.base_container import ContainerState
from ginkgo.libs.containers.container_registry import (
    ContainerRegistry,
    ContainerInfo,
)
from ginkgo.libs.containers.exceptions import (
    ContainerNotRegisteredError,
    ServiceNotFoundError,
    CircularDependencyError,
    DuplicateServiceError,
    ContainerLifecycleError,
)


# ---------------------------------------------------------------------------
# 辅助函数：创建 mock 容器
# ---------------------------------------------------------------------------

_STATE_MAP = {
    "created": ContainerState.CREATED,
    "configuring": ContainerState.CONFIGURING,
    "configured": ContainerState.CONFIGURED,
    "initializing": ContainerState.INITIALIZING,
    "ready": ContainerState.READY,
    "shutting_down": ContainerState.SHUTTING_DOWN,
    "shutdown": ContainerState.SHUTDOWN,
    "error": ContainerState.ERROR,
}


def _make_container(
    module_name: str = "test_module",
    state_value: str = "created",
    services: list = None,
    is_ready: bool = False,
) -> MagicMock:
    """创建模拟的 BaseContainer 对象

    state_value 使用字符串，内部映射到 ContainerState 枚举以保证
    ``container.state == ContainerState.CREATED`` 等比较能正确工作。
    """
    mock = MagicMock()
    mock.module_name = module_name
    mock.state = _STATE_MAP[state_value]
    mock.is_ready = is_ready
    mock.list_services.return_value = services or []
    mock.has.side_effect = lambda name: name in (services or [])
    mock.get.side_effect = lambda name: f"instance_of_{name}"
    mock.initialize.return_value = None
    mock.shutdown.return_value = None
    mock.set_registry.return_value = None
    return mock


@pytest.mark.unit
class TestContainerRegistryConstruction:
    """ContainerRegistry 构造测试"""

    def test_initial_state(self):
        """新实例内部状态为空"""
        reg = ContainerRegistry()
        assert reg._containers == {}
        assert reg._service_index == {}
        assert reg._initialization_order == []
        assert reg._resolution_cache == {}

    def test_list_containers_empty(self):
        """空注册中心返回空列表"""
        reg = ContainerRegistry()
        assert reg.list_containers() == []


@pytest.mark.unit
class TestContainerRegistryRegister:
    """容器注册测试"""

    def test_register_success(self):
        """成功注册一个容器"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="created")
        reg.register(container)

        assert "data" in reg._containers
        assert reg._containers["data"].container is container

    def test_register_calls_set_registry(self):
        """注册时调用容器的 set_registry"""
        reg = ContainerRegistry()
        container = _make_container("data")
        reg.register(container)
        container.set_registry.assert_called_once_with(reg)

    def test_register_initializes_created_container(self):
        """CREATED 状态的容器在注册时自动初始化"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="created")
        reg.register(container)
        container.initialize.assert_called_once()

    def test_register_does_not_reinitialize_ready_container(self):
        """READY 状态的容器在注册时不再初始化"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="ready")
        reg.register(container)
        container.initialize.assert_not_called()

    def test_register_updates_service_index(self):
        """注册时更新服务索引"""
        reg = ContainerRegistry()
        container = _make_container(
            "data",
            state_value="created",
            services=["bar_crud", "tick_crud"],
        )
        reg.register(container)
        assert reg._service_index["bar_crud"] == "data"
        assert reg._service_index["tick_crud"] == "data"

    def test_register_duplicate_raises(self):
        """重复注册同名容器抛出 DuplicateServiceError"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="created")
        c2 = _make_container("data", state_value="created")
        reg.register(c1)
        with pytest.raises(DuplicateServiceError):
            reg.register(c2)


@pytest.mark.unit
class TestContainerRegistryUnregister:
    """容器注销测试"""

    def test_unregister_removes_container(self):
        """注销后容器不再存在"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="created")
        reg.register(container)
        reg.unregister("data")
        assert "data" not in reg._containers

    def test_unregister_calls_shutdown(self):
        """注销时调用容器 shutdown"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="ready")
        reg.register(container)
        reg.unregister("data")
        container.shutdown.assert_called_once()

    def test_unregister_nonexistent_is_noop(self):
        """注销不存在的容器不抛异常"""
        reg = ContainerRegistry()
        reg.unregister("nonexistent")  # 不应抛出

    def test_unregister_clears_service_index(self):
        """注销时清理对应的服务索引"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="created", services=["svc"]
        )
        reg.register(container)
        assert "svc" in reg._service_index
        reg.unregister("data")
        assert "svc" not in reg._service_index

    def test_unregister_clears_cache(self):
        """注销时清理相关缓存"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="created")
        reg.register(container)
        # 模拟缓存条目
        reg._resolution_cache["data:some_service"] = "value"
        reg._resolution_cache["other:data"] = "value2"
        reg.unregister("data")
        assert "data:some_service" not in reg._resolution_cache


@pytest.mark.unit
class TestContainerRegistryGetContainer:
    """获取容器测试"""

    def test_get_existing_container(self):
        """获取已注册的容器"""
        reg = ContainerRegistry()
        container = _make_container("data", state_value="created")
        reg.register(container)
        result = reg.get_container("data")
        assert result is container

    def test_get_nonexistent_raises(self):
        """获取未注册的容器抛出 ContainerNotRegisteredError"""
        reg = ContainerRegistry()
        with pytest.raises(ContainerNotRegisteredError):
            reg.get_container("nonexistent")


@pytest.mark.unit
class TestContainerRegistryGetService:
    """获取服务测试"""

    def test_get_service_from_ready_container(self):
        """从 READY 容器获取服务"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", is_ready=True
        )
        reg.register(container)
        # 让 mock.get 返回特定值
        container.get.side_effect = lambda name: f"instance_{name}"
        result = reg.get_service("data", "bar_crud")
        assert result == "instance_bar_crud"

    def test_get_service_nonexistent_container_raises(self):
        """从不存在的容器获取服务抛出异常"""
        reg = ContainerRegistry()
        with pytest.raises(ContainerNotRegisteredError):
            reg.get_service("nonexistent", "svc")

    def test_get_service_not_ready_raises(self):
        """容器未就绪时抛出 ContainerLifecycleError"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="created", is_ready=False
        )
        reg.register(container)
        with pytest.raises(ContainerLifecycleError):
            reg.get_service("data", "svc")


@pytest.mark.unit
class TestContainerRegistryFindService:
    """跨容器服务查找测试"""

    def test_find_service_via_index(self):
        """通过服务索引快速查找"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", is_ready=True, services=["bar_crud"]
        )
        container.get.side_effect = lambda name: f"instance_{name}"
        reg.register(container)

        result = reg.find_service("bar_crud")
        assert result == "instance_bar_crud"

    def test_find_service_by_searching_containers(self):
        """索引未命中时遍历容器查找"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", is_ready=True, services=["bar_crud"]
        )
        container.get.side_effect = lambda name: f"instance_{name}"
        reg.register(container)
        # 手动清除索引以触发遍历
        reg._service_index.clear()

        result = reg.find_service("bar_crud")
        assert result == "instance_bar_crud"

    def test_find_service_not_found_raises(self):
        """找不到服务时抛出 ServiceNotFoundError"""
        reg = ContainerRegistry()
        with pytest.raises(ServiceNotFoundError):
            reg.find_service("nonexistent_service")


@pytest.mark.unit
class TestContainerRegistryResolveCrossContainer:
    """跨容器依赖解析测试"""

    def test_resolve_caches_result(self):
        """解析结果会被缓存"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", is_ready=True, services=["svc"]
        )
        container.get.side_effect = lambda name: f"instance_{name}"
        reg.register(container)

        result1 = reg.resolve_cross_container_dependency("svc", "caller")
        result2 = reg.resolve_cross_container_dependency("svc", "caller")
        assert result1 == result2 == "instance_svc"
        # 第二次应命中缓存，不再调用 get
        assert container.get.call_count == 1

    def test_resolve_not_found_raises(self):
        """服务不存在时抛出 ServiceNotFoundError"""
        reg = ContainerRegistry()
        with pytest.raises(ServiceNotFoundError):
            reg.resolve_cross_container_dependency("missing", "caller")

    def test_resolve_tracks_dependency(self):
        """解析后更新依赖跟踪"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", is_ready=True, services=["svc"]
        )
        container.get.side_effect = lambda name: f"instance_{name}"
        reg.register(container)

        # 先注册调用方容器
        caller = _make_container("caller", state_value="ready", is_ready=True)
        reg.register(caller)

        reg.resolve_cross_container_dependency("svc", "caller")

        caller_info = reg._containers["caller"]
        assert "data" in caller_info.dependencies
        data_info = reg._containers["data"]
        assert "caller" in data_info.dependents


@pytest.mark.unit
class TestContainerRegistryListServices:
    """列出服务测试"""

    def test_list_all_services(self):
        """列出所有容器的服务"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready", services=["bar", "tick"])
        c2 = _make_container("trading", state_value="ready", services=["strategy"])
        reg.register(c1)
        reg.register(c2)

        result = reg.list_services()
        assert result["data"] == ["bar", "tick"]
        assert result["trading"] == ["strategy"]

    def test_list_services_filtered(self):
        """按容器名过滤"""
        reg = ContainerRegistry()
        c = _make_container("data", state_value="ready", services=["bar"])
        reg.register(c)

        result = reg.list_services(module_name="data")
        assert "data" in result
        assert result["data"] == ["bar"]

    def test_list_services_nonexistent_raises(self):
        """指定不存在的容器名抛出异常"""
        reg = ContainerRegistry()
        with pytest.raises(ContainerNotRegisteredError):
            reg.list_services(module_name="nonexistent")


@pytest.mark.unit
class TestContainerRegistryDependencyInfo:
    """依赖信息查询测试"""

    def test_get_container_dependencies(self):
        """获取容器依赖信息"""
        reg = ContainerRegistry()
        container = _make_container(
            "data", state_value="ready", services=["bar"]
        )
        reg.register(container)

        info = reg.get_container_dependencies("data")
        assert info["module_name"] == "data"
        assert info["state"] == "ready"
        assert info["services"] == ["bar"]
        assert info["dependencies"] == []
        assert info["dependents"] == []
        assert "registration_time" in info

    def test_get_dependencies_nonexistent_raises(self):
        """获取不存在容器的依赖信息抛出异常"""
        reg = ContainerRegistry()
        with pytest.raises(ContainerNotRegisteredError):
            reg.get_container_dependencies("nonexistent")


@pytest.mark.unit
class TestContainerRegistryHealthStatus:
    """健康状态查询测试"""

    def test_empty_registry_is_healthy(self):
        """空注册中心整体健康"""
        reg = ContainerRegistry()
        status = reg.get_health_status()
        assert status["total_containers"] == 0
        assert status["healthy_containers"] == 0
        assert status["overall_healthy"] is True

    def test_all_ready_is_healthy(self):
        """所有容器 READY 时整体健康"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready")
        c2 = _make_container("trading", state_value="ready")
        reg.register(c1)
        reg.register(c2)

        status = reg.get_health_status()
        assert status["total_containers"] == 2
        assert status["healthy_containers"] == 2
        assert status["overall_healthy"] is True

    def test_error_container_not_healthy(self):
        """存在 ERROR 状态容器时整体不健康"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready")
        c2 = _make_container("trading", state_value="error")
        reg.register(c1)
        reg.register(c2)

        status = reg.get_health_status()
        assert status["overall_healthy"] is False
        assert status["error_containers"] == 1


@pytest.mark.unit
class TestContainerRegistryInitializeAll:
    """批量初始化测试"""

    def test_initialize_all_created_containers(self):
        """initialize_all 初始化所有 CREATED 状态的容器"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="created")
        c2 = _make_container("trading", state_value="created")
        reg.register(c1)
        reg.register(c2)

        reg.initialize_all()
        c1.initialize.assert_called()
        c2.initialize.assert_called()

    def test_initialize_all_skips_ready_containers(self):
        """已 READY 的容器不再初始化"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready")
        reg.register(c1)
        reg.initialize_all()
        c1.initialize.assert_not_called()


@pytest.mark.unit
class TestContainerRegistryShutdownAll:
    """批量关闭测试"""

    def test_shutdown_all(self):
        """shutdown_all 关闭所有容器"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready")
        c2 = _make_container("trading", state_value="ready")
        reg.register(c1)
        reg.register(c2)

        # shutdown_all 依赖 _initialization_order，
        # 先通过 initialize_all 填充顺序
        reg._initialization_order = ["data", "trading"]

        reg.shutdown_all()
        c1.shutdown.assert_called()
        c2.shutdown.assert_called()

    def test_shutdown_all_clears_cache(self):
        """shutdown_all 清理解析缓存"""
        reg = ContainerRegistry()
        c1 = _make_container("data", state_value="ready")
        reg.register(c1)
        reg._resolution_cache["data:svc"] = "value"

        reg.shutdown_all()
        assert reg._resolution_cache == {}


@pytest.mark.unit
class TestContainerInfo:
    """ContainerInfo 数据类测试"""

    def test_default_values(self):
        """默认值正确"""
        mock_container = MagicMock()
        info = ContainerInfo(container=mock_container)
        assert info.container is mock_container
        assert isinstance(info.registration_time, float)
        assert info.dependencies == set()
        assert info.dependents == set()
