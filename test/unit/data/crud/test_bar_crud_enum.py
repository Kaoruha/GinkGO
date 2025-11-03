#!/usr/bin/env python3
"""
BarCRUD枚举处理测试

测试BarCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- K线数据查询中的枚举处理
- 数据源和频率枚举的转换
- 时序数据相关的枚举处理
"""

import pytest
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.bar_crud import BarCRUD
from ginkgo.data.models.model_bar import MBar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestBarCRUDEnum(BaseEnumCRUDTest):
    """BarCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回BarCRUD类"""
        return BarCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回Bar模型的测试数据"""
        return {
            "code": "000001.SZ",
            "timestamp": datetime.now(),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000000,
            "frequency": FREQUENCY_TYPES.DAY,
            "source": SOURCE_TYPES.TUSHARE
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回BarCRUD预期的枚举字段映射"""
        return {
            'frequency': FREQUENCY_TYPES,
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_frequency_enum_conversions(self):
        """测试频率枚举转换"""
        # 测试日线频率
        daily_frequency = FREQUENCY_TYPES.DAY
        converted_daily = self.crud_instance._normalize_single_enum_value(
            daily_frequency, FREQUENCY_TYPES, "frequency"
        )
        assert converted_daily == FREQUENCY_TYPES.DAY.value, "日线频率应该转换为对应的整数值"

        # 测试分钟线频率
        minute_frequency = FREQUENCY_TYPES.MIN1
        converted_minute = self.crud_instance._normalize_single_enum_value(
            minute_frequency, FREQUENCY_TYPES, "frequency"
        )
        assert converted_minute == FREQUENCY_TYPES.MIN1.value, "分钟线频率应该转换为对应的整数值"

        # 测试int值保持不变
        int_daily = FREQUENCY_TYPES.DAY.value
        converted_int = self.crud_instance._normalize_single_enum_value(
            int_daily, FREQUENCY_TYPES, "frequency"
        )
        assert converted_int == int_daily, "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_source_enum_for_bar_data(self):
        """测试K线数据的数据源枚举"""
        # 测试主要数据源
        main_sources = [
            SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE
        ]

        for source in main_sources:
            converted = self.crud_instance._normalize_single_enum_value(
                source, SOURCE_TYPES, "source"
            )
            assert converted == source.value, f"数据源 {source} 应该转换为对应的整数值"

        # 测试数据源查询
        source_filters = {
            "source__in": [
                SOURCE_TYPES.TUSHARE,
                SOURCE_TYPES.YAHOO,
                1  # SIM的int值
            ]
        }

        converted_filters = self.crud_instance._convert_enum_values(source_filters)
        expected_values = [
            SOURCE_TYPES.TUSHARE.value,
            SOURCE_TYPES.YAHOO.value,
            1  # int值保持不变
        ]

        assert converted_filters["source__in"] == expected_values, \
            "数据源过滤器中的枚举值应该正确转换"

    @pytest.mark.enum
    def test_bar_data_query_scenarios(self):
        """测试K线数据查询场景"""
        # 场景1：查询日线数据
        daily_bar_filters = {
            "code": "000001.SZ",
            "frequency": FREQUENCY_TYPES.DAY,
            "source": SOURCE_TYPES.TUSHARE
        }

        converted_filters = self.crud_instance._convert_enum_values(daily_bar_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["frequency"] == FREQUENCY_TYPES.DAY.value, "日线频率应该转换"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "数据源应该转换"

        # 场景2：查询多数据源的分钟线数据
        minute_bar_filters = {
            "code": "000001.SZ",
            "frequency": FREQUENCY_TYPES.MIN1,
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE, SOURCE_TYPES.SIM]
        }

        converted_filters = self.crud_instance._convert_enum_values(minute_bar_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["frequency"] == FREQUENCY_TYPES.MIN1.value, "分钟线频率应该转换"
        assert len(converted_filters["source__in"]) == 3, "数据源列表应该包含3个元素"

    @pytest.mark.enum
    def test_time_series_enum_queries(self):
        """测试时序数据的枚举查询"""
        # 测试时间范围查询结合枚举过滤
        time_range_filters = {
            "code": "000001.SZ",
            "timestamp__gte": "2023-01-01",
            "timestamp__lte": "2023-12-31",
            "frequency": FREQUENCY_TYPES.DAY,
            "source": SOURCE_TYPES.YAHOO
        }

        converted_filters = self.crud_instance._convert_enum_values(time_range_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        # 应该有5个条件：code, timestamp_gte, timestamp_lte, frequency, source
        assert len(conditions) == 5, "应该生成5个查询条件"

        # 验证枚举字段转换
        assert converted_filters["frequency"] == FREQUENCY_TYPES.DAY.value
        assert converted_filters["source"] == SOURCE_TYPES.YAHOO.value

        # 测试复杂的多频率查询
        multi_frequency_filters = {
            "code": "000001.SZ",
            "frequency__in": [FREQUENCY_TYPES.DAY, FREQUENCY_TYPES.MIN1],
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE]
        }

        converted_filters = self.crud_instance._convert_enum_values(multi_frequency_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件（code, frequency__in, source__in）"

    @pytest.mark.enum
    def test_bar_creation_enum_validation(self):
        """测试K线数据创建时的枚举字段验证"""
        # 测试使用枚举对象创建K线数据
        enum_bar_data = {
            "code": "000001.SZ",
            "timestamp": datetime.now(),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000000,
            "frequency": FREQUENCY_TYPES.MIN1,  # 枚举对象
            "source": SOURCE_TYPES.AKSHARE  # 枚举对象
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_bar_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["frequency"] == FREQUENCY_TYPES.MIN1.value, \
            "分钟线频率应该转换为int值"
        assert validated_data["source"] == SOURCE_TYPES.AKSHARE.value, \
            "AKShare数据源应该转换为int值"

        # 测试使用int值创建K线数据
        int_bar_data = {
            "code": "000001.SZ",
            "timestamp": datetime.now(),
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000000,
            "frequency": FREQUENCY_TYPES.DAY.value,  # int值
            "source": SOURCE_TYPES.TUSHARE.value  # int值
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_bar_data.copy())

        # 验证int值保持不变
        assert validated_data["frequency"] == FREQUENCY_TYPES.DAY.value, \
            "有效的int值应该保持不变"
        assert validated_data["source"] == SOURCE_TYPES.TUSHARE.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_data_quality_enum_scenarios(self):
        """测试数据质量相关的枚举场景"""
        # 场景1：查询高质量数据源的日线数据
        quality_daily_filters = {
            "frequency": FREQUENCY_TYPES.DAY,
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO],
            "volume__gte": 100000  # 成交量过滤
        }

        converted_filters = self.crud_instance._convert_enum_values(quality_daily_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 场景2：查询特定数据源的所有频率数据
        all_frequency_filters = {
            "source": SOURCE_TYPES.TUSHARE,
            "frequency__in": [FREQUENCY_TYPES.DAY, FREQUENCY_TYPES.MIN1]
        }

        converted_filters = self.crud_instance._convert_enum_values(all_frequency_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 验证频率列表转换
        expected_frequencies = [FREQUENCY_TYPES.DAY.value, FREQUENCY_TYPES.MIN1.value]
        assert converted_filters["frequency__in"] == expected_frequencies, \
            "频率列表应该正确转换"

    @pytest.mark.enum
    def test_enum_combination_analysis(self):
        """测试枚举组合分析场景"""
        # 测试所有频率和数据源的组合
        all_frequencies = [FREQUENCY_TYPES.DAY, FREQUENCY_TYPES.MIN1]
        all_sources = [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]

        combination_count = 0
        for freq in all_frequencies:
            for source in all_sources:
                combination_filters = {
                    "frequency": freq,
                    "source": source,
                    "code": "000001.SZ"
                }

                converted_filters = self.crud_instance._convert_enum_values(combination_filters)
                conditions = self.crud_instance._parse_filters(converted_filters)

                assert len(conditions) == 3, f"组合 {freq.name}+{source.name} 应该生成3个条件"
                assert converted_filters["frequency"] == freq.value, "频率应该转换为int值"
                assert converted_filters["source"] == source.value, "数据源应该转换为int值"

                combination_count += 1

        assert combination_count == 6, "应该测试6种组合（2频率 × 3数据源）"

    @pytest.mark.enum
    def test_bar_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("BarCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("BarCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("BarCRUD")

        # 验证生成的测试数据包含所有必要的枚举字段
        expected_fields = ['frequency', 'source']
        for field in expected_fields:
            assert field in test_filters, f"测试过滤器应该包含字段: {field}"
            assert field in test_model_data, f"测试模型数据应该包含字段: {field}"

        # 验证组合测试数据
        assert len(combination_tests) > 0, "应该生成组合测试数据"
        for combination in combination_tests:
            for field in expected_fields:
                assert field in combination, f"组合测试应该包含字段: {field}"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("BarCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_invalid_bar_enum_handling(self):
        """测试无效K线枚举值的处理"""
        # 测试无效的频率值
        invalid_frequency_filters = {"frequency": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_frequency_filters)

        assert converted_filters["frequency"] == 999, "无效的频率值应该保留原样"

        # 测试无效的数据源值
        invalid_source_filters = {"source": -1}
        converted_filters = self.crud_instance._convert_enum_values(invalid_source_filters)

        assert converted_filters["source"] == -1, "无效的数据源值应该保留原样"

        # 测试包含无效值的组合查询
        mixed_enum_filters = {
            "frequency": FREQUENCY_TYPES.DAY,  # 有效枚举
            "source": 999,  # 无效int
            "volume__gte": 100000
        }

        converted_filters = self.crud_instance._convert_enum_values(mixed_enum_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["frequency"] == FREQUENCY_TYPES.DAY.value, \
            "有效枚举应该转换"
        assert converted_filters["source"] == 999, "无效int应该保留原样"