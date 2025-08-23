#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
因子管理服务

提供因子数据的计算、存储、查询和分析功能，支持多种实体类型：
- 个股因子：技术指标、基本面指标等
- 市场因子：市场情绪、波动率等  
- 宏观因子：GDP、CPI、利率等
- 行业因子：行业轮动、估值等
- 商品因子：库存、期货溢价等
- 汇率因子：汇率波动率、利差等
- 债券因子：收益率曲线、信用利差等
- 基金因子：基金评级、业绩指标等
- 加密货币因子：链上数据、挖矿指标等
"""

import time
from datetime import datetime, timedelta
from typing import List, Union, Any, Dict, Optional, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal

from ...libs import GLOG, datetime_normalize, to_decimal, retry, time_logger, cache_with_expiration
from ...enums import ENTITY_TYPES, SOURCE_TYPES
from .base_service import DataService, ServiceResult


class FactorService(DataService):
    """
    因子管理服务类
    
    提供因子的计算、存储、查询和分析功能，支持多种实体类型的因子管理。
    """

    def __init__(self, factor_crud, **additional_deps):
        """
        初始化因子服务
        
        Args:
            factor_crud: 因子CRUD操作对象
            **additional_deps: 其他依赖服务
        """
        super().__init__(crud_repo=factor_crud, data_source=None, **additional_deps)
        self.factor_crud = factor_crud

    # ============================================================================
    # 因子数据存储和查询
    # ============================================================================

    @time_logger
    @retry(max_try=3)
    def add_factor_batch(
        self,
        factors_data: List[Dict[str, Any]]
    ) -> ServiceResult:
        """
        批量添加因子数据
        
        Args:
            factors_data: 因子数据列表，每个元素为包含因子信息的字典
            
        Returns:
            ServiceResult: 操作结果
        """
        result = self.create_result()
        
        try:
            # 数据验证和转换
            validated_factors = []
            for i, factor_data in enumerate(factors_data):
                try:
                    # 确保必要字段存在
                    required_fields = ['entity_type', 'entity_id', 'factor_name', 'factor_value']
                    for field in required_fields:
                        if field not in factor_data:
                            raise ValueError(f"Missing required field: {field}")
                    
                    # 类型转换
                    processed_factor = {
                        'entity_type': factor_data['entity_type'],
                        'entity_id': str(factor_data['entity_id']),
                        'factor_name': str(factor_data['factor_name']),
                        'factor_value': to_decimal(factor_data['factor_value']),
                        'factor_category': str(factor_data.get('factor_category', '')),
                        'timestamp': datetime_normalize(factor_data.get('timestamp', datetime.now())),
                        'source': factor_data.get('source', SOURCE_TYPES.OTHER)
                    }
                    
                    validated_factors.append(processed_factor)
                    
                except Exception as e:
                    self._logger.ERROR(f"Failed to validate factor data at index {i}: {e}")
                    continue
            
            if not validated_factors:
                result.error = "No valid factor data to add"
                return result
            
            # 批量添加到数据库
            add_result = self.factor_crud.add_batch(validated_factors)
            
            result.success = True
            result.set_data("records_added", len(validated_factors))
            result.set_data("add_result", add_result)
            
            self._logger.INFO(f"Successfully added {len(validated_factors)} factors")
            
        except Exception as e:
            result.error = f"Failed to add factor batch: {str(e)}"
            self._logger.ERROR(f"Factor batch addition failed: {e}")
        
        return result

    @time_logger
    def get_factors_by_entity(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        factor_category: Optional[str] = None,
        as_dataframe: bool = True
    ) -> ServiceResult:
        """
        查询指定实体的因子数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_names: 因子名称列表
            start_time: 开始时间
            end_time: 结束时间  
            factor_category: 因子分类
            as_dataframe: 是否返回DataFrame格式
            
        Returns:
            ServiceResult: 查询结果
        """
        result = self.create_result()
        
        try:
            factors = self.factor_crud.get_factors_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                factor_names=factor_names,
                start_time=start_time,
                end_time=end_time,
                factor_category=factor_category,
                as_dataframe=as_dataframe
            )
            
            result.success = True
            result.set_data("factors", factors)
            result.set_data("count", len(factors) if isinstance(factors, list) else factors.shape[0])
            
            self._logger.DEBUG(f"Retrieved factors for entity {entity_type}:{entity_id}")
            
        except Exception as e:
            result.error = f"Failed to get factors: {str(e)}"
            self._logger.ERROR(f"Factor query failed: {e}")
            
        return result

    @time_logger
    def get_latest_factors_by_entity(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        factor_category: Optional[str] = None,
        as_dataframe: bool = True
    ) -> ServiceResult:
        """
        获取指定实体的最新因子值
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_names: 因子名称列表
            factor_category: 因子分类
            as_dataframe: 是否返回DataFrame格式
            
        Returns:
            ServiceResult: 最新因子数据
        """
        result = self.create_result()
        
        try:
            latest_factors = self.factor_crud.get_latest_factors_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                factor_names=factor_names,
                factor_category=factor_category,
                as_dataframe=as_dataframe
            )
            
            result.success = True
            result.set_data("latest_factors", latest_factors)
            result.set_data("count", len(latest_factors) if isinstance(latest_factors, list) else latest_factors.shape[0])
            
            self._logger.DEBUG(f"Retrieved latest factors for entity {entity_type}:{entity_id}")
            
        except Exception as e:
            result.error = f"Failed to get latest factors: {str(e)}"
            self._logger.ERROR(f"Latest factor query failed: {e}")
            
        return result

    # ============================================================================
    # 因子分析功能
    # ============================================================================

    @time_logger
    def calculate_factor_correlation(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_ids: List[str],
        factor_names: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        计算因子相关性矩阵
        
        Args:
            entity_type: 实体类型
            entity_ids: 实体标识列表
            factor_names: 因子名称列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            ServiceResult: 包含相关性矩阵的结果
        """
        result = self.create_result()
        
        try:
            # 收集所有因子数据
            all_factor_data = []
            
            for entity_id in entity_ids:
                factors_result = self.get_factors_by_entity(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    factor_names=factor_names,
                    start_time=start_time,
                    end_time=end_time,
                    as_dataframe=True
                )
                
                if factors_result.success:
                    factors_df = factors_result.get_data("factors")
                    if not factors_df.empty:
                        factors_df['entity_factor'] = factors_df['entity_id'] + '_' + factors_df['factor_name']
                        all_factor_data.append(factors_df)
            
            if not all_factor_data:
                result.error = "No factor data found for correlation analysis"
                return result
            
            # 合并所有数据
            combined_df = pd.concat(all_factor_data, ignore_index=True)
            
            # 构建因子值矩阵
            pivot_df = combined_df.pivot_table(
                index='timestamp',
                columns='entity_factor',
                values='factor_value',
                aggfunc='last'  # 如果同一时间有多个值，取最后一个
            )
            
            # 计算相关性矩阵
            correlation_matrix = pivot_df.corr()
            
            result.success = True
            result.set_data("correlation_matrix", correlation_matrix)
            result.set_data("factor_data", pivot_df)
            result.set_data("entity_count", len(entity_ids))
            result.set_data("factor_count", len(factor_names))
            
            self._logger.INFO(f"Calculated correlation matrix for {len(entity_ids)} entities and {len(factor_names)} factors")
            
        except Exception as e:
            result.error = f"Failed to calculate factor correlation: {str(e)}"
            self._logger.ERROR(f"Factor correlation calculation failed: {e}")
            
        return result

    @time_logger
    def analyze_factor_distribution(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        factor_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        分析因子分布特征
        
        Args:
            entity_type: 实体类型
            factor_name: 因子名称
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            ServiceResult: 包含分布统计信息的结果
        """
        result = self.create_result()
        
        try:
            # 查询因子数据
            filters = {
                "factor_name": factor_name
            }
            
            # 实体类型处理
            if isinstance(entity_type, ENTITY_TYPES):
                filters["entity_type"] = entity_type.value
            elif isinstance(entity_type, str):
                entity_enum = ENTITY_TYPES.enum_convert(entity_type)
                if entity_enum:
                    filters["entity_type"] = entity_enum.value
            elif isinstance(entity_type, int):
                filters["entity_type"] = entity_type
            
            # 时间范围
            if start_time:
                filters["timestamp__gte"] = start_time
            if end_time:
                filters["timestamp__lte"] = end_time
            
            factors_df = self.factor_crud.find(filters=filters, as_dataframe=True)
            
            if factors_df.empty:
                result.error = f"No data found for factor {factor_name}"
                return result
            
            # 计算分布统计
            factor_values = factors_df['factor_value'].astype(float)
            
            distribution_stats = {
                'count': len(factor_values),
                'mean': float(factor_values.mean()),
                'std': float(factor_values.std()),
                'min': float(factor_values.min()),
                'max': float(factor_values.max()),
                'median': float(factor_values.median()),
                'q25': float(factor_values.quantile(0.25)),
                'q75': float(factor_values.quantile(0.75)),
                'skewness': float(factor_values.skew()),
                'kurtosis': float(factor_values.kurtosis())
            }
            
            # 异常值检测（IQR方法）
            q1 = factor_values.quantile(0.25)
            q3 = factor_values.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outliers = factor_values[(factor_values < lower_bound) | (factor_values > upper_bound)]
            distribution_stats['outlier_count'] = len(outliers)
            distribution_stats['outlier_percentage'] = len(outliers) / len(factor_values) * 100
            
            result.success = True
            result.set_data("distribution_stats", distribution_stats)
            result.set_data("factor_data", factors_df)
            result.set_data("outliers", outliers.tolist())
            
            self._logger.INFO(f"Analyzed distribution for factor {factor_name}: {distribution_stats['count']} records")
            
        except Exception as e:
            result.error = f"Failed to analyze factor distribution: {str(e)}"
            self._logger.ERROR(f"Factor distribution analysis failed: {e}")
            
        return result

    # ============================================================================
    # 数据管理功能
    # ============================================================================

    @cache_with_expiration(expiration_seconds=300)  # 缓存5分钟
    def get_available_entities(
        self, 
        entity_type: Optional[Union[ENTITY_TYPES, str, int]] = None
    ) -> ServiceResult:
        """
        获取可用的实体列表
        
        Args:
            entity_type: 实体类型过滤
            
        Returns:
            ServiceResult: 可用实体列表
        """
        result = self.create_result()
        
        try:
            entities = self.factor_crud.get_available_entities(entity_type=entity_type)
            
            result.success = True
            result.set_data("entities", entities)
            result.set_data("count", len(entities))
            
            self._logger.DEBUG(f"Retrieved {len(entities)} available entities")
            
        except Exception as e:
            result.error = f"Failed to get available entities: {str(e)}"
            self._logger.ERROR(f"Available entities query failed: {e}")
            
        return result

    @cache_with_expiration(expiration_seconds=300)  # 缓存5分钟
    def get_available_factors(
        self,
        entity_type: Optional[Union[ENTITY_TYPES, str, int]] = None,
        factor_category: Optional[str] = None
    ) -> ServiceResult:
        """
        获取可用的因子列表
        
        Args:
            entity_type: 实体类型过滤
            factor_category: 因子分类过滤
            
        Returns:
            ServiceResult: 可用因子列表
        """
        result = self.create_result()
        
        try:
            factors = self.factor_crud.get_available_factors(
                entity_type=entity_type,
                factor_category=factor_category
            )
            
            result.success = True
            result.set_data("factors", factors)
            result.set_data("count", len(factors))
            
            self._logger.DEBUG(f"Retrieved {len(factors)} available factors")
            
        except Exception as e:
            result.error = f"Failed to get available factors: {str(e)}"
            self._logger.ERROR(f"Available factors query failed: {e}")
            
        return result

    @time_logger
    def delete_factors_by_entity(
        self,
        entity_type: Union[ENTITY_TYPES, str, int],
        entity_id: str,
        factor_names: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> ServiceResult:
        """
        删除指定实体的因子数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体标识
            factor_names: 因子名称列表
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            ServiceResult: 删除操作结果
        """
        result = self.create_result()
        
        try:
            self.factor_crud.remove_factors_by_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                factor_names=factor_names,
                start_time=start_time,
                end_time=end_time
            )
            
            result.success = True
            self._logger.INFO(f"Deleted factors for entity {entity_type}:{entity_id}")
            
        except Exception as e:
            result.error = f"Failed to delete factors: {str(e)}"
            self._logger.ERROR(f"Factor deletion failed: {e}")
            
        return result

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取因子服务健康状态
        
        Returns:
            服务健康状态信息
        """
        base_status = super().get_health_status()
        
        try:
            # 检查因子数据总数
            total_factors = self.factor_crud.count()
            
            # 检查各实体类型的因子数量
            entity_type_counts = {}
            for entity_type in ENTITY_TYPES:
                if entity_type != ENTITY_TYPES.VOID:
                    count = self.factor_crud.count({"entity_type": entity_type.value})
                    entity_type_counts[entity_type.name] = count
            
            base_status.update({
                "total_factors": total_factors,
                "entity_type_counts": entity_type_counts,
            })
            
        except Exception as e:
            base_status["health_check_error"] = str(e)
            
        return base_status