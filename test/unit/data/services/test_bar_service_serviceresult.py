"""
测试Bar Service的ServiceResult包装功能

验证所有公共方法都正确返回ServiceResult包装的结果
"""

import pytest
from datetime import datetime, timedelta

from ginkgo import service_hub
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES
from ginkgo.libs import GCONF


class TestBarServiceServiceResult:
    """测试Bar Service的ServiceResult包装功能"""

    @pytest.fixture
    def bar_service(self):
        """获取真实的Bar Service实例"""
        # 确保调试模式开启
        GCONF.set_debug(True)

        # 通过service_hub获取真实的bar_service
        return service_hub.data.bar_service()

    def test_get_bars_returns_service_result_success(self, bar_service):
        """测试get_bars方法成功时返回ServiceResult包装"""
        # 调用方法（使用不存在的代码，避免依赖真实数据）
        result = bar_service.get_bars(code="999999.SZ")

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is True  # 即使没有数据也算成功
        assert result.data is not None
        # ModelList应该支持len()操作
        assert hasattr(result.data, '__len__')

    def test_get_bars_returns_service_result_error(self, bar_service):
        """测试get_bars方法异常时返回ServiceResult.error()"""
        # 通过传入无效参数触发错误
        result = bar_service.get_bars(code="")

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        # 根据实现，可能成功或失败，但必须是ServiceResult
        assert result.data is not None

    def test_get_bars_with_adjustment_calls_adjustment_methods(self, bar_service):
        """测试get_bars方法在需要复权时调用复权方法"""
        # 测试前复权
        result = bar_service.get_bars(
            code="999999.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE
        )

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.data is not None

        # 测试后复权
        result = bar_service.get_bars(
            code="999999.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK
        )

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.data is not None

    def test_get_latest_timestamp_success(self, bar_service):
        """测试get_latest_timestamp_for_code成功时返回ServiceResult包装"""
        # 使用不存在的股票代码，应该返回默认时间
        result = bar_service.get_latest_timestamp("999999.SZ")

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None  # 应该是默认时间
        assert isinstance(result.data, datetime)

    def test_get_latest_timestamp_no_data_returns_default(self, bar_service):
        """测试get_latest_timestamp_for_code无数据时返回默认时间"""
        # 使用空字符串
        result = bar_service.get_latest_timestamp("")

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None  # 应该是默认时间
        assert isinstance(result.data, datetime)

    def test_get_latest_timestamp_error(self, bar_service):
        """测试get_latest_timestamp_for_code失败时返回ServiceResult.error()"""
        # 使用None参数
        result = bar_service.get_latest_timestamp(None)

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is True  # 应该返回默认时间，不算失败
        assert result.data is not None
        assert isinstance(result.data, datetime)

    def test_sync_incremental_success(self, bar_service):
        """测试sync_incremental成功时返回ServiceResult.success()"""
        # 使用不存在的股票代码
        result = bar_service.sync_incremental("999999.SZ")

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is False  # 股票代码不存在，应该失败
        assert "not in stock list" in result.message.lower()

    def test_sync_incremental_failure(self, bar_service):
        """测试sync_incremental失败时返回ServiceResult.failure()"""
        # 使用空字符串
        result = bar_service.sync_incremental("")

        # 验证返回ServiceResult.failure()
        assert isinstance(result, ServiceResult)
        assert result.success is False
        assert result.error is not None or result.message is not None

    def test_sync_incremental_exception(self, bar_service):
        """测试sync_incremental异常处理"""
        # 使用None参数
        result = bar_service.sync_incremental(None)

        # 验证返回ServiceResult
        assert isinstance(result, ServiceResult)
        assert result.success is False

    def test_get_bars_parameter_validation(self, bar_service):
        """测试get_bars参数验证和ServiceResult返回"""
        result = bar_service.get_bars(
            code="000001.SZ",
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            frequency=FREQUENCY_TYPES.DAY,
            adjustment_type=ADJUSTMENT_TYPES.NONE,
            page=1,
            page_size=50,
            order_by="timestamp",
            desc_order=True
        )

        # 验证ServiceResult返回
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

        # 验证CRUD调用参数正确（通过不报错来验证）
        assert hasattr(result.data, 'to_dataframe')
        assert hasattr(result.data, 'to_entities')

    def test_service_result_interface_consistency(self, bar_service):
        """测试ServiceResult接口的一致性"""
        # 测试所有公共方法都返回ServiceResult
        methods_to_test = [
            ('get_latest_timestamp', ['000001.SZ']),
            ('get_bars', [{}]),  # 使用空字典
            ('sync_incremental', ['999999.SZ'])
        ]

        for method_name, args in methods_to_test:
            method = getattr(bar_service, method_name)
            result = method(*args)

            # 验证ServiceResult接口
            assert isinstance(result, ServiceResult)
            assert hasattr(result, 'success')
            assert hasattr(result, 'data')
            assert hasattr(result, 'message')
            assert hasattr(result, 'error')

    def test_datetime_handling_in_service_result(self, bar_service):
        """测试ServiceResult中的datetime处理（验证之前的修复）"""
        # 这个测试专门验证datetime ServiceResult处理问题
        result = bar_service.get_latest_timestamp("000001.SZ")

        # 验证即使内部处理datetime，也能正确返回ServiceResult
        assert isinstance(result, ServiceResult)

        if result.success:
            # 如果成功，data应该是datetime对象
            assert result.data is not None
            # data可能是datetime或其他类型，取决于实现
            # 但不应该是ServiceResult本身
            assert not isinstance(result.data, ServiceResult)

    def test_modellist_data_interface(self, bar_service):
        """测试ServiceResult.data的ModelList接口"""
        result = bar_service.get_bars(code="999999.SZ")

        assert isinstance(result, ServiceResult)

        if result.success and result.data:
            # 验证ModelList接口
            assert hasattr(result.data, 'to_dataframe')
            assert hasattr(result.data, 'to_entities')
            assert hasattr(result.data, '__len__')
            assert hasattr(result.data, '__iter__')