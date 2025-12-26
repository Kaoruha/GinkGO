"""
Factor Engine - 因子计算引擎

核心计算引擎，负责：
- 表达式解析和执行
- 因子批量计算
- 结果存储和管理
- 错误处理和日志记录
"""

from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ginkgo.libs import GLOG
from ginkgo.libs import cache_with_expiration, time_logger, retry
from ginkgo.enums import ENTITY_TYPES, SOURCE_TYPES
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.features.engines.expression.parser import ExpressionParser, ParseError


class FactorEngine:
    """
    因子计算引擎 - 遵循现有DI模式
    
    提供基于表达式的因子计算功能，支持：
    - 多种表达式语法
    - 批量计算和存储
    - 错误处理和恢复
    - 性能优化和缓存
    """
    
    def __init__(self, factor_service, bar_service, expression_parser=None):
        """
        初始化因子引擎
        
        Args:
            factor_service: 因子存储服务(来自data模块)
            bar_service: K线数据服务(来自data模块)
            expression_parser: 表达式解析器(可选，默认创建新实例)
        """
        self.factor_service = factor_service
        self.bar_service = bar_service
        self.parser = expression_parser or ExpressionParser()
        
        # 统计信息
        self.stats = {
            "expressions_parsed": 0,
            "factors_calculated": 0,
            "errors_encountered": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        GLOG.INFO("FactorEngine initialized successfully")
    
    @time_logger
    def calculate_and_store(self, 
                           expressions: Dict[str, str],
                           entity_ids: List[str], 
                           start_date: str, 
                           end_date: str,
                           entity_type: ENTITY_TYPES = ENTITY_TYPES.STOCK,
                           batch_size: int = 1000,
                           continue_on_error: bool = True) -> ServiceResult:
        """
        计算并存储因子
        
        Args:
            expressions: 因子表达式字典 {"factor_name": "expression"}
            entity_ids: 实体ID列表 ["000001.SZ", "000002.SZ"]
            start_date: 开始日期 "2024-01-01"
            end_date: 结束日期 "2024-08-17"
            entity_type: 实体类型，默认为STOCK
            batch_size: 批量存储大小
            continue_on_error: 遇到错误是否继续处理其他实体
            
        Returns:
            ServiceResult: 计算结果和统计信息
        """
        result = ServiceResult()
        
        try:
            # 预验证表达式
            invalid_expressions = self._validate_expressions(expressions)
            if invalid_expressions:
                result.error = f"Invalid expressions: {invalid_expressions}"
                return result
            
            # 统计信息
            total_entities = len(entity_ids)
            total_expressions = len(expressions)
            processed_entities = 0
            total_factors_stored = 0
            errors = []
            
            GLOG.INFO(f"Starting factor calculation for {total_entities} entities, {total_expressions} expressions")
            
            # 逐个处理实体
            for i, entity_id in enumerate(entity_ids):
                try:
                    GLOG.DEBUG(f"Processing entity {i+1}/{total_entities}: {entity_id}")
                    
                    # 计算该实体的所有因子
                    entity_result = self._calculate_entity_factors(
                        entity_id=entity_id,
                        expressions=expressions,
                        start_date=start_date,
                        end_date=end_date,
                        entity_type=entity_type,
                        batch_size=batch_size
                    )
                    
                    if entity_result.success:
                        factors_count = entity_result.get_data("factors_stored", 0)
                        total_factors_stored += factors_count
                        processed_entities += 1
                        GLOG.DEBUG(f"Successfully processed {entity_id}: {factors_count} factors stored")
                    else:
                        error_msg = f"Failed to process {entity_id}: {entity_result.error}"
                        errors.append(error_msg)
                        GLOG.ERROR(error_msg)
                        
                        if not continue_on_error:
                            result.error = error_msg
                            return result
                    
                except Exception as e:
                    error_msg = f"Exception processing entity {entity_id}: {str(e)}"
                    errors.append(error_msg)
                    GLOG.ERROR(error_msg)
                    self.stats["errors_encountered"] += 1
                    
                    if not continue_on_error:
                        result.error = error_msg
                        return result
            
            # 设置结果
            result.success = True
            result.set_data("processed_entities", processed_entities)
            result.set_data("total_factors_stored", total_factors_stored)
            result.set_data("errors", errors)
            result.set_data("stats", self.stats.copy())
            
            success_rate = processed_entities / total_entities * 100 if total_entities > 0 else 0
            GLOG.INFO(f"Factor calculation completed: {processed_entities}/{total_entities} entities "
                     f"({success_rate:.1f}%), {total_factors_stored} factors stored")
            
            if errors:
                GLOG.WARN(f"Encountered {len(errors)} errors during processing")
            
        except Exception as e:
            result.error = f"Factor calculation failed: {str(e)}"
            GLOG.ERROR(f"Factor calculation failed: {e}")
            self.stats["errors_encountered"] += 1
        
        return result
    
    def _validate_expressions(self, expressions: Dict[str, str]) -> List[str]:
        """
        预验证表达式语法
        
        Args:
            expressions: 表达式字典
            
        Returns:
            List[str]: 无效表达式的名称列表
        """
        invalid_expressions = []
        
        for factor_name, expression in expressions.items():
            try:
                if not self.parser.validate_expression(expression):
                    invalid_expressions.append(factor_name)
                    GLOG.ERROR(f"Invalid expression for {factor_name}: {expression}")
                else:
                    self.stats["expressions_parsed"] += 1
            except Exception as e:
                invalid_expressions.append(factor_name)
                GLOG.ERROR(f"Failed to validate expression for {factor_name}: {e}")
        
        return invalid_expressions
    
    def _calculate_entity_factors(self, 
                                 entity_id: str,
                                 expressions: Dict[str, str],
                                 start_date: str,
                                 end_date: str,
                                 entity_type: ENTITY_TYPES,
                                 batch_size: int) -> ServiceResult:
        """
        计算单个实体的所有因子
        
        Args:
            entity_id: 实体ID
            expressions: 表达式字典
            start_date: 开始日期
            end_date: 结束日期
            entity_type: 实体类型
            batch_size: 批量大小
            
        Returns:
            ServiceResult: 计算结果
        """
        result = ServiceResult()
        
        try:
            # 获取K线数据
            bars_result = self._get_entity_data(entity_id, start_date, end_date)
            if not bars_result.success:
                result.error = f"Failed to get data for {entity_id}: {bars_result.error}"
                return result
            
            bars_data = bars_result.get_data("bars")
            if bars_data is None or bars_data.empty:
                result.error = f"No data available for {entity_id}"
                return result
            
            GLOG.DEBUG(f"Retrieved {len(bars_data)} data points for {entity_id}")
            
            # 计算所有因子
            all_calculated_factors = []
            
            for factor_name, expression in expressions.items():
                try:
                    factor_records = self._calculate_single_factor(
                        entity_id=entity_id,
                        entity_type=entity_type,
                        factor_name=factor_name,
                        expression=expression,
                        bars_data=bars_data
                    )
                    
                    if factor_records:
                        all_calculated_factors.extend(factor_records)
                        self.stats["factors_calculated"] += len(factor_records)
                        GLOG.DEBUG(f"Calculated {len(factor_records)} values for factor {factor_name}")
                    
                except Exception as e:
                    GLOG.ERROR(f"Failed to calculate factor {factor_name} for {entity_id}: {e}")
                    continue
            
            # 批量存储因子
            if all_calculated_factors:
                factors_stored = self._store_factors_in_batches(all_calculated_factors, batch_size)
                result.success = True
                result.set_data("factors_stored", factors_stored)
            else:
                result.success = True
                result.set_data("factors_stored", 0)
                GLOG.WARN(f"No factors calculated for {entity_id}")
            
        except Exception as e:
            result.error = f"Failed to calculate factors for {entity_id}: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result
    
    @cache_with_expiration(expiration_seconds=300)
    def _get_entity_data(self, entity_id: str, start_date: str, end_date: str) -> ServiceResult:
        """
        获取实体数据（带缓存）
        
        Args:
            entity_id: 实体ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            ServiceResult: 数据获取结果
        """
        result = ServiceResult()
        
        try:
            # 转换日期字符串为datetime对象
            from ginkgo.libs import datetime_normalize
            start_dt = datetime_normalize(start_date) if isinstance(start_date, str) else start_date
            end_dt = datetime_normalize(end_date) if isinstance(end_date, str) else end_date
            
            # 调用现有的get_bars方法
            bars_data = self.bar_service.get_bars(
                code=entity_id,
                start_date=start_dt,
                end_date=end_dt,
                as_dataframe=True,
                adjustment_type="NONE"  # features模块使用原始价格
            )
            
            if bars_data is not None and not bars_data.empty:
                result.success = True
                result.set_data("bars", bars_data)
                self.stats["cache_misses"] += 1
                GLOG.DEBUG(f"Retrieved {len(bars_data)} bars for {entity_id}")
            else:
                result.success = True
                result.set_data("bars", pd.DataFrame())  # 返回空DataFrame
                self.stats["cache_misses"] += 1
                GLOG.DEBUG(f"No bars found for {entity_id} in date range")
                
        except Exception as e:
            result.error = f"Failed to get bars data for {entity_id}: {str(e)}"
            GLOG.ERROR(result.error)
            
        return result
    
    def _calculate_single_factor(self, 
                                entity_id: str,
                                entity_type: ENTITY_TYPES,
                                factor_name: str,
                                expression: str,
                                bars_data: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        计算单个因子
        
        Args:
            entity_id: 实体ID
            entity_type: 实体类型
            factor_name: 因子名称
            expression: 因子表达式
            bars_data: K线数据
            
        Returns:
            List[Dict]: 因子记录列表
        """
        try:
            # 解析表达式为AST
            ast = self.parser.parse(expression)
            
            # 执行AST计算因子值
            factor_series = ast.execute(bars_data)
            
            if factor_series is None or len(factor_series) == 0:
                GLOG.WARN(f"Factor {factor_name} calculation returned empty result")
                return []
            
            # 转换为因子记录
            factor_records = []
            
            for timestamp, factor_value in factor_series.items():
                # 跳过NaN值
                if pd.isna(factor_value) or np.isinf(factor_value):
                    continue
                
                # 确保timestamp是datetime类型
                if isinstance(timestamp, str):
                    timestamp = pd.to_datetime(timestamp)
                elif hasattr(timestamp, 'to_pydatetime'):
                    timestamp = timestamp.to_pydatetime()
                
                factor_records.append({
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "factor_name": factor_name,
                    "factor_value": float(factor_value),
                    "factor_category": "computed",
                    "timestamp": timestamp,
                    "source": SOURCE_TYPES.OTHER
                })
            
            return factor_records
            
        except ParseError as e:
            GLOG.ERROR(f"Parse error for factor {factor_name}: {e}")
            return []
        except Exception as e:
            GLOG.ERROR(f"Calculation error for factor {factor_name}: {e}")
            return []
    
    @retry(max_try=3)
    def _store_factors_in_batches(self, factor_records: List[Dict[str, Any]], batch_size: int) -> int:
        """
        分批存储因子数据
        
        Args:
            factor_records: 因子记录列表
            batch_size: 批量大小
            
        Returns:
            int: 成功存储的记录数
        """
        total_stored = 0
        
        try:
            # 分批处理
            for i in range(0, len(factor_records), batch_size):
                batch = factor_records[i:i + batch_size]
                
                try:
                    store_result = self.factor_service.add_factor_batch(batch)
                    
                    if store_result.success:
                        stored_count = store_result.get_data("records_added", len(batch))
                        total_stored += stored_count
                        GLOG.DEBUG(f"Stored batch {i//batch_size + 1}: {stored_count} records")
                    else:
                        GLOG.ERROR(f"Failed to store batch {i//batch_size + 1}: {store_result.error}")
                        
                except Exception as e:
                    GLOG.ERROR(f"Exception storing batch {i//batch_size + 1}: {e}")
                    continue
            
            GLOG.INFO(f"Successfully stored {total_stored}/{len(factor_records)} factor records")
            
        except Exception as e:
            GLOG.ERROR(f"Failed to store factors in batches: {e}")
        
        return total_stored
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats = {
            "expressions_parsed": 0,
            "factors_calculated": 0,
            "errors_encountered": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        GLOG.INFO("FactorEngine stats reset")
    
    def validate_expression(self, expression: str) -> bool:
        """验证单个表达式"""
        return self.parser.validate_expression(expression)
    
    def get_expression_dependencies(self, expression: str) -> List[str]:
        """获取表达式依赖的字段"""
        return self.parser.get_dependencies(expression)
    
    def preview_calculation(self, 
                           expression: str,
                           entity_id: str,
                           start_date: str,
                           end_date: str,
                           limit: int = 10) -> ServiceResult:
        """
        预览因子计算结果（不存储）
        
        Args:
            expression: 因子表达式
            entity_id: 实体ID
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回的记录数限制
            
        Returns:
            ServiceResult: 预览结果
        """
        result = ServiceResult()
        
        try:
            # 验证表达式
            if not self.parser.validate_expression(expression):
                result.error = "Invalid expression syntax"
                return result
            
            # 获取数据
            bars_result = self._get_entity_data(entity_id, start_date, end_date)
            if not bars_result.success:
                result.error = f"Failed to get data: {bars_result.error}"
                return result
            
            bars_data = bars_result.get_data("bars")
            if bars_data is None or bars_data.empty:
                result.error = "No data available"
                return result
            
            # 解析和执行表达式
            ast = self.parser.parse(expression)
            factor_series = ast.execute(bars_data)
            
            # 准备预览结果
            preview_data = []
            count = 0
            
            for timestamp, value in factor_series.items():
                if count >= limit:
                    break
                
                if not pd.isna(value) and not np.isinf(value):
                    preview_data.append({
                        "timestamp": timestamp,
                        "value": float(value)
                    })
                    count += 1
            
            result.success = True
            result.set_data("preview", preview_data)
            result.set_data("total_points", len(factor_series))
            result.set_data("valid_points", count)
            result.set_data("dependencies", self.parser.get_dependencies(expression))
            
        except Exception as e:
            result.error = f"Preview calculation failed: {str(e)}"
            GLOG.ERROR(result.error)
        
        return result