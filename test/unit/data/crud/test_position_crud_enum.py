#!/usr/bin/env python3
"""
PositionCRUD枚举处理测试

测试PositionCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- 持仓查询中的枚举处理
- 数据源枚举的转换
- 持仓管理相关的枚举处理
"""

import pytest
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.position_crud import PositionCRUD
from ginkgo.data.models.model_position import MPosition
from ginkgo.trading.entities import Position
from ginkgo.enums import SOURCE_TYPES

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestPositionCRUDEnum(BaseEnumCRUDTest):
    """PositionCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回PositionCRUD类"""
        return PositionCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回Position模型的测试数据"""
        return {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000,
            "available_volume": 800,
            "avg_price": 10.50,
            "current_price": 11.00,
            "market_value": 11000.0,
            "unrealized_pnl": 500.0,
            "source": SOURCE_TYPES.TUSHARE
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回PositionCRUD预期的枚举字段映射"""
        return {
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_source_enum_conversions(self):
        """测试数据源枚举转换"""
        # 测试所有主要数据源
        test_sources = [
            SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO,
            SOURCE_TYPES.AKSHARE, SOURCE_TYPES.BAOSTOCK, SOURCE_TYPES.TDX
        ]

        for source in test_sources:
            converted = self.crud_instance._normalize_single_enum_value(
                source, SOURCE_TYPES, "source"
            )
            assert converted == source.value, f"数据源 {source} 应该转换为对应的整数值"

        # 测试int值保持不变
        int_source = SOURCE_TYPES.TUSHARE.value
        converted_int = self.crud_instance._normalize_single_enum_value(
            int_source, SOURCE_TYPES, "source"
        )
        assert converted_int == int_source, "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_position_query_with_source_enum(self):
        """测试持仓查询中的数据源枚举处理"""
        # 场景1：查询特定数据源的持仓
        tushare_positions_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.TUSHARE
        }

        converted_filters = self.crud_instance._convert_enum_values(tushare_positions_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "数据源枚举应该转换"

        # 场景2：查询多数据源的持仓
        multi_source_positions_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]
        }

        converted_filters = self.crud_instance._convert_enum_values(multi_source_positions_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"
        expected_sources = [SOURCE_TYPES.TUSHARE.value, SOURCE_TYPES.YAHOO.value, SOURCE_TYPES.AKSHARE.value]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_position_creation_enum_validation(self):
        """测试持仓创建时的枚举字段验证"""
        # 测试使用枚举对象创建持仓
        enum_position_data = {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000,
            "available_volume": 800,
            "avg_price": 10.50,
            "current_price": 11.00,
            "market_value": 11000.0,
            "unrealized_pnl": 500.0,
            "source": SOURCE_TYPES.AKSHARE  # 枚举对象
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_position_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["source"] == SOURCE_TYPES.AKSHARE.value, \
            "AKShare数据源应该转换为int值"

        # 测试使用int值创建持仓
        int_position_data = {
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000,
            "available_volume": 800,
            "avg_price": 10.50,
            "current_price": 11.00,
            "market_value": 11000.0,
            "unrealized_pnl": 500.0,
            "source": SOURCE_TYPES.YAHOO.value  # int值
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_position_data.copy())

        # 验证int值保持不变
        assert validated_data["source"] == SOURCE_TYPES.YAHOO.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_portfolio_position_analysis(self):
        """测试投资组合持仓分析中的枚举处理"""
        # 场景1：分析不同数据源的持仓质量
        quality_analysis_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO],
            "volume__gte": 100,
            "market_value__gte": 10000.0
        }

        converted_filters = self.crud_instance._convert_enum_values(quality_analysis_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"
        assert converted_filters["source__in"] == [SOURCE_TYPES.TUSHARE.value, SOURCE_TYPES.YAHOO.value], \
            "高质量数据源应该正确转换"

        # 场景2：查找特定数据源的持仓
        source_specific_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.SIM,
            "unrealized_pnl__lt": -1000.0  # 亏损持仓
        }

        converted_filters = self.crud_instance._convert_enum_values(source_specific_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value, "模拟数据源应该转换"

    @pytest.mark.enum
    def test_position_risk_monitoring(self):
        """测试持仓风险监控中的枚举处理"""
        # 场景1：监控高风险持仓（特定数据源）
        risk_monitoring_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.TUSHARE,  # 只监控真实数据源
            "available_volume__lt": 500,  # 可用数量较少
            "unrealized_pnl__lt": -500.0  # 亏损较多
        }

        converted_filters = self.crud_instance._convert_enum_values(risk_monitoring_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "真实数据源应该转换"

        # 场景2：多数据源风险对比
        risk_comparison_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE],
            "volume__gt": 0  # 只要有持仓的
        }

        converted_filters = self.crud_instance._convert_enum_values(risk_comparison_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

    @pytest.mark.enum
    def test_position_performance_analysis(self):
        """测试持仓绩效分析中的枚举处理"""
        # 场景1：分析最佳表现持仓（按数据源）
        performance_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.TUSHARE,
            "unrealized_pnl__gte": 1000.0,  # 盈利较多
            "volume__gte": 500  # 持仓量较大
        }

        converted_filters = self.crud_instance._convert_enum_values(performance_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 场景2：跨数据源绩效对比
        cross_source_performance_filters = {
            "portfolio_id": "test_portfolio",
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE],
            "market_value__gte": 5000.0
        }

        converted_filters = self.crud_instance._convert_enum_values(cross_source_performance_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 验证数据源列表
        expected_sources = [s.value for s in [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_position_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("PositionCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("PositionCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("PositionCRUD")

        # 验证生成的测试数据包含必要的枚举字段
        assert "source" in test_filters, "测试过滤器应该包含source字段"
        assert "source" in test_model_data, "测试模型数据应该包含source字段"

        # PositionCRUD只有一个枚举字段，组合测试应该有基本的数据
        assert len(combination_tests) >= 1, "应该至少生成1个组合测试"
        for combination in combination_tests:
            assert "source" in combination, "组合测试应该包含source字段"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("PositionCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_position_data_integrity(self):
        """测试持仓数据的完整性（涉及枚举字段）"""
        # 场景1：验证数据源一致性
        consistency_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.TUSHARE,
            "volume__gt": 0,
            "market_value__gt": 0
        }

        converted_filters = self.crud_instance._convert_enum_values(consistency_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 场景2：检查缺失数据源
        missing_source_filters = {
            "portfolio_id": "test_portfolio",
            "source__ne": SOURCE_TYPES.SIM,  # 排除模拟数据
            "current_price": None  # 当前价格为空
        }

        converted_filters = self.crud_instance._convert_enum_filters(missing_source_filters, "source")
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value, "数据源应该转换"

    @pytest.mark.enum
    def test_invalid_position_enum_handling(self):
        """测试无效持仓枚举值的处理"""
        # 测试无效的数据源值
        invalid_source_filters = {"source": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_source_filters)

        assert converted_filters["source"] == 999, "无效的数据源值应该保留原样"

        # 测试包含无效值的查询
        mixed_source_filters = {
            "portfolio_id": "test_portfolio",
            "source": SOURCE_TYPES.TUSHARE,  # 有效枚举
            "volume": 1000
        }

        # 添加无效的字段（非枚举字段）
        mixed_source_filters["invalid_field"] = 999

        converted_filters = self.crud_instance._convert_enum_values(mixed_source_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        # 有效枚举应该转换，无效字段应该保持原样
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "有效枚举应该转换"
        assert "invalid_field" not in converted_filters, "无效字段应该被过滤掉（因为没有对应的模型字段）"

    @pytest.mark.enum
    def test_position_batch_operations_with_enums(self):
        """测试批量持仓操作中的枚举处理"""
        # 创建包含不同数据源的持仓数据列表
        batch_position_data = [
            {
                "portfolio_id": "test_portfolio",
                "code": "000001.SZ",
                "volume": 1000,
                "source": SOURCE_TYPES.TUSHARE  # 枚举对象
            },
            {
                "portfolio_id": "test_portfolio",
                "code": "000002.SZ",
                "volume": 500,
                "source": SOURCE_TYPES.YAHOO.value  # int值
            },
            {
                "portfolio_id": "test_portfolio",
                "code": "000003.SZ",
                "volume": 800,
                "source": SOURCE_TYPES.AKSHARE  # 枚举对象
            }
        ]

        # 测试批量转换
        converted_batch = []
        for position_data in batch_position_data:
            validated_data = self.crud_instance._validate_item_enum_fields(position_data.copy())
            converted_batch.append(validated_data)

        # 验证批量转换结果
        assert len(converted_batch) == 3, "应该转换3个持仓记录"

        expected_sources = [
            SOURCE_TYPES.TUSHARE.value,
            SOURCE_TYPES.YAHOO.value,
            SOURCE_TYPES.AKSHARE.value
        ]

        for i, expected_source in enumerate(expected_sources):
            assert converted_batch[i]["source"] == expected_source, \
                f"第{i+1}个持仓的数据源应该正确转换为{expected_source}"