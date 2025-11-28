"""
DataIntegrityCheckResult TDD测试用例
测试通用数据完整性检查结果类的功能
"""

import pytest
from datetime import datetime

from ginkgo.libs.data.results import DataIntegrityCheckResult

# 测试标记
pytest.mark.tdd
pytest.mark.unit


class TestDataIntegrityCheckResultBasics:
    """DataIntegrityCheckResult基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        result = DataIntegrityCheckResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,12,31)),
            total_records=250,
            missing_records=5,
            duplicate_records=0,
            integrity_score=95.0,
            check_duration=1.2
        )
        assert result.entity_type == "bars"
        assert result.entity_identifier == "000001.SZ"
        assert result.total_records == 250
        assert result.integrity_score == 95.0
        assert result.is_healthy() == False  # 有缺失记录

    def test_healthy_case(self):
        """测试健康情况"""
        result = DataIntegrityCheckResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,12,31)),
            total_records=250,
            missing_records=0,
            duplicate_records=0,
            integrity_score=100.0,
            check_duration=1.0
        )
        assert result.is_healthy() == True

    def test_add_issue(self):
        """测试添加完整性问题"""
        result = DataIntegrityCheckResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,12,31)),
            total_records=250,
            missing_records=0,
            duplicate_records=0,
            integrity_score=100.0,
            check_duration=0.0
        )

        result.add_issue("missing_data", "2024-01-02 data missing")
        result.add_issue("duplicate_timestamp", "Duplicate at 2024-01-03 09:30")

        assert len(result.integrity_issues) == 2
        assert result.integrity_score < 100.0
        assert result.is_healthy() == False


class TestDataIntegrityCheckResultMetadata:
    """DataIntegrityCheckResult元数据管理测试"""

    def test_set_metadata(self):
        """测试设置元数据"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            check_duration=0.5
        )

        result.set_metadata("frequency", "DAY")
        result.set_metadata("trading_days_count", 22)
        result.set_metadata("missing_dates_count", 2)

        assert result.metadata["frequency"] == "DAY"
        assert result.metadata["trading_days_count"] == 22
        assert result.metadata["missing_dates_count"] == 2

    def test_integrity_score_recalculation(self):
        """测试完整性评分自动重新计算"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            check_duration=0.0
        )

        # 设置总记录数和缺失记录
        result.total_records = 250
        result.missing_records = 25  # 缺失10%

        # 手动触发重新计算
        result._recalculate_integrity_score()

        # 验证评分: 100 - (25/250)*50 = 95分
        expected_score = 100.0 - (25/250) * 50.0
        assert abs(result.integrity_score - expected_score) < 0.01


class TestDataIntegrityCheckResultFactory:
    """DataIntegrityCheckResult工厂方法测试"""

    def test_create_for_entity(self):
        """测试为实体创建完整性检查结果"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,12,31)),
            check_duration=1.0
        )

        assert result.entity_type == "bars"
        assert result.entity_identifier == "000001.SZ"
        assert result.total_records == 0
        assert result.missing_records == 0
        assert result.duplicate_records == 0
        assert result.integrity_score == 100.0
        assert result.is_healthy() == True


class TestDataIntegrityCheckResultConversion:
    """DataIntegrityCheckResult转换功能测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = DataIntegrityCheckResult(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            total_records=250,
            missing_records=5,
            duplicate_records=2,
            integrity_score=92.0,
            check_duration=1.5
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["entity_type"] == "bars"
        assert result_dict["entity_identifier"] == "000001.SZ"
        assert result_dict["total_records"] == 250
        assert result_dict["missing_records"] == 5
        assert result_dict["duplicate_records"] == 2
        assert result_dict["integrity_score"] == 92.0
        assert result_dict["is_healthy"] == False
        assert "check_range" in result_dict


class TestDataIntegrityCheckResultFinancialScenarios:
    """DataIntegrityCheckResult金融场景测试"""

    def test_bars_missing_trading_days(self):
        """测试Bars缺失交易日场景"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            check_duration=1.2
        )

        # 模拟交易日缺失
        result.missing_records = 5  # 缺失5个交易日
        result.total_records = 17  # 22个交易日 - 5个缺失
        result.add_recommendation("Check data source for 2024-01-15 trading holiday")
        result.add_recommendation("Verify market closure dates")

        result.set_metadata("expected_trading_days", 22)
        result.set_metadata("actual_trading_days", 17)
        result.set_metadata("missing_dates", ["2024-01-15", "2024-01-22", "2024-01-29"])

        assert result.missing_records == 5
        assert len(result.recommendations) == 2
        assert result.is_healthy() == False
        assert result.metadata["missing_dates"][0] == "2024-01-15"

    def test_bars_duplicate_timestamps(self):
        """测试Bars重复时间戳场景"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            check_duration=0.8
        )

        # 模拟重复时间戳
        result.duplicate_records = 3
        result.total_records = 25  # 包含重复记录

        result.add_issue("duplicate_timestamp", "Duplicate record at 2024-01-02")
        result.add_issue("duplicate_timestamp", "Duplicate record at 2024-01-03")

        result.set_metadata("duplicate_timestamps", ["2024-01-02", "2024-01-03"])
        result.set_metadata("frequency", "DAY")

        assert result.duplicate_records == 3
        assert len(result.integrity_issues) == 2
        assert result.integrity_score < 100.0
        assert result.metadata["frequency"] == "DAY"


class TestDataIntegrityCheckResultEdgeCases:
    """DataIntegrityCheckResult边界情况测试"""

    def test_empty_data_scenario(self):
        """测试空数据场景"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,31)),
            check_duration=0.1
        )

        # 空数据情况
        result.total_records = 22  # 期望的记录数
        result.missing_records = 22  # 所有交易日都缺失

        # 手动触发评分计算
        result._recalculate_integrity_score()

        assert result.total_records == 22
        assert result.missing_records == 22
        assert result.is_healthy() == False  # 缺失记录，不健康
        assert result.integrity_score < 100.0

    def test_extreme_performance_scenario(self):
        """测试极端性能场景"""
        result = DataIntegrityCheckResult.create_for_entity(
            entity_type="ticks",
            entity_identifier="000001.SZ",
            check_range=(datetime(2024,1,1), datetime(2024,1,2)),
            check_duration=0.0
        )

        # 模拟大量数据的完整性检查
        import time
        start_time = time.time()

        result.total_records = 1000000  # 100万条tick记录
        result.missing_records = 50
        result.duplicate_records = 10

        # 添加一些完整性问题
        for i in range(100):
            result.add_issue("timestamp_gap", f"Gap detected around {datetime(2024,1,1,9,i%60)}")

        end_time = time.time()

        # 验证处理结果
        assert result.total_records == 1000000
        assert len(result.integrity_issues) == 100
        assert result.duplicate_records == 10

        # 验证性能（应该快速完成）
        processing_time = end_time - start_time
        assert processing_time < 2.0  # 应该在2秒内完成

        # 验证检查耗时设置
        result.check_duration = processing_time
        assert 0 < result.check_duration < 2.0