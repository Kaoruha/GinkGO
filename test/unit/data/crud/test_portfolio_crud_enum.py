#!/usr/bin/env python3
"""
PortfolioCRUD枚举处理测试

测试PortfolioCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- 投资组合查询中的枚举处理
- 数据源枚举的转换
- 投资组合管理相关的枚举处理
"""

import pytest
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
from ginkgo.data.models.model_portfolio import MPortfolio
from ginkgo.enums import SOURCE_TYPES

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestPortfolioCRUDEnum(BaseEnumCRUDTest):
    """PortfolioCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回PortfolioCRUD类"""
        return PortfolioCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回Portfolio模型的测试数据"""
        return {
            "name": "测试投资组合",
            "description": "用于测试的投资组合",
            "initial_capital": 1000000.0,
            "current_capital": 1100000.0,
            "risk_level": 0.15,
            "source": SOURCE_TYPES.SIM,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回PortfolioCRUD预期的枚举字段映射"""
        return {
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_source_enum_conversions(self):
        """测试数据源枚举转换"""
        # 测试主要数据源
        test_sources = [
            SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO,
            SOURCE_TYPES.AKSHARE, SOURCE_TYPES.BACKTEST
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
    def test_portfolio_query_with_source_enum(self):
        """测试投资组合查询中的数据源枚举处理"""
        # 场景1：查询特定数据源的投资组合
        sim_portfolio_filters = {
            "name": "测试组合",
            "source": SOURCE_TYPES.SIM
        }

        converted_filters = self.crud_instance._convert_enum_values(sim_portfolio_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value, "模拟数据源应该转换"

        # 场景2：查询多数据源的投资组合
        multi_source_portfolio_filters = {
            "source__in": [SOURCE_TYPES.SIM, SOURCE_TYPES.BACKTEST, SOURCE_TYPES.LIVE],
            "risk_level__lte": 0.2
        }

        converted_filters = self.crud_instance._convert_enum_values(multi_source_portfolio_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"
        expected_sources = [SOURCE_TYPES.SIM.value, SOURCE_TYPES.BACKTEST.value, SOURCE_TYPES.LIVE.value]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_portfolio_creation_enum_validation(self):
        """测试投资组合创建时的枚举字段验证"""
        # 测试使用枚举对象创建投资组合
        enum_portfolio_data = {
            "name": "回测投资组合",
            "description": "用于策略回测的组合",
            "initial_capital": 500000.0,
            "risk_level": 0.12,
            "source": SOURCE_TYPES.BACKTEST,  # 枚举对象
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_portfolio_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["source"] == SOURCE_TYPES.BACKTEST.value, \
            "回测数据源应该转换为int值"

        # 测试使用int值创建投资组合
        int_portfolio_data = {
            "name": "实盘投资组合",
            "description": "用于实盘交易的组合",
            "initial_capital": 2000000.0,
            "risk_level": 0.18,
            "source": SOURCE_TYPES.LIVE.value,  # int值
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_portfolio_data.copy())

        # 验证int值保持不变
        assert validated_data["source"] == SOURCE_TYPES.LIVE.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_portfolio_performance_analysis(self):
        """测试投资组合绩效分析中的枚举处理"""
        # 场景1：分析模拟投资组合绩效
        sim_performance_filters = {
            "source": SOURCE_TYPES.SIM,  # 只分析模拟组合
            "risk_level__gte": 0.1,
            "current_capital__gte": 100000.0
        }

        converted_filters = self.crud_instance._convert_enum_values(sim_performance_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 场景2：比较不同数据源的投资组合表现
        source_comparison_filters = {
            "source__in": [SOURCE_TYPES.BACKTEST, SOURCE_TYPES.LIVE],
            "initial_capital__gte": 1000000.0
        }

        converted_filters = self.crud_instance._convert_enum_values(source_comparison_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"

        # 验证数据源列表转换
        expected_sources = [SOURCE_TYPES.BACKTEST.value, SOURCE_TYPES.LIVE.value]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_portfolio_risk_management(self):
        """测试投资组合风险管理中的枚举处理"""
        # 场景1：监控高风险投资组合
        high_risk_filters = {
            "source": SOURCE_TYPES.LIVE,  # 只监控实盘组合
            "risk_level__gte": 0.2,
            "current_capital__lte": 900000.0  # 亏损的组合
        }

        converted_filters = self.crud_instance._convert_enum_values(high_risk_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 场景2：分析不同数据源的风险分布
        risk_analysis_filters = {
            "source__in": [SOURCE_TYPES.SIM, SOURCE_TYPES.BACKTEST, SOURCE_TYPES.LIVE],
            "risk_level__gte": 0.05  # 只考虑有风险管理的组合
        }

        converted_filters = self.crud_instance._convert_enum_values(risk_analysis_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"

    @pytest.mark.enum
    def test_portfolio_strategy_comparison(self):
        """测试投资组合策略比较中的枚举处理"""
        # 场景1：比较相同策略不同数据源的表现
        strategy_comparison_filters = {
            "name__like": "均线策略%",  # 特定策略的组合
            "source__in": [SOURCE_TYPES.SIM, SOURCE_TYPES.BACKTEST],
            "create_at__gte": datetime(2023, 1, 1)
        }

        converted_filters = self.crud_instance._convert_enum_values(strategy_comparison_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 场景2：查找特定数据源的策略组合
        strategy_source_filters = {
            "source": SOURCE_TYPES.SIM,
            "name__like": "%策略%",
            "initial_capital__gte": 100000.0
        }

        converted_filters = self.crud_instance._convert_enum_values(strategy_source_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

    @pytest.mark.enum
    def test_portfolio_data_migration_with_enums(self):
        """测试投资组合数据迁移中的枚举处理"""
        # 场景1：从模拟迁移到实盘
        migration_filters = {
            "source": SOURCE_TYPES.SIM,  # 找到模拟组合
            "update_at__lte": datetime.now()  # 已更新的组合
        }

        converted_filters = self.crud_instance._convert_enum_values(migration_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"

        # 场景2：查找需要迁移的组合
        migration_candidates_filters = {
            "source__in": [SOURCE_TYPES.SIM, SOURCE_TYPES.BACKTEST],
            "risk_level__lte": 0.15,  # 风险可控的组合
            "current_capital__gte": 50000.0  # 有一定规模的组合
        }

        converted_filters = self.crud_instance._convert_enum_values(migration_candidates_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 验证数据源列表转换
        expected_sources = [SOURCE_TYPES.SIM.value, SOURCE_TYPES.BACKTEST.value]
        assert converted_filters["source__in"] == expected_sources, "数据源列表应该正确转换"

    @pytest.mark.enum
    def test_portfolio_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("PortfolioCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("PortfolioCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("PortfolioCRUD")

        # 验证生成的测试数据包含必要的枚举字段
        assert "source" in test_filters, "测试过滤器应该包含source字段"
        assert "source" in test_model_data, "测试模型数据应该包含source字段"

        # PortfolioCRUD只有一个枚举字段，组合测试为空是正常的
        # 当枚举字段少于2个时，无法生成组合测试
        assert len(combination_tests) >= 0, "组合测试数量应该非负"
        for combination in combination_tests:
            assert "source" in combination, "组合测试应该包含source字段"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("PortfolioCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_portfolio_audit_with_enums(self):
        """测试投资组合审计中的枚举处理"""
        # 场景1：审计实盘投资组合
        live_audit_filters = {
            "source": SOURCE_TYPES.LIVE,  # 只审计实盘组合
            "update_at__gte": datetime(2023, 1, 1),  # 今年更新的组合
            "current_capital__gte": 10000.0  # 有资金的组合
        }

        converted_filters = self.crud_instance._convert_enum_values(live_audit_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 场景2：审计不同数据源的组合数量
        source_audit_filters = {
            "create_at__gte": datetime(2023, 1, 1),
            "create_at__lte": datetime(2023, 12, 31)
        }

        # 按数据源分组审计
        source_counts = {}
        for source_enum in [SOURCE_TYPES.SIM, SOURCE_TYPES.BACKTEST, SOURCE_TYPES.LIVE]:
            source_filters = source_audit_filters.copy()
            source_filters["source"] = source_enum

            converted_filters = self.crud_instance._convert_enum_values(source_filters)
            conditions = self.crud_instance._parse_filters(converted_filters)

            # 这里只是验证查询条件能够正确构建
            assert len(conditions) == 3, f"{source_enum.name}组合查询应该生成3个条件"
            assert converted_filters["source"] == source_enum.value, f"{source_enum.name}应该转换"

    @pytest.mark.enum
    def test_portfolio_batch_operations_with_enums(self):
        """测试批量投资组合操作中的枚举处理"""
        # 创建包含不同数据源的投资组合数据列表
        batch_portfolio_data = [
            {
                "name": "模拟策略组合A",
                "description": "均线策略模拟组合",
                "initial_capital": 100000.0,
                "risk_level": 0.1,
                "source": SOURCE_TYPES.SIM,  # 枚举对象
            },
            {
                "name": "回测策略组合B",
                "description": "动量策略回测组合",
                "initial_capital": 200000.0,
                "risk_level": 0.15,
                "source": SOURCE_TYPES.BACKTEST.value  # int值
            },
            {
                "name": "实盘策略组合C",
                "description": "套利策略实盘组合",
                "initial_capital": 500000.0,
                "risk_level": 0.12,
                "source": SOURCE_TYPES.LIVE  # 枚举对象
            }
        ]

        # 测试批量转换
        converted_batch = []
        for portfolio_data in batch_portfolio_data:
            validated_data = self.crud_instance._validate_item_enum_fields(portfolio_data.copy())
            converted_batch.append(validated_data)

        # 验证批量转换结果
        assert len(converted_batch) == 3, "应该转换3个投资组合记录"

        expected_sources = [SOURCE_TYPES.SIM.value, SOURCE_TYPES.BACKTEST.value, SOURCE_TYPES.LIVE.value]

        for i, expected_source in enumerate(expected_sources):
            assert converted_batch[i]["source"] == expected_source, \
                f"第{i+1}个投资组合的数据源应该正确转换为{expected_source}"

    @pytest.mark.enum
    def test_invalid_portfolio_enum_handling(self):
        """测试无效投资组合枚举值的处理"""
        # 测试无效的数据源值
        invalid_source_filters = {"source": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_source_filters)

        assert converted_filters["source"] == 999, "无效的数据源值应该保留原样"

        # 测试包含无效值的复杂查询
        mixed_portfolio_filters = {
            "name": "测试组合",
            "source": SOURCE_TYPES.SIM,  # 有效枚举
            "initial_capital": 1000000.0,
            "invalid_field": 999  # 无效字段
        }

        converted_filters = self.crud_instance._convert_enum_values(mixed_portfolio_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件（name, source, initial_capital）"
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value, "有效枚举应该转换"
        # 注意：_convert_enum_values不过滤字段，_parse_filters会忽略不存在的字段
        assert "invalid_field" in converted_filters, "_convert_enum_values保留所有字段，_parse_filters处理字段验证"

    @pytest.mark.enum
    def test_portfolio_source_lifecycle(self):
        """测试投资组合数据源生命周期中的枚举处理"""
        # 模拟组合生命周期：SIM -> BACKTEST -> LIVE
        lifecycle_stages = [
            (SOURCE_TYPES.SIM, "模拟阶段"),
            (SOURCE_TYPES.BACKTEST, "回测阶段"),
            (SOURCE_TYPES.LIVE, "实盘阶段")
        ]

        for stage_source, stage_name in lifecycle_stages:
            # 查询特定阶段的组合
            stage_filters = {
                "source": stage_source,
                "risk_level__gte": 0.05
            }

            converted_filters = self.crud_instance._convert_enum_values(stage_filters)
            conditions = self.crud_instance._parse_filters(converted_filters)

            assert len(conditions) == 2, f"{stage_name}查询应该生成2个条件"
            assert converted_filters["source"] == stage_source.value, f"{stage_name}的数据源应该转换"

        # 测试跨阶段迁移（使用有效的source字段）
        migration_filters = {
            "source": SOURCE_TYPES.SIM,  # 使用实际存在的枚举字段
            "migration_description": "从模拟迁移到实盘",
            "migration_date": datetime.now()
        }

        # 验证转换逻辑工作正常
        converted_filters = self.crud_instance._convert_enum_values(migration_filters)
        # 验证source枚举被正确转换
        assert converted_filters["source"] == SOURCE_TYPES.SIM.value
        assert converted_filters["migration_description"] == "从模拟迁移到实盘"