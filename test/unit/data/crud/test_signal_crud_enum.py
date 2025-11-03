#!/usr/bin/env python3
"""
SignalCRUD枚举处理测试

测试SignalCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- 交易信号查询中的枚举处理
- 方向和数据源枚举的转换
- 策略信号相关的枚举处理
"""

import pytest
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.signal_crud import SignalCRUD
from ginkgo.data.models.model_signal import MSignal
from ginkgo.trading.entities import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestSignalCRUDEnum(BaseEnumCRUDTest):
    """SignalCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回SignalCRUD类"""
        return SignalCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回Signal模型的测试数据"""
        return {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "timestamp": datetime.now(),
            "source": SOURCE_TYPES.TUSHARE,
            "price": 10.50,
            "volume": 1000,
            "weight": 0.1
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回SignalCRUD预期的枚举字段映射"""
        return {
            'direction': DIRECTION_TYPES,
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_direction_enum_conversions(self):
        """测试交易方向枚举转换"""
        # 测试多头信号
        long_signal = DIRECTION_TYPES.LONG
        converted_long = self.crud_instance._normalize_single_enum_value(
            long_signal, DIRECTION_TYPES, "direction"
        )
        assert converted_long == DIRECTION_TYPES.LONG.value, "多头信号应该转换为对应的整数值"

        # 测试空头信号
        short_signal = DIRECTION_TYPES.SHORT
        converted_short = self.crud_instance._normalize_single_enum_value(
            short_signal, DIRECTION_TYPES, "direction"
        )
        assert converted_short == DIRECTION_TYPES.SHORT.value, "空头信号应该转换为对应的整数值"

        # 测试int值保持不变
        int_long = DIRECTION_TYPES.LONG.value
        converted_int = self.crud_instance._normalize_single_enum_value(
            int_long, DIRECTION_TYPES, "direction"
        )
        assert converted_int == int_long, "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_source_enum_for_signals(self):
        """测试信号数据源枚举"""
        # 测试主要信号数据源
        main_sources = [
            SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO
        ]

        for source in main_sources:
            converted = self.crud_instance._normalize_single_enum_value(
                source, SOURCE_TYPES, "source"
            )
            assert converted == source.value, f"信号数据源 {source} 应该转换为对应的整数值"

        # 测试信号数据源查询
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
            "信号数据源过滤器中的枚举值应该正确转换"

    @pytest.mark.enum
    def test_signal_query_scenarios(self):
        """测试交易信号查询场景"""
        # 场景1：查询多头信号
        long_signal_filters = {
            "portfolio_id": "test_portfolio",
            "direction": DIRECTION_TYPES.LONG,
            "source": SOURCE_TYPES.TUSHARE
        }

        converted_filters = self.crud_instance._convert_enum_values(long_signal_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["direction"] == DIRECTION_TYPES.LONG.value, "多头方向应该转换"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "数据源应该转换"

        # 场景2：查询特定时间范围的空头信号
        short_signal_filters = {
            "portfolio_id": "test_portfolio",
            "direction": DIRECTION_TYPES.SHORT,
            "timestamp__gte": "2023-01-01",
            "timestamp__lte": "2023-12-31",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO]
        }

        converted_filters = self.crud_instance._convert_enum_values(short_signal_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 5, "应该生成5个查询条件"
        assert converted_filters["direction"] == DIRECTION_TYPES.SHORT.value, "空头方向应该转换"

    @pytest.mark.enum
    def test_strategy_signal_analysis(self):
        """测试策略信号分析中的枚举处理"""
        # 场景1：分析多头/空头信号比例
        signal_analysis_filters = {
            "portfolio_id": "test_portfolio",
            "timestamp__gte": "2023-01-01",
            "source": SOURCE_TYPES.TUSHARE
        }

        # 查询多头信号
        long_filters = signal_analysis_filters.copy()
        long_filters["direction"] = DIRECTION_TYPES.LONG

        converted_long = self.crud_instance._convert_enum_values(long_filters)
        assert converted_long["direction"] == DIRECTION_TYPES.LONG.value, "多头方向应该转换"

        # 查询空头信号
        short_filters = signal_analysis_filters.copy()
        short_filters["direction"] = DIRECTION_TYPES.SHORT

        converted_short = self.crud_instance._convert_enum_values(short_filters)
        assert converted_short["direction"] == DIRECTION_TYPES.SHORT.value, "空头方向应该转换"

        # 场景2：多数据源信号质量分析
        quality_analysis_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE],
            "volume__gte": 100,  # 最小交易量
            "weight__gte": 0.05  # 最小权重
        }

        converted_filters = self.crud_instance._convert_enum_values(quality_analysis_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 5, "应该生成5个查询条件"

        # 验证数据源列表转换
        expected_sources = [s.value for s in [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_signal_creation_enum_validation(self):
        """测试信号创建时的枚举字段验证"""
        # 测试使用枚举对象创建信号
        enum_signal_data = {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.SHORT,  # 枚举对象
            "timestamp": datetime.now(),
            "source": SOURCE_TYPES.AKSHARE,  # 枚举对象
            "price": 10.50,
            "volume": 1000,
            "weight": 0.1
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_signal_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["direction"] == DIRECTION_TYPES.SHORT.value, \
            "空头方向应该转换为int值"
        assert validated_data["source"] == SOURCE_TYPES.AKSHARE.value, \
            "AKShare数据源应该转换为int值"

        # 测试使用int值创建信号
        int_signal_data = {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG.value,  # int值
            "timestamp": datetime.now(),
            "source": SOURCE_TYPES.TUSHARE.value,  # int值
            "price": 10.50,
            "volume": 1000,
            "weight": 0.1
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_signal_data.copy())

        # 验证int值保持不变
        assert validated_data["direction"] == DIRECTION_TYPES.LONG.value, \
            "有效的int值应该保持不变"
        assert validated_data["source"] == SOURCE_TYPES.TUSHARE.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_signal_backtesting_scenarios(self):
        """测试回测场景中的信号枚举处理"""
        # 场景1：回测期间的信号查询
        backtesting_filters = {
            "portfolio_id": "test_portfolio",
            "timestamp__gte": "2023-01-01",
            "timestamp__lte": "2023-12-31",
            "direction": DIRECTION_TYPES.LONG,
            "source": SOURCE_TYPES.SIM  # 回测使用模拟数据源
        }

        converted_filters = self.crud_instance._convert_enum_values(backtesting_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 5, "应该生成5个查询条件"
        assert converted_filters["direction"] == DIRECTION_TYPES.LONG.value, "多头方向应该转换"
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value, "模拟数据源应该转换"

        # 场景2：多策略信号对比
        strategy_comparison_filters = {
            "portfolio_id": "test_portfolio",
            "direction__in": [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT],
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO],
            "weight__gte": 0.1  # 高权重信号
        }

        converted_filters = self.crud_instance._convert_enum_values(strategy_comparison_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 验证方向列表转换
        expected_directions = [DIRECTION_TYPES.LONG.value, DIRECTION_TYPES.SHORT.value]
        assert converted_filters["direction__in"] == expected_directions, "方向列表应该正确转换"

    @pytest.mark.enum
    def test_signal_performance_evaluation(self):
        """测试信号绩效评估中的枚举处理"""
        # 场景1：评估不同方向信号的绩效
        performance_evaluation_filters = {
            "portfolio_id": "test_portfolio",
            "timestamp__gte": "2023-01-01",
            "source": SOURCE_TYPES.TUSHARE,  # 只评估真实数据源的信号
            "volume__gte": 100
        }

        # 评估多头信号绩效
        long_performance = performance_evaluation_filters.copy()
        long_performance["direction"] = DIRECTION_TYPES.LONG

        converted_long = self.crud_instance._convert_enum_values(long_performance)
        assert converted_long["direction"] == DIRECTION_TYPES.LONG.value, "多头方向应该转换"

        # 评估空头信号绩效
        short_performance = performance_evaluation_filters.copy()
        short_performance["direction"] = DIRECTION_TYPES.SHORT

        converted_short = self.crud_instance._convert_enum_values(short_performance)
        assert converted_short["direction"] == DIRECTION_TYPES.SHORT.value, "空头方向应该转换"

        # 场景2：多数据源信号准确性对比
        accuracy_comparison_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE],
            "weight__gte": 0.05  # 只考虑有足够权重的信号
        }

        converted_filters = self.crud_instance._convert_enum_values(accuracy_comparison_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

    @pytest.mark.enum
    def test_signal_risk_management(self):
        """测试信号风险管理中的枚举处理"""
        # 场景1：监控高频信号（可能过度交易）
        high_frequency_filters = {
            "portfolio_id": "test_portfolio",
            "direction": DIRECTION_TYPES.LONG,
            "source": SOURCE_TYPES.TUSHARE,
            "timestamp__gte": datetime.now().strftime("%Y-%m-%d"),  # 今日信号
            "volume__gte": 1000  # 大额信号
        }

        converted_filters = self.crud_instance._convert_enum_values(high_frequency_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 5, "应该生成5个查询条件"

        # 场景2：检测信号方向突变
        direction_change_filters = {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "source": SOURCE_TYPES.TUSHARE,
            "direction__in": [DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT],
            "timestamp__gte": "2023-01-01"
        }

        converted_filters = self.crud_instance._convert_enum_values(direction_change_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 验证方向列表
        expected_directions = [DIRECTION_TYPES.LONG.value, DIRECTION_TYPES.SHORT.value]
        assert converted_filters["direction__in"] == expected_directions, "方向列表应该正确转换"

    @pytest.mark.enum
    def test_signal_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("SignalCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("SignalCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("SignalCRUD")

        # 验证生成的测试数据包含所有必要的枚举字段
        expected_fields = ['direction', 'source']
        for field in expected_fields:
            assert field in test_filters, f"测试过滤器应该包含字段: {field}"
            assert field in test_model_data, f"测试模型数据应该包含字段: {field}"

        # 验证组合测试数据
        assert len(combination_tests) > 0, "应该生成组合测试数据"
        for combination in combination_tests:
            for field in expected_fields:
                assert field in combination, f"组合测试应该包含字段: {field}"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("SignalCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_signal_batch_operations_with_enums(self):
        """测试批量信号操作中的枚举处理"""
        # 创建包含不同方向和数据源的信号数据列表
        batch_signal_data = [
            {
                "portfolio_id": "test_portfolio",
                "code": "000001.SZ",
                "direction": DIRECTION_TYPES.LONG,  # 枚举对象
                "source": SOURCE_TYPES.TUSHARE,
                "weight": 0.1
            },
            {
                "portfolio_id": "test_portfolio",
                "code": "000002.SZ",
                "direction": DIRECTION_TYPES.SHORT.value,  # int值
                "source": SOURCE_TYPES.YAHOO,  # 枚举对象
                "weight": 0.15
            },
            {
                "portfolio_id": "test_portfolio",
                "code": "000003.SZ",
                "direction": DIRECTION_TYPES.LONG,  # 枚举对象
                "source": SOURCE_TYPES.AKSHARE.value,  # int值
                "weight": 0.08
            }
        ]

        # 测试批量转换
        converted_batch = []
        for signal_data in batch_signal_data:
            validated_data = self.crud_instance._validate_item_enum_fields(signal_data.copy())
            converted_batch.append(validated_data)

        # 验证批量转换结果
        assert len(converted_batch) == 3, "应该转换3个信号记录"

        expected_directions = [
            DIRECTION_TYPES.LONG.value,
            DIRECTION_TYPES.SHORT.value,
            DIRECTION_TYPES.LONG.value
        ]

        expected_sources = [
            SOURCE_TYPES.TUSHARE.value,
            SOURCE_TYPES.YAHOO.value,
            SOURCE_TYPES.AKSHARE.value
        ]

        for i, (expected_dir, expected_src) in enumerate(zip(expected_directions, expected_sources)):
            assert converted_batch[i]["direction"] == expected_dir, \
                f"第{i+1}个信号的方向应该正确转换为{expected_dir}"
            assert converted_batch[i]["source"] == expected_src, \
                f"第{i+1}个信号的数据源应该正确转换为{expected_src}"

    @pytest.mark.enum
    def test_invalid_signal_enum_handling(self):
        """测试无效信号枚举值的处理"""
        # 测试无效的方向值
        invalid_direction_filters = {"direction": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_direction_filters)

        assert converted_filters["direction"] == 999, "无效的方向值应该保留原样"

        # 测试无效的数据源值
        invalid_source_filters = {"source": -1}
        converted_filters = self.crud_instance._convert_enum_values(invalid_source_filters)

        assert converted_filters["source"] == -1, "无效的数据源值应该保留原样"

        # 测试包含无效值的复杂查询
        mixed_signal_filters = {
            "portfolio_id": "test_portfolio",
            "direction": DIRECTION_TYPES.LONG,  # 有效枚举
            "source": 999,  # 无效int
            "weight__gte": 0.1
        }

        converted_filters = self.crud_instance._convert_enum_values(mixed_signal_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["direction"] == DIRECTION_TYPES.LONG.value, \
            "有效枚举应该转换"
        assert converted_filters["source"] == 999, "无效int应该保留原样"