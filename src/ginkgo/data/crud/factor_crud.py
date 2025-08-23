#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import List, Optional, Union, Any, Dict
import pandas as pd
from datetime import datetime
from decimal import Decimal

from .base_crud import BaseCRUD
from ..models import MFactor
from ...enums import ENTITY_TYPES, SOURCE_TYPES
from ...libs import datetime_normalize, GLOG, Number, to_decimal
from ..access_control import restrict_crud_access


@restrict_crud_access
class FactorCRUD(BaseCRUD[MFactor]):
    """
    因子数据CRUD操作，支持多种实体类型的因子管理
    
    支持的实体类型：
    - STOCK: 个股因子 (RSI, PE, ROE等)
    - MARKET: 市场因子 (VIX, 市场情绪等)
    - COUNTRY: 宏观因子 (GDP增长率, CPI, 利率等)
    - INDUSTRY: 行业因子 (行业轮动, 估值等)
    - COMMODITY: 商品因子 (库存水平, 期货溢价等)
    - CURRENCY: 汇率因子 (汇率波动率, 利差等)
    - BOND: 债券因子 (收益率曲线, 信用利差等)
    - FUND: 基金因子 (基金评级, 业绩指标等)
    - CRYPTO: 加密货币因子 (链上活跃度, 挖矿难度等)
    """

    def __init__(self):
        super().__init__(MFactor)

    def _get_field_config(self) -> dict:
        """
        定义因子数据的字段配置 - 业务必填字段验证
        
        Returns:
            dict: 字段配置字典
        """
        return {
            # 实体类型 - 枚举值，必填
            "entity_type": {
                "type": "enum",
                "choices": [e for e in ENTITY_TYPES if e != ENTITY_TYPES.VOID],
            },
            # 实体标识 - 非空字符串
            "entity_id": {"type": "string", "min": 1},
            # 因子名称 - 非空字符串
            "factor_name": {"type": "string", "min": 1},
            # 因子值 - 数值类型
            "factor_value": {"type": ["decimal", "float", "int"]},
            # 因子分类 - 非空字符串  
            "factor_category": {"type": "string", "min": 1},
        }

    def _create_from_params(self, **kwargs) -> MFactor:
        """
        从参数创建因子对象
        
        Args:
            **kwargs: 因子参数
            
        Returns:
            MFactor: 创建的因子对象
        """
        factor = MFactor()
        factor.update(
            entity_type=kwargs.get("entity_type"),
            entity_id=kwargs.get("entity_id", ""),
            factor_name=kwargs.get("factor_name", ""),
            factor_value=kwargs.get("factor_value", 0),
            factor_category=kwargs.get("factor_category", ""),
            timestamp=datetime_normalize(kwargs.get("timestamp")) or datetime.now(),
            source=kwargs.get("source", SOURCE_TYPES.OTHER),
        )
        return factor

    def _convert_input_item(self, item: Any) -> Optional[MFactor]:
        """
        支持输入类型转换
        
        Args:
            item: 输入项，可以是字典、Series等
            
        Returns:
            Optional[MFactor]: 转换后的因子对象
        """
        if isinstance(item, dict):
            try:
                return self._create_from_params(**item)
            except Exception as e:
                GLOG.DEBUG(f"Failed to convert dict to MFactor: {e}")
                return None
        elif isinstance(item, pd.Series):
            try:
                return self._create_from_params(**item.to_dict())
            except Exception as e:
                GLOG.DEBUG(f"Failed to convert Series to MFactor: {e}")
                return None
        return None

    # ============================================================================
    # 因子特化查询方法
    # ============================================================================

    def get_factors_by_entity(
        self, 
        entity_type: Union[ENTITY_TYPES, str, int], 
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        factor_category: Optional[str] = None,
        as_dataframe: bool = False
    ) -> Union[List[MFactor], pd.DataFrame]:
        """
        查询指定实体的因子数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_names: 因子名称列表，None表示查询所有
            start_time: 开始时间
            end_time: 结束时间
            factor_category: 因子分类过滤
            as_dataframe: 是否返回DataFrame
            
        Returns:
            因子数据列表或DataFrame
        """
        # 构建过滤条件
        filters = {}
        
        # 实体类型转换
        if isinstance(entity_type, ENTITY_TYPES):
            filters["entity_type"] = entity_type.value
        elif isinstance(entity_type, str):
            entity_enum = ENTITY_TYPES.enum_convert(entity_type)
            if entity_enum:
                filters["entity_type"] = entity_enum.value
            else:
                raise ValueError(f"Invalid entity_type string: {entity_type}")
        elif isinstance(entity_type, int):
            filters["entity_type"] = entity_type
        
        filters["entity_id"] = entity_id
        
        # 时间范围过滤
        if start_time:
            filters["timestamp__gte"] = start_time
        if end_time:
            filters["timestamp__lte"] = end_time
            
        # 因子分类过滤
        if factor_category:
            filters["factor_category"] = factor_category
            
        # 因子名称过滤
        if factor_names:
            filters["factor_name__in"] = factor_names
        
        return self.find(
            filters=filters,
            as_dataframe=as_dataframe,
            order_by="timestamp",
            desc_order=False
        )

    def get_latest_factors_by_entity(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        factor_category: Optional[str] = None,
        as_dataframe: bool = False
    ) -> Union[List[MFactor], pd.DataFrame]:
        """
        获取指定实体的最新因子值
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识  
            factor_names: 因子名称列表
            factor_category: 因子分类过滤
            as_dataframe: 是否返回DataFrame
            
        Returns:
            最新因子数据
        """
        # 如果指定了因子名称，分别查询每个因子的最新值
        if factor_names:
            all_factors = []
            for factor_name in factor_names:
                factors = self.get_factors_by_entity(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    factor_names=[factor_name],
                    factor_category=factor_category,
                    as_dataframe=False
                )
                if factors:
                    # 获取最新的那个
                    latest_factor = max(factors, key=lambda x: x.timestamp)
                    all_factors.append(latest_factor)
            
            if as_dataframe and all_factors:
                # 转换为DataFrame
                data = []
                for factor in all_factors:
                    data.append({
                        'entity_type': factor.entity_type,
                        'entity_id': factor.entity_id,
                        'factor_name': factor.factor_name,
                        'factor_value': factor.factor_value,
                        'factor_category': factor.factor_category,
                        'timestamp': factor.timestamp
                    })
                return pd.DataFrame(data)
            return all_factors
        else:
            # 查询所有因子，按因子名称分组取最新
            all_factors = self.get_factors_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                factor_category=factor_category,
                as_dataframe=False
            )
            
            if not all_factors:
                return pd.DataFrame() if as_dataframe else []
            
            # 按因子名称分组，取每组最新的
            factor_groups = {}
            for factor in all_factors:
                factor_name = factor.factor_name
                if factor_name not in factor_groups or factor.timestamp > factor_groups[factor_name].timestamp:
                    factor_groups[factor_name] = factor
            
            latest_factors = list(factor_groups.values())
            
            if as_dataframe:
                data = []
                for factor in latest_factors:
                    data.append({
                        'entity_type': factor.entity_type,
                        'entity_id': factor.entity_id,
                        'factor_name': factor.factor_name,
                        'factor_value': factor.factor_value,
                        'factor_category': factor.factor_category,
                        'timestamp': factor.timestamp
                    })
                return pd.DataFrame(data)
            return latest_factors

    def get_available_entities(
        self, 
        entity_type: Optional[Union[ENTITY_TYPES, str, int]] = None
    ) -> List[str]:
        """
        获取可用的实体标识列表
        
        Args:
            entity_type: 实体类型过滤，None表示所有类型
            
        Returns:
            实体标识列表
        """
        filters = {}
        if entity_type is not None:
            if isinstance(entity_type, ENTITY_TYPES):
                filters["entity_type"] = entity_type.value
            elif isinstance(entity_type, str):
                entity_enum = ENTITY_TYPES.enum_convert(entity_type)
                if entity_enum:
                    filters["entity_type"] = entity_enum.value
            elif isinstance(entity_type, int):
                filters["entity_type"] = entity_type
        
        return self.find(
            filters=filters,
            distinct_field="entity_id"
        )

    def get_available_factors(
        self,
        entity_type: Optional[Union[ENTITY_TYPES, str, int]] = None,
        factor_category: Optional[str] = None
    ) -> List[str]:
        """
        获取可用的因子名称列表
        
        Args:
            entity_type: 实体类型过滤
            factor_category: 因子分类过滤
            
        Returns:
            因子名称列表
        """
        filters = {}
        if entity_type is not None:
            if isinstance(entity_type, ENTITY_TYPES):
                filters["entity_type"] = entity_type.value
            elif isinstance(entity_type, str):
                entity_enum = ENTITY_TYPES.enum_convert(entity_type)
                if entity_enum:
                    filters["entity_type"] = entity_enum.value
            elif isinstance(entity_type, int):
                filters["entity_type"] = entity_type
                
        if factor_category:
            filters["factor_category"] = factor_category
        
        return self.find(
            filters=filters,
            distinct_field="factor_name"
        )

    def remove_factors_by_entity(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> None:
        """
        删除指定实体的因子数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_names: 因子名称列表，None表示删除所有
            start_time: 开始时间
            end_time: 结束时间
        """
        filters = {}
        
        # 实体类型转换
        if isinstance(entity_type, ENTITY_TYPES):
            filters["entity_type"] = entity_type.value
        elif isinstance(entity_type, str):
            entity_enum = ENTITY_TYPES.enum_convert(entity_type)
            if entity_enum:
                filters["entity_type"] = entity_enum.value
            else:
                raise ValueError(f"Invalid entity_type string: {entity_type}")
        elif isinstance(entity_type, int):
            filters["entity_type"] = entity_type
            
        filters["entity_id"] = entity_id
        
        # 时间范围过滤
        if start_time:
            filters["timestamp__gte"] = start_time
        if end_time:
            filters["timestamp__lte"] = end_time
            
        # 因子名称过滤
        if factor_names:
            filters["factor_name__in"] = factor_names
        
        self.remove(filters)