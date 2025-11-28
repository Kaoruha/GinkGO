"""
DataValidationResult TDD测试用例
测试通用数据验证结果类的功能
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

from ginkgo.libs.data.results import DataValidationResult

# 测试标记
pytest.mark.tdd
pytest.mark.unit


class TestDataValidationResultBasics:
    """DataValidationResult基础功能测试"""

    def test_default_constructor(self):
        """测试默认构造函数"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )
        assert result.is_valid == True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.data_quality_score == 100.0
        assert result.entity_type == "bars"
        assert result.entity_identifier == "000001.SZ"

    def test_initialization_with_errors(self):
        """测试包含错误的初始化"""
        errors = ["OHLC relationship violation", "Negative price detected"]
        result = DataValidationResult(
            is_valid=False,
            error_count=2,
            warning_count=0,
            data_quality_score=80.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ",
            errors=errors
        )
        assert result.is_valid == False
        assert result.error_count == 2
        assert len(result.errors) == 2
        assert "OHLC relationship violation" in result.errors

    def test_initialization_with_warnings(self):
        """测试包含警告的初始化"""
        warnings = ["High volatility detected", "Unusual volume spike"]
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=2,
            data_quality_score=96.0,
            validation_timestamp=datetime.now(),
            validation_type="data_quality",
            entity_type="bars",
            entity_identifier="000001.SZ",
            warnings=warnings
        )
        assert result.is_valid == True
        assert result.warning_count == 2
        assert len(result.warnings) == 2
        assert "High volatility detected" in result.warnings


class TestDataValidationResultErrorManagement:
    """DataValidationResult错误管理测试"""

    def test_add_error_increases_count(self):
        """测试添加错误增加计数"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 添加第一个错误
        result.add_error("OHLC relationship violation")
        assert result.error_count == 1
        assert len(result.errors) == 1
        assert result.data_quality_score == 90.0

        # 添加第二个错误
        result.add_error("Negative price detected")
        assert result.error_count == 2
        assert len(result.errors) == 2
        assert result.data_quality_score == 80.0

    def test_add_warning_increases_count(self):
        """测试添加警告增加计数"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="data_quality",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 添加第一个警告
        result.add_warning("High volatility detected")
        assert result.warning_count == 1
        assert len(result.warnings) == 1
        assert result.data_quality_score == 98.0

        # 添加第二个警告
        result.add_warning("Unusual volume spike")
        assert result.warning_count == 2
        assert len(result.warnings) == 2
        assert result.data_quality_score == 96.0

    def test_quality_score_recalculation(self):
        """测试质量评分自动重新计算"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 混合添加错误和警告
        result.add_error("OHLC violation")           # -10分
        result.add_warning("High volatility")        # -2分
        result.add_error("Negative price")           # -10分
        result.add_warning("Unusual volume")         # -2分

        # 验证最终评分: 100 - 10 - 2 - 10 - 2 = 76
        assert result.error_count == 2
        assert result.warning_count == 2
        assert result.data_quality_score == 76.0


class TestDataValidationResultMetadata:
    """DataValidationResult元数据管理测试"""

    def test_set_metadata(self):
        """测试设置元数据"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 设置不同类型的元数据
        result.set_metadata("frequency", "DAY")
        result.set_metadata("market", "SZSE")
        result.set_metadata("record_count", 1000)
        result.set_metadata("is_trading_day", True)

        assert result.metadata["frequency"] == "DAY"
        assert result.metadata["market"] == "SZSE"
        assert result.metadata["record_count"] == 1000
        assert result.metadata["is_trading_day"] == True
        assert len(result.metadata) == 4

    def test_bars_specific_metadata(self):
        """测试Bars特定元数据"""
        result = DataValidationResult(
            is_valid=False,
            error_count=2,
            warning_count=0,
            data_quality_score=80.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 设置Bars特定元数据
        result.set_metadata("ohlc_violations", ["High < max(Open, Close)"])
        result.set_metadata("frequency", "DAY")
        result.set_metadata("trading_day", "2024-01-02")
        result.set_metadata("market", "SZSE")

        assert "ohlc_violations" in result.metadata
        assert result.metadata["frequency"] == "DAY"
        assert len(result.metadata["ohlc_violations"]) == 1


class TestDataValidationResultFactory:
    """DataValidationResult工厂方法测试"""

    def test_create_for_entity(self):
        """测试为实体创建验证结果"""
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="business_rules"
        )

        assert result.is_valid == True
        assert result.error_count == 0
        assert result.warning_count == 0
        assert result.data_quality_score == 100.0
        assert result.entity_type == "bars"
        assert result.entity_identifier == "000001.SZ"
        assert result.validation_type == "business_rules"

    def test_create_with_different_validation_types(self):
        """测试不同验证类型的创建"""
        # 测试business_rules类型
        result1 = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="business_rules"
        )
        assert result1.validation_type == "business_rules"

        # 测试data_quality类型
        result2 = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="data_quality"
        )
        assert result2.validation_type == "data_quality"

        # 测试integrity类型
        result3 = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="integrity"
        )
        assert result3.validation_type == "integrity"


class TestDataValidationResultConversion:
    """DataValidationResult转换功能测试"""

    def test_to_dict(self):
        """测试转换为字典"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["is_valid"] == True
        assert result_dict["entity_type"] == "bars"
        assert result_dict["entity_identifier"] == "000001.SZ"
        assert "validation_timestamp" in result_dict

    def test_dict_contains_all_fields(self):
        """测试字典包含所有必要字段"""
        result = DataValidationResult(
            is_valid=False,
            error_count=2,
            warning_count=1,
            data_quality_score=78.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ",
            errors=["OHLC violation", "Negative price"],
            warnings=["High volatility"],
            metadata={"frequency": "DAY"}
        )

        result_dict = result.to_dict()

        # 验证基础字段
        assert "is_valid" in result_dict
        assert "error_count" in result_dict
        assert "warning_count" in result_dict
        assert "data_quality_score" in result_dict
        assert "validation_timestamp" in result_dict
        assert "validation_type" in result_dict
        assert "entity_type" in result_dict
        assert "entity_identifier" in result_dict

        # 验证列表字段
        assert "errors" in result_dict
        assert "warnings" in result_dict
        assert "metadata" in result_dict

        # 验证具体值
        assert result_dict["is_valid"] == False
        assert result_dict["error_count"] == 2
        assert result_dict["entity_type"] == "bars"
        assert len(result_dict["errors"]) == 2
        assert result_dict["metadata"]["frequency"] == "DAY"


class TestDataValidationResultEdgeCases:
    """DataValidationResult边界情况测试"""

    def test_negative_quality_score(self):
        """测试负质量评分的边界处理"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 添加大量错误使评分低于0
        for i in range(15):  # 15个错误，扣150分
            result.add_error(f"Error {i}")

        # 验证评分不低于0
        assert result.error_count == 15
        assert result.data_quality_score == 0.0  # 边界处理，不低于0

    def test_quality_score_above_100(self):
        """测试质量评分超过100的边界处理"""
        # 创建一个初始评分为100的结果，验证重新计算时不超过100
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 验证初始评分
        assert result.data_quality_score == 100.0

        # 添加少量错误和警告，然后重新验证边界
        result.add_error("Single error")  # 扣10分
        assert result.data_quality_score == 90.0

        # 验证评分不会超过100（由于_recalculate_quality_score中已有边界处理）
        # 这个测试主要验证现有实现不会产生>100的评分
        assert result.data_quality_score <= 100.0

    def test_multiple_error_addition(self):
        """测试多次添加错误"""
        result = DataValidationResult(
            is_valid=True,
            error_count=0,
            warning_count=0,
            data_quality_score=100.0,
            validation_timestamp=datetime.now(),
            validation_type="business_rules",
            entity_type="bars",
            entity_identifier="000001.SZ"
        )

        # 多次添加错误
        errors = ["First error", "Second error", "Third error"]
        for error in errors:
            result.add_error(error)

        # 验证错误计数和列表长度一致
        assert result.error_count == 3
        assert len(result.errors) == 3
        assert result.errors == errors
        assert result.data_quality_score == 70.0  # 100 - 3*10


class TestDataValidationResultFinancialScenarios:
    """DataValidationResult金融场景测试"""

    def test_bars_ohlc_violation(self):
        """测试Bars OHLC关系违规场景"""
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="business_rules"
        )

        # 模拟OHLC关系验证
        result.add_error("OHLC relationship violation: High < max(Open, Close) at 2024-01-02")
        result.add_error("OHLC relationship violation: Low > min(Open, Close) at 2024-01-03")

        # 设置Bars特定的OHLC违规元数据
        result.set_metadata("ohlc_violations", [
            "High < max(Open, Close) at 2024-01-02",
            "Low > min(Open, Close) at 2024-01-03"
        ])
        result.set_metadata("frequency", "DAY")
        result.set_metadata("affected_records", 2)

        assert result.error_count == 2
        assert result.data_quality_score == 80.0
        assert len(result.metadata["ohlc_violations"]) == 2
        assert result.metadata["affected_records"] == 2

    def test_bars_price_validation(self):
        """测试Bars价格验证场景"""
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="business_rules"
        )

        # 模拟价格合理性检查
        result.add_error("Negative price detected: Close = -1.25 at 2024-01-02")
        result.add_warning("Unusual price jump: +50% in one day at 2024-01-03")

        result.set_metadata("price_issues", ["negative_price", "unusual_jump"])
        result.set_metadata("frequency", "DAY")

        assert result.error_count == 1
        assert result.warning_count == 1
        assert result.data_quality_score == 88.0  # 100 - 10 - 2

    def test_ticks_timestamp_validation(self):
        """测试Ticks时间戳验证场景"""
        result = DataValidationResult.create_for_entity(
            entity_type="ticks",
            entity_identifier="000001.SZ",
            validation_type="business_rules"
        )

        # 模拟时间戳唯一性检查
        result.add_error("Duplicate timestamp: 2024-01-02 09:30:00 appears 3 times")
        result.add_error("Timestamp out of order: 2024-01-02 09:29:00 after 09:30:00")

        result.set_metadata("timestamp_issues", ["duplicates", "out_of_order"])
        result.set_metadata("tick_frequency", "1min")

        assert result.error_count == 2
        assert result.data_quality_score == 80.0


class TestDataValidationResultPerformance:
    """DataValidationResult性能测试"""

    def test_large_error_list_handling(self):
        """测试大量错误的处理性能"""
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="data_quality"
        )

        # 添加大量错误
        import time
        start_time = time.time()

        for i in range(1000):
            result.add_error(f"Data quality issue {i}: Missing field at record {i}")

        end_time = time.time()

        # 验证处理结果
        assert result.error_count == 1000
        assert len(result.errors) == 1000
        assert result.data_quality_score == 0.0  # 边界处理

        # 验证性能（应该在合理时间内完成）
        processing_time = end_time - start_time
        assert processing_time < 1.0  # 应该在1秒内完成

    def test_metadata_memory_efficiency(self):
        """测试元数据内存效率"""
        result = DataValidationResult.create_for_entity(
            entity_type="bars",
            entity_identifier="000001.SZ",
            validation_type="integrity"
        )

        # 添加大量元数据
        for i in range(100):
            result.set_metadata(f"validation_rule_{i}", f"Rule description {i}")
            result.set_metadata(f"check_timestamp_{i}", datetime.now().isoformat())

        # 验证元数据存储
        assert len(result.metadata) == 200  # 100 rules + 100 timestamps
        assert result.metadata["validation_rule_0"] == "Rule description 0"
        assert result.metadata["validation_rule_99"] == "Rule description 99"