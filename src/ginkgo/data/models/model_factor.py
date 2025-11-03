#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column
from clickhouse_sqlalchemy import types, engines

from ginkgo.data.models.model_clickbase import MClickBase
from ginkgo.data.crud.model_conversion import ModelConversion
from ginkgo.libs import base_repr, to_decimal
from ginkgo.enums import ENTITY_TYPES, SOURCE_TYPES


class MFactor(MClickBase, ModelConversion):
    """
    因子数据模型 - 支持多种实体类型的因子存储

    存储各种类型实体的因子值，包括：
    - 个股因子 (STOCK): 技术指标、基本面指标等
    - 市场因子 (MARKET): 市场情绪、波动率等
    - 宏观因子 (COUNTRY): GDP、CPI、利率等
    - 行业因子 (INDUSTRY): 行业轮动、估值等
    - 商品因子 (COMMODITY): 库存、期货溢价等
    - 汇率因子 (CURRENCY): 汇率波动率、利差等
    - 债券因子 (BOND): 收益率曲线、信用利差等
    - 基金因子 (FUND): 基金评级、业绩指标等
    - 加密货币因子 (CRYPTO): 链上数据、挖矿指标等
    """
    __abstract__ = False
    __tablename__ = "factors"

    # ClickHouse优化配置：按实体ID+因子名+时间排序
    # 优化场景：查询单个实体的某个因子的历史数据
    __table_args__ = (
        engines.MergeTree(
            order_by=("entity_id", "factor_name", "timestamp")
        ),
        {"extend_existing": True},
    )

    # 实体标识字段
    entity_type: Mapped[int] = mapped_column(types.Int8, default=-1)  # 实体类型枚举值
    entity_id: Mapped[str] = mapped_column(String(), default="")      # 实体具体标识

    # 因子字段
    factor_name: Mapped[str] = mapped_column(String(), default="")               # 因子名称
    factor_value: Mapped[Decimal] = mapped_column(DECIMAL(16, 6), default=0)     # 因子值
    factor_category: Mapped[str] = mapped_column(String(), default="")           # 因子分类

    def get_entity_type_enum(self) -> Optional[ENTITY_TYPES]:
        """获取实体类型枚举对象"""
        return ENTITY_TYPES.from_int(self.entity_type)

    def set_entity_type(self, entity_type) -> None:
        """
        设置实体类型（支持多种输入格式）
        
        Args:
            entity_type: 可以是 ENTITY_TYPES 枚举、字符串或整数
            
        Raises:
            ValueError: 当输入的实体类型无效时
        """
        validated = ENTITY_TYPES.validate_input(entity_type)
        if validated is not None:
            self.entity_type = validated
        else:
            raise ValueError(f"Invalid entity_type: {entity_type}")

    def update(
        self,
        entity_type: Optional[ENTITY_TYPES] = None,
        entity_id: Optional[str] = None,
        factor_name: Optional[str] = None,
        factor_value: Optional[Decimal] = None,
        factor_category: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None,
        source: Optional[SOURCE_TYPES] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        更新因子数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_name: 因子名称
            factor_value: 因子值
            factor_category: 因子分类
            timestamp: 时间戳
            source: 数据源
        """
        if entity_type is not None:
            self.set_entity_type(entity_type)
        if entity_id is not None:
            self.entity_id = entity_id
        if factor_name is not None:
            self.factor_name = factor_name
        if factor_value is not None:
            self.factor_value = to_decimal(factor_value)
        if factor_category is not None:
            self.factor_category = factor_category
        if timestamp is not None:
            self.timestamp = timestamp
        if source is not None:
            self.source = SOURCE_TYPES.validate_input(source) or -1

    def __repr__(self) -> str:
        return base_repr(self, "DBFactor", 12, 60)