"""
表达式服务 - 通用表达式处理服务

提供表达式验证、解析、执行等通用服务，
支持各种表达式集合的统一处理。
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult

from ginkgo.features.engines import ExpressionEngine


class ExpressionService:
    """
    表达式服务 - 通用表达式处理接口
    
    提供：
    - 表达式验证和依赖分析
    - 批量表达式解析
    - 表达式执行和结果处理
    - 操作符管理和查询
    """
    
    def __init__(self, expression_engine: ExpressionEngine):
        """
        初始化表达式服务
        
        Args:
            expression_engine: 表达式处理引擎
        """
        self.expression_engine = expression_engine
        
        GLOG.INFO("ExpressionService initialized successfully")
    
    def validate_expressions(self, expressions: Dict[str, str]) -> ServiceResult:
        """
        验证表达式集合
        
        Args:
            expressions: 表达式字典 {name: expression}
            
        Returns:
            ServiceResult: 验证结果，包含无效表达式信息
        """
        return self.expression_engine.validate_expressions(expressions)
    
    def parse_expressions(self, expressions: Dict[str, str]) -> ServiceResult:
        """
        解析表达式集合为AST
        
        Args:
            expressions: 表达式字典
            
        Returns:
            ServiceResult: 解析结果，包含AST对象
        """
        return self.expression_engine.parse_expressions(expressions)
    
    def analyze_dependencies(self, expressions: Dict[str, str]) -> ServiceResult:
        """
        分析表达式依赖关系
        
        Args:
            expressions: 表达式字典
            
        Returns:
            ServiceResult: 依赖分析结果
        """
        return self.expression_engine.analyze_dependencies(expressions)
    
    def execute_expression(self, expression: str, data: pd.DataFrame) -> ServiceResult:
        """
        执行单个表达式
        
        Args:
            expression: 表达式字符串
            data: 输入数据
            
        Returns:
            ServiceResult: 执行结果
        """
        return self.expression_engine.execute_expression(expression, data)
    
    def batch_execute(self, expressions: Dict[str, str], data: pd.DataFrame) -> ServiceResult:
        """
        批量执行表达式
        
        Args:
            expressions: 表达式字典
            data: 输入数据
            
        Returns:
            ServiceResult: 批量执行结果
        """
        return self.expression_engine.batch_execute(expressions, data)
    
    def get_available_operators(self) -> List[str]:
        """获取可用操作符列表"""
        return self.expression_engine.get_available_operators()
    
    def get_operator_info(self, operator_name: str) -> Optional[Dict[str, Any]]:
        """
        获取操作符详细信息
        
        Args:
            operator_name: 操作符名称
            
        Returns:
            Dict: 操作符信息，包含签名、描述等
        """
        try:
            registry = self.expression_engine.operator_registry
            if registry.is_function_registered(operator_name):
                return {
                    "name": operator_name,
                    "registered": True,
                    # 可以扩展更多信息，如参数签名、文档等
                }
            return None
        except Exception as e:
            GLOG.ERROR(f"获取操作符信息失败: {e}")
            return None
    
    def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        return {
            "available_operators": len(self.get_available_operators()),
            "engine_stats": self.expression_engine.get_engine_stats(),
        }