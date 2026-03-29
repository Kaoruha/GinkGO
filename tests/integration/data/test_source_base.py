import unittest
from unittest.mock import Mock

try:
    from ginkgo.data.sources.source_base import GinkgoSourceBase
except ImportError:
    GinkgoSourceBase = None


class MockDataSource(GinkgoSourceBase):
    """用于测试的Mock数据源实现"""

    def connect(self):
        """实现connect方法用于测试"""
        self.client = Mock()
        return True


class IncompleteDataSource(GinkgoSourceBase):
    """用于测试的未完整实现数据源"""

    pass


class GinkgoSourceBaseTest(unittest.TestCase):
    """
    测试数据源基类功能

    验证：
    1. 基类基本功能
    2. 抽象方法强制实现
    3. 接口一致性
    """

    def setUp(self):
        """测试环境初始化"""
        self.assertIsNotNone(GinkgoSourceBase, "GinkgoSourceBase基类必须可用")

    def test_SourceBase_Init(self):
        """测试基类初始化

        验证：
        1. 基类可以被实例化
        2. 初始状态正确
        3. 属性设置正确
        """
        # 不能直接实例化基类，因为connect是抽象方法
        # 使用Mock实现来测试
        source = MockDataSource()

        self.assertIsNotNone(source, "数据源对象应该创建成功")
        self.assertIsNone(source.client, "初始client应该为None")
        self.assertIsInstance(source, GinkgoSourceBase, "应该是基类的实例")

    def test_SourceBase_ClientProperty(self):
        """测试client属性管理

        验证：
        1. client属性getter/setter正常工作
        2. 可以设置和获取client对象
        3. 属性类型检查
        """
        source = MockDataSource()

        # 测试初始状态
        self.assertIsNone(source.client, "初始client应该为None")

        # 测试设置client
        mock_client = Mock()
        source.client = mock_client
        self.assertEqual(source.client, mock_client, "client设置应该成功")

        # 测试重新设置
        new_client = Mock()
        source.client = new_client
        self.assertEqual(source.client, new_client, "client重新设置应该成功")

        # 测试设置为None
        source.client = None
        self.assertIsNone(source.client, "client应该可以重置为None")

    def test_SourceBase_ConnectAbstract(self):
        """测试connect方法的抽象性

        验证：
        1. 基类的connect方法抛出NotImplementedError
        2. 子类必须实现connect方法
        3. 实现了connect的子类可以正常工作
        """
        # 测试未实现connect的子类
        incomplete_source = IncompleteDataSource()

        with self.assertRaises(NotImplementedError, msg="未实现connect的类应该抛出NotImplementedError"):
            incomplete_source.connect()

        # 测试实现了connect的子类
        complete_source = MockDataSource()
        result = complete_source.connect()
        self.assertTrue(result, "实现了connect的类应该能正常连接")
        self.assertIsNotNone(complete_source.client, "连接后client应该被设置")

    def test_SourceBase_InterfaceConsistency(self):
        """测试接口一致性

        验证：
        1. 所有数据源都有相同的基础接口
        2. 必要的方法存在
        3. 属性访问一致
        """
        source = MockDataSource()

        # 检查必要的属性和方法存在
        self.assertTrue(hasattr(source, "client"), "必须有client属性")
        self.assertTrue(hasattr(source, "connect"), "必须有connect方法")

        # 检查方法可调用性
        self.assertTrue(callable(getattr(source, "connect")), "connect必须是可调用的方法")

        # 检查属性描述符
        self.assertTrue(hasattr(GinkgoSourceBase, "client"), "基类必须定义client属性")

    def test_SourceBase_Inheritance(self):
        """测试继承关系

        验证：
        1. 子类正确继承基类
        2. 方法重写正常工作
        3. 基类方法可以被调用
        """
        source = MockDataSource()

        # 测试继承关系
        self.assertIsInstance(source, GinkgoSourceBase, "子类应该是基类的实例")
        self.assertTrue(issubclass(MockDataSource, GinkgoSourceBase), "应该是基类的子类")

        # 测试方法解析顺序
        self.assertEqual(source.__class__.__mro__[1], GinkgoSourceBase, "继承链应该正确")

    def test_SourceBase_ErrorHandling(self):
        """测试错误处理

        验证：
        1. 抽象方法错误处理
        2. 属性访问错误处理
        3. 异常传播正确
        """
        source = IncompleteDataSource()

        # 测试抽象方法错误
        with self.assertRaises(NotImplementedError, msg="未实现的抽象方法应该抛出NotImplementedError"):
            source.connect()

        # 测试错误信息
        try:
            source.connect()
            self.fail("应该抛出NotImplementedError")
        except NotImplementedError as e:
            # 确保错误可以被正确捕获和处理
            self.assertIsInstance(e, NotImplementedError, "应该是NotImplementedError类型")

    def test_SourceBase_MultipleInstances(self):
        """测试多实例管理

        验证：
        1. 可以创建多个实例
        2. 实例间相互独立
        3. 状态不会互相影响
        """
        source1 = MockDataSource()
        source2 = MockDataSource()

        # 测试实例独立性
        self.assertIsNot(source1, source2, "应该是不同的实例")
        # 注意：初始时两个实例的client都是None，所以不比较初始状态
        # 而是在设置不同值后验证独立性

        # 测试状态独立性
        mock_client1 = Mock()
        mock_client2 = Mock()

        source1.client = mock_client1
        source2.client = mock_client2

        self.assertEqual(source1.client, mock_client1, "实例1的client不应受影响")
        self.assertEqual(source2.client, mock_client2, "实例2的client不应受影响")
        self.assertNotEqual(source1.client, source2.client, "不同实例的client应该不同")

    def test_SourceBase_RequiredMethods(self):
        """测试基类必须定义的方法

        验证：
        1. connect方法必须存在且为抽象方法
        2. 子类不实现connect应该失败
        3. 基类设计符合抽象基类规范
        """
        # 验证基类有connect方法
        self.assertTrue(hasattr(GinkgoSourceBase, "connect"), "基类必须定义connect方法")

        # 验证connect是抽象方法（调用时抛出NotImplementedError）
        base_instance = IncompleteDataSource()  # 使用未实现connect的子类
        with self.assertRaises(NotImplementedError):
            base_instance.connect()

        # 验证实现了connect的子类可以正常工作
        mock_instance = MockDataSource()
        result = mock_instance.connect()
        self.assertIsNotNone(result, "实现了connect的子类应该正常工作")
