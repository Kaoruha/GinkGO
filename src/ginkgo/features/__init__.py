"""
Ginkgo Features Module - 特征因子解析引擎

基于表达式的因子计算和管理功能，采用三层架构设计：
- Definitions: 因子和指标定义层
- Engines: 计算和解析引擎层  
- Services: 高级业务逻辑服务层

使用示例:
    from ginkgo import services
    
    # 便捷的Alpha158因子计算
    factor_service = services.features.services.factor()
    result = factor_service.calculate_alpha158_factors(
        entity_ids=["000001.SZ", "000002.SZ"],
        start_date="2024-01-01",
        end_date="2024-08-17"
    )
    
    # 获取因子定义
    alpha158 = services.features.definitions.alpha158()
    expressions = alpha158.get_all_factors()
    
    # 表达式处理服务
    expr_service = services.features.services.expression()
    validation = expr_service.validate_expressions(expressions)
"""

from ginkgo.features.containers import feature_container

# 导出核心模块
from ginkgo.features import definitions
from ginkgo.features import engines  
from ginkgo.features import services

# 导出主要类供直接使用
from ginkgo.features.definitions import (
    Alpha158Factors,
    MovingAverageIndicators,
    OscillatorIndicators,
    BandIndicators,
    PatternDetectionIndicators
)

from ginkgo.features.engines import (
    FactorEngine,
    ExpressionEngine,
    ExpressionParser,
    OperatorRegistry
)

from ginkgo.features.services import (
    FactorService,
    ExpressionService
)

# 便捷函数接口 - 参考data模块模式
def calculate_alpha158_factors(entity_ids, start_date, end_date, factor_names=None):
    """
    便捷函数：计算Alpha158因子
    
    Args:
        entity_ids: 实体ID列表
        start_date: 开始日期
        end_date: 结束日期
        factor_names: 指定因子名称（可选）
        
    Returns:
        ServiceResult: 计算结果
    """
    factor_service = feature_container.services.factor()
    return factor_service.calculate_alpha158_factors(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date,
        factor_names=factor_names
    )

def calculate_core_factors(entity_ids, start_date, end_date):
    """
    便捷函数：计算核心常用因子
    """
    factor_service = feature_container.services.factor()
    return factor_service.calculate_core_factors(
        entity_ids=entity_ids,
        start_date=start_date,
        end_date=end_date
    )

def get_alpha158_expressions():
    """
    便捷函数：获取Alpha158因子表达式
    """
    return Alpha158Factors.get_all_factors()

def get_core_expressions():
    """
    便捷函数：获取核心因子表达式
    """
    return Alpha158Factors.get_core_factors()

def validate_expressions(expressions):
    """
    便捷函数：验证表达式
    """
    expr_service = feature_container.services.expression()
    return expr_service.validate_expressions(expressions)

def get_available_operators():
    """
    便捷函数：获取可用操作符
    """
    expr_service = feature_container.services.expression()
    return expr_service.get_available_operators()

__all__ = [
    # 容器
    "feature_container",
    
    # 模块
    "definitions",
    "engines", 
    "services",
    
    # 主要类
    "Alpha158Factors",
    "MovingAverageIndicators",
    "OscillatorIndicators", 
    "BandIndicators",
    "PatternDetectionIndicators",
    "FactorEngine",
    "ExpressionEngine",
    "ExpressionParser",
    "OperatorRegistry",
    "FactorService",
    "ExpressionService",
    
    # 便捷函数
    "calculate_alpha158_factors",
    "calculate_core_factors",
    "get_alpha158_expressions",
    "get_core_expressions", 
    "validate_expressions",
    "get_available_operators",
]

__version__ = "2.0.0"
__author__ = "Ginkgo Team" 
__description__ = "特征因子解析引擎 - 基于表达式的因子计算（重构版）"