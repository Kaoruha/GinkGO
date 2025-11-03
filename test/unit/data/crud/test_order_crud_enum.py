#!/usr/bin/env python3
"""
OrderCRUD枚举处理测试

测试OrderCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- 查询条件中的枚举处理
- add操作的枚举验证
- 业务逻辑相关的枚举状态转换
"""

import pytest
import sys
import os
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.order_crud import OrderCRUD
from ginkgo.data.models.model_order import MOrder
from ginkgo.trading.entities import Order
from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
)

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestOrderCRUDEnum(BaseEnumCRUDTest):
    """OrderCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回OrderCRUD类"""
        return OrderCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回Order模型的测试数据"""
        return {
            "engine_id": "test_engine",
            "run_id": "test_run",
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "order_type": ORDER_TYPES.LIMITORDER,
            "volume": 1000,
            "limit_price": 10.50,
            "status": ORDERSTATUS_TYPES.NEW,
            "source": SOURCE_TYPES.TUSHARE
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回OrderCRUD预期的枚举字段映射"""
        return {
            'direction': DIRECTION_TYPES,
            'order_type': ORDER_TYPES,
            'status': ORDERSTATUS_TYPES,
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_direction_enum_conversions(self):
        """测试交易方向枚举转换"""
        # 测试多头方向
        long_direction = DIRECTION_TYPES.LONG
        converted_long = self.crud_instance._normalize_single_enum_value(
            long_direction, DIRECTION_TYPES, "direction"
        )
        assert converted_long == DIRECTION_TYPES.LONG.value, "LONG方向应该转换为对应的整数值"

        # 测试空头方向
        short_direction = DIRECTION_TYPES.SHORT
        converted_short = self.crud_instance._normalize_single_enum_value(
            short_direction, DIRECTION_TYPES, "direction"
        )
        assert converted_short == DIRECTION_TYPES.SHORT.value, "SHORT方向应该转换为对应的整数值"

        # 测试int值保持不变
        int_long = DIRECTION_TYPES.LONG.value
        converted_int = self.crud_instance._normalize_single_enum_value(
            int_long, DIRECTION_TYPES, "direction"
        )
        assert converted_int == int_long, "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_order_status_transitions(self):
        """测试订单状态转换逻辑"""
        # 测试所有有效状态
        valid_statuses = [
            ORDERSTATUS_TYPES.NEW,
            ORDERSTATUS_TYPES.SUBMITTED,
            ORDERSTATUS_TYPES.PARTIAL_FILLED,
            ORDERSTATUS_TYPES.FILLED,
            ORDERSTATUS_TYPES.CANCELED
        ]

        for status in valid_statuses:
            converted = self.crud_instance._normalize_single_enum_value(
                status, ORDERSTATUS_TYPES, "status"
            )
            assert converted == status.value, f"状态 {status} 应该转换为对应的整数值"

        # 测试状态查询过滤器
        status_filters = {
            "status__in": [
                ORDERSTATUS_TYPES.NEW,
                ORDERSTATUS_TYPES.FILLED,
                3  # PARTIAL_FILLED的int值
            ]
        }

        converted_filters = self.crud_instance._convert_enum_values(status_filters)
        expected_values = [
            ORDERSTATUS_TYPES.NEW.value,
            ORDERSTATUS_TYPES.FILLED.value,
            3  # int值保持不变
        ]

        assert converted_filters["status__in"] == expected_values, \
            "状态过滤器中的枚举值应该正确转换"

    @pytest.mark.enum
    def test_order_type_validation(self):
        """测试订单类型验证"""
        # 测试市价单
        market_order = ORDER_TYPES.MARKETORDER
        converted_market = self.crud_instance._normalize_single_enum_value(
            market_order, ORDER_TYPES, "order_type"
        )
        assert converted_market == ORDER_TYPES.MARKETORDER.value, "市价单应该转换为对应的整数值"

        # 测试限价单
        limit_order = ORDER_TYPES.LIMITORDER
        converted_limit = self.crud_instance._normalize_single_enum_value(
            limit_order, ORDER_TYPES, "order_type"
        )
        assert converted_limit == ORDER_TYPES.LIMITORDER.value, "限价单应该转换为对应的整数值"

        # 测试订单类型查询
        order_type_filters = {
            "order_type": ORDER_TYPES.LIMITORDER,
            "direction": DIRECTION_TYPES.LONG
        }

        converted_filters = self.crud_instance._convert_enum_values(order_type_filters)
        assert converted_filters["order_type"] == ORDER_TYPES.LIMITORDER.value, \
            "订单类型过滤器中的枚举应该转换"
        assert converted_filters["direction"] == DIRECTION_TYPES.LONG.value, \
            "方向过滤器中的枚举应该转换"

    @pytest.mark.enum
    def test_source_enum_coverage(self):
        """测试数据源枚举覆盖"""
        # 测试所有数据源类型
        all_sources = [
            SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO,
            SOURCE_TYPES.AKSHARE, SOURCE_TYPES.BAOSTOCK, SOURCE_TYPES.TDX
        ]

        for source in all_sources:
            converted = self.crud_instance._normalize_single_enum_value(
                source, SOURCE_TYPES, "source"
            )
            assert converted == source.value, f"数据源 {source} 应该转换为对应的整数值"

        # 测试数据源查询组合
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
    def test_complex_order_queries(self):
        """测试复杂订单查询场景"""
        # 场景1：查询多头且未成交的限价单
        long_unfilled_filters = {
            "direction": DIRECTION_TYPES.LONG,
            "status__in": [ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.SUBMITTED],
            "order_type": ORDER_TYPES.LIMITORDER,
            "source": SOURCE_TYPES.TUSHARE
        }

        converted_filters = self.crud_instance._convert_enum_values(long_unfilled_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"
        assert converted_filters["direction"] == DIRECTION_TYPES.LONG.value, "多头方向应该转换"
        assert converted_filters["order_type"] == ORDER_TYPES.LIMITORDER.value, "限价单应该转换"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, "数据源应该转换"

        # 场景2：查询所有已成交订单（多数据源）
        filled_orders_filters = {
            "status": ORDERSTATUS_TYPES.FILLED,
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO, SOURCE_TYPES.AKSHARE]
        }

        converted_filters = self.crud_instance._convert_enum_values(filled_orders_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "应该生成2个查询条件"
        assert converted_filters["status"] == ORDERSTATUS_TYPES.FILLED.value, "成交状态应该转换"

    @pytest.mark.enum
    def test_order_creation_enum_validation(self):
        """测试订单创建时的枚举字段验证"""
        # 测试使用枚举对象创建订单
        enum_order_data = {
            "engine_id": "test_engine",
            "run_id": "test_run",
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.SHORT,  # 枚举对象
            "order_type": ORDER_TYPES.MARKETORDER,  # 枚举对象
            "volume": 1000,
            "limit_price": 10.50,
            "status": ORDERSTATUS_TYPES.NEW,  # 枚举对象
            "source": SOURCE_TYPES.SIM  # 枚举对象
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_order_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["direction"] == DIRECTION_TYPES.SHORT.value, \
            "空头方向应该转换为int值"
        assert validated_data["order_type"] == ORDER_TYPES.MARKETORDER.value, \
            "市价单应该转换为int值"
        assert validated_data["status"] == ORDERSTATUS_TYPES.NEW.value, \
            "新建状态应该转换为int值"
        assert validated_data["source"] == SOURCE_TYPES.SIM.value, \
            "模拟数据源应该转换为int值"

        # 测试使用int值创建订单
        int_order_data = {
            "engine_id": "test_engine",
            "run_id": "test_run",
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG.value,  # int值
            "order_type": ORDER_TYPES.LIMITORDER.value,  # int值
            "volume": 1000,
            "limit_price": 10.50,
            "status": ORDERSTATUS_TYPES.NEW.value,  # int值
            "source": SOURCE_TYPES.TUSHARE.value  # int值
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_order_data.copy())

        # 验证int值保持不变
        assert validated_data["direction"] == DIRECTION_TYPES.LONG.value, \
            "有效的int值应该保持不变"
        assert validated_data["order_type"] == ORDER_TYPES.LIMITORDER.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_order_enum_business_logic(self):
        """测试订单相关的枚举业务逻辑"""
        # 业务场景1：不同方向的订单查询
        buy_orders_filters = {"direction": DIRECTION_TYPES.LONG}
        sell_orders_filters = {"direction": DIRECTION_TYPES.SHORT}

        converted_buy = self.crud_instance._convert_enum_values(buy_orders_filters)
        converted_sell = self.crud_instance._convert_enum_values(sell_orders_filters)

        assert converted_buy["direction"] != converted_sell["direction"], \
            "买卖方向的转换值应该不同"

        # 业务场景2：不同状态的订单处理
        active_statuses = [ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.SUBMITTED, ORDERSTATUS_TYPES.PARTIAL_FILLED]
        completed_statuses = [ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.CANCELED]

        active_filters = {"status__in": active_statuses}
        completed_filters = {"status__in": completed_statuses}

        converted_active = self.crud_instance._convert_enum_values(active_filters)
        converted_completed = self.crud_instance._convert_enum_values(completed_filters)

        assert len(converted_active["status__in"]) == 3, "活跃状态应该有3个"
        assert len(converted_completed["status__in"]) == 2, "完成状态应该有2个"

        # 业务场景3：不同数据源的订单质量验证
        quality_sources = [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO]  # 高质量数据源
        quality_filters = {"source__in": quality_sources, "volume__gte": 1000}

        converted_quality = self.crud_instance._convert_enum_values(quality_filters)
        conditions = self.crud_instance._parse_filters(converted_quality)

        assert len(conditions) == 3, "应该生成3个查询条件（2个枚举+1个数值）"

    @pytest.mark.enum
    def test_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("OrderCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("OrderCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("OrderCRUD")

        # 验证生成的测试数据包含所有必要的枚举字段
        expected_fields = ['direction', 'order_type', 'status', 'source']
        for field in expected_fields:
            assert field in test_filters, f"测试过滤器应该包含字段: {field}"
            assert field in test_model_data, f"测试模型数据应该包含字段: {field}"

        # 验证组合测试数据
        assert len(combination_tests) > 0, "应该生成组合测试数据"
        for combination in combination_tests:
            for field in expected_fields:
                assert field in combination, f"组合测试应该包含字段: {field}"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("OrderCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_invalid_order_enum_handling(self):
        """测试无效订单枚举值的处理"""
        # 测试无效的方向值
        invalid_direction_filters = {"direction": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_direction_filters)

        # 无效值应该保留原样
        assert converted_filters["direction"] == 999, "无效的方向值应该保留原样"

        # 测试无效的状态值
        invalid_status_filters = {"status": -1}
        converted_filters = self.crud_instance._convert_enum_values(invalid_status_filters)

        assert converted_filters["status"] == -1, "无效的状态值应该保留原样"

        # 测试包含无效值的列表
        mixed_status_filters = {
            "status__in": [
                ORDERSTATUS_TYPES.NEW,  # 有效枚举
                999,  # 无效int
                ORDERSTATUS_TYPES.FILLED  # 有效枚举
            ]
        }

        converted_filters = self.crud_instance._convert_enum_values(mixed_status_filters)
        expected_values = [
            ORDERSTATUS_TYPES.NEW.value,
            999,  # 无效值保留
            ORDERSTATUS_TYPES.FILLED.value
        ]

        assert converted_filters["status__in"] == expected_values, \
            "混合状态列表中的枚举应该转换，无效值应该保留"