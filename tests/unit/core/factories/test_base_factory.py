"""
基础工厂单元测试

测试 BaseFactory 抽象工厂类，
验证组件注册、注销、依赖解析、DI 创建等功能。
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.core.factories.base_factory import BaseFactory


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcreteFactory(BaseFactory):
    """BaseFactory 的具体实现"""

    def create(self, component_type, **kwargs):
        if self.has_component(component_type):
            component_class = self._component_registry[component_type]
            return self._create_with_di(component_class, kwargs)
        raise ValueError(f"未知组件类型: {component_type}")


# ── 简单组件类用于测试 ──────────────────────────────────────────────


class SimpleComponent:
    """简单组件"""
    def __init__(self, name="simple"):
        self.name = name


class ComponentWithDeps:
    """带依赖的组件"""
    def __init__(self, name="deps", service=None):
        self.name = name
        self.service = service


# ── BaseFactory 构造测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryConstruction:
    """BaseFactory 构造测试"""

    def test_default_construction(self):
        """默认构造"""
        factory = ConcreteFactory()
        assert factory._container is None
        assert factory._component_registry == {}

    def test_with_container(self):
        """带容器构造"""
        container = MagicMock()
        factory = ConcreteFactory(container)
        assert factory._container is container


# ── BaseFactory 组件注册测试 ────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryRegistration:
    """BaseFactory 组件注册测试"""

    def test_register_component(self):
        """注册组件"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        assert factory.has_component("simple") is True

    def test_register_multiple_components(self):
        """注册多个组件"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        factory.register_component("deps", ComponentWithDeps)
        assert len(factory.list_components()) == 2

    def test_unregister_component(self):
        """注销组件"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        factory.unregister_component("simple")
        assert factory.has_component("simple") is False

    def test_unregister_nonexistent_no_error(self):
        """注销不存在的组件不报错"""
        factory = ConcreteFactory()
        factory.unregister_component("nonexistent")  # 不应抛出异常

    def test_list_components(self):
        """列出所有组件"""
        factory = ConcreteFactory()
        factory.register_component("a", SimpleComponent)
        factory.register_component("b", ComponentWithDeps)
        components = factory.list_components()
        assert "a" in components
        assert "b" in components

    def test_has_component(self):
        """检查组件是否存在"""
        factory = ConcreteFactory()
        assert factory.has_component("nonexistent") is False
        factory.register_component("simple", SimpleComponent)
        assert factory.has_component("simple") is True


# ── BaseFactory 创建测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryCreation:
    """BaseFactory 创建组件测试"""

    def test_create_simple_component(self):
        """创建简单组件"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        component = factory.create("simple")
        assert isinstance(component, SimpleComponent)

    def test_create_with_params(self):
        """带参数创建组件"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        component = factory.create("simple", name="custom")
        assert component.name == "custom"

    def test_create_unknown_raises(self):
        """创建未知组件抛出异常"""
        factory = ConcreteFactory()
        with pytest.raises(ValueError, match="未知组件"):
            factory.create("unknown")


# ── BaseFactory 依赖注入测试 ────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryDI:
    """BaseFactory 依赖注入测试"""

    def test_resolve_dependencies_no_container(self):
        """无容器时依赖为空"""
        factory = ConcreteFactory()
        deps = factory._resolve_dependencies(SimpleComponent)
        assert deps == {}

    def test_resolve_dependencies_with_container(self):
        """有容器时解析依赖"""
        factory = ConcreteFactory()
        container = MagicMock()
        container.has.return_value = False
        factory.set_container(container)
        deps = factory._resolve_dependencies(SimpleComponent)
        # SimpleComponent 无类型注解依赖
        assert isinstance(deps, dict)

    def test_create_with_di_no_container(self):
        """无容器时 DI 创建仍然有效"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        component = factory.create("simple", name="test")
        assert component.name == "test"

    def test_create_with_di_container_provides_dep(self):
        """容器提供依赖"""
        factory = ConcreteFactory()
        container = MagicMock()
        mock_service = MagicMock(name="MockService")

        # 模拟容器提供 service 依赖
        container.has.side_effect = lambda name: name == "service"
        container.get.side_effect = lambda name: mock_service if name == "service" else None

        factory.set_container(container)
        factory.register_component("deps", ComponentWithDeps)
        component = factory.create("deps", name="test")
        assert isinstance(component, ComponentWithDeps)
        assert component.name == "test"


# ── BaseFactory 信息查询测试 ────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryInfo:
    """BaseFactory 信息查询测试"""

    def test_get_component_info(self):
        """获取组件信息"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        info = factory.get_component_info("simple")
        assert info["name"] == "simple"
        assert info["class_name"] == "SimpleComponent"
        assert info["module"] == SimpleComponent.__module__
        assert "doc" in info
        assert "dependencies" in info

    def test_get_component_info_nonexistent(self):
        """获取不存在组件信息返回 None"""
        factory = ConcreteFactory()
        assert factory.get_component_info("nonexistent") is None

    def test_get_factory_info(self):
        """获取工厂信息"""
        factory = ConcreteFactory()
        factory.register_component("simple", SimpleComponent)
        info = factory.get_factory_info()
        assert info["factory_class"] == "ConcreteFactory"
        assert info["registered_components"] == 1
        assert "simple" in info["components"]

    def test_set_container(self):
        """设置容器"""
        factory = ConcreteFactory()
        container = MagicMock()
        factory.set_container(container)
        assert factory._container is container


# ── BaseFactory 继承测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestBaseFactoryInheritance:
    """BaseFactory 继承测试"""

    def test_cannot_instantiate_abstract(self):
        """不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            BaseFactory()
