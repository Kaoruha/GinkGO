#!/usr/bin/env python3
"""
StockInfoCRUD枚举处理测试

测试StockInfoCRUD类中枚举字段的完整处理功能，包括：
- 枚举字段映射验证
- 股票信息查询中的枚举处理
- 市场和货币枚举的转换
- 多市场支持相关的枚举处理
"""

import pytest
import sys
import os
from typing import Dict, Any
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.models.model_stock_info import MStockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES, SOURCE_TYPES

import sys
import os
test_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, test_dir)

from base_enum_crud_test import BaseEnumCRUDTest
from enum_test_data_factory import EnumTestDataFactory


@pytest.mark.enum
@pytest.mark.database
class TestStockInfoCRUDEnum(BaseEnumCRUDTest):
    """StockInfoCRUD枚举处理专项测试"""

    def get_crud_class(self):
        """返回StockInfoCRUD类"""
        return StockInfoCRUD

    def get_test_model_data(self) -> Dict[str, Any]:
        """返回StockInfo模型的测试数据"""
        return {
            "code": "000001.SZ",
            "name": "平安银行",
            "market": MARKET_TYPES.CHINA,
            "currency": CURRENCY_TYPES.CNY,
            "industry": "银行",
            "listing_date": datetime(1991, 4, 3),
            "total_shares": 19405918198,
            "float_shares": 19405918198,
            "source": SOURCE_TYPES.TUSHARE
        }

    def get_expected_enum_mappings(self) -> Dict[str, Any]:
        """返回StockInfoCRUD预期的枚举字段映射"""
        return {
            'market': MARKET_TYPES,
            'currency': CURRENCY_TYPES,
            'source': SOURCE_TYPES
        }

    @pytest.mark.enum
    def test_market_enum_conversions(self):
        """测试市场枚举转换"""
        # 测试中国A股市场
        china_market = MARKET_TYPES.CHINA
        converted_china = self.crud_instance._normalize_single_enum_value(
            china_market, MARKET_TYPES, "market"
        )
        assert converted_china == MARKET_TYPES.CHINA.value, "中国A股市场应该转换为对应的整数值"

        # 测试纳斯达克市场
        nasdaq_market = MARKET_TYPES.NASDAQ
        converted_nasdaq = self.crud_instance._normalize_single_enum_value(
            nasdaq_market, MARKET_TYPES, "market"
        )
        assert converted_nasdaq == MARKET_TYPES.NASDAQ.value, "纳斯达克市场应该转换为对应的整数值"

        # 测试int值保持不变
        int_market = MARKET_TYPES.CHINA.value
        converted_int = self.crud_instance._normalize_single_enum_value(
            int_market, MARKET_TYPES, "market"
        )
        assert converted_int == int_market, "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_currency_enum_conversions(self):
        """测试货币枚举转换"""
        # 测试人民币
        cny_currency = CURRENCY_TYPES.CNY
        converted_cny = self.crud_instance._normalize_single_enum_value(
            cny_currency, CURRENCY_TYPES, "currency"
        )
        assert converted_cny == CURRENCY_TYPES.CNY.value, "人民币应该转换为对应的整数值"

        # 测试美元
        usd_currency = CURRENCY_TYPES.USD
        converted_usd = self.crud_instance._normalize_single_enum_value(
            usd_currency, CURRENCY_TYPES, "currency"
        )
        assert converted_usd == CURRENCY_TYPES.USD.value, "美元应该转换为对应的整数值"

        # 测试港币
        hkd_currency = CURRENCY_TYPES.USD
        converted_hkd = self.crud_instance._normalize_single_enum_value(
            hkd_currency, CURRENCY_TYPES, "currency"
        )
        assert converted_hkd == CURRENCY_TYPES.USD.value, "港币应该转换为对应的整数值"

    @pytest.mark.enum
    def test_stock_info_query_scenarios(self):
        """测试股票信息查询场景"""
        # 场景1：查询中国A股的股票信息
        china_stocks_filters = {
            "market": MARKET_TYPES.CHINA,
            "currency": CURRENCY_TYPES.CNY,
            "source": SOURCE_TYPES.TUSHARE
        }

        converted_filters = self.crud_instance._convert_enum_values(china_stocks_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"
        assert converted_filters["market"] == MARKET_TYPES.CHINA.value, "中国A股市场应该转换"
        assert converted_filters["currency"] == CURRENCY_TYPES.CNY.value, "人民币应该转换"

        # 场景2：查询多市场股票
        multi_market_filters = {
            "market__in": [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ],
            "currency__in": [CURRENCY_TYPES.CNY, CURRENCY_TYPES.USD],
            "source": SOURCE_TYPES.YAHOO
        }

        converted_filters = self.crud_instance._convert_enum_values(multi_market_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "应该生成3个查询条件"

        # 验证市场列表转换
        expected_markets = [MARKET_TYPES.CHINA.value, MARKET_TYPES.NASDAQ.value]
        assert converted_filters["market__in"] == expected_markets, "市场列表应该正确转换"

        # 验证货币列表转换
        expected_currencies = [CURRENCY_TYPES.CNY.value, CURRENCY_TYPES.USD.value]
        assert converted_filters["currency__in"] == expected_currencies, "货币列表应该正确转换"

    @pytest.mark.enum
    def test_cross_market_analysis(self):
        """测试跨市场分析中的枚举处理"""
        # 场景1：比较不同市场的股票数量
        market_comparison_filters = {
            "source": SOURCE_TYPES.TUSHARE,  # 使用统一数据源进行公平比较
            "total_shares__gte": 1000000000  # 只考虑大盘股
        }

        # 中国A股市场
        china_filter = market_comparison_filters.copy()
        china_filter["market"] = MARKET_TYPES.CHINA

        converted_china = self.crud_instance._convert_enum_values(china_filter)
        conditions_china = self.crud_instance._parse_filters(converted_china)

        assert len(conditions_china) == 3, "中国A股查询应该生成3个条件"
        assert converted_china["market"] == MARKET_TYPES.CHINA.value, "中国A股市场应该转换"

        # 美股市场
        us_filter = market_comparison_filters.copy()
        us_filter["market"] = MARKET_TYPES.NASDAQ

        converted_us = self.crud_instance._convert_enum_values(us_filter)
        conditions_us = self.crud_instance._parse_filters(converted_us)

        assert len(conditions_us) == 3, "美股查询应该生成3个条件"
        assert converted_us["market"] == MARKET_TYPES.NASDAQ.value, "美股市场应该转换"

        # 场景2：分析货币分布
        currency_analysis_filters = {
            "source": SOURCE_TYPES.TUSHARE,
            "market__in": [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ]
        }

        converted_filters = self.crud_instance._convert_enum_values(currency_analysis_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 2, "货币分析查询应该生成2个条件"

    @pytest.mark.enum
    def test_stock_info_creation_enum_validation(self):
        """测试股票信息创建时的枚举字段验证"""
        # 测试使用枚举对象创建股票信息
        enum_stock_data = {
            "code": "AAPL",
            "name": "Apple Inc.",
            "market": MARKET_TYPES.NASDAQ,  # 枚举对象
            "currency": CURRENCY_TYPES.USD,  # 枚举对象
            "industry": "Technology",
            "listing_date": datetime(1980, 12, 12),
            "total_shares": 15600000000,
            "float_shares": 15600000000,
            "source": SOURCE_TYPES.YAHOO  # 枚举对象
        }

        validated_data = self.crud_instance._validate_item_enum_fields(enum_stock_data.copy())

        # 验证枚举字段被正确转换
        assert validated_data["market"] == MARKET_TYPES.NASDAQ.value, \
            "美股市场应该转换为int值"
        assert validated_data["currency"] == CURRENCY_TYPES.USD.value, \
            "美元应该转换为int值"
        assert validated_data["source"] == SOURCE_TYPES.YAHOO.value, \
            "Yahoo数据源应该转换为int值"

        # 测试使用int值创建股票信息
        int_stock_data = {
            "code": "000001.SZ",
            "name": "平安银行",
            "market": MARKET_TYPES.CHINA.value,  # int值
            "currency": CURRENCY_TYPES.CNY.value,  # int值
            "industry": "银行",
            "listing_date": datetime(1991, 4, 3),
            "total_shares": 19405918198,
            "float_shares": 19405918198,
            "source": SOURCE_TYPES.TUSHARE.value  # int值
        }

        validated_data = self.crud_instance._validate_item_enum_fields(int_stock_data.copy())

        # 验证int值保持不变
        assert validated_data["market"] == MARKET_TYPES.CHINA.value, \
            "有效的int值应该保持不变"
        assert validated_data["currency"] == CURRENCY_TYPES.CNY.value, \
            "有效的int值应该保持不变"

    @pytest.mark.enum
    def test_multi_market_data_sync(self):
        """测试多市场数据同步中的枚举处理"""
        # 场景1：同步特定市场的股票信息
        sync_china_filters = {
            "market": MARKET_TYPES.CHINA,
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE],
            "listing_date__lte": datetime.now()
        }

        converted_filters = self.crud_instance._convert_enum_values(sync_china_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "中国A股同步查询应该生成3个条件"

        # 场景2：同步美股数据
        sync_us_filters = {
            "market": MARKET_TYPES.NASDAQ,
            "source": SOURCE_TYPES.YAHOO,
            "currency": CURRENCY_TYPES.USD
        }

        converted_filters = self.crud_instance._convert_enum_values(sync_us_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 3, "美股同步查询应该生成3个条件"
        assert converted_filters["currency"] == CURRENCY_TYPES.USD.value, "美元应该转换"

    @pytest.mark.enum
    def test_stock_info_enum_test_data_factory_integration(self):
        """测试与EnumTestDataFactory的集成"""
        # 使用工厂创建测试数据
        test_filters = EnumTestDataFactory.create_test_filters("StockInfoCRUD")
        test_model_data = EnumTestDataFactory.create_test_model_data("StockInfoCRUD")
        combination_tests = EnumTestDataFactory.create_enum_combination_tests("StockInfoCRUD")

        # 验证生成的测试数据包含所有必要的枚举字段
        expected_fields = ['market', 'currency', 'source']
        for field in expected_fields:
            assert field in test_filters, f"测试过滤器应该包含字段: {field}"
            assert field in test_model_data, f"测试模型数据应该包含字段: {field}"

        # 验证组合测试数据
        assert len(combination_tests) > 0, "应该生成组合测试数据"
        for combination in combination_tests:
            for field in expected_fields:
                assert field in combination, f"组合测试应该包含字段: {field}"

        # 验证工厂配置与实际映射的一致性
        errors = EnumTestDataFactory.validate_enum_mappings("StockInfoCRUD", self.enum_mappings)
        assert len(errors) == 0, f"枚举映射验证失败: {errors}"

    @pytest.mark.enum
    def test_market_currency_combination_analysis(self):
        """测试市场-货币组合分析"""
        # 测试所有有效的市场-货币组合
        valid_combinations = [
            (MARKET_TYPES.CHINA, CURRENCY_TYPES.CNY),      # 中国A股-人民币
            (MARKET_TYPES.NASDAQ, CURRENCY_TYPES.USD),      # 美股-美元
            (MARKET_TYPES.NASDAQ, CURRENCY_TYPES.USD),      # 港股-港币
        ]

        combination_count = 0
        for market, currency in valid_combinations:
            combination_filters = {
                "market": market,
                "currency": currency,
                "source": SOURCE_TYPES.TUSHARE
            }

            converted_filters = self.crud_instance._convert_enum_values(combination_filters)
            conditions = self.crud_instance._parse_filters(converted_filters)

            assert len(conditions) == 3, f"组合 {market.name}+{currency.name} 应该生成3个条件"
            assert converted_filters["market"] == market.value, "市场应该转换为int值"
            assert converted_filters["currency"] == currency.value, "货币应该转换为int值"

            combination_count += 1

        assert combination_count == 3, "应该测试3种市场-货币组合"

    @pytest.mark.enum
    def test_stock_quality_filtering_with_enums(self):
        """测试基于枚举的股票质量过滤"""
        # 场景1：高质量股票（指定市场和数据源）
        quality_filters = {
            "market": MARKET_TYPES.CHINA,
            "currency": CURRENCY_TYPES.CNY,
            "source__in": [SOURCE_TYPES.TUSHARE, SOURCE_TYPES.AKSHARE],
            "total_shares__gte": 1000000000,  # 大盘股
            "float_shares__gte": 500000000     # 流通盘充足
        }

        converted_filters = self.crud_instance._convert_enum_values(quality_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 5, "应该生成5个查询条件"

        # 场景2：国际股票（美股、港股）
        international_filters = {
            "market__in": [MARKET_TYPES.NASDAQ],
            "currency__in": [CURRENCY_TYPES.USD, CURRENCY_TYPES.USD],
            "source": SOURCE_TYPES.YAHOO,
            "total_shares__gte": 100000000
        }

        converted_filters = self.crud_instance._convert_enum_values(international_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"

        # 验证货币列表转换
        expected_currencies = [CURRENCY_TYPES.USD.value, CURRENCY_TYPES.USD.value]
        assert converted_filters["currency__in"] == expected_currencies, "货币列表应该正确转换"

    @pytest.mark.enum
    def test_invalid_stock_info_enum_handling(self):
        """测试无效股票信息枚举值的处理"""
        # 测试无效的市场值
        invalid_market_filters = {"market": 999}
        converted_filters = self.crud_instance._convert_enum_values(invalid_market_filters)

        assert converted_filters["market"] == 999, "无效的市场值应该保留原样"

        # 测试无效的货币值
        invalid_currency_filters = {"currency": -1}
        converted_filters = self.crud_instance._convert_enum_values(invalid_currency_filters)

        assert converted_filters["currency"] == -1, "无效的货币值应该保留原样"

        # 测试包含无效值的复杂查询
        mixed_enum_filters = {
            "market": MARKET_TYPES.CHINA,  # 有效枚举
            "currency": 999,  # 无效int
            "source": SOURCE_TYPES.TUSHARE,  # 有效枚举
            "code": "000001.SZ"
        }

        converted_filters = self.crud_instance._convert_enum_values(mixed_enum_filters)
        conditions = self.crud_instance._parse_filters(converted_filters)

        assert len(conditions) == 4, "应该生成4个查询条件"
        assert converted_filters["market"] == MARKET_TYPES.CHINA.value, \
            "有效枚举应该转换"
        assert converted_filters["currency"] == 999, "无效int应该保留原样"
        assert converted_filters["source"] == SOURCE_TYPES.TUSHARE.value, \
            "有效枚举应该转换"

    @pytest.mark.enum
    def test_stock_info_batch_operations_with_enums(self):
        """测试批量股票信息操作中的枚举处理"""
        # 创建包含不同市场和货币的股票信息列表
        batch_stock_data = [
            {
                "code": "000001.SZ",
                "name": "平安银行",
                "market": MARKET_TYPES.CHINA,  # 枚举对象
                "currency": CURRENCY_TYPES.CNY,  # 枚举对象
                "source": SOURCE_TYPES.TUSHARE
            },
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "market": MARKET_TYPES.NASDAQ.value,  # int值
                "currency": CURRENCY_TYPES.USD,  # 枚举对象
                "source": SOURCE_TYPES.YAHOO
            },
            {
                "code": "0700.HK",
                "name": "腾讯控股",
                "market": MARKET_TYPES.NASDAQ,  # 枚举对象
                "currency": CURRENCY_TYPES.USD.value,  # int值
                "source": SOURCE_TYPES.AKSHARE.value  # int值
            }
        ]

        # 测试批量转换
        converted_batch = []
        for stock_data in batch_stock_data:
            validated_data = self.crud_instance._validate_item_enum_fields(stock_data.copy())
            converted_batch.append(validated_data)

        # 验证批量转换结果
        assert len(converted_batch) == 3, "应该转换3个股票记录"

        expected_markets = [MARKET_TYPES.CHINA.value, MARKET_TYPES.NASDAQ.value, MARKET_TYPES.NASDAQ.value]
        expected_currencies = [CURRENCY_TYPES.CNY.value, CURRENCY_TYPES.USD.value, CURRENCY_TYPES.USD.value]

        for i, (expected_market, expected_currency) in enumerate(zip(expected_markets, expected_currencies)):
            assert converted_batch[i]["market"] == expected_market, \
                f"第{i+1}个股票的市场应该正确转换为{expected_market}"
            assert converted_batch[i]["currency"] == expected_currency, \
                f"第{i+1}个股票的货币应该正确转换为{expected_currency}"