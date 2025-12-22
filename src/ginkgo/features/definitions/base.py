"""
因子定义基类 - 统一接口和业务逻辑

所有因子定义类的基类，实现完整的业务逻辑，
子类只需提供配置数据：NAME, DESCRIPTION, EXPRESSIONS, CATEGORIES
"""

from typing import Dict, List, Optional, Any
import re
from abc import ABC
from ginkgo.libs import GLOG


class BaseDefinition(ABC):
    """
    因子定义基类
    
    子类只需定义以下类属性：
    - NAME: str - 定义名称
    - DESCRIPTION: str - 描述信息
    - EXPRESSIONS: Dict[str, str] - 表达式字典 {name: expression}
    - CATEGORIES: Dict[str, List[str]] - 分类字典 {category: [expression_names]}
    """
    
    # 子类必须定义的属性
    NAME: str = ""
    DESCRIPTION: str = ""
    EXPRESSIONS: Dict[str, str] = {}
    CATEGORIES: Dict[str, List[str]] = {}
    
    @classmethod
    def get_all_expressions(cls) -> Dict[str, str]:
        """
        获取所有表达式
        
        Returns:
            Dict[str, str]: 表达式名称到表达式字符串的映射
        """
        return cls.EXPRESSIONS.copy()
    
    @classmethod
    def get_expression_names(cls) -> List[str]:
        """
        获取所有表达式名称列表
        
        Returns:
            List[str]: 表达式名称列表
        """
        return list(cls.EXPRESSIONS.keys())
    
    @classmethod
    def get_expression(cls, name: str) -> Optional[str]:
        """
        获取指定名称的表达式
        
        Args:
            name: 表达式名称
            
        Returns:
            Optional[str]: 表达式字符串，不存在时返回None
        """
        return cls.EXPRESSIONS.get(name)
    
    @classmethod
    def get_categories(cls) -> Dict[str, List[str]]:
        """
        获取所有分类
        
        Returns:
            Dict[str, List[str]]: 分类名称到表达式名称列表的映射
        """
        return cls.CATEGORIES.copy()
    
    @classmethod
    def get_category_names(cls) -> List[str]:
        """
        获取所有分类名称
        
        Returns:
            List[str]: 分类名称列表
        """
        return list(cls.CATEGORIES.keys())
    
    @classmethod
    def get_expressions_by_category(cls, category: str) -> Dict[str, str]:
        """
        根据分类获取表达式
        
        Args:
            category: 分类名称
            
        Returns:
            Dict[str, str]: 该分类下的表达式映射
        """
        if category not in cls.CATEGORIES:
            GLOG.WARN(f"Category '{category}' not found in {cls.NAME}")
            return {}
        
        expression_names = cls.CATEGORIES[category]
        return {name: cls.EXPRESSIONS[name] for name in expression_names 
                if name in cls.EXPRESSIONS}
    
    @classmethod
    def search_expressions(cls, pattern: str) -> Dict[str, str]:
        """
        按模式搜索表达式
        
        Args:
            pattern: 搜索模式（支持正则表达式）
            
        Returns:
            Dict[str, str]: 匹配的表达式映射
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            return {name: expr for name, expr in cls.EXPRESSIONS.items()
                    if regex.search(name) or regex.search(expr)}
        except re.error as e:
            GLOG.ERROR(f"Invalid regex pattern '{pattern}': {e}")
            return {}
    
    @classmethod
    def filter_expressions(cls, names: List[str]) -> Dict[str, str]:
        """
        按名称列表过滤表达式
        
        Args:
            names: 表达式名称列表
            
        Returns:
            Dict[str, str]: 过滤后的表达式映射
        """
        return {name: cls.EXPRESSIONS[name] for name in names 
                if name in cls.EXPRESSIONS}
    
    @classmethod
    def validate_expressions(cls) -> Dict[str, bool]:
        """
        验证所有表达式的基本语法
        
        Returns:
            Dict[str, bool]: 表达式名称到验证结果的映射
        """
        results = {}
        
        for name, expression in cls.EXPRESSIONS.items():
            # 基本语法验证
            try:
                # 检查括号匹配
                if expression.count('(') != expression.count(')'):
                    results[name] = False
                    continue
                
                # 检查是否包含基本字段引用
                if not any(field in expression for field in ['$close', '$open', '$high', '$low', '$volume']):
                    # 允许不含字段引用的表达式（可能是复合表达式）
                    pass
                
                # 基本字符检查
                if not expression or expression.isspace():
                    results[name] = False
                    continue
                
                results[name] = True
                
            except Exception as e:
                GLOG.DEBUG(f"Validation error for expression '{name}': {e}")
                results[name] = False
        
        return results
    
    @classmethod
    def get_statistics(cls) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict[str, Any]: 包含各种统计数据的字典
        """
        total_expressions = len(cls.EXPRESSIONS)
        valid_expressions = sum(cls.validate_expressions().values())
        
        category_stats = {category: len(names) 
                         for category, names in cls.CATEGORIES.items()}
        
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "total_expressions": total_expressions,
            "valid_expressions": valid_expressions,
            "invalid_expressions": total_expressions - valid_expressions,
            "categories": len(cls.CATEGORIES),
            "category_distribution": category_stats,
        }
    
    @classmethod
    def get_complexity_stats(cls) -> Dict[str, int]:
        """
        获取表达式复杂度统计
        
        Returns:
            Dict[str, int]: 复杂度统计数据
        """
        complexities = []
        
        for expression in cls.EXPRESSIONS.values():
            # 简单复杂度计算：函数调用次数 + 嵌套层数
            function_count = len(re.findall(r'[A-Z][a-z]*\(', expression))
            nesting_depth = max(0, expression.count('('))
            complexity = function_count + nesting_depth
            complexities.append(complexity)
        
        if not complexities:
            return {"min": 0, "max": 0, "avg": 0}
        
        return {
            "min": min(complexities),
            "max": max(complexities),
            "avg": sum(complexities) // len(complexities),
            "total": sum(complexities)
        }
    
    @classmethod
    def get_info(cls) -> Dict[str, Any]:
        """
        获取完整的定义信息
        
        Returns:
            Dict[str, Any]: 包含所有元数据的字典
        """
        return {
            "name": cls.NAME,
            "description": cls.DESCRIPTION,
            "statistics": cls.get_statistics(),
            "complexity": cls.get_complexity_stats(),
            "categories": cls.get_category_names(),
            "sample_expressions": dict(list(cls.EXPRESSIONS.items())[:5])  # 显示前5个作为示例
        }
    
    @classmethod
    def get_expression_details(cls, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定表达式的详细信息
        
        Args:
            name: 表达式名称
            
        Returns:
            Optional[Dict[str, Any]]: 表达式详细信息，不存在时返回None
        """
        if name not in cls.EXPRESSIONS:
            return None
        
        expression = cls.EXPRESSIONS[name]
        
        # 查找该表达式属于哪些分类
        categories = [cat for cat, names in cls.CATEGORIES.items() if name in names]
        
        # 计算复杂度
        function_count = len(re.findall(r'[A-Z][a-z]*\(', expression))
        nesting_depth = expression.count('(')
        
        return {
            "name": name,
            "expression": expression,
            "categories": categories,
            "complexity": {
                "functions": function_count,
                "nesting": nesting_depth,
                "total": function_count + nesting_depth
            },
            "length": len(expression),
            "valid": cls.validate_expressions().get(name, False)
        }