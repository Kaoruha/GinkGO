"""
DataSyncResult TDD测试用例
测试通用数据同步结果类的功能
"""

import pytest
from datetime import datetime

from ginkgo.libs.data.results import DataSyncResult

# 测试标记
pytest.mark.tdd
pytest.mark.unit


class TestDataSyncResultBasics:
    """DataSyncResult基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,31)),
            records_processed=100,
            records_added=80,
            records_updated=20,
            records_skipped=0,
            records_failed=0,
            sync_duration=2.5,
            is_idempotent=True,
            sync_strategy="incremental"
        )
        assert result.entity_type == "bars"
        assert result.entity_identifier == "000001.SZ"
        assert result.records_processed == 100
        assert result.is_successful() == True

    def test_success_rate_calculation(self):
        """测试成功率计算"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=100,
            records_added=60,
            records_updated=30,
            records_skipped=10,
            records_failed=0,
            sync_duration=1.0,
            is_idempotent=True,
            sync_strategy="incremental"
        )
        success_rate = result.get_success_rate()
        assert success_rate == 0.9  # (60+30)/100

    def test_error_detection(self):
        """测试错误检测"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=100,
            records_added=80,
            records_updated=10,
            records_skipped=0,
            records_failed=10,
            sync_duration=1.0,
            is_idempotent=False,
            sync_strategy="full"
        )
        assert result.has_errors() == True
        assert result.is_successful() == False

    def test_efficiency_score(self):
        """测试效率评分"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=100,
            records_added=50,
            records_updated=30,
            records_skipped=20,  # 高效幂等性
            records_failed=0,
            sync_duration=1.0,
            is_idempotent=True,
            sync_strategy="incremental"
        )
        efficiency = result.get_efficiency_score()
        assert efficiency == 84.0  # 成功率80% + 跳过比例20% * 20分 = 84分


class TestDataSyncResultStatistics:
    """DataSyncResult统计功能测试"""

    def test_get_total_changes(self):
        """测试获取总变更记录数"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=100,
            records_added=60,
            records_updated=30,
            records_skipped=10,
            records_failed=0,
            sync_duration=1.0,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        total_changes = result.get_total_changes()
        assert total_changes == 90  # 60 + 30

    def test_empty_sync_scenario(self):
        """测试空同步场景"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=0,
            records_added=0,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.1,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        assert result.get_success_rate() == 0.0
        assert result.get_total_changes() == 0
        assert result.get_efficiency_score() == 100.0


class TestDataSyncResultFinancialScenarios:
    """DataSyncResult金融场景测试"""

    def test_bars_incremental_sync(self):
        """测试Bars增量同步场景"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,31)),
            records_processed=22,
            records_added=0,
            records_updated=22,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.5,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        result.set_metadata("frequency", "DAY")
        result.set_metadata("trading_days", 22)
        result.set_metadata("update_type", "price_adjustment")

        assert result.get_success_rate() == 1.0
        assert result.is_successful() == True
        assert result.metadata["frequency"] == "DAY"

    def test_bars_batch_sync_efficiency(self):
        """测试Bars批量同步效率"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,12,31)),
            records_processed=2500,
            records_added=2500,
            records_updated=0,
            records_skipped=0,
            records_failed=0,
            sync_duration=5.2,
            is_idempotent=True,
            sync_strategy="full"
        )

        result.set_metadata("batch_size", 100)
        result.set_metadata("chunks", 25)
        result.set_metadata("data_source", "tushare")

        efficiency = result.get_efficiency_score()
        assert result.get_success_rate() == 1.0
        assert efficiency > 90.0
        assert result.metadata["batch_size"] == 100

    def test_ticks_high_frequency_sync(self):
        """测试Ticks高频数据同步"""
        result = DataSyncResult(
            entity_type="ticks",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,2)),
            records_processed=50000,
            records_added=45000,
            records_updated=5000,
            records_skipped=0,
            records_failed=0,
            sync_duration=12.3,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        result.set_metadata("tick_frequency", "1min")
        result.set_metadata("market", "SZSE")
        result.set_metadata("trading_session", "continuous")

        assert result.get_success_rate() == 1.0
        # 高频数据应该有合理的处理时间
        assert result.sync_duration < 30.0  # 应该在30秒内完成
        assert result.metadata["tick_frequency"] == "1min"

    def test_stockinfo_full_sync_metadata(self):
        """测试StockInfo全量同步元数据"""
        result = DataSyncResult(
            entity_type="stockinfo",
            entity_identifier="000001.SZ",
            sync_range=(None, None),
            records_processed=1,
            records_added=0,
            records_updated=1,
            records_skipped=0,
            records_failed=0,
            sync_duration=0.3,
            is_idempotent=True,
            sync_strategy="full"
        )

        result.set_metadata("info_type", "basic")
        result.set_metadata("update_source", "exchange")
        result.set_metadata("last_updated", datetime.now().isoformat())
        result.set_metadata("fields_updated", ["company_name", "industry", "market_cap"])

        assert result.get_total_changes() == 1
        assert result.metadata["info_type"] == "basic"
        assert "fields_updated" in result.metadata


class TestDataSyncResultEdgeCases:
    """DataSyncResult边界情况测试"""

    def test_extreme_error_ratio(self):
        """测试极端错误比例场景"""
        result = DataSyncResult(
            entity_type="ticks",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,2)),
            records_processed=1000,
            records_added=0,
            records_updated=0,
            records_skipped=0,
            records_failed=1000,  # 全部失败
            sync_duration=5.0,
            is_idempotent=False,
            sync_strategy="full"
        )

        # 添加详细错误信息
        for i in range(10):
            result.add_error(i, f"Data validation error: Invalid price at record {i*100}")

        assert result.has_errors() == True
        assert result.is_successful() == False
        assert result.get_success_rate() == 0.0
        assert result.get_efficiency_score() == 0.0  # 100%错误率
        assert len(result.errors) == 10


class TestDataSyncResultConversion:
    """DataSyncResult转换功能测试"""

    def test_to_dict_comprehensive(self):
        """测试完整的字典转换"""
        result = DataSyncResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,31)),
            records_processed=250,
            records_added=200,
            records_updated=30,
            records_skipped=15,
            records_failed=5,
            sync_duration=3.5,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        # 添加错误和警告
        result.add_error(100, "Invalid OHLC data")
        result.add_warning("High volatility detected")

        # 设置元数据
        result.set_metadata("frequency", "DAY")
        result.set_metadata("data_source", "tushare")

        result_dict = result.to_dict()

        # 验证所有字段都存在
        assert "entity_type" in result_dict
        assert "records_processed" in result_dict
        assert "success_rate" in result_dict
        assert "efficiency_score" in result_dict
        assert "is_successful" in result_dict
        assert "sync_range" in result_dict
        assert "metadata" in result_dict
        assert "errors" in result_dict
        assert "warnings" in result_dict

        # 验证具体值
        assert result_dict["entity_type"] == "bars"
        assert result_dict["success_rate"] == 0.92  # (200+30)/250
        assert result_dict["is_successful"] == False  # 有5个失败
        assert result_dict["metadata"]["frequency"] == "DAY"
        assert len(result_dict["errors"]) == 1


class TestDataSyncResultPerformance:
    """DataSyncResult性能测试"""

    def test_large_sync_result_creation(self):
        """测试大数据量同步结果创建性能"""
        import time
        start_time = time.time()

        result = DataSyncResult(
            entity_type="ticks",
            entity_identifier="000001.SZ",
            sync_range=(datetime(2024,1,1), datetime(2024,1,31)),
            records_processed=500000,  # 50万条记录
            records_added=400000,
            records_updated=80000,
            records_skipped=15000,
            records_failed=5000,
            sync_duration=25.7,
            is_idempotent=True,
            sync_strategy="incremental"
        )

        # 添加大量元数据
        for i in range(100):
            result.set_metadata(f"batch_{i}_status", "completed")
            result.set_metadata(f"batch_{i}_records", 5000)

        end_time = time.time()

        # 验证处理结果
        assert result.records_processed == 500000
        assert len(result.metadata) == 200  # 100 status + 100 records
        assert result.get_success_rate() == 0.96  # (400k+80k)/500k

        # 验证性能（应该快速完成）
        creation_time = end_time - start_time
        assert creation_time < 1.0  # 应该在1秒内完成创建

        # 验证内存效率（元数据应该正确存储）
        assert result.metadata["batch_0_status"] == "completed"
        assert result.metadata["batch_99_records"] == 5000