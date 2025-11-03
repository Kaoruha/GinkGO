#!/usr/bin/env python3
"""
EnumTestDataFactory - 枚举测试数据工厂

提供统一的枚举测试数据生成和管理，支持所有CRUD类的枚举测试需求。
"""

import sys
import os
from typing import Dict, List, Any, Type, Union
from dataclasses import dataclass
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

from ginkgo.enums import (
    DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES,
    FREQUENCY_TYPES, MARKET_TYPES, CURRENCY_TYPES,
    TRANSFERDIRECTION_TYPES, TRANSFERSTATUS_TYPES, CAPITALADJUSTMENT_TYPES
)


@dataclass
class EnumTestCase:
    """枚举测试用例数据结构"""
    field_name: str
    enum_class: Type
    test_values: List[Any]  # 测试用的枚举值
    invalid_values: List[Any] = None  # 无效值列表
    business_scenarios: List[str] = None  # 业务场景描述


class EnumTestDataFactory:
    """
    枚举测试数据工厂

    为所有CRUD类提供标准化的枚举测试数据，确保测试的一致性和完整性。
    """

    # 枚举测试数据定义
    ENUM_TEST_DATA = {
        # 交易相关枚举
        'DIRECTION_TYPES': EnumTestCase(
            field_name='direction',
            enum_class=DIRECTION_TYPES,
            test_values=[DIRECTION_TYPES.LONG, DIRECTION_TYPES.SHORT],
            invalid_values=[999, -1, None],
            business_scenarios=['买入交易', '卖出交易']
        ),

        'ORDER_TYPES': EnumTestCase(
            field_name='order_type',
            enum_class=ORDER_TYPES,
            test_values=[ORDER_TYPES.MARKETORDER, ORDER_TYPES.LIMITORDER],
            invalid_values=[999, -1, None],
            business_scenarios=['市价单', '限价单']
        ),

        'ORDERSTATUS_TYPES': EnumTestCase(
            field_name='status',
            enum_class=ORDERSTATUS_TYPES,
            test_values=[
                ORDERSTATUS_TYPES.NEW, ORDERSTATUS_TYPES.SUBMITTED,
                ORDERSTATUS_TYPES.PARTIAL_FILLED, ORDERSTATUS_TYPES.FILLED,
                ORDERSTATUS_TYPES.CANCELED
            ],
            invalid_values=[999, -1, None],
            business_scenarios=[
                '新建订单', '已提交', '部分成交', '完全成交', '已取消'
            ]
        ),

        # 数据源枚举
        'SOURCE_TYPES': EnumTestCase(
            field_name='source',
            enum_class=SOURCE_TYPES,
            test_values=[
                SOURCE_TYPES.SIM, SOURCE_TYPES.TUSHARE, SOURCE_TYPES.YAHOO,
                SOURCE_TYPES.AKSHARE, SOURCE_TYPES.BAOSTOCK, SOURCE_TYPES.TDX
            ],
            invalid_values=[999, -1, None],
            business_scenarios=[
                '模拟数据', 'Tushare数据', 'Yahoo数据', 'AKShare数据',
                'BaoStock数据', '通达信数据'
            ]
        ),

        # 时间频率枚举
        'FREQUENCY_TYPES': EnumTestCase(
            field_name='frequency',
            enum_class=FREQUENCY_TYPES,
            test_values=[FREQUENCY_TYPES.DAY, FREQUENCY_TYPES.MIN1],
            invalid_values=[999, -1, None],
            business_scenarios=['日线数据', '分钟线数据']
        ),

        # 市场信息枚举
        'MARKET_TYPES': EnumTestCase(
            field_name='market',
            enum_class=MARKET_TYPES,
            test_values=[MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ],
            invalid_values=[999, -1, None],
            business_scenarios=['中国A股', '纳斯达克']
        ),

        'CURRENCY_TYPES': EnumTestCase(
            field_name='currency',
            enum_class=CURRENCY_TYPES,
            test_values=[CURRENCY_TYPES.CNY, CURRENCY_TYPES.USD],
            invalid_values=[999, -1, None],
            business_scenarios=['人民币', '美元']
        ),

        # 资金相关枚举
        'TRANSFERDIRECTION_TYPES': EnumTestCase(
            field_name='direction',
            enum_class=TRANSFERDIRECTION_TYPES,
            test_values=[TRANSFERDIRECTION_TYPES.IN, TRANSFERDIRECTION_TYPES.OUT],
            invalid_values=[999, -1, None],
            business_scenarios=['资金转入', '资金转出']
        ),

      'TRANSFERSTATUS_TYPES': EnumTestCase(
            field_name='status',
            enum_class=TRANSFERSTATUS_TYPES,
            test_values=[
                TRANSFERSTATUS_TYPES.NEW, TRANSFERSTATUS_TYPES.SUBMITTED,
                TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.CANCELED
            ],
            invalid_values=[999, -1, None],
            business_scenarios=['新建转账', '已提交', '已完成', '已取消']
        ),

        'CAPITALADJUSTMENT_TYPES': EnumTestCase(
            field_name='adjustment_type',
            enum_class=CAPITALADJUSTMENT_TYPES,
            test_values=[
                CAPITALADJUSTMENT_TYPES.EXR_EXD, CAPITALADJUSTMENT_TYPES.CAPITALCHANGE,
                CAPITALADJUSTMENT_TYPES.SPLIT_REVERSE_SPLIT, CAPITALADJUSTMENT_TYPES.ADDITIONAL_ISSUANCE
            ],
            invalid_values=[999, -1, None],
            business_scenarios=['除权除息', '股本变化', '扩缩股', '新股发行']
        )
    }

    # CRUD类特定的枚举配置
    CRUD_ENUM_CONFIGS = {
        'OrderCRUD': {
            'enum_fields': ['direction', 'order_type', 'status', 'source'],
            'primary_enums': ['DIRECTION_TYPES', 'ORDER_TYPES', 'ORDERSTATUS_TYPES'],
            'test_scenarios': ['订单创建', '订单状态变更', '订单查询']
        },

        'BarCRUD': {
            'enum_fields': ['frequency', 'source'],
            'primary_enums': ['FREQUENCY_TYPES', 'SOURCE_TYPES'],
            'test_scenarios': ['K线数据查询', '多数据源合并', '时间序列分析']
        },

        'PositionCRUD': {
            'enum_fields': ['source'],
            'primary_enums': ['SOURCE_TYPES'],
            'test_scenarios': ['持仓查询', '持仓统计', '风险监控']
        },

        'SignalCRUD': {
            'enum_fields': ['direction', 'source'],
            'primary_enums': ['DIRECTION_TYPES', 'SOURCE_TYPES'],
            'test_scenarios': ['信号生成', '信号查询', '策略回测']
        },

        'StockInfoCRUD': {
            'enum_fields': ['market', 'currency', 'source'],
            'primary_enums': ['MARKET_TYPES', 'CURRENCY_TYPES', 'SOURCE_TYPES'],
            'test_scenarios': ['股票信息查询', '多市场支持', '汇率处理']
        },
        'PortfolioCRUD': {
            'enum_fields': ['source'],
            'primary_enums': ['SOURCE_TYPES'],
            'test_scenarios': ['投资组合管理', '绩效分析', '风险控制']
        },

        'TradeDayCRUD': {
            'enum_fields': ['source'],
            'primary_enums': ['SOURCE_TYPES'],
            'test_scenarios': ['交易日历', '数据同步', '时间序列对齐']
        },

        'TransferCRUD': {
            'enum_fields': ['direction', 'status', 'market', 'source'],
            'primary_enums': ['TRANSFERDIRECTION_TYPES', 'TRANSFERSTATUS_TYPES', 'MARKET_TYPES', 'SOURCE_TYPES'],
            'test_scenarios': ['资金转账', '流水查询', '资金统计']
        },

        'AdjustfactorCRUD': {
            'enum_fields': ['source'],
            'primary_enums': ['SOURCE_TYPES'],
            'test_scenarios': ['复权因子查询', '历史数据修正', '价格调整']
        },

        'CapitalAdjustmentCRUD': {
            'enum_fields': ['source'],
            'primary_enums': ['SOURCE_TYPES'],
            'test_scenarios': ['资金调整', '分红处理', '拆股处理']
        }
    }

    @classmethod
    def get_enum_test_case(cls, enum_name: str) -> EnumTestCase:
        """
        获取指定枚举的测试用例

        Args:
            enum_name: 枚举类型名称

        Returns:
            EnumTestCase: 枚举测试用例

        Raises:
            KeyError: 当枚举类型不存在时
        """
        if enum_name not in cls.ENUM_TEST_DATA:
            raise KeyError(f"Enum type {enum_name} not found in test data")
        return cls.ENUM_TEST_DATA[enum_name]

    @classmethod
    def get_crud_enum_config(cls, crud_class_name: str) -> Dict[str, Any]:
        """
        获取指定CRUD类的枚举配置

        Args:
            crud_class_name: CRUD类名

        Returns:
            Dict[str, Any]: CRUD枚举配置

        Raises:
            KeyError: 当CRUD类配置不存在时
        """
        if crud_class_name not in cls.CRUD_ENUM_CONFIGS:
            # 返回默认配置
            return {
                'enum_fields': [],
                'primary_enums': [],
                'test_scenarios': ['基础CRUD操作']
            }
        return cls.CRUD_ENUM_CONFIGS[crud_class_name]

    @classmethod
    def create_test_filters(cls, crud_class_name: str,
                          include_invalid: bool = False) -> Dict[str, Any]:
        """
        为指定CRUD类创建测试过滤器

        Args:
            crud_class_name: CRUD类名
            include_invalid: 是否包含无效值

        Returns:
            Dict[str, Any]: 测试过滤器
        """
        config = cls.get_crud_enum_config(crud_class_name)
        filters = {}

        for field in config['enum_fields']:
            # 查找对应的枚举类型
            enum_case = cls._find_enum_case_by_field(field)
            if enum_case:
                # 使用第一个有效枚举值
                test_value = enum_case.test_values[0]
                filters[field] = test_value

                # 为某些字段添加操作符测试
                if field in ['direction', 'status', 'source']:
                    filters[f"{field}__in"] = enum_case.test_values[:2]

                if include_invalid and enum_case.invalid_values:
                    filters[f"invalid_{field}"] = enum_case.invalid_values[0]

        # 添加一些通用字段
        filters.update({
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000
        })

        return filters

    @classmethod
    def create_test_model_data(cls, crud_class_name: str,
                             include_invalid: bool = False) -> Dict[str, Any]:
        """
        为指定CRUD类创建测试模型数据

        Args:
            crud_class_name: CRUD类名
            include_invalid: 是否包含无效值

        Returns:
            Dict[str, Any]: 测试模型数据
        """
        config = cls.get_crud_enum_config(crud_class_name)
        model_data = {}

        for field in config['enum_fields']:
            enum_case = cls._find_enum_case_by_field(field)
            if enum_case:
                # 使用第一个有效枚举值
                test_value = enum_case.test_values[0]
                model_data[field] = test_value

        # 添加通用字段
        model_data.update({
            "portfolio_id": "test_portfolio",
            "code": "000001.SZ",
            "volume": 1000,
            "price": 10.50,
            "timestamp": datetime.now()
        })

        return model_data

    @classmethod
    def create_enum_combination_tests(cls, crud_class_name: str) -> List[Dict[str, Any]]:
        """
        创建枚举组合测试用例

        Args:
            crud_class_name: CRUD类名

        Returns:
            List[Dict[str, Any]]: 枚举组合测试列表
        """
        config = cls.get_crud_enum_config(crud_class_name)
        combinations = []

        if len(config['enum_fields']) < 2:
            return combinations  # 没有足够的枚举字段进行组合测试

        # 创建基本组合：每个枚举字段选择第一个值
        basic_combination = {}
        for field in config['enum_fields']:
            enum_case = cls._find_enum_case_by_field(field)
            if enum_case:
                basic_combination[field] = enum_case.test_values[0]

        combinations.append(basic_combination)

        # 创建更多组合：每个枚举字段选择不同的值
        if len(config['enum_fields']) >= 2:
            for i, field in enumerate(config['enum_fields'][:2]):  # 只测试前两个字段的组合
                enum_case = cls._find_enum_case_by_field(field)
                if enum_case and len(enum_case.test_values) > 1:
                    combination = basic_combination.copy()
                    combination[field] = enum_case.test_values[1]  # 使用第二个值
                    combinations.append(combination)

        return combinations

    @classmethod
    def _find_enum_case_by_field(cls, field_name: str) -> Union[EnumTestCase, None]:
        """
        根据字段名查找对应的枚举测试用例

        Args:
            field_name: 字段名

        Returns:
            EnumTestCase or None: 找到的枚举测试用例
        """
        for enum_case in cls.ENUM_TEST_DATA.values():
            if enum_case.field_name == field_name:
                return enum_case
        return None

    @classmethod
    def get_all_enum_values(cls, enum_name: str) -> List[Any]:
        """
        获取指定枚举类型的所有有效值

        Args:
            enum_name: 枚举类型名称

        Returns:
            List[Any]: 所有枚举值
        """
        enum_case = cls.get_enum_test_case(enum_name)
        return enum_case.test_values

    @classmethod
    def get_invalid_enum_values(cls, enum_name: str) -> List[Any]:
        """
        获取指定枚举类型的无效值

        Args:
            enum_name: 枚举类型名称

        Returns:
            List[Any]: 无效枚举值列表
        """
        enum_case = cls.get_enum_test_case(enum_name)
        return enum_case.invalid_values or []

    @classmethod
    def validate_enum_mappings(cls, crud_class_name: str,
                             actual_mappings: Dict[str, Type]) -> List[str]:
        """
        验证CRUD类的枚举映射是否完整

        Args:
            crud_class_name: CRUD类名
            actual_mappings: 实际的枚举映射

        Returns:
            List[str]: 验证错误列表，空列表表示验证通过
        """
        errors = []
        config = cls.get_crud_enum_config(crud_class_name)

        # 如果没有配置枚举字段，跳过验证
        if not config['enum_fields']:
            return errors

        # 检查预期字段是否存在
        for field in config['enum_fields']:
            if field not in actual_mappings:
                errors.append(f"Missing expected enum field: {field}")

        # 检查是否有未预期的枚举字段
        for field in actual_mappings:
            if field not in config['enum_fields']:
                # 这可能是正常情况，记录为警告而非错误
                from ginkgo.libs import GLOG
                GLOG.DEBUG(f"Unexpected enum field {field} in {crud_class_name}")

        return errors