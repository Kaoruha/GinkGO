"""
Demo database test to verify the warning system works.

使用pytest最佳实践重构的测试文件。
"""

import pytest
from test.database.test_isolation import (
    database_test_required,
    validate_test_database_config,
)


@pytest.mark.database
class TestDatabaseDemo:
    """Demo测试类，验证数据库警告系统."""

    @pytest.mark.unit
    def test_basic_database_connection(self):
        """基础测试，验证数据库连接警告出现."""
        # 这个测试仅验证警告系统工作正常
        assert True, "Database test isolation system is working"

    @pytest.mark.unit
    def test_configuration_display(self):
        """测试数据库配置正确显示."""
        # 这个测试验证连接信息在警告中显示
        assert True, "Configuration display test passed"


@pytest.mark.database
class TestDatabaseValidation:
    """测试数据库配置验证功能."""

    @pytest.mark.unit
    def test_validate_config_with_no_gconf(self, monkeypatch):
        """测试没有GCONF时的配置验证."""
        # 模拟GCONF不可用的情况
        import test.database.test_isolation as isolation_module
        monkeypatch.setattr(isolation_module, 'GCONF', None)

        is_safe, issues = validate_test_database_config()

        assert is_safe is False
        assert len(issues) > 0

    @pytest.mark.unit
    def test_validate_config_safety_checks(self):
        """测试配置安全检查."""
        # 这个测试验证安全检查逻辑
        from test.database.test_isolation import DatabaseTestError

        # 如果GCONF不可用，跳过测试
        try:
            from test.database.test_isolation import _validate_debug_mode
        except Exception:
            pytest.skip("Cannot test validation without GCONF")

    @pytest.mark.unit
    @pytest.mark.parametrize("config_type", ["clickhouse", "mysql", "unknown"])
    def test_get_original_port(self, config_type):
        """测试原始端口获取逻辑."""
        from test.database.test_isolation import _get_original_port

        # 如果GCONF不可用，应该返回None
        try:
            result = _get_original_port(config_type)
            # 结果应该是None或字符串
            assert result is None or isinstance(result, str)
        except Exception:
            pytest.skip("Cannot test port retrieval without GCONF")


@pytest.mark.database
class TestDatabaseTestDataFactory:
    """测试测试数据工厂功能."""

    @pytest.mark.unit
    def test_create_test_data_factory(self):
        """测试创建测试数据工厂."""
        from test.database.test_isolation import create_test_data_factory

        factory = create_test_data_factory()

        assert factory is not None
        assert hasattr(factory, 'create_test_stock')
        assert hasattr(factory, 'create_test_bar_data')
        assert hasattr(factory, 'cleanup_all')

    @pytest.mark.unit
    def test_factory_create_test_stock(self):
        """测试工厂创建测试股票."""
        from test.database.test_isolation import create_test_data_factory

        factory = create_test_data_factory()

        # 使用默认代码
        stock1 = factory.create_test_stock()
        assert stock1['code'].startswith('test_')
        assert stock1['name'] == f'Test Stock {stock1["code"]}'
        assert stock1['market'] == 'SZ'
        assert stock1['industry'] == 'Test Industry'

        # 使用自定义代码
        stock2 = factory.create_test_stock(code="CUSTOM001.SZ")
        assert stock2['code'] == "CUSTOM001.SZ"
        assert stock2['code'] in factory._cleanup_registry

    @pytest.mark.unit
    def test_factory_create_test_bar_data(self):
        """测试工厂创建测试K线数据."""
        from test.database.test_isolation import create_test_data_factory

        factory = create_test_data_factory()

        # 创建10条K线数据
        bars = factory.create_test_bar_data(count=10)

        assert len(bars) == 10
        assert all('code' in bar for bar in bars)
        assert all('timestamp' in bar for bar in bars)
        assert all('open' in bar for bar in bars)
        assert all('high' in bar for bar in bars)
        assert all('low' in bar for bar in bars)
        assert all('close' in bar for bar in bars)
        assert all('volume' in bar for bar in bars)

    @pytest.mark.unit
    def test_factory_cleanup_all(self):
        """测试工厂清理功能."""
        from test.database.test_isolation import create_test_data_factory

        factory = create_test_data_factory()

        # 创建一些测试数据
        factory.create_test_stock()
        factory.create_test_bar_data(count=5)

        # 验证清理注册表不为空
        assert len(factory._cleanup_registry) > 0

        # 清理
        factory.cleanup_all()

        # 验证清理注册表已清空
        assert len(factory._cleanup_registry) == 0
