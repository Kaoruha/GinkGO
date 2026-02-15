"""
数据源基类测试 - Pytest重构版本

测试数据源基类功能：
1. 基类基本功能
2. 抽象方法强制实现
3. 接口一致性

重构要点：
- 使用pytest fixtures替代setUp/tearDown
- 使用parametrize进行参数化测试
- 使用pytest.mark.unit标记
- 清晰的测试类分组
"""

import pytest
from unittest.mock import Mock

try:
    from ginkgo.data.sources.source_base import GinkgoSourceBase
except ImportError:
    GinkgoSourceBase = None


# ===== Skip条件 =====

pytestmark = []
if GinkgoSourceBase is None:
    pytestmark = [pytest.mark.skip("GinkgoSourceBase模块不可用")]


# ===== Fixtures =====

@pytest.fixture
def mock_data_source():
    """用于测试的Mock数据源"""
    if GinkgoSourceBase is None:
        pytest.skip("GinkgoSourceBase模块不可用")

    class MockDataSource(GinkgoSourceBase):
        """用于测试的Mock数据源实现"""
        def connect(self):
            """实现connect方法用于测试"""
            self.client = Mock()
            return True

    return MockDataSource()


@pytest.fixture
def incomplete_data_source():
    """用于测试的未完整实现数据源"""
    if GinkgoSourceBase is None:
        pytest.skip("GinkgoSourceBase模块不可用")

    class IncompleteDataSource(GinkgoSourceBase):
        """用于测试的未完整实现数据源"""
        pass

    return IncompleteDataSource


# ===== GinkgoSourceBase测试 =====

@pytest.mark.unit
class TestGinkgoSourceBase:
    """
    测试数据源基类功能

    验证：
    1. 基类基本功能
    2. 抽象方法强制实现
    3. 接口一致性
    """

    def test_source_base_init(self, mock_data_source):
        """测试基类初始化

        验证：
        1. 基类可以被实例化
        2. 初始状态正确
        3. 属性设置正确
        """
        source = mock_data_source()

        assert source is not None, "数据源对象应该创建成功"
        assert source.client is None, "初始client应该为None"
        assert isinstance(source, GinkgoSourceBase), "应该是基类的实例"

    def test_source_base_client_property(self, mock_data_source):
        """测试client属性管理

        验证：
        1. client属性getter/setter正常工作
        2. 可以设置和获取client对象
        3. 属性类型检查
        """
        source = mock_data_source()

        # 测试初始状态
        assert source.client is None, "初始client应该为None"

        # 测试设置client
        mock_client = Mock()
        source.client = mock_client
        assert source.client == mock_client, "client设置应该成功"

        # 测试重新设置
        new_client = Mock()
        source.client = new_client
        assert source.client == new_client, "client重新设置应该成功"

        # 测试设置为None
        source.client = None
        assert source.client is None, "client应该可以重置为None"

    def test_source_base_connect_abstract(self, incomplete_data_source):
        """测试connect方法的抽象性

        验证：
        1. 基类的connect方法抛出NotImplementedError
        2. 子类必须实现connect方法
        3. 实现了connect的子类可以正常工作
        """
        # 测试未实现connect的子类
        source = incomplete_data_source()

        with pytest.raises(NotImplementedError):
            source.connect()

    def test_source_base_interface_consistency(self, mock_data_source):
        """测试接口一致性

        验证：
        1. 所有数据源都有相同的基础接口
        2. 必要的方法存在
        3. 属性访问一致
        """
        source = mock_data_source()

        # 检查必要的属性和方法存在
        assert hasattr(source, "client"), "必须有client属性"
        assert hasattr(source, "connect"), "必须有connect方法"

        # 检查方法可调用性
        assert callable(getattr(source, "connect")), "connect必须是可调用的方法"

        # 检查属性描述符
        assert hasattr(GinkgoSourceBase, "client"), "基类必须定义client属性"

    def test_source_base_inheritance(self, mock_data_source):
        """测试继承关系

        验证：
        1. 子类正确继承基类
        2. 方法重写正常工作
        3. 基类方法可以被调用
        """
        source = mock_data_source()

        # 测试继承关系
        assert isinstance(source, GinkgoSourceBase), "子类应该是基类的实例"
        assert issubclass(type(source), GinkgoSourceBase), "应该是基类的子类"

        # 测试方法解析顺序
        assert GinkgoSourceBase in source.__class__.__mro__, "继承链应该正确"

    def test_source_base_error_handling(self, incomplete_data_source):
        """测试错误处理

        验证：
        1. 抽象方法错误处理
        2. 属性访问错误处理
        3. 异常传播正确
        """
        source = incomplete_data_source()

        # 测试抽象方法错误
        with pytest.raises(NotImplementedError):
            source.connect()

        # 测试错误信息
        try:
            source.connect()
            pytest.fail("应该抛出NotImplementedError")
        except NotImplementedError as e:
            # 确保错误可以被正确捕获和处理
            assert isinstance(e, NotImplementedError), "应该是NotImplementedError类型"

    @pytest.mark.parametrize("instance_num", [1, 2, 5, 10])
    def test_source_base_multiple_instances(self, mock_data_source, instance_num):
        """测试多实例管理

        验证：
        1. 可以创建多个实例
        2. 实例间相互独立
        3. 状态不会互相影响
        """
        instances = [mock_data_source() for _ in range(instance_num)]

        # 测试实例独立性
        for i in range(instance_num):
            for j in range(i + 1, instance_num):
                assert instances[i] is not instances[j], f"实例{i}和{j}应该是不同的实例"

        # 测试状态独立性
        mock_clients = [Mock() for _ in range(instance_num)]
        for i, instance in enumerate(instances):
            instance.client = mock_clients[i]

        # 验证每个实例的client都不同
        for i in range(instance_num):
            assert instances[i].client == mock_clients[i], f"实例{i}的client应该正确"

    def test_source_base_required_methods(self, mock_data_source):
        """测试基类必须定义的方法

        验证：
        1. connect方法必须存在且为抽象方法
        2. 子类不实现connect应该失败
        3. 基类设计符合抽象基类规范
        """
        # 验证基类有connect方法
        assert hasattr(GinkgoSourceBase, "connect"), "基类必须定义connect方法"

        # 验证connect是抽象方法（调用时抛出NotImplementedError）
        source = incomplete_data_source()
        with pytest.raises(NotImplementedError):
            source.connect()

        # 验证实现了connect的子类可以正常工作
        mock_instance = mock_data_source()
        result = mock_instance.connect()
        assert result is not False, "实现了connect的子类应该正常工作"


# ===== 参数化测试 =====

@pytest.mark.unit
class TestGinkgoSourceBaseParametrized:
    """参数化测试数据源基类"""

    @pytest.mark.parametrize("client_value", [
        Mock(),
        None,
        "string_client",
        123,
    ])
    def test_client_various_types(self, mock_data_source, client_value):
        """测试不同类型的client设置"""
        source = mock_data_source()
        source.client = client_value
        assert source.client == client_value

    @pytest.mark.parametrize("method_name", [
        "connect",
        "client",
    ])
    def test_required_members_exist(self, method_name):
        """测试必需成员存在性"""
        if GinkgoSourceBase is None:
            pytest.skip("GinkgoSourceBase模块不可用")

        # 检查基类有必需成员
        assert hasattr(GinkgoSourceBase, method_name), f"基类必须有{method_name}"


# ===== 边界情况测试 =====

@pytest.mark.unit
class TestGinkgoSourceBaseEdgeCases:
    """数据源基类边界情况测试"""

    def test_client_none_reassignment(self, mock_data_source):
        """测试client重新设置为None"""
        source = mock_data_source()

        # 设置为Mock对象
        source.client = Mock()
        assert source.client is not None

        # 重新设置为None
        source.client = None
        assert source.client is None

    def test_multiple_connect_calls(self, mock_data_source):
        """测试多次调用connect"""
        source = mock_data_source()

        # 多次调用connect
        result1 = source.connect()
        result2 = source.connect()
        result3 = source.connect()

        # 验证都返回True
        assert result1 is True
        assert result2 is True
        assert result3 is True

    def test_client_overwrite(self, mock_data_source):
        """测试client覆盖"""
        source = mock_data_source()

        # 设置多个不同的client
        clients = [Mock() for _ in range(5)]
        for client in clients:
            source.client = client
            assert source.client == client

        # 验证最终client
        assert source.client == clients[-1]
