"""
ServiceHub基础功能测试

测试ServiceHub的基本功能，包括：
- 初始化和配置
- 模块访问和懒加载
- 错误处理和诊断
- 性能监控和缓存
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock


class TestServiceHubBasics:
    """ServiceHub基础功能测试"""

    def test_servicehub_initialization(self):
        """测试ServiceHub初始化"""
        from ginkgo.service_hub import ServiceHub, ServiceHubError

        # 基本初始化
        hub = ServiceHub()

        # 检查基本属性
        assert hasattr(hub, '_module_errors')
        assert hasattr(hub, '_debug_mode')
        assert hasattr(hub, '_performance_stats')
        assert hasattr(hub, '_start_time')
        assert hasattr(hub, '_module_cache')

        # 检查初始状态
        assert hub._debug_mode is False
        assert len(hub._module_errors) == 0
        assert len(hub._performance_stats) == 0
        assert len(hub._module_cache) == 0
        assert hub.get_uptime() > 0

    def test_servicehub_debug_mode(self):
        """测试ServiceHub调试模式"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 默认关闭调试模式
        assert hub._debug_mode is False

        # 启用调试模式
        hub.enable_debug()
        assert hub._debug_mode is True

        # 禁用调试模式
        hub.disable_debug()
        assert hub._debug_mode is False

    def test_servicehub_data_module_access(self):
        """测试数据模块访问"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 访问data模块
        data_module = hub.data

        # 验证data模块不为空
        assert data_module is not None
        # 验证data模块有必要的属性
        assert hasattr(data_module, 'cruds')
        assert hasattr(data_module, 'services')

        # 验证缓存生效
        assert 'data' in hub._module_cache
        # 再次访问应该返回同一个对象
        data_module2 = hub.data
        assert data_module is data_module2

    @patch('ginkgo.service_hub.time.perf_counter')
    def test_servicehub_performance_stats(self, mock_perf_counter):
        """测试ServiceHub性能统计"""
        from ginkgo.service_hub import ServiceHub

        # 设置时间模拟
        start_time = 1000.0
        load_time = 1000.1
        mock_perf_counter.side_effect = [start_time, load_time, load_time]

        hub = ServiceHub()

        # 访问data模块触发性能统计
        _ = hub.data

        # 验证性能统计
        stats = hub.get_performance_stats()
        assert 'uptime' in stats
        assert 'total_errors' in stats
        assert 'cached_modules' in stats
        assert 'module_performance' in stats

        # 验证data模块的性能统计
        if 'data' in stats['module_performance']:
            data_stats = stats['module_performance']['data']
            assert 'load_time' in data_stats
            assert 'last_access' in data_stats

    def test_servicehub_cache_management(self):
        """测试ServiceHub缓存管理"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 初始状态缓存为空
        assert len(hub._module_cache) == 0

        # 访问模块触发缓存
        _ = hub.data
        assert len(hub._module_cache) == 1
        assert 'data' in hub._module_cache

        # 清理特定模块缓存
        hub.clear_cache('data')
        assert len(hub._module_cache) == 0

        # 重新访问
        _ = hub.data
        assert len(hub._module_cache) == 1

        # 清理所有缓存
        hub.clear_cache()
        assert len(hub._module_cache) == 0

    def test_servicehub_module_status(self):
        """测试ServiceHub模块状态"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 获取模块状态
        status = hub.get_module_status()

        # 验证状态结构
        assert isinstance(status, dict)

        # 至少应该包含data模块
        assert 'data' in status

        # 验证data模块状态
        data_status = status['data']
        assert 'available' in data_status
        assert 'type' in data_status
        assert 'error' in data_status
        assert 'cached' in data_status
        assert 'load_time' in data_status

        # data模块应该是可用的
        assert data_status['available'] is True
        assert data_status['error'] is None

    def test_servicehub_available_modules(self):
        """测试ServiceHub可用模块列表"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 获取可用模块列表
        available_modules = hub.list_available_modules()

        # 验证返回类型
        assert isinstance(available_modules, list)

        # data模块应该总是可用
        assert 'data' in available_modules

    @patch('ginkgo.service_hub.ServiceHub.data')
    def test_servicehub_error_handling(self, mock_data):
        """测试ServiceHub错误处理"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()
        hub.enable_debug()

        # 模拟data模块访问错误
        mock_data.side_effect = Exception("Test error")

        # 访问data模块应该返回None并记录错误
        result = hub.data
        assert result is None
        assert 'data' in hub._module_errors
        assert "Test error" in hub._module_errors['data']

    def test_servicehub_diagnose_issues(self):
        """测试ServiceHub问题诊断"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 正常情况下应该没有问题
        issues = hub.diagnose_issues()
        assert isinstance(issues, list)
        # 正常情况下应该为空列表
        # 如果有不可用模块，会返回问题列表

    def test_servicehub_uptime_calculation(self):
        """测试ServiceHub运行时间计算"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 获取运行时间
        uptime = hub.get_uptime()

        # 验证返回类型和合理性
        assert isinstance(uptime, float)
        assert uptime >= 0
        # 应该非常小（刚创建）
        assert uptime < 1.0

    @patch('ginkgo.service_hub.importlib.import_module')
    def test_servicehub_lazy_loading(self, mock_import):
        """测试ServiceHub懒加载机制"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 模拟trading模块导入
        mock_trading_module = Mock()
        mock_import.return_value = mock_trading_module

        # 第一次访问trading模块
        trading1 = hub.trading
        assert trading1 is mock_trading_module

        # 验证import被调用
        mock_import.assert_called()

        # 重置mock
        mock_import.reset_mock()

        # 第二次访问应该使用缓存
        trading2 = hub.trading
        assert trading2 is trading1

        # import不应该再被调用
        mock_import.assert_not_called()

    def test_servicehub_concurrent_access_safety(self):
        """测试ServiceHub并发访问安全性"""
        from ginkgo.service_hub import ServiceHub
        import threading

        hub = ServiceHub()
        results = []

        def access_data():
            try:
                data = hub.data
                results.append(data is not None)
            except Exception as e:
                results.append(False)

        # 创建多个线程同时访问
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=access_data)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有访问都成功
        assert len(results) == 10
        assert all(results)

        # 验证缓存中只有一个data实例
        assert len(hub._module_cache) == 1
        assert 'data' in hub._module_cache


class TestServiceHubErrorHandling:
    """ServiceHub错误处理测试"""

    def test_servicehub_import_error_handling(self):
        """测试导入错误处理"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()
        hub.enable_debug()

        # 测试不存在的模块
        with patch('ginkgo.service_hub.importlib.import_module') as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            # 尝试访问不存在的模块属性
            result = getattr(hub, 'nonexistent_module', None)
            # 应该返回None或抛出适当的异常
            # 这取决于ServiceHub的实现

    def test_servicehub_attribute_error_handling(self):
        """测试属性错误处理"""
        from ginkgo.service_hub import ServiceHub

        hub = ServiceHub()

        # 测试访问不存在的属性
        with pytest.raises(AttributeError):
            _ = hub.nonexistent_property

    def test_servicehub_type_validation(self):
        """测试ServiceHub类型验证"""
        from ginkgo.service_hub import ServiceHub, ServiceHubError

        hub = ServiceHub()

        # 验证ServiceHub类型
        assert isinstance(hub, ServiceHub)

        # 验证ServiceHubError异常类型
        assert issubclass(ServiceHubError, Exception)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])